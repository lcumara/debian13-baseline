# 1. Preparar el laboratorio

**Objetivo:** disponer de una VM recuperable antes de aplicar seguridad.

**Dónde:** Proxmox para crear la VM; Debian para ejecutar los comandos Linux.

## 1.1 Crear la VM

En Proxmox crea una VM Debian 13 mínima, sin escritorio, en una red de pruebas. Instala OpenSSH y un usuario administrador con sudo. Usa una ISO oficial verificada o una imagen cloud oficial verificada. No uses una copia de un servidor con datos o agentes productivos.

Conserva acceso a la consola de Proxmox. El tamaño de disco/RAM debe representar el servicio piloto; no hay un tamaño universal para todas las bases de datos y aplicaciones.

Registra estos datos fuera de Git:

| Dato | Ejemplo ficticio |
|---|---|
| VMID y nombre de laboratorio | 9100 / deb13-lab |
| Usuario administrativo | operador |
| IP/CIDR, gateway, DNS y NTP | Los de tu red de pruebas |
| Red administrativa autorizada | La de tu VPN o salto administrativo |
| Perfil del futuro clon | Aplicación, base de datos, proxy o Docker |
| Recuperación | Acceso a consola y snapshot/respaldo probado |

## 1.2 Confirmar el sistema

En la VM:

```bash
cat /etc/os-release
systemd-detect-virt --vm
uname -r
sudo -v
ip -br address
ip route
```

**Esperado:** Debian 13, KVM/QEMU, red de laboratorio y sudo funcional. El ejecutor rechaza Windows, otras versiones y el host Proxmox.

## 1.3 Llevar el repositorio a la VM

Para la plantilla, descarga el ZIP desde GitHub en tu PC autenticada y transfiérelo con SCP. Así no guardas credenciales de GitHub dentro de la imagen.

En PowerShell, ajusta ruta, usuario e IP:

```powershell
scp "$env:USERPROFILE\Downloads\debian13-baseline-main.zip" operador@IP_LAB:/tmp/baseline.zip
```

En Debian:

```bash
sudo apt-get update
sudo apt-get install --no-remove python3 unzip
mkdir -p ~/trabajo
unzip /tmp/baseline.zip -d ~/trabajo
cd ~/trabajo/debian13-baseline-main
python3 bin/baseline.py paquetes
```

**Esperado:** aparece un PLAN; todavía no instala nada. Los comandos posteriores parten de esta carpeta. La IP `IP_LAB` es un dato a sustituir, no un nombre real.

## 1.4 Actualizar y tomar referencia

```bash
sudo apt-get update
sudo apt-get -s upgrade
```

Revisa lo que propone APT. Después, en esta VM de laboratorio:

```bash
sudo apt-get upgrade
sudo reboot
```

Reconecta y recoge el estado inicial:

```bash
cd ~/trabajo/debian13-baseline-main
sudo python3 bin/auditar.py --recopilar --salida /root
```

La ausencia de agentes o utilidades puede devolver código 2: lee el informe; no significa automáticamente una vulnerabilidad. Guarda esa carpeta como evidencia privada.

## 1.5 Crear el punto de recuperación

En Proxmox, con la VM detenida, crea un snapshot llamado `antes-baseline`. Si el almacenamiento no admite snapshots, utiliza un respaldo y ensaya su restauración en otra VM aislada. El ejecutor pide el nombre como registro; **no comprueba que el snapshot exista**.

Vuelve a encender la VM. Continúa con [2. Seguridad base](02-base.md).

**Si falla:** detén el avance. Resuelve red, sudo y recuperación antes de aplicar cambios. Un snapshot del sistema no sustituye un respaldo consistente de una BD productiva.
