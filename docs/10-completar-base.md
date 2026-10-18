# 10. Completar paquetes, PAM y controles del sistema

**Objetivo:** ampliar la base del capítulo 9 en Debian 13 amd64/KVM, con cuentas locales y SSH por contraseña.

## Ejecutar en la VM

Mantén abierta tu sesión actual. No reinicies hasta confirmar el acceso nuevo.

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
sudo python3 bin/completar_base.py --aplicar
```

Cuando termine, abre **otra conexión SSH**. Desde esa nueva conexión:

```bash
sudo -k
sudo -v
cd ~/trabajo/debian13-baseline
sudo python3 bin/completar_base.py --confirmar
sudo python3 bin/completar_base.py --verificar
sudo python3 bin/configurar_base.py --verificar --usuario "$USER" --conexion "$SSH_CONNECTION"
```

La recuperación se programa antes de escribir los nuevos controles, después de instalar paquetes. Si no confirmas en 20 minutos, restaura archivos respaldados y valores sysctl anteriores. Los paquetes instalados permanecen. El timer es transitorio: **no reinicies con la confirmación pendiente**. Un respaldo de archivos no sustituye una imagen de recuperación.

## Cambios incluidos

| Área | Configuración |
|---|---|
| Paquetes | libpam-pwquality, libpwquality-tools, cracklib-runtime, rsyslog, needrestart |
| Contraseñas nuevas | 14 caracteres como mínimo, sin créditos de longitud; diccionario, nombre de usuario, diferencias y repeticiones comprobados |
| Historial | 24 contraseñas, obligatorio también cuando root cambia una contraseña |
| Hash de contraseñas nuevas | yescrypt; no convierte hashes existentes |
| Intentos fallidos | Bloqueo de cuentas locales no root tras 5 fallos en 15 minutos; desbloqueo después de 15 minutos |
| PAM | Sin nullok; mantiene SSH con contraseña; rechaza pilas con SSSD/LDAP u otros módulos no reconocidos |
| Logs | rsyslog activo; permisos 0640 para archivos nuevos; rotación suministrada por el paquete; conserva journald |
| Reinicios pendientes | needrestart en modo listado, sin ordenar reinicios automáticos desde needrestart |
| Volcados de memoria | Límite core 0 para sesiones nuevas, suid_dumpable=0, almacenamiento de systemd-coredump deshabilitado |
| Red | Rechazo de redirecciones y source routing IPv4; SYN cookies; ignora broadcasts ICMP y errores inválidos |
| Auditoría | Cambios de hora/hostname, módulos del kernel, accesos denegados, cambios de permisos y eliminaciones de usuarios con auid >= 1000 |

Se conserva timesyncd. No se cambian forwarding, IPv6 ni rp_filter; no se aplica un firewall de Docker con reglas genéricas. Las opciones de red `all/default` requieren revisión adicional de interfaces existentes y de nuevas interfaces del perfil final.

PAM se administra directamente en common-auth/account/password. No ejecutar `pam-auth-update --force` después: podría reemplazar este perfil. Si se incorpora autenticación central, debe migrarse la pila de forma explícita. La detección previa de módulos conocidos no equivale a una prueba funcional PAM.

Las contraseñas existentes no se invalidan ni se fuerzan a cambiar. Root queda exento del bloqueo PAM: excepción de recuperación, no cumplimiento universal CIS. El bloqueo por cuenta se suma al bloqueo por IP de Fail2ban.

## Pruebas funcionales al final

Después de confirmar el nuevo acceso, crea una cuenta temporal sin sudo:

```bash
sudo useradd -m -s /bin/bash prueba-baseline
sudo passwd prueba-baseline
```

En el diálogo privado de passwd, comprueba que rechaza una contraseña corta y acepta una larga y distinta del usuario. No publiques contraseñas. Para comprobar historial, cambia a otra contraseña válida y después intenta reutilizar la anterior: debe rechazarla.

Para probar bloqueo, usa la consola de la VM con esta cuenta temporal: cinco fallos deben bloquearla. No uses tu cuenta administrativa ni repitas fallos SSH desde tu IP administrativa porque también actúa Fail2ban. Consulta y restablece el contador:

```bash
sudo faillock --user prueba-baseline
sudo faillock --user prueba-baseline --reset
```

Comprueba que la contraseña correcta permite entrar después del desbloqueo. Cierra esa sesión y elimina únicamente la cuenta temporal creada para esta prueba:

```bash
sudo userdel -r prueba-baseline
logger -t baseline-prueba 'Prueba local de rsyslog'
sudo grep 'baseline-prueba' /var/log/syslog
sudo logrotate --debug /etc/logrotate.conf
sudo needrestart -r l
```

La eliminación de la cuenta no limpia todas sus trazas de auditoría/historial. El sellado debe considerar estos archivos y las copias privadas de configuración.

Reinicia cuando hayas confirmado el acceso y completado las pruebas. Repite ambos verificadores. El límite de core se aplica a sesiones nuevas; servicios pueden tener límites propios.

## Recuperación manual

Desde la sesión que conservaste abierta o la consola, antes de confirmar:

```bash
sudo python3 bin/completar_base.py --restaurar "$(sudo cat /var/lib/debian13-baseline/ultimo-complemento)"
```

Si un instalador falla, el programa restaura los archivos PAM respaldados; revisa el estado de APT antes de repetir. No hay transacción de desinstalación de paquetes. Después de confirmar, la restauración automática deja de estar disponible; los respaldos siguen en el registro privado para recuperación supervisada.

## Alcance CIS real y trabajo restante

Este complemento implementa controles de endurecimiento, **no ejecuta todo el benchmark ni asigna un porcentaje CIS**. No se han validado equivalencias por ID contra el benchmark Debian 13 1.1.0. La referencia de Ansible del capítulo 8 declara otra versión y no se ejecuta automáticamente.

Siguen pendientes: política de caducidad para cuentas existentes/nuevas, root en faillock, permisos e inventario completo de archivos/cuentas/servicios, cron/at, módulos y montajes según función, reglas completas de auditoría (incluidos ejecutables privilegiados), opciones de arranque, firewall base IPv4/IPv6, evaluación CIS por ID y excepciones, agentes y sellado manual. No convertir todavía en plantilla aprobada.

**Pruebas del repositorio:** pruebas unitarias locales con comandos simulados. Las pruebas funcionales anteriores se ejecutan en la VM; no se consideran aprobadas hasta tener su resultado.

Fuentes: [PAM pwquality Debian 13](https://manpages.debian.org/trixie/libpam-pwquality/pam_pwquality.8.en.html), [Linux-PAM faillock](https://github.com/linux-pam/linux-pam/blob/master/modules/pam_faillock/pam_faillock.8.xml), [Linux-PAM pwhistory](https://github.com/linux-pam/linux-pam/blob/master/modules/pam_pwhistory/pam_pwhistory.8.xml), [referencia CIS del proyecto](08-reutilizar-cis.md).
