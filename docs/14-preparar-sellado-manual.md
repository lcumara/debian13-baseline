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

**Estado:** procedimiento destructivo final todavía pendiente de la comprobación previa. El sellado técnico no resuelve automáticamente los pendientes CIS del capítulo 13.
