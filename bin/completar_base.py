#!/usr/bin/env python3
"""Controles adicionales para el piloto Debian 13 con cuentas locales."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import baseline as core
import configurar_base as base

PACKAGES = ('libpam-pwquality', 'libpwquality-tools', 'cracklib-runtime',
            'rsyslog', 'needrestart')
PAM = {
    'common-auth': '''# Administrado por completar_base.py: cuentas locales
auth requisite pam_faillock.so preauth silent
auth [success=1 default=bad] pam_unix.so
auth [default=die] pam_faillock.so authfail
auth sufficient pam_faillock.so authsucc
auth requisite pam_deny.so
auth required pam_permit.so
''',
    'common-account': '''# Administrado por completar_base.py: cuentas locales
account required pam_faillock.so
account [success=1 new_authtok_reqd=done default=ignore] pam_unix.so
account requisite pam_deny.so
account required pam_permit.so
''',
    'common-password': '''# Administrado por completar_base.py: cuentas locales
password requisite pam_pwquality.so retry=3 minlen=14 difok=2 maxrepeat=3 maxsequence=3 dcredit=0 ucredit=0 lcredit=0 ocredit=0 dictcheck=1 usercheck=1 enforcing=1 enforce_for_root
password requisite pam_pwhistory.so remember=24 enforce_for_root use_authtok
password [success=1 default=ignore] pam_unix.so obscure use_authtok yescrypt
password requisite pam_deny.so
password required pam_permit.so
''',
}
# No cambia forwarding, IPv6, rp_filter ni la memoria para bases de datos.
SYSCTL = {
    'fs.suid_dumpable': '0',
    'net.ipv4.conf.all.accept_redirects': '0',
    'net.ipv4.conf.default.accept_redirects': '0',
    'net.ipv4.conf.all.secure_redirects': '0',
    'net.ipv4.conf.default.secure_redirects': '0',
    'net.ipv4.conf.all.send_redirects': '0',
    'net.ipv4.conf.default.send_redirects': '0',
    'net.ipv4.conf.all.accept_source_route': '0',
    'net.ipv4.conf.default.accept_source_route': '0',
    'net.ipv4.icmp_echo_ignore_broadcasts': '1',
    'net.ipv4.icmp_ignore_bogus_error_responses': '1',
    'net.ipv4.tcp_syncookies': '1',
}
FILES = {
    '/etc/security/faillock.conf': 'deny = 5\nfail_interval = 900\nunlock_time = 900\nsilent\n',
    '/etc/security/limits.d/90-baseline-core.conf': '* hard core 0\nroot hard core 0\n',
    '/etc/systemd/coredump.conf.d/90-baseline.conf': '[Coredump]\nStorage=none\nProcessSizeMax=0\n',
    '/etc/rsyslog.d/00-baseline-permissions.conf': '$FileCreateMode 0640\n',
    '/etc/needrestart/conf.d/90-baseline.conf': "$nrconf{restart} = 'l';\n",
    '/etc/sysctl.d/91-baseline-complemento.conf': ''.join(f'{k} = {v}\n' for k, v in SYSCTL.items()),
}


def without_cap(text):
    return ''.join(line for line in text.splitlines(keepends=True)
                   if not re.match(r'^\s*auth\s+optional\s+pam_cap\.so(?:\s|$)', line))


def local_stack(name, text):
    """Only replace stock local PAM stacks; reject external/custom providers."""
    if without_cap(text) == PAM[name]:
        return
    allowed = {
        'common-auth': {'pam_unix.so', 'pam_deny.so', 'pam_permit.so', 'pam_cap.so'},
        'common-account': {'pam_unix.so', 'pam_deny.so', 'pam_permit.so'},
        'common-password': {'pam_unix.so', 'pam_deny.so', 'pam_permit.so', 'pam_pwquality.so'},
    }[name]
    active = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    modules = []
    for line in active:
        found = re.findall(r'\bpam_[\w]+\.so\b', line)
        if len(found) != 1 or found[0] not in allowed or '/' in line or line.startswith('@'):
            raise ValueError(f'{name}: pila personalizada; no se sobrescribe: {line}')
        modules.extend(found)
    if any(modules.count(m) != 1 for m in ('pam_unix.so', 'pam_deny.so', 'pam_permit.so')):
        raise ValueError(f'{name}: pila local no reconocida')
    # Require Debian's usual primary control, not an arbitrary custom jump.
    unix = next(line for line in active if 'pam_unix.so' in line)
    expected = '[success=1 new_authtok_reqd=done default=ignore]' if name == 'common-account' else '[success=1 default=ignore]'
    if expected not in unix:
        raise ValueError(f'{name}: control pam_unix no estándar')


def audit_rules():
    lines = ['# Complemento: amd64; sin inmovilizar reglas durante construcción']
    for arch in ('b64', 'b32'):
        lines.extend([
            f'-a always,exit -F arch={arch} -S sethostname,setdomainname -k red_identidad',
            f'-a always,exit -F arch={arch} -S adjtimex,settimeofday,clock_settime -k cambio_hora',
            f'-a always,exit -F arch={arch} -S init_module,finit_module,delete_module -k modulos_kernel',
        ])
        # Only human sessions; exclude unset auid, keep service activity out.
        for error in ('EACCES', 'EPERM'):
            lines.append(f'-a always,exit -F arch={arch} -S open,openat,creat,truncate,ftruncate -F exit=-{error} -F auid>=1000 -F auid!=unset -k acceso_denegado')
        lines.append(f'-a always,exit -F arch={arch} -S chmod,fchmod,fchmodat,chown,fchown,lchown,fchownat -F auid>=1000 -F auid!=unset -k permisos')
        lines.append(f'-a always,exit -F arch={arch} -S unlink,unlinkat,rename,renameat -F auid>=1000 -F auid!=unset -k eliminaciones')
        if arch == 'b32':
            lines.append('-a always,exit -F arch=b32 -S stime -k cambio_hora')
    for target in ('/etc/localtime', '/etc/hosts', '/etc/issue', '/etc/issue.net', '/var/log/lastlog', '/var/log/wtmp', '/var/log/btmp'):
        if Path(target).exists():
            lines.append(f'-w {target} -p wa -k configuracion_sesiones')
    return '\n'.join(lines) + '\n'


def latest(name=None):
    name = name or (core.STATE / 'ultimo-complemento').read_text().strip()
    if not re.fullmatch(r'complemento-[a-z0-9_]+', name):
        raise ValueError('Registro inválido')
    folder = core.STATE / name
    return folder, json.loads((folder / 'general.json').read_text())


def recover(folder, state):
    base.restore_group(folder, state, 'complemento')
    for key, value in state['sysctl_antes'].items():
        core.run(['sysctl', '-w', f'{key}={value}'])
    core.run(['augenrules', '--load'])
    core.run(['rsyslogd', '-N1'])
    core.run(['systemctl', 'restart', 'rsyslog'])
    state['estado'] = 'REVERTIDO'
    base.state_write(folder, state)


def apply():
    if core.run(['dpkg', '--print-architecture']).strip() != 'amd64':
        raise ValueError('Solo amd64')
    if re.search(r'(?m)^enabled\s+2$', core.run(['auditctl', '-s'])):
        raise ValueError('Auditoría inmutable; no se modifica')
    for name in PAM:
        local_stack(name, Path('/etc/pam.d', name).read_text())
    with core.locked():
        if (core.STATE / 'ultimo-complemento').exists() and latest()[1]['estado'] == 'PENDIENTE':
            raise ValueError('Confirma o restaura la ejecución pendiente')
        folder = Path(tempfile.mkdtemp(prefix='complemento-', dir=core.STATE))
        state = {'estado': 'INICIADO', 'archivos': {}, 'sysctl_antes': {
            k: core.run(['sysctl', '-n', k]).strip() for k in SYSCTL}}
        base.state_write(folder, state)
        # Save PAM BEFORE package maintainer scripts can enable pwquality.
        for name in PAM:
            base.remember(folder, state, Path('/etc/pam.d', name), 'complemento')
        print('Respaldo privado:', folder, flush=True)
        try:
            core.run(['apt-get', 'update'], capture=False)
            core.run(['apt-get', 'install', '--yes', '--no-remove', '--no-install-recommends', *PACKAGES], capture=False)
        except Exception:
            base.restore_group(folder, state, 'complemento')
            raise
        for module in ('pam_pwquality.so', 'pam_pwhistory.so', 'pam_faillock.so'):
            if not any(Path('/usr/lib').glob('*/security/' + module)):
                raise ValueError('Falta módulo ' + module)
        # Preserve optional pam_cap from the original local authentication stack.
        auth = Path('/etc/pam.d/common-auth').read_text()
        # pam_cap is optional in Debian. Keep it before authsucc's early success.
        extra = '\n'.join(line for line in auth.splitlines() if re.match(r'^\s*auth\s+optional\s+pam_cap\.so(?:\s|$)', line))
        content = {**FILES, '/etc/audit/rules.d/52-baseline-complemento.rules': audit_rules()}
        content.update({str(Path('/etc/pam.d', name)): text for name, text in PAM.items()})
        if extra:
            content['/etc/pam.d/common-auth'] = PAM['common-auth'].replace('auth sufficient pam_faillock.so authsucc', extra + '\nauth sufficient pam_faillock.so authsucc')
        # Root-private helper survives terminal disconnect and cannot be edited via Git.
        for module in (Path(__file__), Path(base.__file__), Path(core.__file__)):
            core.atomic_write(folder / module.name, module.read_bytes())
        state['timer'] = 'baseline-' + folder.name
        state['estado'] = 'PENDIENTE'
        base.state_write(folder, state)
        core.atomic_write(core.STATE / 'ultimo-complemento', (folder.name + '\n').encode())
        core.run(['systemd-run', '--unit=' + state['timer'], '--on-active=20m',
                  '/usr/bin/python3', str(folder / Path(__file__).name), '--restaurar', folder.name])
        try:
            for path, text in content.items():
                base.put(folder, state, path, text, 'complemento', 0o644)
            core.run(['rsyslogd', '-N1'])
            core.run(['systemctl', 'enable', '--now', 'rsyslog'])
            core.run(['systemctl', 'restart', 'rsyslog'])
            core.run(['sysctl', '-p', '/etc/sysctl.d/91-baseline-complemento.conf'])
            core.run(['augenrules', '--load'])
            core.run(['sshd', '-t'])
            core.run(['visudo', '-c'])
        except Exception:
            recover(folder, state)
            core.run(['systemctl', 'stop', state['timer'] + '.timer'])
            raise
    print('Aplicado. Abre otra sesión SSH y prueba sudo antes de 20 minutos.')
    print('En la NUEVA sesión: sudo python3 bin/completar_base.py --confirmar')
    print('Sin confirmación se restauran los archivos y sysctl. No reinicies todavía.')


def verify():
    checks = []
    def check(name, fn):
        try:
            ok = bool(fn())
        except (OSError, ValueError, subprocess.SubprocessError):
            ok = False
        checks.append(ok)
        print(('OK       ' if ok else 'REVISAR  ') + name)
    for package in PACKAGES:
        check(package, lambda p=package: core.run(['dpkg-query', '-W', '-f=${Status}', p]).strip() == 'install ok installed')
    for name, text in PAM.items():
        check(name, lambda n=name, t=text: without_cap(Path('/etc/pam.d', n).read_text()) == t)
    for path, text in FILES.items():
        check(path, lambda p=path, t=text: Path(p).read_text() == t)
    for key, value in SYSCTL.items():
        check(key, lambda k=key, v=value: core.run(['sysctl', '-n', k]).strip() == v)
    check('rsyslog_activo', lambda: core.run(['systemctl', 'is-active', 'rsyslog']).strip() == 'active')
    check('rsyslog_sintaxis', lambda: core.run(['rsyslogd', '-N1']) is not None)
    check('audit_reglas_adicionales', lambda: all(key in core.run(['auditctl', '-l']) for key in ('cambio_hora', 'modulos_kernel', 'acceso_denegado', 'permisos', 'eliminaciones')))
    check('audit_sin_perdidas', lambda: bool(re.search(r'(?m)^lost\s+0$', core.run(['auditctl', '-s']))))
    check('acceso_confirmado', lambda: latest()[1]['estado'] == 'CONFIRMADO')
    print('PAM: comprobación de archivos; falta probar cambio/rechazo de contraseña con cuenta de prueba.')
    print('No certifica CIS. Consulta alcance y pruebas en docs/10-completar-base.md.')
    return 0 if all(checks) else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--aplicar', action='store_true')
    mode.add_argument('--verificar', action='store_true')
    mode.add_argument('--confirmar', action='store_true')
    mode.add_argument('--restaurar', metavar='REGISTRO')
    args = parser.parse_args(argv)
    if not any(vars(args).values()):
        print('PLAN: PAM local, calidad/historial/bloqueo, rsyslog, needrestart, coredumps, red y auditoría. Sin cambios.')
        return 0
    try:
        core.environment()
        if args.aplicar:
            apply()
        elif args.verificar:
            return verify()
        else:
            with core.locked():
                folder, state = latest(args.restaurar)
                if state['estado'] != 'PENDIENTE':
                    if args.confirmar:
                        raise ValueError('No hay cambio pendiente; pudo revertirse por tiempo')
                    return 0
                if args.confirmar:
                    core.run(['systemctl', 'stop', state['timer'] + '.timer'])
                    state['estado'] = 'CONFIRMADO'
                    base.state_write(folder, state)
                else:
                    recover(folder, state)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('DETENIDO:', exc, file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
