# Operación para infraestructura

**Objetivo:** administrar una VM ya configurada sin repetir la instalación ni depender del home del usuario que la construyó.

Este repositorio es privado: su propietario debe conceder acceso al encargado en GitHub. Compartir el enlace no concede permisos. No compartir el token personal del constructor.

## Conservar una copia de administración fuera del home

Si `/opt/debian13-baseline` todavía no existe, desde Debian con una cuenta autorizada:

```bash
sudo git -c credential.helper= clone https://github.com/lcumara/debian13-baseline.git /opt/debian13-baseline
cd /opt/debian13-baseline
```

Usar las credenciales propias del encargado, sin incluir tokens en la URL. Para actualizar esta copia root:root:

```bash
cd /opt/debian13-baseline
sudo git -c credential.helper= pull --ff-only
```

También puedes usar tu copia existente en `~/trabajo/debian13-baseline`. La ruta del repositorio no es la ruta del servicio: eliminar el home no elimina la copia privada del firewall. No ejecutar el clonado sobre un directorio existente ni reemplazar una copia con modificaciones sin revisarlas.

## Consultar estado

```bash
cd /opt/debian13-baseline
sudo python3 bin/configurar_base.py --verificar --usuario "$USER" --conexion "$SSH_CONNECTION"
sudo python3 bin/completar_base.py --verificar
sudo python3 bin/cuentas_tareas.py --verificar
sudo python3 bin/firewall_base.py --verificar
systemctl --failed
```

La primera consulta requiere una sesión SSH con usuario no root. Los verificadores comprueban controles concretos; no son un escáner CIS completo.

## Firewall (UFW)

El firewall del host se administra mediante **UFW** (backend `iptables-nft`), con IPv6 desactivado y Fail2ban enlazado:

```bash
sudo ufw status verbose
sudo fail2ban-client status sshd
```

Abrir HTTPS público (puerto 443 TCP):
```bash
sudo ufw allow 443/tcp comment "HTTPS Web"
```

Abrir HTTP (puerto 80 TCP, solo si se requiere redirección):
```bash
sudo ufw allow 80/tcp comment "HTTP Redireccion"
```

Abrir un puerto restringido solo a una IP o subred de aplicación (ej. PostgreSQL 5432):
```bash
read -r -p 'IP o CIDR autorizado: ' RED_APP
sudo ufw allow from "$RED_APP" to any port 5432 proto tcp comment "PostgreSQL App"
```

Retirar ese permiso exacto:
```bash
sudo ufw status numbered
sudo ufw delete <NUMERO_DE_REGLA>
```

Para más detalles sobre la arquitectura del firewall, consulta [12. Firewall UFW](12-firewall-ufw.md).

## Registros, auditoría, contraseñas e integridad

```bash
sudo auditctl -s
sudo auditctl -l
sudo journalctl -u auditd -u rsyslog -b --no-pager -n 50
sudo journalctl -u ssh -b --no-pager -n 50
sudo python3 bin/revisar_edades.py
sudo journalctl -t baseline-password-review --since today --no-pager
sudo chage -l "$USER"
sudo systemctl status baseline-aide.timer --no-pager
sudo journalctl -u baseline-aide.service --no-pager -n 50
systemctl list-timers --all --no-pager
sudo needrestart -r l
```

La referencia AIDE debe inicializarse por clon después de personalizarlo y validar su estado, según capítulo 9. No reemplazarla automáticamente para silenciar diferencias. Los avisos de contraseñas del quinto año son locales; recepción central pendiente de agentes. Los registros pueden incluir IP/usuarios: mantenerlos fuera de Git.

## Recuperación: efecto de cada comando

Ejecutar solo para una incidencia concreta, desde una sesión conservada o consola:

| Comando | Efecto |
|---|---|
| `sudo python3 bin/firewall_base.py --restaurar` | Elimina la tabla propia y deshabilita el servicio; deja de filtrar entradas con esta política |
| `sudo python3 bin/cuentas_tareas.py --restaurar` | Restaura archivos y permisos del último bloque de cuentas/cron; no revierte chage aplicado manualmente |
| `sudo python3 bin/completar_base.py --restaurar REGISTRO` | Recupera el complemento mientras su ejecución está pendiente; no desinstala paquetes |
| `sudo python3 bin/configurar_base.py --restaurar-ssh REGISTRO` | Recupera SSH si ese cambio sigue pendiente; no restaura todo el servidor |

Los parámetros internos `--cargar` y `--vencer` del firewall son para el servicio y timer; no son comandos habituales de operación. Los capítulos 9, 10 y 12 documentan confirmaciones durante instalación. No ejecutar `baseline.py` antiguo para modificar esta instalación: tiene otro perfil.

## Rutas que se deben conservar

| Ruta | Motivo |
|---|---|
| `/etc/systemd/system/baseline-firewall.service` | Servicio de arranque |
| `/var/lib/debian13-baseline/ultimo-firewall` | Referencia al estado utilizado por el servicio |
| `/var/lib/debian13-baseline/firewall-*` activo | Ejecutores privados, permisos de puertos y estado persistente |
| `/etc/cron.daily/baseline-password-review` | Revisión informativa de antigüedad |
| Configuración baseline bajo `/etc` | Políticas SSH/PAM, audit, logs, APT, sysctl y servicios |

**No borrar todo `/var/lib/debian13-baseline` como si fuera caché.** La selección de respaldos retirables se hace durante el sellado, conservando el estado y código activo. No borrar el usuario administrativo antes de probar SSH y sudo con su reemplazo o disponer del procedimiento de acceso por consola.

## Alcance y entrega

El sellado técnico tiene comandos propios, documentados en el [capítulo 14](14-preparar-sellado-manual.md): `sudo python3 bin/sellar_identidad.py --comprobar` y, únicamente al terminar la preparación, `sudo python3 bin/sellar_identidad.py --sellar-y-apagar`. El segundo elimina identidades y apaga la VM. No es un comando de mantenimiento de servidores productivos.

Los verificadores compartidos por el operador pasaron después de reinicios. Las pruebas funcionales completas, la evaluación CIS por ID y el sellado manual no están todos concluidos. Ver [13. Cierre pendiente](13-cierre-pendiente.md). No etiquetar esta imagen como CIS certificada ni ya aprobada para producción.
