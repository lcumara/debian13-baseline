#!/usr/bin/env python3
"""Sellado técnico de identidad para el piloto manual. No certifica CIS ni limpia todos los secretos."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import baseline as core

DROP = Path('/etc/systemd/system/sshd-keygen.service.d/90-baseline-template.conf')
KEYGEN = '''[Unit]
# Generate only missing keys on every boot, without forcing systemd first-boot presets.
ConditionFirstBoot=
ConditionPathIsReadWrite=/etc/ssh
ConditionPathIsSymbolicLink=!/etc/ssh
'''


def secret_candidates(homes):
    found = []
    for home in homes:
        for name in ('.git-credentials', '.netrc', '.aws/credentials', '.docker/config.json',
                     '.config/gh/hosts.yml', '.config/git/credentials', '.ssh/authorized_keys'):
            p = home / name
            if p.exists() or p.is_symlink():
                found.append(str(p))
        ssh = home / '.ssh'
        if ssh.exists():
            found.extend(str(p) for p in ssh.glob('id_*') if not p.name.endswith('.pub'))
    return found


def preflight():
    import pwd
    core.environment()
    cmdline = Path('/proc/cmdline').read_text()
    if any(x in cmdline for x in ('systemd.machine_id=', 'systemd.condition_first_boot=', 'container_uuid=')):
        raise ValueError('Identidad/primer arranque impuesto en kernel; revisar antes de sellar')
    unit = core.run(['systemctl', 'cat', 'sshd-keygen.service'])
    if 'ssh-keygen -A' not in unit:
        raise ValueError('No se reconoce el generador nativo de llaves')
    if 'sshd-keygen.service' not in core.run(['systemctl', 'show', 'ssh.service', '-p', 'Wants', '--value']):
        raise ValueError('SSH no solicita sshd-keygen.service')
    if 'sshd-keygen.service' not in core.run(['systemctl', 'show', 'ssh.service', '-p', 'After', '--value']):
        raise ValueError('SSH no espera a sshd-keygen.service')
    for p in (Path('/etc/machine-id'), Path('/etc/ssh')):
        if p.is_symlink():
            raise ValueError('No se modifica una identidad/ruta enlazada: ' + str(p))
    if core.run(['findmnt', '-n', '-o', 'TARGET', '-T', '/etc/machine-id']).strip() == '/etc/machine-id':
        raise ValueError('machine-id es un montaje: completar arranque antes de sellar')
    for ref, data, field in [('ultima-general', 'general.json', 'ssh'),
                              ('ultimo-complemento', 'general.json', 'estado'),
                              ('ultimo-firewall', 'state.json', 'estado')]:
        name = (core.STATE / ref).read_text().strip()
        if '/' in name or '\\' in name or name.startswith('.'):
            raise ValueError('Referencia de estado inválida')
        state = json.loads((core.STATE / name / data).read_text())
        if state.get(field) not in ('CONFIRMADO', 'CONFIRMADO_POR_OPERADOR'):
            raise ValueError('Falta confirmación de ' + ref)
    core.run(['systemctl', 'is-active', 'baseline-firewall.service'])
    core.run(['systemctl', 'is-enabled', 'baseline-firewall.service'])
    core.run(['sshd', '-t'])
    core.run(['visudo', '-c'])
    packages = core.run(['dpkg-query', '-W', '-f=${binary:Package} ${db:Status-Status}\n'])
    installed = [line for line in packages.splitlines() if line.endswith(' installed')]
    if any(any(term in line.lower() for term in ('wazuh', 'zabbix', 'forti', 'gdata', 'g-data', 'cloud-init')) for line in installed):
        raise ValueError('Hay agentes o cloud-init: requieren su preparación específica antes de sellar')
    for name in ('/var/ossec/etc/client.keys', '/etc/zabbix/zabbix_agent2.psk', '/var/lib/aide-baseline/base.db'):
        if Path(name).exists():
            raise ValueError('Identidad o referencia que debe revisarse: ' + name)
    homes = {Path(u.pw_dir) for u in pwd.getpwall() if u.pw_uid == 0 or 1000 <= u.pw_uid < 65534}
    candidates = secret_candidates(homes)
    if candidates:
        raise ValueError('Revisar credenciales antes del sellado (solo rutas): ' + ', '.join(candidates))
    print('Precomprobación de identidad aprobada; no detecta todos los secretos posibles.')


def seal():
    preflight()
    with core.locked():
        if DROP.exists() and DROP.read_text() != KEYGEN:
            raise ValueError('Existe un drop-in distinto; no sobrescribir')
        DROP.parent.mkdir(parents=True, exist_ok=True)
        core.atomic_write(DROP, KEYGEN.encode(), 0o644)
        core.run(['systemctl', 'daemon-reload'])
        core.run(['systemctl', 'enable', 'sshd-keygen.service'])
        # Remaining unrelated drop-ins must not retain first-boot restriction.
        conditions = core.run(['systemctl', 'show', 'sshd-keygen.service', '-p', 'Conditions', '--value'])
        if 'ConditionFirstBoot' in conditions:
            raise ValueError('Persiste una condición FirstBoot; no se borran identidades')
        core.run(['apt-get', 'clean'])
        # Stop first, since stopping this service writes the seed back to disk.
        core.run(['systemctl', 'stop', 'systemd-random-seed.service'])
        Path('/var/lib/systemd/random-seed').unlink(missing_ok=True)
        dbus = Path('/var/lib/dbus/machine-id')
        dbus.parent.mkdir(parents=True, exist_ok=True)
        dbus.unlink(missing_ok=True)
        dbus.symlink_to('/etc/machine-id')
        for pattern in ('ssh_host_*_key', 'ssh_host_*_key.pub'):
            for p in Path('/etc/ssh').glob(pattern):
                p.unlink()
        core.atomic_write(Path('/etc/machine-id'), b'', 0o444)
        core.atomic_write(core.STATE / 'sellado-identidad.json',
                          json.dumps({'estado': 'IDENTIDAD_PREPARADA', 'cis_completo': False,
                                      'limpieza_total_secretos': False}).encode())
        core.run(['sync'])
        print('Identidad preparada. Apagando: no volver a arrancar esta base; convertirla en plantilla.', flush=True)
        core.run(['systemctl', 'poweroff'])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--comprobar', action='store_true')
    g.add_argument('--sellar-y-apagar', action='store_true')
    a = p.parse_args(argv)
    try:
        if a.sellar_y_apagar:
            seal()
        elif a.comprobar:
            preflight()
        else:
            print('PLAN: preparar generación SSH, limpiar identidad máquina/DBus/llaves/semilla y caché APT, apagar.')
            print('No borra usuarios, home, historiales, registros ni ejecutores del firewall. Leer capítulo 14.')
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('DETENIDO:', exc, file=sys.stderr)
        print('Si ya se inició el sellado, no reiniciar ni volver a producción; revisar el error desde la sesión/consola.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
