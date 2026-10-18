#!/usr/bin/env python3
"""Firewall de entrada para plantilla SSH/22; no gestiona forwarding Docker."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import baseline as core

TABLE = 'baseline_host'
SERVICE = 'baseline-firewall.service'
UNIT = Path('/etc/systemd/system') / SERVICE
RULES = '''table inet baseline_host {
    chain input {
        type filter hook input priority 0; policy drop;
        iifname != "lo" ip saddr 127.0.0.0/8 counter drop
        iifname != "lo" ip6 saddr ::1 counter drop
        iifname "lo" counter accept
        ct state invalid counter drop
        ct state established,related counter accept
        meta l4proto icmp counter accept
        meta l4proto ipv6-icmp counter accept
        udp sport 67 udp dport 68 counter accept
        udp sport 547 udp dport 546 counter accept
        tcp dport 22 ct state new counter accept
        counter drop
    }
}
'''


def save(folder, state):
    core.atomic_write(folder / 'state.json', json.dumps(state).encode())


def latest():
    name = (core.STATE / 'ultimo-firewall').read_text().strip()
    if not re.fullmatch(r'firewall-[a-z0-9_]+', name):
        raise ValueError('Registro inválido')
    folder = core.STATE / name
    return folder, json.loads((folder / 'state.json').read_text())


def exists():
    # Listing the whole ruleset must succeed; do not confuse permission errors
    # or a broken nft invocation with an absent table.
    return f'table inet {TABLE}' in core.run(['nft', 'list', 'tables']).splitlines()


def transaction(present):
    return (f'delete table inet {TABLE}\n' if present else '') + RULES


def install_rules(folder):
    batch = folder / 'load.nft'
    core.atomic_write(batch, transaction(exists()).encode())
    core.run(['nft', '-c', '-f', str(batch)])
    core.run(['nft', '-f', str(batch)])


def restore(folder, state):
    # The table was absent before apply. Never flush other owners' tables.
    if exists():
        core.run(['nft', 'delete', 'table', 'inet', TABLE])
    core.run(['systemctl', 'disable', '--now', SERVICE])
    state['estado'] = 'REVERTIDO'
    save(folder, state)


def apply():
    ports = re.findall(r'(?m)^port (\d+)$', core.run(['sshd', '-T']))
    if set(ports) != {'22'}:
        raise ValueError('Este perfil requiere SSH en 22; no se aplica a otro puerto')
    with core.locked():
        if UNIT.exists() or UNIT.is_symlink() or exists():
            raise ValueError('Ya existe el servicio o tabla baseline_host; verificar antes de repetir')
        folder = Path(tempfile.mkdtemp(prefix='firewall-', dir=core.STATE))
        state = {'estado': 'PENDIENTE', 'timer': 'rollback-' + folder.name}
        for source in (Path(__file__), Path(core.__file__)):
            core.atomic_write(folder / source.name, source.read_bytes())
        save(folder, state)
        core.atomic_write(core.STATE / 'ultimo-firewall', (folder.name + '\n').encode())
        # Validate syntax before activating or scheduling any changes.
        core.atomic_write(folder / 'check.nft', RULES.encode())
        core.run(['nft', '-c', '-f', str(folder / 'check.nft')])
        unit = f'''[Unit]
Description=Firewall baseline de entrada IPv4/IPv6
DefaultDependencies=no
After=local-fs.target systemd-modules-load.service
Before=network-pre.target fail2ban.service shutdown.target
Conflicts=shutdown.target
Wants=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 {folder}/firewall_base.py --cargar
ExecReload=/usr/bin/python3 {folder}/firewall_base.py --cargar

[Install]
WantedBy=multi-user.target
'''
        core.atomic_write(UNIT, unit.encode(), 0o644)
        core.run(['systemctl', 'daemon-reload'])
        core.run(['systemd-run', '--unit=' + state['timer'], '--on-active=20m',
                  '/usr/bin/python3', str(folder / 'firewall_base.py'), '--vencer'])
        try:
            # Persistence is enabled only after a successful second SSH session.
            core.run(['systemctl', 'start', SERVICE])
        except Exception:
            restore(folder, state)
            raise
    print('Firewall aplicado. Abre otra conexión SSH y confirma antes de 20 minutos.')
    print('sudo python3 bin/firewall_base.py --confirmar')
    print('Sin confirmación se retira solamente la tabla baseline_host. No reinicies aún.')


def verify():
    folder, state = latest()
    checks = {
        'acceso_confirmado': state['estado'] == 'CONFIRMADO',
        'servicio_activo': core.run(['systemctl', 'is-active', SERVICE]).strip() == 'active',
        'persistencia_habilitada': core.run(['systemctl', 'is-enabled', SERVICE]).strip() == 'enabled',
    }
    # Text checks describe this narrow profile, not a packet reachability test.
    rules = core.run(['nft', 'list', 'table', 'inet', TABLE])
    checks['entrada_drop'] = 'hook input' in rules and 'policy drop' in rules
    checks['ssh_22'] = 'tcp dport 22' in rules
    checks['establecidas'] = 'ct state established,related' in rules
    checks['ipv6_icmp'] = 'ipv6-icmp' in rules
    for name, ok in checks.items():
        print(('OK       ' if ok else 'REVISAR  ') + name)
    print('Entrada del host solamente; salida permitida y forwarding Docker pendiente por función.')
    return 0 if all(checks.values()) else 2


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    for flag in ('aplicar', 'confirmar', 'restaurar', 'verificar', 'cargar', 'vencer'):
        g.add_argument('--' + flag, action='store_true')
    a = p.parse_args(argv)
    if not any(vars(a).values()):
        print('PLAN: entrada deny por defecto, SSH/22, ICMP/ICMPv6, DHCP, loopback y conexiones establecidas. Sin cambios.')
        return 0
    try:
        core.environment()
        if a.aplicar:
            apply()
        elif a.verificar:
            return verify()
        elif a.cargar:
            # Called synchronously by systemd while apply holds the global lock.
            folder, state = latest()
            if state['estado'] not in ('PENDIENTE', 'CONFIRMADO'):
                raise ValueError('El perfil está revertido')
            install_rules(folder)
        else:
            with core.locked():
                folder, state = latest()
                if a.confirmar:
                    if state['estado'] != 'PENDIENTE':
                        raise ValueError('No hay firewall pendiente; pudo revertirse por tiempo')
                    core.run(['systemctl', 'enable', SERVICE])
                    core.run(['systemctl', 'stop', state['timer'] + '.timer'])
                    state['estado'] = 'CONFIRMADO'
                    save(folder, state)
                elif state['estado'] == 'PENDIENTE' or (a.restaurar and state['estado'] == 'CONFIRMADO'):
                    restore(folder, state)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('DETENIDO:', exc, file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
