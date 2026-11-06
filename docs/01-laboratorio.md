# 1. Preparación del Servidor

**Objetivo:** Disponer de un servidor Debian 13 limpio y verificable antes de aplicar la línea base de seguridad.

**Dónde:** Servidor Debian 13 (físico o virtual), ejecutando como usuario no root con privilegios `sudo`.

---

## 1.1 Requisitos Previos

El servidor debe contar con una instalación limpia de Debian 13 (Trixie) mínima, sin entorno gráfico de escritorio, con conectividad de red y acceso SSH inicial.

Registra los parámetros operativos del servidor fuera de Git:

| Dato | Ejemplo |
|---|---|
| Hostname / FQDN | `srv-proxy01.ejemplo.local` |
| Usuario administrativo | `operador` |
| IP/CIDR, Gateway y DNS | Los asignados a la interfaz de red |
| Red administrativa autorizada | Subred de administración / VPN |
| Rol asignado | Proxy Frontend, Proxy Backend, etc. |
| Mecanismo de recuperación | Respaldo / Snapshot previo de la máquina |

---

## 1.2 Confirmar el Sistema Operativo

En la terminal del servidor:

```bash
cat /etc/os-release
uname -r
sudo -v
ip -br address
ip route
```

**Esperado:** Debian GNU/Linux 13 (trixie), arquitectura x86_64, red operativa y sudo funcional.

---

## 1.3 Transferir el Repositorio al Servidor

Para evitar dejar tokens o credenciales de Git en servidores en proceso de endurecimiento, puedes transferir una copia del repositorio mediante SCP desde tu estación de trabajo o clonarlo de forma segura:

Desde PowerShell (Windows):
```powershell
scp -r "C:\ruta\debian13-baseline" usuario@IP_SERVIDOR:~/debian13-baseline
```

O clonando con credenciales temporales en el servidor:
```bash
git clone https://github.com/<tu-organizacion>/debian13-baseline.git ~/debian13-baseline
cd ~/debian13-baseline
```

---

## 1.4 Actualizar el Sistema y Verificar Estado Inicial

Antes de aplicar controles, actualiza el índice de paquetes y el sistema:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove --purge -y
```

Recoge el estado inicial del sistema con la herramienta de auditoría de solo lectura:

```bash
cd ~/debian13-baseline
sudo python3 bin/auditar.py --recopilar --salida /root
```

Guarda ese informe como evidencia de partida del servidor.

---

## 1.5 Crear Punto de Recuperación

Antes de aplicar cambios en PAM, kernel o firewall, genera un punto de respaldo o snapshot del servidor en la plataforma de virtualización correspondiente.

Una vez asegurada la recuperación, continúa con la **Parte 1: [2. Instalar y Comprobar la Seguridad Base](02-base.md)** o directamente mediante la ejecución automatizada en bloque con **[9. Base en Bloque](09-base-en-bloque.md)**.
