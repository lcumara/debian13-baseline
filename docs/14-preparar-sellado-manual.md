# 14. Preparación del sellado manual

**Objetivo:** recopilar el estado que determina cómo limpiar la VM sin perder regeneración de llaves, acceso ni firewall. Esta fase no borra identidades ni apaga la VM.

El perfil actual no usa Cloud-Init. No ejecutar los comandos de limpieza Cloud-Init del capítulo 4.

## Comprobación previa en la VM

```bash
sudo systemctl cat sshd-keygen.service
sudo systemctl show ssh.service -p Requires -p Wants -p After
sudo ls -ld /etc/machine-id /var/lib/dbus/machine-id
sudo systemctl cat baseline-firewall.service
sudo systemctl list-timers --all --no-pager
dpkg-query -W -f='${binary:Package}\t${Version}\n' | grep -Ei 'wazuh|zabbix|forti|gdata|g-data|cloud-init' || true
sudo test ! -s /var/ossec/etc/client.keys; printf 'Sin clave Wazuh (0 esperado): %s\n' "$?"
sudo test ! -e /etc/zabbix/zabbix_agent2.psk; printf 'Sin PSK Zabbix (0 esperado): %s\n' "$?"
sudo test ! -e /var/lib/aide-baseline/base.db; printf 'Sin referencia AIDE por clon (0 esperado): %s\n' "$?"
```

Los test no imprimen secretos. Estos nombres de paquetes/rutas no detectan todos los agentes, certificados o credenciales posibles. Hay que revisar también credenciales Git/APT, llaves privadas del usuario/root, archivos temporales, diagnósticos, historial y artefactos de instalación. No imprimir ni publicar su contenido.

## Condiciones para el procedimiento final

1. Preservar el firewall y sus ejecutores privados (ver guía de operación).
2. Confirmar regeneración de llaves de host antes de SSH y tratamiento de machine-id/DBus al primer arranque. No borrar llaves a ciegas por asumir que el paquete las recreará.
3. Definir acceso inicial por consola y cambio de contraseña por clon. No conservar una contraseña administrativa compartida en servidores productivos.
4. Exportar evidencias privadas y seleccionar datos de construcción retirables. La eliminación de archivos no garantiza borrado forense del disco virtual.
5. Apagar tras el sellado; el encargado de Proxmox convierte la VM apagada en plantilla. No arrancar otra vez la base sellada para probarla.
6. Crear dos clones con MAC/UUID distintos; arrancarlos con NIC desconectada o red aislada. Configurar hostname/IP/DNS desde consola antes de conectarlos a redes compartidas, evitando la IP heredada de la plantilla.
7. Verificar machine-id y huellas SSH distintas, acceso sudo/SSH, firewall y servicios. Registrar agentes con identidad nueva; inicializar AIDE por clon.

## Sellado técnico disponible para este piloto

El operador confirmó `sshd-keygen.service` con `ssh-keygen -A`, requerido y ordenado antes de SSH, y una copia independiente de identidad en `/var/lib/dbus/machine-id`. El ejecutor comprueba esas dependencias de nuevo en la VM.

Se instala un drop-in que elimina la condición FirstBoot y conserva las condiciones de ruta. `ssh-keygen -A` crea únicamente llaves faltantes en cada arranque. Esto permite dejar machine-id vacío sin forzar la semántica de primer arranque que también puede aplicar presets de servicios. D-Bus pasa a enlazar `/etc/machine-id`.

### Antes de apagar

- El encargado debe poder acceder a la consola Proxmox de los clones para cambiar nombre/red y contraseña antes de conectarlos a una red compartida. No borrar ahora el único usuario administrativo.
- Revisar/retirar credenciales de construcción, informes privados e historiales; exportar evidencias necesarias antes de borrar cualquier archivo. La comprobación detecta algunas rutas habituales y detiene el sellado si aparecen, sin mostrar contenido. No es un escáner completo de secretos.
- Mantener el repositorio accesible al encargado según la guía de operación. La copia en home se puede conservar, pero no debe contener tokens ni informes privados.
- No distribuir la imagen fuera del entorno autorizado: conserva cuentas y hashes de contraseña, registros e información de construcción. Un sellado de identidad no es una sanitización completa ni un borrado forense.

Desde la VM:

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
sudo python3 bin/sellar_identidad.py --comprobar
```

Si termina correctamente y están resueltos los puntos anteriores, el comando siguiente **borra identidades de la VM y la apaga**:

```bash
sudo python3 bin/sellar_identidad.py --sellar-y-apagar
```

Limpia caché APT y semilla aleatoria de systemd (detiene el servicio antes de retirar su archivo), elimina llaves SSH de host, prepara machine-id y D-Bus. Conserva firewall, políticas y ejecutores privados. No borra usuarios/home/historiales/logs ni intenta limpiar agentes registrados: si detecta paquetes de agentes o Cloud-Init, se detiene para aplicar su procedimiento específico.

Si el comando falla después de comenzar, conservar la sesión/consola y resolver el error; no volver la VM a producción. No hay reversión de llaves borradas. Después del apagado, convertir en plantilla sin volver a encender la base.

### En Proxmox y en cada clon

1. Convertir la VM apagada en plantilla; crear dos clones de prueba con UUID SMBIOS y MAC diferentes.
2. Desconectar la NIC de cada clon o usar una red de preparación aislada que evite conflictos de IP heredada.
3. Desde consola, asignar hostname y adaptar `/etc/hosts`, red/DNS según la configuración real. Cambiar la contraseña administrativa con `passwd` sin restablecer artificialmente su antigüedad. No cambiar simultáneamente la red de la plantilla y todos los clones.
4. Verificar en cada clon:

```bash
test -s /etc/machine-id && echo 'machine-id generado'
sha256sum /etc/machine-id
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
sudo systemctl status sshd-keygen.service ssh.service baseline-firewall.service --no-pager
systemctl --failed
```

Los hashes de machine-id y huellas SSH deben ser distintos entre clones. No es necesario publicarlos en Git. Conectar la NIC a la red definitiva solo con identidad y dirección únicas, probar SSH/sudo y repetir los verificadores desde la sesión SSH nueva. Una huella SSH nueva se verifica desde consola; no desactivar su comprobación en el cliente.

5. Configurar agentes y función, comprobar recepción/alertas e inicializar AIDE según capítulo 9.

**Límite de validación:** pruebas locales unitarias con llamadas simuladas; el ciclo real de sellar/arrancar y la unicidad solo se aceptan tras verificar los dos clones. Los pendientes CIS del capítulo 13 permanecen.

Fuente: [machine-id Debian 13, semántica de primer arranque](https://manpages.debian.org/trixie/systemd/machine-id.5.en.html).
