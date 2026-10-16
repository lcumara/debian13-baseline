# 5. Registrar agentes por servidor

**Objetivo:** que cada clon aparezca una sola vez, con identidad propia, en las consolas de seguridad y monitoreo.

**Dónde:** clon con nombre/IP definitivos, todavía aislado del tráfico productivo.

## 5.1 Orden y compatibilidad

1. Confirmar hostname/FQDN, DNS, hora e identidad única.
2. Seleccionar versiones soportadas por los servidores centrales y Debian 13/kernel actual.
3. Instalar un agente; comprobar su funcionamiento y consumo.
4. Añadir el siguiente y repetir. Probar reinicio y carga representativa con todos presentes.

“Última estable” no significa compatible con tu manager o con otro agente. Registra paquete, versión, hash, repositorio y matriz de soporte. No fijamos números de build empresariales sin conocer la consola contratada.

```bash
hostname -f
uname -r
chronyc tracking
dpkg-query -W -f='${Package}\t${Version}\n' > /tmp/paquetes-piloto.txt
```

## 5.2 Wazuh

Usa **Deploy new agent / Desplegar nuevo agente** en tu consola Wazuh. Selecciona Debian/Linux, arquitectura correcta, manager, nombre único y grupo del perfil. Revisa el comando generado antes de ejecutarlo en el clon; las opciones de enrollment dependen de la configuración institucional.

Procedimiento oficial: [instalación del agente Linux](https://documentation.wazuh.com/current/installation-guide/wazuh-agent/wazuh-agent-package-linux.html).

Después de instalar y enrolar:

```bash
sudo systemctl enable --now wazuh-agent
sudo /var/ossec/bin/wazuh-control status
sudo journalctl -u wazuh-agent -n 30 --no-pager
```

**Esperado en la consola:** agente nuevo, nombre correcto, conexión reciente, inventario recibido y política SCA Debian 13 identificada. Registra nombre/versión/hash de esa política. El estado local activo no prueba que el manager reciba datos.

No copies `/var/ossec/etc/client.keys` entre servidores. Para reinstalar un equipo, coordina la baja de la identidad anterior desde la consola; no borres todas las altas ni reutilices el ID de otro equipo.

## 5.3 Zabbix Agent 2

Preferencia inicial: comprobaciones **activas** con TLS-PSK, si las plantillas del servidor Zabbix lo permiten. Instala el paquete oficial para Debian 13 y una rama compatible con tu servidor/proxy. Revisa que la plantilla de monitoreo use ítems activos: cambiar el agente no convierte ítems pasivos en activos.

Crea una PSK diferente por host, sin imprimirla en terminal ni almacenarla en Git:

```bash
sudo install -o root -g zabbix -m 0640 /dev/null /etc/zabbix/zabbix_agent2.psk
sudo sh -c 'umask 027; openssl rand -hex 32 > /etc/zabbix/zabbix_agent2.psk'
sudo stat -c '%U:%G %a %n' /etc/zabbix/zabbix_agent2.psk
```

Ejecuta esa generación **una sola vez** por alta: repetirla cambia el secreto y corta la conexión hasta actualizar la consola. El paquete debe haber creado antes el grupo `zabbix` y OpenSSL debe estar instalado. Transfiere el secreto a la consola mediante el canal de secretos aprobado.

Adapta el archivo principal `/etc/zabbix/zabbix_agent2.conf`, evitando definiciones duplicadas en sus includes:

```ini
Hostname=FQDN_REAL_DEL_CLON
ServerActive=DNS_REAL_DEL_SERVIDOR_O_PROXY:10051
TLSConnect=psk
TLSPSKIdentity=IDENTIDAD_UNICA_DEL_CLON
TLSPSKFile=/etc/zabbix/zabbix_agent2.psk
```

Para modo exclusivamente activo, elimina/comenta `Server=` en todos los archivos incluidos. No uses `StartAgents=0`: no es la opción de Agent 2. Configura nombre y cifrado correspondientes en el host de Zabbix.

```bash
sudo zabbix_agent2 -T -c /etc/zabbix/zabbix_agent2.conf
sudo systemctl enable --now zabbix-agent2
sudo systemctl restart zabbix-agent2
sudo ss -lntp
sudo journalctl -u zabbix-agent2 -n 30 --no-pager
```

**Esperado:** validación correcta, datos recientes en Zabbix y ausencia de escucha en 10050 para el perfil exclusivamente activo. Si se necesitan ítems pasivos, usa `Server=` restringido al proxy/servidor, `TLSAccept=psk` y firewall limitado; documenta ese perfil distinto.

Fuente: [parámetros oficiales de Agent 2](https://www.zabbix.com/documentation/7.4/en/manual/appendix/config/zabbix_agent2).

## 5.4 FortiEDR

Usa el instalador Linux proporcionado por **tu consola FortiEDR**, correspondiente al tenant/grupo y arquitectura. FortiClient no es el mismo producto.

La [matriz consultada](https://docs.fortinet.com/document/fortiedr/7.2.3/collector-system-requirements/633631/supported-operating-systems) contempla Debian 13 con condiciones de versión de Collector. Confirma build y kernel exactos antes de instalar; no basta con que exista un `.deb`.

Sobre el archivo entregado por tu administrador, antes de instalar:

```bash
sha256sum /ruta/instalador-fortiedr.deb
dpkg-deb --field /ruta/instalador-fortiedr.deb Package Version Architecture
uname -r
```

Compara el hash con una fuente confiable del proveedor; un hash calculado por ti solo no autentica el archivo. Sigue el comando del build suministrado y sus instrucciones de configuración. No inventamos nombre del paquete, token ni servicio.

**Aceptación:** equipo correcto en consola, política aplicada, telemetría reciente, prueba de detección autorizada por el fabricante y funcionamiento tras reinicio. Comprobar convivencia con AppArmor, Docker, Wazuh y antivirus. Las exclusiones deben ser específicas y justificadas.

## 5.5 G DATA: pendiente de soporte confirmado

La [matriz pública consultada](https://www.gdata.de/en/business/endpoint-security-software/technical-information) enumera Debian 11/12; no permitió confirmar Debian 13. Antes de ejecutar un instalador, solicita al proveedor confirmación para **producto, build, Debian 13, kernel y convivencia con FortiEDR**.

Una vez confirmado, descarga el instalador desde la consola del producto y registra su hash/versiones. No fuerces paquetes destinados a Debian 12 ni reutilices un instalador con identidad de otro host.

**Esta etapa está pendiente:** no hay un comando universal fiable de G DATA que podamos publicar con los datos actuales. Si es obligatorio para producción, su compatibilidad es un requisito de aceptación por resolver.

## 5.6 Comprobación conjunta

```bash
systemctl --failed
sudo ss -lntup
free -h
df -h
```

Mide también CPU, latencia y errores bajo carga representativa. Confirma con las consolas recepción y una alerta controlada; guarda evidencias privadas. No agregues exclusiones amplias de todo `/var`, Docker o directorios de BD solo para elevar rendimiento.
