#!/usr/bin/env python3
"""Piloto local Debian 13. Sin argumentos de aplicación solo muestra el plan."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import tempfile

PATH = "/usr/sbin:/usr/bin:/sbin:/bin"
POLICY = Path("/etc/sysctl.d/90-debian13-baseline.conf")
STATE = Path("/var/lib/debian13-baseline")
PACKAGES = (
    "ca-certificates", "sudo", "qemu-guest-agent", "apparmor", "apparmor-utils",
    "auditd", "audispd-plugins", "chrony", "aide", "unattended-upgrades",
    "debian-security-support",
)
# No modifica forwarding, IPv6, rp_filter ni parámetros de memoria para BD.
SETTINGS = {
    "kernel.randomize_va_space": "2",
    "kernel.kptr_restrict": "2",
    "kernel.dmesg_restrict": "1",
    "fs.protected_hardlinks": "1",
    "fs.protected_symlinks": "1",
}


def run(argv, capture=True):
    return subprocess.run(
        argv, check=True, text=True, shell=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        env={"PATH": PATH, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
             "HOME": "/root", "DEBIAN_FRONTEND": "noninteractive"},
        timeout=1800,
    ).stdout


def environment():
    if platform.system() != "Linux":
        raise ValueError("Aplicación permitida únicamente dentro de Debian 13.")
    release = platform.freedesktop_os_release()
    if release.get("ID") != "debian" or release.get("VERSION_ID") != "13":
        raise ValueError("Se requiere Debian 13; no se aceptan derivados.")
    if os.geteuid() != 0:
        raise ValueError("Ejecutar la aplicación/verificación con sudo.")
    if run(["systemd-detect-virt", "--vm"]).strip() not in {"kvm", "qemu"}:
        raise ValueError("Piloto limitado a VM KVM/QEMU. No ejecutar en el host Proxmox.")


def content():
    return "# Administrado por debian13-baseline; piloto de laboratorio\n" + "".join(
        f"{key} = {value}\n" for key, value in SETTINGS.items())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=0o600):
    fd, temporary = tempfile.mkstemp(prefix=".baseline-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def secure_state():
    if STATE.is_symlink():
        raise ValueError("La carpeta de estado no puede ser un enlace.")
    STATE.mkdir(mode=0o700, exist_ok=True)
    stat = STATE.stat()
    if stat.st_uid != 0 or stat.st_gid != 0 or stat.st_mode & 0o077:
        raise ValueError("La carpeta de estado debe ser root:root, modo 0700.")


@contextmanager
def locked():
    import fcntl
    secure_state()
    with (STATE / "ejecucion.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def save(folder, state):
    atomic_write(folder / "estado.json", json.dumps(state, indent=2).encode())


def check_kernel():
    actual = {key: run(["sysctl", "-n", key]).strip() for key in SETTINGS}
    wrong = {key: {"esperado": value, "actual": actual[key]}
             for key, value in SETTINGS.items() if actual[key] != value}
    if wrong:
        raise ValueError("Parámetros efectivos diferentes: " + json.dumps(wrong))
    return actual


def restore_kernel(folder, state):
    # Se intenta recuperar tanto persistencia como valores efectivos, incluso
    # cuando uno falla. No se oculta una recuperación incompleta.
    errors = []
    try:
        if state["existia"]:
            atomic_write(POLICY, (folder / "anterior.conf").read_bytes(), state["modo"])
        else:
            POLICY.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(str(exc))
    for key, value in state["valores_anteriores"].items():
        try:
            run(["sysctl", "-w", f"{key}={value}"])
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(str(exc))
    state["estado"] = "REVERSION_INCOMPLETA" if errors else "REVERTIDO"
    state["errores_reversion"] = errors
    save(folder, state)
    if errors:
        raise ValueError("Recuperación incompleta; usar consola/snapshot. " + "; ".join(errors))


def apply_kernel(folder, state):
    if POLICY.is_symlink():
        raise ValueError("El archivo de política no puede ser un enlace.")
    state["existia"] = POLICY.exists()
    if POLICY.exists():
        stat = POLICY.stat()
        if not POLICY.is_file() or stat.st_uid != 0 or stat.st_gid != 0:
            raise ValueError("La política existente debe ser archivo root:root.")
        state["modo"] = stat.st_mode & 0o777
        atomic_write(folder / "anterior.conf", POLICY.read_bytes())
    state["valores_anteriores"] = {
        key: run(["sysctl", "-n", key]).strip() for key in SETTINGS}
    state["sha256_aplicado"] = digest(content().encode())
    save(folder, state)
    try:
        atomic_write(POLICY, content().encode(), 0o644)
        run(["sysctl", "-p", str(POLICY)])
        check_kernel()
    except (OSError, subprocess.SubprocessError, ValueError):
        restore_kernel(folder, state)
        raise


def apply(stage, snapshot):
    with locked():
        folder = Path(tempfile.mkdtemp(prefix=stage + "-", dir=STATE))
        state = {"etapa": stage, "snapshot_declarado": snapshot, "estado": "INICIADO"}
        save(folder, state)
        print(f"Registro privado: {folder}", flush=True)
        try:
            if stage == "paquetes":
                # Evita que APT elimine paquetes para resolver conflictos de NTP.
                run(["apt-get", "update"], capture=False)
                run(["apt-get", "install", "--yes", "--no-remove", *PACKAGES], capture=False)
            else:
                apply_kernel(folder, state)
            state["estado"] = "APLICADO"
            save(folder, state)
        except (OSError, subprocess.SubprocessError, ValueError):
            if state["estado"] == "INICIADO":
                state["estado"] = "FALLIDO_REVISAR_SNAPSHOT"
                save(folder, state)
            raise
        print("Etapa terminada. Pendientes: verificación, reinicio y aceptación del piloto.")


def rollback(folder):
    with locked():
        folder = folder.resolve(strict=True)
        if folder.parent != STATE.resolve() or not folder.name.startswith("kernel-"):
            raise ValueError("Solo se admite una ejecución kernel dentro de la carpeta de estado.")
        state = json.loads((folder / "estado.json").read_text())
        if state.get("etapa") != "kernel" or state.get("estado") != "APLICADO":
            raise ValueError("La ejecución no corresponde a un kernel aplicado.")
        if set(state.get("valores_anteriores", {})) != set(SETTINGS):
            raise ValueError("Registro de recuperación inválido.")
        if POLICY.is_symlink() or not POLICY.is_file() or digest(POLICY.read_bytes()) != state["sha256_aplicado"]:
            raise ValueError("La política cambió después; revisar manualmente para no sobrescribirla.")
        # No revertir parámetros que otra herramienta modificó después.
        check_kernel()
        restore_kernel(folder, state)
        print("Kernel revertido al estado guardado de esa ejecución.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("etapa", choices=("paquetes", "kernel", "verificar", "revertir"))
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--laboratorio", action="store_true")
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--registro", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.etapa == "verificar":
            environment()
            print(json.dumps(check_kernel(), indent=2))
            print("Cinco parámetros correctos. No equivale a cumplimiento CIS ni aceptación.")
            return 0
        if not args.aplicar:
            if args.etapa == "paquetes":
                print("PLAN: actualiza índices APT e instala paquetes; pueden iniciarse servicios.")
                print("apt-get update")
                print(shlex.join(["apt-get", "install", "--yes", "--no-remove", *PACKAGES]))
            elif args.etapa == "kernel":
                print(f"PLAN: respaldar y escribir {POLICY}; aplicar y comprobar:")
                print(content())
            else:
                print("PLAN: recuperar archivo y valores kernel del registro indicado.")
            return 0
        if not args.laboratorio or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", args.snapshot):
            raise ValueError("Requiere --laboratorio --snapshot NOMBRE. Es una declaración; no verifica Proxmox.")
        environment()
        if args.etapa == "revertir":
            if args.registro is None:
                raise ValueError("Falta --registro /var/lib/debian13-baseline/kernel-...")
            rollback(args.registro)
        else:
            apply(args.etapa, args.snapshot)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"DETENIDO: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
