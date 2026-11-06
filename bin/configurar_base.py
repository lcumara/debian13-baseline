#!/usr/bin/env python3
"""Perfil general de plantilla, con contraseña SSH y sin depender de snapshots."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import baseline as core

PACKAGES = (
    "ca-certificates", "sudo", "qemu-guest-agent", "apparmor", "apparmor-utils",
    "auditd", "audispd-plugins", "aide", "unattended-upgrades",
    "debian-security-support", "fail2ban", "python3-systemd", "nftables", "ufw", "logrotate",
)
SSH_MAIN = Path("/etc/ssh/sshd_config")
SSH_DROP = Path("/etc/ssh/sshd_config.d/00-baseline-password.conf")
SSH_EXPECTED = {
    "permitrootlogin": "no", "passwordauthentication": "yes",
    "kbdinteractiveauthentication": "no", "permitemptypasswords": "no",
    "usepam": "yes", "disableforwarding": "yes", "x11forwarding": "no",
    "maxauthtries": "3", "logingracetime": "60", "loglevel": "VERBOSE",
}
SSH_CONFIG = """# Perfil con contraseña solicitado para esta plantilla.
PermitRootLogin no
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
UsePAM yes
DisableForwarding yes
X11Forwarding no
PermitUserEnvironment no
MaxAuthTries 3
LoginGraceTime 60
LogLevel VERBOSE
"""
AUDIT_OPTIONS = {
    "max_log_file": "32", "num_logs": "10", "max_log_file_action": "ROTATE",
    "space_left": "4096", "space_left_action": "SYSLOG",
    "admin_space_left": "2048", "admin_space_left_action": "SUSPEND",
    "disk_full_action": "SUSPEND", "disk_error_action": "SUSPEND",
}
APT_CONFIG = '''// Seguridad Debian 13; no reiniciar ni eliminar dependencias automáticamente.
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
#clear Unattended-Upgrade::Origins-Pattern;
#clear Unattended-Upgrade::Allowed-Origins;
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=trixie-security,label=Debian-Security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "false";
Unattended-Upgrade::Remove-New-Unused-Dependencies "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "false";
'''
AIDE_CONFIG = """# Perfil propio; no depende de aideinit/aide-common.
database_in=file:/var/lib/aide-baseline/base.db
database_out=file:/var/lib/aide-baseline/base.db.new
report_url=stdout
report_level=summary
num_workers=1
BASE = p+i+n+u+g+s+m+c+sha256
/etc BASE
/usr/bin BASE
/usr/sbin BASE
/usr/lib BASE
/boot BASE
"""
AIDE_SERVICE = """[Unit]
Description=Comprobar integridad de archivos del sistema (baseline)
ConditionPathExists=/var/lib/aide-baseline/base.db

[Service]
Type=oneshot
ExecStart=/usr/bin/aide --config=/etc/aide/baseline.conf --check
Nice=19
IOSchedulingClass=idle
UMask=0077
"""
AIDE_TIMER = """[Unit]
Description=Comprobacion diaria AIDE baseline

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
"""
JOURNAL_CONFIG = """[Journal]
Storage=persistent
Compress=yes
SystemMaxUse=512M
SystemKeepFree=1G
RuntimeMaxUse=64M
MaxRetentionSec=30day
"""
SUDO_CONFIG = 'Defaults use_pty\nDefaults logfile="/var/log/sudo-baseline.log"\n'
SUDO_ROTATE = """/var/log/sudo-baseline.log {
    daily
    maxsize 10M
    rotate 14
    missingok
    notifempty
    compress
    delaycompress
    create 0600 root root
}
"""


def command(argv, capture=True):
    return core.run(argv, capture=capture)


def state_write(folder, state):
    core.atomic_write(folder / "general.json", json.dumps(state, indent=2).encode())


def read_latest():
    name = (core.STATE / "ultima-general").read_text().strip()
    if not re.fullmatch(r"general-[a-z0-9_]+", name):
        raise ValueError("Referencia de ejecución inválida.")
    folder = core.STATE / name
    if folder.is_symlink():
        raise ValueError("El registro no puede ser un enlace.")
    return folder, json.loads((folder / "general.json").read_text())


def remember(folder, state, path, group):
    path = Path(path)
    if str(path) in state["archivos"]:
        return
    if path.is_symlink():
        raise ValueError(f"Revisar enlace antes de modificar: {path}")
    entry = {"existia": path.exists(), "grupo": group}
    if path.exists():
        stat = path.stat()
        if not path.is_file() or stat.st_uid != 0 or stat.st_gid != 0:
            raise ValueError(f"Se requiere un archivo root:root: {path}")
        entry["modo"] = stat.st_mode & 0o777
        entry["copia"] = f"archivo-{len(state['archivos'])}.bak"
        core.atomic_write(folder / entry["copia"], path.read_bytes())
    state["archivos"][str(path)] = entry
    state_write(folder, state)


def put(folder, state, path, value, group, mode=0o644):
    path = Path(path)
    remember(folder, state, path, group)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    core.atomic_write(path, value.encode(), mode)


def restore_group(folder, state, group):
    errors = []
    for path, entry in state["archivos"].items():
        if entry["grupo"] != group:
            continue
        try:
            target = Path(path)
            if entry["existia"]:
                core.atomic_write(target, (folder / entry["copia"]).read_bytes(), entry["modo"])
            else:
                target.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("Reversión incompleta: " + "; ".join(errors))


def replace_options(text, values):
    for key, value in values.items():
        pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
        if len(re.findall(pattern, text)) > 1:
            raise ValueError(f"Parámetro duplicado: {key}")
        if re.search(pattern, text):
            text = re.sub(pattern, f"{key} = {value}", text)
        else:
            text += f"\n{key} = {value}\n"
    return text


def connection_context(user, connection):
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_.-]*\$?", user) or user == "root":
        raise ValueError("Usar el usuario administrativo no root de la sesión SSH.")
    fields = connection.split()
    if len(fields) != 4:
        raise ValueError('Falta --conexion "$SSH_CONNECTION", desde la sesión SSH original.')
    for i in (0, 2):
        ipaddress.ip_address(fields[i])
    for i in (1, 3):
        if not fields[i].isdigit() or not 1 <= int(fields[i]) <= 65535:
            raise ValueError("Puerto de conexión inválido.")
    return f"user={user},host={fields[0]},addr={fields[0]},laddr={fields[2]},lport={fields[3]}"


def ssh_values(context):
    text = command(["sshd", "-T", "-C", context])
    return dict(line.split(None, 1) for line in text.splitlines() if " " in line)


def check_ssh(context):
    values = ssh_values(context)
    wrong = [key for key, val in SSH_EXPECTED.items() if values.get(key, "").lower() != val.lower()]
    if wrong:
        raise ValueError("SSH efectivo no coincide: " + ", ".join(wrong))
    if values.get("authenticationmethods") != "any":
        raise ValueError("Revisar AuthenticationMethods antes de continuar por contraseña.")


def rules_for(targets):
    lines = ["# Reglas administradas por configurar_base.py; no inmovilizar todavía."]
    for path, kind, key in targets:
        if not Path(path).exists():
            raise ValueError(f"No existe la ruta requerida para auditar: {path}")
        for arch in ("b64", "b32"):
            lines.append(f"-a always,exit -F arch={arch} -F {kind}={path} -F perm=wa -k {key}")
    return "\n".join(lines) + "\n"


def configure_audit(folder, state):
    status = command(["auditctl", "-s"])
    if re.search(r"(?m)^enabled\s+2\s*$", status):
        raise ValueError("Auditoría inmovilizada. No se alteran archivos ni se fuerza reinicio.")
    identity = rules_for([(f"/etc/{name}", "path", "identidad") for name in ("passwd", "group", "shadow", "gshadow")])
    general = rules_for([
        ("/etc/sudoers", "path", "privilegios"), ("/etc/sudoers.d", "dir", "privilegios"),
        ("/etc/ssh", "dir", "acceso_ssh"), ("/etc/pam.d", "dir", "autenticacion"),
        ("/etc/security", "dir", "autenticacion"), ("/etc/audit", "dir", "config_audit"),
        ("/etc/sysctl.d", "dir", "config_kernel"),
        ("/etc/systemd/system", "dir", "servicios"),
    ])
    try:
        put(folder, state, "/etc/audit/rules.d/50-baseline-identidad.rules", identity, "audit", 0o600)
        put(folder, state, "/etc/audit/rules.d/51-baseline-general.rules", general, "audit", 0o600)
        config = replace_options(Path("/etc/audit/auditd.conf").read_text(), AUDIT_OPTIONS)
        put(folder, state, "/etc/audit/auditd.conf", config, "audit", 0o640)
        command(["augenrules", "--load"])
        command(["auditctl", "--signal", "reload"])
    except Exception:
        restore_group(folder, state, "audit")
        command(["augenrules", "--load"])
        command(["auditctl", "--signal", "reload"])
        raise


def configure_fail2ban(folder, state, ports):
    config = f"""[sshd]
enabled = true
backend = systemd
port = {','.join(ports)}
filter = sshd
maxretry = 5
findtime = 10m
bantime = 10m
usedns = no
banaction = ufw
"""
    try:
        put(folder, state, "/etc/fail2ban/jail.d/90-baseline-sshd.local", config, "fail2ban")
        command(["fail2ban-client", "-t"])
        command(["systemctl", "enable", "fail2ban"])
        command(["systemctl", "restart", "fail2ban"])
    except Exception:
        restore_group(folder, state, "fail2ban")
        command(["systemctl", "restart", "fail2ban"])
        raise


def configure_ssh(folder, state, context):
    remember(folder, state, SSH_MAIN, "ssh")
    remember(folder, state, SSH_DROP, "ssh")
    # El timer ejecuta copias root:root en almacenamiento privado, nunca código
    # modificable por el usuario dentro de su clon Git.
    core.atomic_write(folder / "runner.py", Path(__file__).read_bytes())
    core.atomic_write(folder / "baseline.py", Path(core.__file__).read_bytes())
    state["ssh"] = "PENDIENTE"
    state["timer"] = "baseline-ssh-" + folder.name.removeprefix("general-")
    state_write(folder, state)
    command(["systemd-run", "--unit=" + state["timer"], "--on-active=20m",
             "--timer-property=AccuracySec=1s", "/usr/bin/python3", str(folder / "runner.py"),
             "--restaurar-ssh", folder.name])
    try:
        put(folder, state, SSH_DROP, SSH_CONFIG, "ssh")
        text = SSH_MAIN.read_text()
        include = f"Include {SSH_DROP}\n"
        text = text.removeprefix(include)
        put(folder, state, SSH_MAIN, include + text, "ssh", 0o600)
        command(["sshd", "-t"])
        check_ssh(context)
        command(["systemctl", "reload", "ssh"])
    except Exception:
        restore_group(folder, state, "ssh")
        command(["sshd", "-t"])
        command(["systemctl", "reload", "ssh"])
        state["ssh"] = "REVERTIDO"
        state_write(folder, state)
        command(["systemctl", "stop", state["timer"] + ".timer"])
        raise


def ssh_resolution(name=None, confirm=False):
    with core.locked():
        if name is None:
            folder, state = read_latest()
        else:
            if not re.fullmatch(r"general-[a-z0-9_]+", name):
                raise ValueError("Registro inválido.")
            folder = core.STATE / name
            state = json.loads((folder / "general.json").read_text())
        if state.get("ssh") != "PENDIENTE":
            if confirm:
                raise ValueError("No hay cambio SSH pendiente; revisar si el timer ya revirtió.")
            return
        if confirm:
            command(["systemctl", "stop", state["timer"] + ".timer"])
            state["ssh"] = "CONFIRMADO_POR_OPERADOR"
        else:
            restore_group(folder, state, "ssh")
            command(["sshd", "-t"])
            command(["systemctl", "reload", "ssh"])
            state["ssh"] = "REVERTIDO"
        state_write(folder, state)
        print("SSH: " + state["ssh"])


def configure(args):
    import pwd
    if command(["dpkg", "--print-architecture"]).strip() != "amd64":
        raise ValueError("Este perfil de auditoría está preparado para amd64.")
    context = connection_context(args.usuario, args.conexion)
    if pwd.getpwnam(args.usuario).pw_uid == 0:
        raise ValueError("No usar una cuenta UID 0.")
    command(["sshd", "-t"])
    command(["visudo", "-c"])
    # Conserva el cliente de hora existente: no instala Chrony ni toca la red.
    if command(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]).strip() != "yes":
        raise ValueError("La hora no está sincronizada; resolver antes de aplicar el perfil.")
    ports = re.findall(r"(?m)^port (\d+)$", command(["sshd", "-T"]))
    if not ports or any(not 1 <= int(p) <= 65535 for p in ports):
        raise ValueError("No se pudieron determinar los puertos SSH.")
    with core.locked():
        if (core.STATE / "ultima-general").exists():
            _, previous = read_latest()
            if previous.get("ssh") == "PENDIENTE":
                raise ValueError("Resolver el cambio SSH pendiente antes de repetir.")
        folder = Path(tempfile.mkdtemp(prefix="general-", dir=core.STATE))
        state = {"version": "0.3", "snapshot": False, "estado": "INICIADO", "archivos": {}, "etapas": []}
        state_write(folder, state)
        core.atomic_write(core.STATE / "ultima-general", (folder.name + "\n").encode())
        print(f"Respaldo y registro privado: {folder}", flush=True)
        try:
            print("1/7 Paquetes, sin eliminar paquetes ni instalar recomendaciones", flush=True)
            command(["apt-get", "update"], capture=False)
            command(["apt-get", "install", "--yes", "--no-remove", "--no-install-recommends", *PACKAGES], capture=False)
            state["etapas"].append("paquetes")
            state_write(folder, state)

            print("2/7 Kernel", flush=True)
            kernel = folder / "kernel"
            kernel.mkdir(mode=0o700)
            core.apply_kernel(kernel, {"etapa": "kernel", "estado": "INICIADO"})
            state["etapas"].append("kernel")

            print("3/7 Auditoría", flush=True)
            configure_audit(folder, state)
            command(["systemctl", "enable", "auditd"])
            state["etapas"].append("audit")

            print("4/7 Sudo y registros", flush=True)
            try:
                put(folder, state, "/etc/sudoers.d/90-baseline", SUDO_CONFIG, "sudo", 0o440)
                command(["visudo", "-c"])
            except Exception:
                restore_group(folder, state, "sudo")
                raise
            put(folder, state, "/etc/logrotate.d/sudo-baseline", SUDO_ROTATE, "logs")
            put(folder, state, "/etc/systemd/journald.conf.d/90-baseline.conf", JOURNAL_CONFIG, "logs")
            command(["systemctl", "restart", "systemd-journald"])
            command(["journalctl", "--flush"])
            state["etapas"].append("logs_sudo")

            print("5/7 Actualizaciones y preparación AIDE", flush=True)
            put(folder, state, "/etc/apt/apt.conf.d/99-baseline-security", APT_CONFIG, "apt")
            command(["apt-config", "dump"])
            command(["systemctl", "enable", "--now", "apt-daily.timer", "apt-daily-upgrade.timer"])
            put(folder, state, "/etc/aide/baseline.conf", AIDE_CONFIG, "aide", 0o600)
            command(["aide", "--config=/etc/aide/baseline.conf", "--config-check"])
            Path("/var/lib/aide-baseline").mkdir(mode=0o700, exist_ok=True)
            put(folder, state, "/etc/systemd/system/baseline-aide.service", AIDE_SERVICE, "aide")
            put(folder, state, "/etc/systemd/system/baseline-aide.timer", AIDE_TIMER, "aide")
            command(["systemctl", "daemon-reload"])
            command(["systemctl", "enable", "--now", "baseline-aide.timer"])
            state["etapas"].append("apt_aide_preparado")

            print("6/7 Fail2ban", flush=True)
            configure_fail2ban(folder, state, ports)
            state["etapas"].append("fail2ban")

            print("7/7 SSH con recuperación automática en 20 minutos", flush=True)
            configure_ssh(folder, state, context)
            state["etapas"].append("ssh")
            state["estado"] = "APLICADO_PENDIENTE_ACEPTACION"
            state_write(folder, state)
        except Exception as exc:
            state["estado"] = "FALLIDO_REVISAR"
            state["error"] = str(exc)
            state_write(folder, state)
            raise
    print("\nAbre OTRA sesión SSH, prueba sudo y confirma antes de 20 minutos:")
    print("sudo python3 bin/configurar_base.py --confirmar-ssh")
    print("Si no confirmas, se recupera la configuración SSH anterior. No reinicies antes.")
    print("AIDE: configuración preparada; referencia inicial pendiente en cada clon.")
    print("No se selló la imagen, no se enrolaron agentes ni se configuró firewall por función.")


def verify(args):
    checks = []
    def check(name, argv, predicate=lambda value: True):
        try:
            output = command(argv)
            ok = predicate(output)
            checks.append((name, "OK" if ok else "REVISAR"))
        except (OSError, subprocess.SubprocessError, ValueError):
            checks.append((name, "REVISAR"))
    for key, value in core.SETTINGS.items():
        check(key, ["sysctl", "-n", key], lambda out, val=value: out.strip() == val)
    for unit in ("ssh", "auditd", "apparmor", "fail2ban", "qemu-guest-agent", "systemd-journald"):
        check(unit, ["systemctl", "is-active", unit], lambda out: out.strip() == "active")
    check("hora", ["timedatectl", "show", "-p", "NTPSynchronized", "--value"], lambda out: out.strip() == "yes")
    check("sudo_sintaxis", ["visudo", "-c"])
    check("ssh_sintaxis", ["sshd", "-t"])
    check("audit_sin_perdidas", ["auditctl", "-s"], lambda out: bool(re.search(r"(?m)^lost\s+0\s*$", out)))
    check("audit_reglas", ["auditctl", "-l"], lambda out: all(k in out for k in ("identidad", "privilegios", "acceso_ssh", "autenticacion", "config_audit", "config_kernel", "servicios")))
    for key, expected in (("maxretry", "5"), ("findtime", "600"), ("bantime", "600")):
        check("fail2ban_" + key, ["fail2ban-client", "get", "sshd", key], lambda out, val=expected: out.strip() == val)
    check("fail2ban_accion", ["fail2ban-client", "get", "sshd", "actions"], lambda out: "ufw" in out)
    check("aide_sintaxis", ["aide", "--config=/etc/aide/baseline.conf", "--config-check"])
    journal_values = {"Storage": "persistent", "SystemMaxUse": "512M", "SystemKeepFree": "1G",
                      "RuntimeMaxUse": "64M", "MaxRetentionSec": "30day"}
    check("journal_config_compuesta", ["systemd-analyze", "cat-config", "systemd/journald.conf"],
          lambda out: all(re.findall(rf"(?m)^\s*{key}\s*=\s*(\S+)", out)[-1:] == [val]
                          for key, val in journal_values.items()))
    def apt_expected(output):
        origins = re.findall(r'^Unattended-Upgrade::Origins-Pattern:: "([^"]*)";', output, re.M)
        return origins == ["origin=Debian,codename=trixie-security,label=Debian-Security"] and all(
            line in output for line in (
                'APT::Periodic::Update-Package-Lists "1";',
                'APT::Periodic::Unattended-Upgrade "1";',
                'Unattended-Upgrade::Automatic-Reboot "false";',
            )) and not re.search(r'^Unattended-Upgrade::Allowed-Origins:: "[^\"]+";', output, re.M)
    check("apt_politica_efectiva", ["apt-config", "dump"], apt_expected)
    try:
        config = Path("/etc/audit/auditd.conf").read_text()
        ok = all(re.findall(rf"(?m)^\s*{key}\s*=\s*(\S+)", config) == [value]
                 for key, value in AUDIT_OPTIONS.items())
        checks.append(("audit_config_guardada", "OK" if ok else "REVISAR"))
    except OSError:
        checks.append(("audit_config_guardada", "REVISAR"))
    for timer in ("apt-daily.timer", "apt-daily-upgrade.timer", "baseline-aide.timer"):
        check(timer, ["systemctl", "is-active", timer], lambda out: out.strip() == "active")
    if args.usuario and args.conexion:
        try:
            check_ssh(connection_context(args.usuario, args.conexion))
            checks.append(("ssh_efectivo_contexto_IP", "OK"))
        except (OSError, ValueError, subprocess.SubprocessError):
            checks.append(("ssh_efectivo_contexto_IP", "REVISAR"))
    else:
        checks.append(("ssh_efectivo_contexto_IP", "REVISAR"))
    try:
        _, state = read_latest()
        checks.append(("ssh_confirmado", "OK" if state.get("ssh") == "CONFIRMADO_POR_OPERADOR" else "REVISAR"))
    except (OSError, ValueError):
        checks.append(("ssh_confirmado", "REVISAR"))
    for name, status in checks:
        print(f"{status:8} {name}")
    print("PENDIENTE: referencia AIDE por clon, firewall por función, agentes, sellado y aceptación.")
    print("OK en estas consultas no equivale a CIS completo ni prueba funcional integral.")
    return 2 if any(status != "OK" for _, status in checks) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--aplicar", action="store_true")
    mode.add_argument("--verificar", action="store_true")
    mode.add_argument("--confirmar-ssh", action="store_true")
    mode.add_argument("--restaurar-ssh", metavar="REGISTRO")
    parser.add_argument("--sin-snapshot", action="store_true")
    parser.add_argument("--usuario", default="")
    parser.add_argument("--conexion", default="")
    args = parser.parse_args(argv)
    if not any((args.aplicar, args.verificar, args.confirmar_ssh, args.restaurar_ssh)):
        print("PLAN: paquetes sin Chrony; kernel; auditoría; sudo/logs; parches de seguridad; AIDE preparado; Fail2ban; SSH por contraseña.")
        print("No aplica cambios. Leer docs/09-base-en-bloque.md para ejecutar y recuperar.")
        return 0
    try:
        core.environment()
        if args.aplicar:
            if not args.sin_snapshot:
                raise ValueError("Este perfil registra --sin-snapshot; los respaldos de archivos no son una imagen recuperable.")
            configure(args)
        elif args.verificar:
            return verify(args)
        else:
            ssh_resolution(args.restaurar_ssh, confirm=args.confirmar_ssh)
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"DETENIDO: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
