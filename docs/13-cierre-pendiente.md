# 13. Lista Consolidada de Cierre y Verificación

**Estado:** Servidor Debian 13 con línea base de endurecimiento aplicada y verificada (Parte 1). La entrega a producción requiere completar la configuración específica por rol y el enrolamiento individual de agentes (Parte 2).

---

## 13.1 Parámetros y Excepciones Institucionales Acordadas

- **Política de contraseñas:** Caducidad de 3650 días (10 años), aviso preventivo 365 días antes y sin bloqueo forzoso por inactividad (`chage -M 3650 -m 1 -W 365 -I -1 -E -1`).
- **Esquema de particionado:** Se conserva la distribución de volúmenes existente; no se fuerza separación de `/home`, `/var/tmp`, `/var/log` ni `/var/log/audit`.
- **Acceso administrativo SSH:** Endurecido con llaves SSH (Ed25519), sin reenvío de puertos ni X11, y acceso directo de `root` deshabilitado (`PermitRootLogin no`).
- **Firewall del host:** Estandarizado en **UFW** (backend nativo `iptables-nft`), IPv6 desactivado (`IPV6=no`) y Fail2ban enlazado directamente (`banaction = ufw`).
- **Aprovisionamiento individual:** Eliminación de plantillas maestras y clonación; cada servidor se aprovisiona y configura de forma directa para garantizar unicidad de credenciales, agentes e identidades.

---

## 13.2 Checklist de Verificación por Servidor (Parte 2: Específica)

Cada servidor debe completar su fase específica antes de integrarse al tráfico de producción:

| Área | Verificación Requerida | Estado |
|---|---|---|
| **Identidad de Host** | Hostname FQDN institucional definitivo, IP estática, DNS y zona horaria verificados. | Pendiente por servidor |
| **Rol de Servicio** | Servicio dedicado instalado y configurado (ej. Nginx Proxy Frontend o Backend). | Según función |
| **Firewall Específico** | Puertos de servicio abiertos exclusivamente en UFW (ej. `443/tcp` para Frontend). | Según función |
| **Certificados SSL/TLS** | Certificados emitidos para el FQDN del servidor instalados con permisos estrictos (`0600`). | Pendiente por servicio |
| **Agente Wazuh** | Enrolado con nombre y ID únicos contra el Wazuh Manager; llave generada en `client.keys`. | Pendiente por servidor |
| **Agente Zabbix** | PSK aleatoria única generada (`zabbix_agent2.psk`), configurado en modo activo. | Pendiente por servidor |
| **Agente EDR / AV** | Conectividad y reporte activo contra la consola central de seguridad. | Según contratación |
| **Línea Base AIDE** | Base de integridad generada tras finalizar la instalación de paquetes (`aideinit`). | Requerido al cierre |

---

## 13.3 Criterio de Aceptación para Producción

Un servidor se considera formalmente entregado para producción cuando:
1. La **Parte 1 (General)** tiene todos sus verificadores en `OK` (`configurar_base.py`, `completar_base.py`, `cuentas_tareas.py`, UFW y Fail2ban).
2. El servicio principal responde correctamente en sus puertos y rechaza orígenes o protocolos no autorizados.
3. Los agentes de seguridad y monitoreo reportan activamente a sus respectivas consolas sin alertas críticas.
4. La base AIDE está generada y su timer programado.
