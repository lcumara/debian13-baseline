# 9. Aplicar el perfil general en bloque

**Objetivo:** completar los ajustes comunes de la VM de preparación sin detenerse a consultar cada comando por separado.

**Perfil acordado:** Debian 13 amd64 en Proxmox; acceso por usuario normal con sudo y contraseña SSH; no se dispone de snapshot; NTP actual sincronizado. Los futuros clones tendrán distintas funciones, algunos con Docker/BD. No ejecutar en el host Proxmox ni sobre aplicaciones ya productivas.

Esta ruta sustituye los pasos de aplicación del piloto anterior: no ejecutar después `baseline.py paquetes`, que incluye Chrony, ni el bloque SSH del capítulo 3 que desactiva contraseñas. No requiere inventar un snapshot. Los respaldos locales permiten recuperar archivos, no reconstruir una VM perdida ni revertir todas las operaciones de APT.

## 9.1 Qué aplica

| Área | Configuración del perfil |
|---|---|
| Paquetes | Sin recomendaciones, sin eliminar paquetes, sin cambiar a Chrony |
| Kernel | Los cinco parámetros del piloto; forwarding/IPv6 se conservan |
| Auditoría | Identidades, sudo, SSH, PAM/security, configuración audit/sysctl y unidades systemd; variantes b64/b32 para amd64 |
| Retención audit | 32 MiB, 10 archivos, avisos a 4096 MiB y suspensión a 2048 MiB; acciones SYSLOG/SUSPEND |
| Sudo | Pseudoterminal y registro local de comandos; no cambia contraseñas ni grupos |
| Journal | Persistencia, compresión, límite de 512 MiB y reserva de 1 GiB; retención máxima 30 días, limitada también por espacio |
| Actualizaciones | Automáticas de seguridad Debian Trixie; sin reinicios automáticos ni autoremove |
| AIDE | Perfil propio de archivos del sistema y timer diario; base inicial por clon |
| Fail2ban | Journal de SSH, 5 fallos en 10 minutos, bloqueo 10 minutos, nftables y puertos SSH detectados |
| SSH | Contraseña habilitada, root prohibido, sin forwarding/X11, 3 intentos por conexión, 60 segundos para autenticarse |

El límite de intentos SSH es por conexión. Fail2ban cuenta fallos detectados por origen y ventana temporal. Ninguno equivale a una defensa completa frente a ataques distribuidos.

No fuerza perfiles AppArmor en complain/unconfined a enforce. AppArmor se verifica activo; la cobertura real de cada aplicación se desarrolla en su perfil. No se modifican GRUB, particiones, políticas globales de contraseñas/PAM, cuentas de servicio, IP/DNS, puertos de escucha o reglas de routing.

**Firewall:** mantiene las reglas existentes y configura el bloqueo de SSH de Fail2ban. No establece una política general de denegación ni abre puertos de aplicación. La matriz de accesos, el firewall por función y su compatibilidad con Docker siguen siendo requisitos antes de producción; Fail2ban no los sustituye.

## 9.2 Obtener esta versión en Debian

En tu sesión SSH, como usuario normal:

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
python3 bin/configurar_base.py
```

Si Git pide acceso, usa tu usuario de GitHub y el token de lectura como contraseña. No lo incluyas en la URL ni lo guardes en la imagen. Si el token expiró, genera otro de lectura del mismo repositorio. Si Git indica cambios locales/conflicto, no uses reset/force: conserva los cambios para revisarlos.

El último comando imprime el plan; no hace cambios. La carpeta clonada por Git es `debian13-baseline`, no `debian13-baseline-main`.

## 9.3 Ejecutar todo el perfil

Mantén abierta la sesión y ejecuta desde tu usuario normal (no desde `sudo -i`):

```bash
sudo python3 bin/configurar_base.py --aplicar --sin-snapshot --usuario "$USER" --conexion "$SSH_CONNECTION"
```

Los valores de las variables se utilizan localmente para comprobar el contexto SSH. No necesitas compartir tus IP. El programa valida Debian/KVM, usuario, hora, sintaxis SSH/sudo y parámetros antes de las etapas relevantes. Detiene la ejecución si detecta errores; un fallo no deshace automáticamente todas las etapas anteriores.

APT puede iniciar/reiniciar servicios. Las nuevas actualizaciones automáticas de seguridad también pueden reiniciar servicios según los paquetes afectados; el reinicio automático de la VM queda desactivado. En clones con requisitos de disponibilidad, adaptar esta política a su ventana de mantenimiento antes de producción.

Cada ejecución guarda archivos anteriores y estado bajo `/var/lib/debian13-baseline/general-...`, privado de root. Una instalación parcial de paquetes requiere revisar APT; no ejecutamos purgas ni reparaciones forzadas.

## 9.4 Confirmar SSH una sola vez al terminar

El último paso programa una recuperación de los dos archivos SSH modificados a los **20 minutos**. El helper se guarda root:root en la carpeta privada, no en el checkout del usuario. Antes de recargar se valida sintaxis y configuración efectiva por usuario/IP; reglas `Match Host` dependientes de resolución DNS requieren revisión adicional si se utilizan.

**Sin cerrar la sesión original**, abre otra conexión SSH con contraseña desde tu PC. En esa nueva sesión:

```bash
sudo -v
cd ~/trabajo/debian13-baseline
sudo python3 bin/configurar_base.py --confirmar-ssh
```

Solo confirma si pudiste autenticarte y usar sudo en la conexión nueva. La confirmación registra tu comprobación; el script no demuestra por sí solo que hayas abierto otra conexión.

Si no confirmas a tiempo, se recupera SSH anterior. No reinicies antes de confirmar: el temporizador es transitorio y no sobrevive al reinicio. No realices otros cambios SSH mientras esté pendiente.

## 9.5 Comprobar al final

Desde la nueva sesión confirmada:

```bash
sudo python3 bin/configurar_base.py --verificar --usuario "$USER" --conexion "$SSH_CONNECTION"
sudo python3 bin/auditar.py --recopilar --salida /root
sudo journalctl -u ssh -u auditd -u fail2ban --since "15 minutes ago" --no-pager
sudo ausearch -m DAEMON_CONFIG -ts recent -i
```

El verificador muestra consultas `OK/REVISAR` sin publicar tus IP. Revisa también el evento `op=reconfigure`/`res=success` de auditd y los mensajes: enviar la señal de recarga no demuestra por sí solo su aceptación. Los errores de herramientas ausentes/agentes no enrolados en el diagnóstico no son automáticamente hallazgos de seguridad.

Después de confirmar SSH y revisar errores, reinicia:

```bash
sudo reboot
```

Reconecta y repite el verificador. Comprueba una nueva sesión SSH, sudo, hora, reglas audit y Fail2ban. La prueba manual de ban/unban con una dirección documental verifica la acción; el bloqueo real y la lectura de fallos de autenticación requieren una prueba desde un equipo de prueba distinto al administrativo.

## 9.6 AIDE: preparado en plantilla, inicializado por clon

El perfil propio `/etc/aide/baseline.conf` revisa `/etc`, binarios/bibliotecas del sistema y `/boot`. No incluye datos de BD, volúmenes Docker ni todo `/var`; ampliar por función. Tiene un worker y ejecución diaria de baja prioridad. No utiliza `aideinit` ni necesita instalar un servidor de correo.

El timer omite la comprobación hasta que exista `/var/lib/aide-baseline/base.db`. **Timer activo sin base no significa vigilancia activa.** La base se crea después de personalizar cada clon y validar su estado; así no aceptamos automáticamente diferencias de identidad o instalaciones posteriores.

En cada clon aprobado, una sola vez y sin cambios/actualizaciones concurrentes:

```bash
sudo sh -c 'set -eu; test ! -e /var/lib/aide-baseline/base.db; test ! -e /var/lib/aide-baseline/base.db.new; umask 077; aide --config=/etc/aide/baseline.conf --init; test -s /var/lib/aide-baseline/base.db.new; mv /var/lib/aide-baseline/base.db.new /var/lib/aide-baseline/base.db'
sudo systemctl start baseline-aide.service
sudo journalctl -u baseline-aide.service -n 30 --no-pager
```

Si la creación falla deja el archivo parcial para revisión; no se promueve automáticamente ni se sobreescribe una referencia existente. Revisar y aprobar diferencias antes de cualquier actualización de la base. Los resultados son locales hasta configurar envío/alertas en cada clon; una comprobación que detecta cambios puede devolver código no cero.

## 9.7 Qué queda antes de convertirla en plantilla

1. Revisar la verificación final tras reinicio; no certificar CIS por estos resultados.
2. Acordar con quien clona la VM cómo se regenerarán hostname/IP, `machine-id`, llaves de host SSH y credenciales de administración. Si se elige cloud-init, integrar y probar primero el datasource de Proxmox; instalarlo a ciegas puede cambiar la gestión de red.
3. Retirar credenciales de construcción, tokens y evidencias privadas de la imagen. Eliminar/revocar el token temporal en GitHub cuando no sea necesario.
4. Mantener agentes sin registrar y no incluir datos productivos. Usuarios/contraseñas de construcción también se heredan: definir su sustitución por credenciales individuales antes de dar acceso productivo.
5. En una ventana final, ejecutar el sellado correspondiente y apagar. **Este programa no borra llaves, machine-id, registros ni apaga automáticamente la VM.**
6. Probar dos clones aislados con identidades diferentes. Crear AIDE e inscribir agentes después de personalizar.

No llamar “lista para clonar” a la imagen hasta completar el método de sellado y la prueba de identidad. La política de firewall por función, aplicaciones, Docker/BD, agentes, soporte G DATA/FortiEDR, backup y pruebas de carga se validan antes de producción.

## 9.8 Recuperación

- Si falla SSH antes de confirmar: espera la reversión automática sin reiniciar, o pide acceso de recuperación.
- Para restaurar manualmente SSH, usa la ruta del registro mostrada por el programa. Por ejemplo, sustituyendo el ID real:

```bash
sudo python3 /var/lib/debian13-baseline/general-ID_REAL/runner.py --restaurar-ssh general-ID_REAL
```

Ese comando solo restaura un cambio pendiente; no revierte otros módulos ni desinstala paquetes. Los archivos de todas las etapas están inventariados con modo y copia anterior en `general.json`. Si falla una etapa, conserva ese registro y revisa la causa; no repetir indefinidamente ni usar `apt --force`.

## Referencias

- [OpenSSH Debian 13](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html): valores efectivos, precedencia y autenticación.
- [Fail2ban](https://manpages.debian.org/trixie/fail2ban/jail.conf.5.en.html): configuración `.local`, filtros/acciones y backend systemd.
- [auditd.conf](https://manpages.debian.org/trixie/auditd/auditd.conf.5.en.html): rotación, umbrales y acciones.
- [journald.conf](https://manpages.debian.org/trixie/systemd/journald.conf.5.en.html): almacenamiento y límites.
- [Unattended Upgrades](https://github.com/mvo5/unattended-upgrades/blob/master/data/50unattended-upgrades.Debian): orígenes y reinicios.
- [AIDE](https://manpages.debian.org/trixie/aide/aide.conf.5.en.html): configuración y bases de referencia.
- [systemd-run](https://manpages.debian.org/trixie/systemd/systemd-run.1.en.html): temporizador de recuperación transitorio.
