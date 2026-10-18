# 11. Cuentas nuevas y permisos cron

**Objetivo:** aplicar los ajustes confirmados por el inventario del piloto, con respaldo y recuperación. No cambia particiones ni caduca cuentas existentes.

## Aplicar y comprobar

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
sudo python3 bin/cuentas_tareas.py --aplicar
sudo python3 bin/cuentas_tareas.py --verificar
```

Política acordada: máximo **3650 días** (aproximadamente diez años), mínimo 1 día y aviso **365 días antes** de caducar, para cuentas nuevas. Inactividad `-1`: sin bloqueo adicional tras caducar la contraseña. Caducar la contraseña sí puede exigir cambiarla para iniciar sesión. Los plazos se cuentan desde el último cambio de contraseña, no desde la clonación. Se conserva yescrypt y se configura umask 027 en login.defs y shells de login. Los archivos personales de un usuario pueden cambiar su umask después; no es una política universal para servicios y contenedores. Las herramientas de creación de cuentas pueden sobrescribir defaults y deben verificarse al dar de alta cada clon.

Se instala `/etc/cron.daily/baseline-password-review`: comprueba diariamente cuentas locales con UID 1000–65533, shell de acceso y contraseña no bloqueada. A partir de **1825 días** desde el último cambio registra un aviso local con etiqueta `baseline-password-review`, sin imprimir hashes ni cambiar cuentas. Excluye root y cuentas de sistema; cuentas de aplicación con UID humano pueden aparecer y requieren clasificación. El aviso se repite mientras siga pendiente. No envía correos ni configura alertas en Wazuh/Zabbix: su recepción central se integrará con los agentes. Los avisos nativos de caducidad al entrar tampoco son correo.

Prueba manual de la revisión informativa:

```bash
sudo python3 bin/revisar_edades.py
sudo journalctl -t baseline-password-review --since today --no-pager
```

Sin cuentas elegibles antiguas, no habrá eventos de advertencia.

**Excepción CIS acordada:** caducidad larga y ausencia de bloqueo adicional por inactividad. No marcar estos controles como conformes al benchmark por el hecho de que el verificador acepte la política local.

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

Esperado: `0027` para la umask; la caducidad de la cuenta existente permanece como estaba. Para la cuenta administrativa del piloto, después de revisar su fecha de último cambio:

```bash
sudo chage -M 3650 -m 1 -W 365 -I -1 -E -1 "$USER"
sudo chage -l "$USER"
```

Ejecutar desde la sesión del administrador no root. `-E -1` quita la fecha de vencimiento de la cuenta; no elimina la caducidad de su contraseña. No modifica la fecha del último cambio ni la contraseña. Si esta ya supera 3650 días, debe cambiarse antes de aplicar; no falsear su antigüedad. No aplicar masivamente a cuentas de servicio. Cada clon tendrá contraseña administrativa propia al personalizarlo.

## Hallazgos del inventario recibido

- `/var` separado, ext4, sin opciones adicionales de endurecimiento.
- `/var/tmp`, `/var/log` y `/var/log/audit` comparten `/var`; `/home` comparte `/`.
- `/tmp` y `/dev/shm` son tmpfs con nosuid,nodev; falta resolver noexec según compatibilidad de aplicaciones.
- Servicios habilitados observados: no justifican una desinstalación masiva. Habilitado no equivale a activo ni a inventario completo de software.
- nftables.service deshabilitado, pero Fail2ban ya usa nftables. Hay que inspeccionar reglas y diseñar persistencia sin borrar sus cadenas.
- `audit=1` no aparece en la línea de arranque; no está completada la evaluación de auditoría temprana/GRUB.
- Los permisos observados de passwd/group son 0644 root:root y shadow/gshadow 0640 root:shadow. Este bloque los conserva.

**Excepción de almacenamiento acordada:** conservar la distribución actual, sin crear particiones o volúmenes separados para /home, /var/tmp, /var/log y /var/log/audit. Proxmox aporta discos virtuales; las particiones, LVM y montajes se gestionan dentro de Debian. No marcar como cumplidos controles de separación que no se implementan.

**Pendiente:** opciones de montaje (sin reparticionar), firewall IPv4/IPv6 y Docker, módulos, cuentas existentes restantes, cron/at completo, cobertura de auditoría, controles de arranque, matriz de evaluación CIS por ID y sellado. Este cambio cierra la decisión de política de contraseñas y separación, no todo CIS.

Fuentes: [login.defs Debian 13](https://manpages.debian.org/trixie/login.defs/login.defs.5.en.html), [useradd Debian 13](https://manpages.debian.org/trixie/passwd/useradd.8.en.html).
