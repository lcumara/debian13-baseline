#!/usr/bin/env python3
"""Evidencia local Debian 13. No remedia ni interpreta resultados como CIS."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

TRUSTED_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"
COMMANDS = (
    ("sistema", ("cat", "/etc/os-release")),
    ("kernel", ("uname", "-r")),
    ("arquitectura", ("dpkg", "--print-architecture")),
    ("virtualizacion", ("systemd-detect-virt",)),
    ("paquetes", ("dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Status}\n")),
    ("pendientes_cache_apt", ("apt", "list", "--upgradable")),
    ("soporte_paquetes", ("check-support-status",)),
    ("servicios_fallidos", ("systemctl", "--failed", "--no-pager")),
    ("unidades_instaladas", ("systemctl", "list-unit-files", "--type=service", "--no-pager")),
    ("temporizadores", ("systemctl", "list-timers", "--all", "--no-pager")),
    ("servicios_base", ("systemctl", "is-active", "ssh", "auditd", "apparmor", "chrony", "rsyslog")),
    ("agentes_conocidos", ("systemctl", "is-active", "wazuh-agent", "zabbix-agent2")),
    ("ssh_sintaxis", ("sshd", "-t")),
    ("ssh_efectivo_sin_match", ("sshd", "-T")),
    ("sudo_sintaxis", ("visudo", "-c")),
    ("direcciones", ("ip", "-br", "address")),
    ("rutas_ipv4", ("ip", "route", "show")),
    ("rutas_ipv6", ("ip", "-6", "route", "show")),
    ("escuchas", ("ss", "-lntu")),
    ("nftables", ("nft", "list", "ruleset")),
    ("iptables_ipv4", ("iptables-save",)),
    ("iptables_ipv6", ("ip6tables-save",)),
    ("forwarding", ("sysctl", "net.ipv4.ip_forward", "net.ipv6.conf.all.forwarding")),
    ("apparmor", ("aa-status",)),
    ("audit_estado", ("auditctl", "-s")),
    ("audit_reglas", ("auditctl", "-l")),
    ("fail2ban_ssh", ("fail2ban-client", "status", "sshd")),
    ("reloj", ("chronyc", "tracking")),
    ("montajes", ("findmnt", "-o", "TARGET,FSTYPE,VFS-OPTIONS")),
    ("espacio", ("df", "-hT")),
    ("inodos", ("df", "-i")),
    ("journal_espacio", ("journalctl", "--disk-usage")),
    ("permisos_cuentas", ("stat", "-c", "%a %U:%G %n", "/etc/passwd", "/etc/group", "/etc/shadow", "/etc/gshadow", "/etc/sudoers")),
    ("permisos_psk_ruta_conocida", ("stat", "-c", "%a %U:%G %n", "/etc/zabbix/zabbix_agent2.psk")),
    ("huella_ssh_publica", ("ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub")),
    ("cloud_init", ("cloud-init", "status", "--long")),
    ("wazuh_estado_local", ("/var/ossec/bin/wazuh-control", "status")),
    ("docker_version_cliente", ("docker", "--version")),
)


def collect_one(label, args, timeout=30):
    """Ejecuta solo argv predefinido, nunca una cadena shell ni contenido externo."""
    command = shutil.which(args[0], path=TRUSTED_PATH)
    result = {"id": label, "argv": list(args), "estado": "NO_DISPONIBLE", "codigo": None, "salida": ""}
    if not command:
        return result
    try:
        proc = subprocess.run(
            [command, *args[1:]], shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            env={"PATH": TRUSTED_PATH, "LC_ALL": "C", "LANG": "C", "HOME": "/root",
                 "SYSTEMD_PAGER": "cat", "PAGER": "cat", "SYSTEMD_COLORS": "0"},
        )
        output = proc.stdout
        if label == "ssh_efectivo_sin_match":
            allowed = {"port", "listenaddress", "permitrootlogin", "passwordauthentication",
                       "pubkeyauthentication", "kbdinteractiveauthentication", "usepam",
                       "authenticationmethods", "permitemptypasswords", "maxauthtries",
                       "maxstartups", "loglevel", "x11forwarding", "allowtcpforwarding",
                       "allowagentforwarding", "permittunnel", "allowusers", "allowgroups",
                       "denyusers", "denygroups", "clientaliveinterval", "clientalivecountmax",
                       "channeltimeout", "logingracetime"}
            output = "\n".join(line for line in output.splitlines()
                               if line.split() and line.split()[0] in allowed) + "\n"
        result.update(codigo=proc.returncode, salida=output,
                      estado="CONSULTADO" if proc.returncode == 0 else "REVISAR")
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        result.update(estado="TIEMPO_EXCEDIDO", salida=output)
    except OSError as exc:
        result.update(estado="ERROR", salida=str(exc))
    return result


def validate_environment():
    if platform.system() != "Linux":
        raise ValueError("La recopilación requiere Linux Debian 13; --listar funciona en cualquier sistema.")
    release = platform.freedesktop_os_release()
    if release.get("ID") != "debian" or release.get("VERSION_ID", "").split(".")[0] != "13":
        raise ValueError("Solo se admite Debian 13. No se han ejecutado consultas.")
    if os.geteuid() != 0:
        raise ValueError("Ejecutar la recopilación con sudo/root para evitar evidencia parcial por permisos.")


def write_reports(folder, results):
    payload = {
        "schema": 1, "baseline": "0.1-diseno",
        "recopilacion_completa": len(results) == len(COMMANDS),
        "fecha_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "nota": "Recopilación local; no certifica CIS ni seguridad. Índices APT no actualizados por este programa.",
        "consultas": results,
        "pendiente": ["Contexto SSH Match", "Exposición externa IPv4/IPv6",
                       "Unicidad de identidades entre clones", "Recepción y alertas centrales",
                       "Compatibilidad G DATA/FortiEDR", "Políticas Docker y aplicación",
                       "Prueba de restauración", "Evaluación CIS por ID/política exacta"],
    }
    (folder / "evidencia.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Evidencia local Debian 13", "", payload["fecha_utc"], "", payload["nota"], "",
             "RESTRINGIDO: contiene metadatos internos. Mantener fuera de Git.", "",
             "Recopilación completa: " + str(payload["recopilacion_completa"]), "",
             "CONSULTADO significa que el comando terminó con 0; no que el control haya sido aprobado.", "",
             "| Consulta | Estado | Código |", "|---|---|---|"]
    for item in results:
        code = "-" if item["codigo"] is None else str(item["codigo"])
        lines.append(f"| {item['id']} | {item['estado']} | {code} |")
    lines += ["", "## Pendientes", "", *["- " + x for x in payload["pendiente"]], ""]
    (folder / "resumen.md").write_text("\n".join(lines), encoding="utf-8")
    for name in ("evidencia.json", "resumen.md"):
        os.chmod(folder / name, 0o600)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--listar", action="store_true", help="Mostrar comandos; no ejecutar ni escribir")
    mode.add_argument("--recopilar", action="store_true", help="Consultar host local y escribir evidencia privada")
    parser.add_argument("--salida", type=Path, default=Path("/root"), help="Directorio padre existente; se crea una subcarpeta única")
    options = parser.parse_args(argv)
    if options.listar:
        for label, args in COMMANDS:
            print(label + ": " + json.dumps(args, ensure_ascii=False))
        return 0
    try:
        validate_environment()
        parent = options.salida.resolve(strict=True)
        if not parent.is_dir():
            raise ValueError("La salida debe ser un directorio existente.")
        os.umask(0o077)
        folder = Path(tempfile.mkdtemp(prefix="auditoria-debian13-", dir=parent))
        results = []
        for label, args in COMMANDS:
            print("Consultando " + label + "...", flush=True)
            results.append(collect_one(label, args))
            # Guardar progreso permite reconocer evidencia parcial ante interrupción.
            write_reports(folder, results)
        print("Evidencia privada: " + str(folder))
        print("No se aplicaron correcciones ni se calculó un porcentaje CIS.")
        return 2 if any(r["estado"] != "CONSULTADO" for r in results) else 0
    except (ValueError, OSError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
