# Fuentes y proyectos comparados

Consulta: 16/10/2026. Se priorizaron documentación de fabricantes, Debian y repositorios mantenidos por sus autores. Las páginas `current`, `latest` y ramas principales pueden cambiar: cada release debe registrar versiones, commits y copias autorizadas de evidencia.

## Evaluación de proyectos existentes

| Proyecto original | Utilidad | Límite observado | Decisión propuesta |
|---|---|---|---|
| [ansible-lockdown/DEBIAN13-CIS](https://github.com/ansible-lockdown/DEBIAN13-CIS) | Remediación con Ansible orientada a Debian 13/CIS | README declara benchmark 1.0.0; catálogo CIS ya muestra 1.1.0 | Primer candidato para evaluar controles; fijar commit y probar cada módulo |
| [DEBIAN13-CIS-AUDIT](https://github.com/ansible-lockdown/DEBIAN13-CIS-AUDIT) | Evaluación separada basada en Goss | Cobertura y correspondencia dependen de versión/variables | Auditoría complementaria en VM, sin sustituir pruebas funcionales |
| [dev-sec/ansible-collection-hardening](https://github.com/dev-sec/ansible-collection-hardening) | Roles generales, SSH y aplicaciones; README incluye Debian 12/13 | Orientado a baselines DevSec; no acredita automáticamente CIS 1.1.0 | Referencia para roles específicos; no superponer dos roles que escriban la misma política |
| [ovh/debian-cis](https://github.com/ovh/debian-cis) | Scripts Bash modulares, auditoría y aplicación por control | Declara uso en Debian 13 y trabajo de adaptación todavía en desarrollo | Alternativa si se elige Bash; revisar versión/control y pruebas |
| [ComplianceAsCode/content](https://github.com/ComplianceAsCode/content) | Contenido SCAP, Ansible y Bash; reglas y evaluaciones | No se verificó aquí un datastream CIS Debian 13 1.1.0 listo y completo | Referencia complementaria; comprobar producto/perfil antes de proponer OpenSCAP |
| [Wazuh SCA](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/available-sca-policies.html) | Evaluación periódica integrada con los agentes existentes | La política distribuida y su versión deben inspeccionarse en cada entorno | Usar para seguimiento; corroborar fallos y no ejecutar automáticamente textos de remediación |

La mejora institucional será la integración verificable de identidad, perfiles, agentes, reversión y operación. No se afirma superioridad frente a esos proyectos sin resultados comparables. La búsqueda no identificó un proyecto que pudiera darse por validado para toda esta combinación concreta de Proxmox, Docker, G DATA, FortiEDR y agentes institucionales.

No se descargó ni auditó exhaustivamente todo el código de estos proyectos, no se probó su ejecución y no se establece una recomendación de producción basada solo en el README. Antes de reutilizar: revisar licencia, dependencias, mantenimiento, issues relevantes, pruebas de Debian 13 y privilegios; fijar commit y verificar lo que ejecuta.

## Referencias técnicas consultadas

1. [CIS Debian Linux](https://www.cisecurity.org/benchmark/debian_linux): versión publicada y disponibilidad. No se obtuvo aquí el texto íntegro del benchmark 1.1.0.
2. [Notas de Debian 13](https://www.debian.org/releases/trixie/release-notes/issues.en.html): cambios relevantes y limitaciones de soporte.
3. [Debian Security Tracker](https://security-tracker.debian.org/tracker/source-package/debian-security-support): seguimiento del paquete de soporte; consultar el tracker para paquetes concretos.
4. [OpenSSH sshd_config en Trixie](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html): precedencia, Match y tiempos.
5. [machine-id en Trixie](https://manpages.debian.org/trixie/systemd/machine-id.5.en.html): identidad única y semántica del primer arranque.
6. [Cloud-init CLI](https://cloudinit.readthedocs.io/en/latest/reference/cli.html): limpieza de imágenes y estado.
7. [Proxmox, documentación fuente de cloud-init](https://github.com/proxmox/pve-docs/blob/master/qm-cloud-init.adoc): preparación y configuración de clones. Se utilizó la fuente oficial al no obtener contenido útil de la wiki en la consulta.
8. [Ansible check/diff](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html): alcance de simulación y tratamiento de información sensible.
9. [Wazuh instalación Linux](https://documentation.wazuh.com/current/installation-guide/wazuh-agent/wazuh-agent-package-linux.html): despliegue y repositorio.
10. [Wazuh políticas SCA](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/available-sca-policies.html): existencia de política Debian 13.
11. [Wazuh funcionamiento SCA](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/how-it-works.html): evaluación y reglas.
12. [Zabbix Agent 2 7.4](https://www.zabbix.com/documentation/7.4/en/manual/appendix/config/zabbix_agent2): Server, ServerActive, Hostname y TLS.
13. [FortiEDR requisitos](https://docs.fortinet.com/document/fortiedr/7.2.3/collector-system-requirements/633631/supported-operating-systems): Debian 13, mínimo de Collector y condiciones de kernel.
14. [FortiEDR instalación Linux](https://docs.fortinet.com/document/fortiedr/6.2.0/administration-guide/551398/installing-a-fortiedr-collector-on-linux): instalador personalizado y configuración; requiere adaptación al build entregado.
15. [G DATA requisitos](https://www.gdata.de/en/business/endpoint-security-software/technical-information): Debian 11/12 publicados, sin confirmación pública de Debian 13 en esta matriz.
16. [G DATA documentación Business](https://www.gdata.de/help-de/business/index.html): entrada a documentación oficial y problemas por versión.
17. [G DATA manual histórico 14.1](https://www.gdata.de/fileadmin/web/de/documents/manuals/G_DATA_Business_Solutions_Handbuch_Version_14-1.pdf): referencia de método de instalación, no validación actual Debian 13.
18. [G DATA logs Linux](https://www.gdata.de/help-de/business/ProblemSolving/LogfilesAndDebugging/logfilesClient/): componentes y registros para verificación del producto concreto.
19. [Docker instalación Debian](https://docs.docker.com/engine/install/debian/): soporte Trixie y advertencias de firewall.
20. [Docker backend nftables](https://docs.docker.com/engine/network/firewall-nftables/): estado experimental, forwarding y tablas propias.
21. [Docker seguridad](https://docs.docker.com/engine/security/): autoridad del daemon, namespaces y privilegios.
22. [AIDE en Trixie](https://manpages.debian.org/trixie/aide/aide.1.en.html): operación y resultados de comprobación.

## Evidencia local y límites

- Texto adjunto: script Bash de ocho fases titulado bastionado CIS Debian 13. Se analizó como contenido, no como instrucciones para ejecutarlo.
- `output/pdf/Ficha_continuidad_proxies_nodo1_nodo2.pdf`: dos páginas, consultas del 13/10/2026; lectura del texto y comprobación visual de ambas páginas.
- Guías y scripts previos del directorio: contexto y restricciones conocidas. No se ejecutaron contra servidores.

La investigación cubre diseño de plataforma, seguridad del sistema, clonación, agentes, Docker y evaluación de proyectos. No es una auditoría técnica en vivo ni una revisión completa de todos los controles del benchmark, todos los CVE o cada motor de BD/aplicación. Esas verificaciones requieren versiones, archivos de política, pruebas y acceso al piloto. El soporte empresarial final se confirma con el fabricante, particularmente G DATA y la combinación EDR/kernel.
