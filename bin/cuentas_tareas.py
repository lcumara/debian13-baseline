#!/usr/bin/env python3
"""Política para cuentas nuevas y permisos cron, sin caducar cuentas existentes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import baseline as core
import configurar_base as base

DEFAULTS = {'PASS_MAX_DAYS': '3650', 'PASS_MIN_DAYS': '1', 'PASS_WARN_AGE': '365',
            'UMASK': '027', 'ENCRYPT_METHOD': 'YESCRYPT'}
CRON = {'/etc/crontab': 0o600, **{f'/etc/cron.{part}': 0o700
        for part in ('d', 'hourly', 'daily', 'weekly', 'monthly')}}
PROFILE = '# Permisos por defecto de shells de login; no cambia archivos existentes.\numask 027\n'


def set_defaults(text):
    for key, value in DEFAULTS.items():
        pattern = rf'(?m)^[ \t]*{key}[ \t]+[^\n]*$'
        if len(re.findall(pattern, text)) > 1:
            raise ValueError(f'Definición duplicada: {key}')
        if re.search(pattern, text):
            text = re.sub(pattern, f'{key} {value}', text)
        else:
            text += f'\n{key} {value}\n'
    return text


def load():
    name = (core.STATE / 'ultima-cuentas-tareas').read_text().strip()
    if not re.fullmatch(r'cuentas-[a-z0-9_]+', name):
        raise ValueError('Registro inválido')
    folder = core.STATE / name
    return folder, json.loads((folder / 'general.json').read_text())


def restore(folder, state):
    base.restore_group(folder, state, 'cuentas')
    for path, mode in state['modos'].items():
        target = Path(path)
        if target.is_symlink():
            raise ValueError('No se restaura un enlace: ' + path)
        target.chmod(mode)
    state['estado'] = 'REVERTIDO'
    base.state_write(folder, state)


def apply():
    # Preflight before any mutation; no recursive permission changes.
    for path in CRON:
        p = Path(path)
        s = p.lstat()
        if p.is_symlink() or s.st_uid != 0 or s.st_gid != 0:
            raise ValueError('Revisar propietario o enlace: ' + path)
    text = set_defaults(Path('/etc/login.defs').read_text())
    with core.locked():
        folder = Path(tempfile.mkdtemp(prefix='cuentas-', dir=core.STATE))
        state = {'estado': 'INICIADO', 'archivos': {}, 'modos': {
            path: Path(path).stat().st_mode & 0o7777 for path in CRON}}
        base.state_write(folder, state)
        core.atomic_write(core.STATE / 'ultima-cuentas-tareas', (folder.name + '\n').encode())
        try:
            base.remember(folder, state, '/etc/default/useradd', 'cuentas')
            base.put(folder, state, '/etc/login.defs', text, 'cuentas')
            base.put(folder, state, '/etc/profile.d/90-baseline-umask.sh', PROFILE, 'cuentas')
            core.run(['useradd', '-D', '-f', '-1'])
            base.put(folder, state, '/etc/cron.daily/baseline-password-review',
                     Path(__file__).with_name('revisar_edades.py').read_text(encoding='utf-8'),
                     'cuentas', 0o700)
            for path, mode in CRON.items():
                Path(path).chmod(mode)
            state['estado'] = 'APLICADO'
            base.state_write(folder, state)
        except Exception:
            restore(folder, state)
            raise
        print('Aplicado; respaldo privado:', folder)
        print('Cuentas existentes: sin cambios. Caducidad/inactividad se revisan por cuenta.')


def verify():
    results = []
    def check(label, fn):
        try:
            ok = bool(fn())
        except (OSError, ValueError, subprocess.SubprocessError):
            ok = False
        results.append(ok)
        print(('OK       ' if ok else 'REVISAR  ') + label)
    text = Path('/etc/login.defs').read_text()
    for key, value in DEFAULTS.items():
        check(key + '_cuentas_nuevas', lambda k=key, v=value: re.findall(
            rf'(?m)^[ \t]*{k}[ \t]+(\S+)', text) == [v])
    check('inactividad_cuentas_nuevas', lambda: 'INACTIVE=-1' in core.run(['useradd', '-D']).splitlines())
    check('revision_cinco_anos_instalada', lambda: Path('/etc/cron.daily/baseline-password-review').read_text(encoding='utf-8')
          == Path(__file__).with_name('revisar_edades.py').read_text(encoding='utf-8')
          and Path('/etc/cron.daily/baseline-password-review').stat().st_mode & 0o7777 == 0o700)
    check('umask_shell_configurada', lambda: Path('/etc/profile.d/90-baseline-umask.sh').read_text() == PROFILE)
    for path, mode in CRON.items():
        check(path, lambda p=path, m=mode: not Path(p).is_symlink()
              and Path(p).stat().st_mode & 0o7777 == m
              and Path(p).stat().st_uid == Path(p).stat().st_gid == 0)
    check('cron_activo', lambda: core.run(['systemctl', 'is-active', 'cron']).strip() == 'active')
    print('Verificación acotada; no certifica CIS ni evalúa caducidad de cuentas existentes.')
    return 0 if all(results) else 2


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    for name in ('aplicar', 'verificar', 'restaurar'):
        g.add_argument('--' + name, action='store_true')
    a = p.parse_args(argv)
    if not any(vars(a).values()):
        print('PLAN: cuentas nuevas 3650/1/365 días, sin bloqueo adicional por inactividad; revisión informativa a 1825 días, umask 027, permisos cron. Sin cambios.')
        return 0
    try:
        core.environment()
        if a.aplicar:
            apply()
        elif a.verificar:
            return verify()
        else:
            with core.locked():
                restore(*load())
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('DETENIDO:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
