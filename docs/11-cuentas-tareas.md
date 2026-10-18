# 11. Cuentas nuevas y permisos cron

**Objetivo:** aplicar los ajustes confirmados por el inventario del piloto, con respaldo y recuperación. No cambia particiones ni caduca cuentas existentes.

## Aplicar y comprobar

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
sudo python3 bin/cuentas_tareas.py --aplicar
sudo python3 bin/cuentas_tareas.py --verificar
```

Configura máximos/mínimos/aviso de contraseña en 365/1/7 días para cuentas nuevas, inactividad de 30 días después de caducar la contraseña (no desde el último acceso), yescrypt, umask 027 en login.defs y shells de login. Los archivos personales de un usuario pueden cambiar su umask después; no es una política universal para servicios y contenedores. Las herramientas de creación de cuentas pueden sobrescribir defaults y deben verificarse al dar de alta cada clon.

Restringe `/etc/crontab` a 0600 y los directorios de cron a 0700, propiedad root:root. No recorre ni modifica permisos de scripts individuales. No restringe todavía quién puede usar `crontab` ni configura `at`.

Los respaldos quedan bajo `/var/lib/debian13-baseline/cuentas-*`, fuera de Git. Para recuperar la última aplicación:

```bash
sudo python3 bin/cuentas_tareas.py --restaurar
```

Después de aplicar, en una nueva conexión SSH:

```bash
umask
sudo chage -l "$USER"
```

Esperado: `0027` para la umask; la caducidad de la cuenta existente permanece como estaba. No aplicamos `chage` masivo: podría caducar inmediatamente cuentas con contraseñas antiguas. El ajuste para cuentas existentes se define al personalizar cada clon, junto al cambio de contraseña.

## Hallazgos del inventario recibido

- `/var` separado, ext4, sin opciones adicionales de endurecimiento.
- `/var/tmp`, `/var/log` y `/var/log/audit` comparten `/var`; `/home` comparte `/`.
- `/tmp` y `/dev/shm` son tmpfs con nosuid,nodev; falta resolver noexec según compatibilidad de aplicaciones.
- Servicios habilitados observados: no justifican una desinstalación masiva. Habilitado no equivale a activo ni a inventario completo de software.
- nftables.service deshabilitado, pero Fail2ban ya usa nftables. Hay que inspeccionar reglas y diseñar persistencia sin borrar sus cadenas.
- `audit=1` no aparece en la línea de arranque; no está completada la evaluación de auditoría temprana/GRUB.
- Los permisos observados de passwd/group son 0644 root:root y shadow/gshadow 0640 root:shadow. Este bloque los conserva.

**Pendiente:** montajes/particiones, firewall IPv4/IPv6 y Docker, módulos, cuentas existentes, cron/at completo, cobertura de auditoría, controles de arranque, matriz de evaluación CIS por ID y sellado. No representa el cierre CIS.

Fuentes: [login.defs Debian 13](https://manpages.debian.org/trixie/login.defs/login.defs.5.en.html), [useradd Debian 13](https://manpages.debian.org/trixie/passwd/useradd.8.en.html).
