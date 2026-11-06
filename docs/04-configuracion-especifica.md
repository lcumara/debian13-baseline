# 4. Configuración Específica: Servicios y Agentes

**Objetivo:** Configurar de manera individual e independiente cada servidor según su función en la infraestructura (servicios dedicados, certificados y agentes corporativos), garantizando identidades, claves y registros no compartidos.

---

## 4.1 Principio de Separación: Parte 1 vs Parte 2

El aseguramiento de infraestructura institucional se compone de dos niveles:

1. **Parte 1 (Configuración General - Línea Base):**
   - Endurecimiento idéntico y homogéneo del sistema operativo Debian 13.
   - Parámetros de kernel, políticas PAM (`pwquality`, `faillock`), contraseñas a 10 años, límites del sistema, auditoría (`auditd`, `rsyslog`) y firewall base UFW bloqueando todo el tráfico entrante salvo SSH administrativo.

2. **Parte 2 (Configuración Específica - Rol y Agentes):**
   - Configuración propia del servicio de red que alojará el host.
   - Reglas de firewall UFW dedicadas al servicio.
   - Certificados SSL/TLS propios de cada servicio.
   - Enrolamiento de agentes de seguridad y monitoreo (Wazuh, Zabbix, EDR) con identidades, IDs y secretos criptográficos únicos.

> **Importante:** Cada servidor se aprovisiona y endurece de manera individual. No se utilizan plantillas genéricas ni clonado de imágenes de disco para evitar la duplicación accidental de:
> - `machine-id` de systemd y D-Bus.
> - Llaves privadas SSH del host (`/etc/ssh/ssh_host_*_key`).
> - Llaves criptográficas de Wazuh (`/var/ossec/etc/client.keys`).
> - Secretos compartidos TLS-PSK de Zabbix (`/etc/zabbix/zabbix_agent2.psk`).
> - Certificados digitales y claves privadas TLS/SSL.
> - Registros e historiales administrativos.

---

## 4.2 Matriz de Perfiles y Servicios

| Rol del Servidor | Servicio Principal | Puertos en UFW | Consideraciones de Seguridad |
|---|---|---|---|
| **Proxy Frontend** | Nginx Reverse Proxy | `443/tcp` (HTTPS) | Certificados SSL públicos, cabeceras de seguridad HSTS/CSP. Puerto 80 cerrado si no se requiere HTTP. |
| **Proxy Backend** | Nginx Balanceador Interno | Puertos internos específicos | Permitir tráfico entrante únicamente desde la subred del Frontend. |
| **Base de Datos** | PostgreSQL / MySQL | `5432/tcp` o `3306/tcp` | Acceso restringido exclusivamente a las IPs de los servidores de aplicación autorizados. |
| **Host Docker** | Docker Engine | Reglas según contenedor | Aislar el daemon y coordinar reglas con la política de UFW según [Capítulo 6](06-docker.md). |

---

## 4.3 Procedimiento de Configuración Específica

### Paso 1: Asignar Identidad de Red y Hostname Definitivo
Antes de desplegar el servicio o enrolar agentes:
```bash
# Verificar hostname único institucional
hostnamectl set-hostname srv-proxy01.ejemplo.local
hostnamectl status

# Verificar sincronización horaria
timedatectl show -p NTP -p NTPSynchronized
```

### Paso 2: Configurar el Servicio Dedicado (Ejemplo: Proxy Frontend)
1. Instalar el servicio necesario:
   ```bash
   sudo apt update
   sudo apt install -y nginx
   sudo systemctl enable --now nginx
   ```
2. Desplegar los certificados SSL en `/etc/ssl/certs/` y `/etc/ssl/private/` con permisos `0600` para la llave privada.
3. Habilitar la apertura del puerto en UFW:
   ```bash
   sudo ufw allow 443/tcp comment "Nginx HTTPS"
   sudo ufw status verbose
   ```

### Paso 3: Enrolar Agentes Corporativos
Seguir las instrucciones detalladas del [Capítulo 5: Agentes](05-agentes.md):
- **Wazuh:** Registrar con nombre único (`agent_name`), obtener ID propio del Manager y verificar `/var/ossec/etc/client.keys`.
- **Zabbix:** Generar PSK criptográfico aleatorio único por host y registrarlo en el proxy o servidor Zabbix.
- **Antivirus / EDR:** Instalar y verificar la comunicación con la consola central.

### Paso 4: Generar la Línea Base de Integridad (AIDE)
Una vez que el servidor tiene todos sus paquetes, servicios y agentes instalados y funcionando, se toma la huella de integridad del sistema de archivos:

```bash
sudo aideinit
sudo cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db
sudo chmod 0600 /var/lib/aide/aide.db
```

A partir de este momento, cualquier modificación no autorizada en binarios del sistema, configuraciones bajo `/etc` o librerías será detectada por el chequeo periódico de AIDE.
