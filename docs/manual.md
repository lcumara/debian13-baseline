# Manual de diseño y preparación de la base Debian 13

> Documento de diseño de referencia. Para ejecutar el piloto actual, comienza por [la guía operativa numerada](01-laboratorio.md); consulta el [estado de implementación](../CHANGELOG.md).

**Estado:** propuesta de ingeniería, edición 0.1. Alcance confirmado: VM Proxmox; algunas VM incorporarán Docker. Fecha de consulta: 16/10/2026, America/La_Paz.

## 1. Objetivo mejorado

Construir una plataforma de servidores Debian 13 que permita instalar, endurecer, clonar, personalizar, validar y mantener cada instancia mediante procedimientos reproducibles. Cada servidor tendrá una identidad y secretos propios, controles comunes verificables y un perfil acorde con su servicio. La incorporación de aplicaciones y los cambios de IP o nombre deberán conservar los controles aplicables y activar una nueva validación.

La plantilla es el punto de partida de esa plataforma. El resultado depende también de parches posteriores, permisos, aplicaciones, red, administración de Proxmox, copias y respuesta a incidentes. No existe una configuración máxima que sea adecuada para todos los usos.

**Criterio de éxito propuesto:** todos los controles críticos aplicables superados; acceso, aplicaciones, monitoreo y restauración probados; excepciones con responsable y vencimiento; versión y evidencia identificables. Un objetivo porcentual de CIS se fija después del diagnóstico y de definir el denominador.

CIS publica actualmente Debian Linux 13 **1.1.0**. El encabezado del script indica 1.0 y el repositorio DEBIAN13-CIS consultado declara 1.0.0: se requiere una comparación de versiones, no asumir equivalencia. [CIS Debian](https://www.cisecurity.org/benchmark/debian_linux), [Ansible Lockdown](https://github.com/ansible-lockdown/DEBIAN13-CIS).

## 2. Separación en cuatro capas

| Capa | Contenido | Momento |
|---|---|---|
| Base común | SO mínimo, repositorios confiables, controles de acceso, registros, auditoría, AppArmor, política de parches y configuraciones de integridad | Construcción de plantilla |
| Identidad | Hostname/FQDN, IP, DNS, MAC/UUID, machine-id, claves SSH del servidor, certificados y cuentas de acceso | Primer arranque aislado de cada clon |
| Función | Proxy, aplicación, base de datos o Docker; puertos, permisos, montajes, servicios y excepciones | Antes del paso a producción |
| Integraciones y operación | Registro individual en Wazuh/Zabbix/EDR/AV, respaldos, alertas, inventario y mantenimiento | Tras identidad definitiva y antes de recibir tráfico de producción |

Cambiar solamente hostname e IP no individualiza un clon. La identidad de los agentes, PSK, claves SSH, certificados y estado de cloud-init también cuentan.

Recomiendo una imagen base única y perfiles combinables. Mantener una segunda imagen con Docker solo si acelera despliegues y puede reconstruirse mediante el mismo proceso. No instalar Nginx, motores de BD o Docker en toda la flota por anticipado.

## 3. Formato del manual y del ejecutor

**Markdown + Ansible + inventario YAML + evidencias JSON**, dentro de un repositorio privado. Markdown mantiene comandos copiables, historial y revisión; el PDF será una edición de consulta/aprobación. Word puede servir para un acta, pero no debería ser el origen de los comandos.

Cada procedimiento debe incluir: propósito, aplicabilidad, entradas, dependencias, configuración candidata, validación, aplicación, prueba funcional, reversión y evidencia. Evitar un bloque único que cambie red, PAM, GRUB y agentes a la vez.

Arquitectura prevista del motor — todavía por implementar:

```text
inventories/        datos por ambiente y por host, sin secretos en claro
roles/base/        paquetes y configuraciones comunes
roles/access/      SSH, sudo y PAM con transición controlada
roles/network/     firewall por perfil y origen
roles/audit/       auditoría, logs, integridad y políticas de evaluación
roles/docker/      motor, red y controles de contenedores
roles/agents/      despliegue y registro específico de cada producto
playbooks/         diagnóstico, base, personalización, rol y validación
docs/              explicación y procedimientos de recuperación
tests/             pruebas estáticas y escenarios en VM
```

Contrato del futuro ejecutor:

1. `diagnosticar`: estado real y evidencia, sin remediación.
2. `planificar`: variables resueltas, diferencias y controles afectados.
3. `aplicar-base`: módulos explícitos sobre una VM de construcción identificada.
4. `sellar`: operación exclusiva de imagen; verifica condiciones y termina con apagado.
5. `personalizar`: instancia única, inventario definitivo y acceso probado.
6. `registrar-agentes`: credenciales únicas y verificación en consolas.
7. `validar`: función, seguridad y evidencia posterior al reinicio.

El `--check` de Ansible es una simulación parcial según soporte de los módulos. No valida conectividad ni reversión real. Deshabilitar diferencias y salida de secretos en tareas sensibles; revisar tareas que fuercen ejecución aun en check mode. [Ansible](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html).

## 4. Base común y controles por contexto

Las siguientes son recomendaciones de diseño. No sustituyen el texto oficial de cada control CIS ni prueban que ya se haya aplicado.

| Área | Política común propuesta | Adaptación y comprobación |
|---|---|---|
| Instalación | Debian 13 mínimo, sin escritorio ni servicios ajenos a su función | Imagen verificada, arquitectura y firmware documentados |
| APT | Trixie, trixie-updates y trixie-security; firmas válidas; keyrings delimitados por Signed-By | No mezclar testing/unstable ni desactivar verificación; terceros por necesidad |
| Parches | Aplicación frecuente con responsable y plazo por exposición | Piloto, pruebas y reinicio; no dejar kernel antiguo activo indefinidamente |
| Acceso | Administradores individuales, sudo acotado, root SSH deshabilitado como objetivo | Probar llaves y recuperación antes de retirar contraseña SSH; MFA en bastión/VPN o integración validada |
| SSH | Acceso desde redes administrativas, registro suficiente, funciones innecesarias restringidas | Revisar túneles, SFTP, automatización y Match antes de limitar |
| PAM/cuentas | Política institucional, bloqueo de cuentas de servicio y mínima capacidad de login | Probar calidad, historial y bloqueo con usuario de prueba; no bloquear cuentas críticas accidentalmente |
| Red | Denegar entradas no autorizadas; permitir solo flujos documentados | IPv4 e IPv6; DNS, NTP, DHCP/RA si aplican; administración y monitoreo por origen |
| Salidas | Inventariar y posteriormente restringir destinos/servicios | APT, PKI, respaldos, proxies, agentes y aplicación; no asumir que salida ACCEPT controla exfiltración |
| Auditoría | auditd selectivo, tiempos fiables, retención dimensionada y envío central | Verificar eventos perdidos, espacio y alerta; decidir fail-open/fail-closed por disponibilidad |
| Logs | Journal persistente cuando corresponda, rotación y recepción central autenticada | Evitar duplicación indiscriminada journal/rsyslog/Wazuh; probar recepción y búsqueda |
| AppArmor | Activo y perfiles efectivos para servicios relevantes | Desarrollar perfil en laboratorio, probar carga y luego enforce; instalado no equivale a protegido |
| Integridad | FIM Wazuh y/o AIDE con alcance justificado | Base confiable tras configurar el host; no aceptar automáticamente toda diferencia |
| Discos | Diseño LVM/particiones que evite que logs o temporales llenen el sistema | Evaluar /var/log, /var/log/audit, /tmp, datos y Docker según carga; tamaños medidos |
| Montajes | nodev/nosuid/noexec donde sean compatibles | noexec puede romper instaladores y runtimes; no es barrera suficiente por sí solo |
| Kernel | Deshabilitar funciones/módulos no usados; restringir interfaces sensibles según necesidad | Validar sysctl con Docker, EDR, depuración y red asimétrica; no copiar listas universales |
| Arranque | Control de consola Proxmox, arranque y almacenamiento | UEFI/Secure Boot y cifrado según soporte de kernel/agentes y modelo de recuperación |
| Servicios | Usuario propio, mínimos permisos, límites y aislamiento systemd | No aplicar todos los sandbox flags a todos los servicios; verificar escritura y sockets necesarios |
| Secretos | Almacén externo; permisos mínimos; rotación y revocación | Nunca en imagen, repositorio, historial, variables visibles del proceso o informe |
| Copias | Copias independientes y protegidas con credenciales separadas | Consistencia de BD y volúmenes; restauración medida; snapshot no sustituye respaldo |
| Vulnerabilidades | Inventario actualizado y priorización por exposición/explotabilidad | Contrastar parches Debian y soporte del paquete, no solo versiones upstream |
| Respuesta | Alertas atendidas, escalamiento y aislamiento coordinado | Ensayar quién decide y cómo recuperar acceso ante bloqueo EDR |

`debian-security-support` ayuda a identificar limitaciones de soporte. Las correcciones de Debian pueden estar incorporadas mediante backports de seguridad sin coincidir con la última versión upstream. [Notas de Debian 13](https://www.debian.org/releases/trixie/release-notes/issues.en.html), [rastreador Debian](https://security-tracker.debian.org/tracker/).

No prescribir tamaños de disco, volumen de auditoría, plazos de retención o tiempos de indisponibilidad sin medir la aplicación y acordarlos con su responsable.

## 5. Preparación manual en laboratorio

Estos bloques son un punto de partida para una **VM nueva de laboratorio**, con consola y respaldo disponibles. No fueron ejecutados en servidores durante esta investigación. Ejecutarlos individualmente y detenerse ante errores. No incorporar automáticamente todas las opciones a producción.

### 5.1 Identificación y evidencia inicial

```bash
cat /etc/os-release
uname -r
systemd-detect-virt
sudo /usr/sbin/sshd -t
sudo python3 bin/auditar.py --recopilar --salida /root
```

Si falta Python, puede instalarse desde los repositorios Debian verificados; no es necesario para consultar los tres primeros comandos. El recolector exige Debian 13 y root, y genera archivos locales privados.

### 5.2 Parches y herramientas base

```bash
sudo apt update
sudo apt upgrade
sudo apt install python3 sudo openssh-server ca-certificates \
  chrony auditd audispd-plugins apparmor apparmor-utils \
  rsyslog logrotate debian-security-support needrestart unattended-upgrades
sudo check-support-status
sudo needrestart -r l
```

Revisar la propuesta de APT; los mantenedores de paquetes pueden iniciar/reiniciar servicios. La instalación de unattended-upgrades no reemplaza definir y verificar orígenes, periodicidad, alertas y reinicio. Coordinar chrony con cualquier sincronizador existente.

Instalar/configurar `nftables` para la variante sin Docker. Para la variante Docker elegir primero el backend de firewall y diseñar las reglas compatibles. AIDE y Fail2ban son módulos adicionales: AIDE necesita base y rutina de revisión; Fail2ban aporta protección de acceso cuando aplica, y no reemplaza llaves, MFA o restricción de origen.

### 5.3 Comprobaciones posteriores, sin remediación

```bash
sudo /usr/sbin/sshd -T
sudo visudo -c
sudo ss -lntup
sudo aa-status
sudo auditctl -s
sudo auditctl -l
chronyc tracking
sudo systemctl --failed --no-pager
```

`sshd -T` sin contexto no basta si hay Match. Comprobar también con `-C` para cada usuario/origen relevante. No copiar toda la salida ni secretos a un repositorio público.

## 6. Imagen maestra y clonación

**Preferencia inicial: instalar los agentes después de individualizar el clon.** Evita heredar registros y secretos. Si se necesita preinstalar binarios para velocidad o despliegue sin Internet, validar un procedimiento por fabricante que impida inicio, inscripción e identidad persistente durante construcción. En versiones que no lo permitan, conservar solo instaladores verificados en un repositorio restringido externo a la imagen.

Flujo operativo:

1. Construir una VM limpia en red de preparación. Usar datos sintéticos y credenciales temporales; desactivar integraciones que puedan enviar datos o ejecutar tareas productivas.
2. Actualizar y aplicar la base común. Definir usuario administrativo y vía de consola. Registrar paquetes, kernel, versión de baseline y pruebas.
3. Preparar cloud-init y su fuente Proxmox; comprobar que la identidad y acceso del siguiente clon se generarán correctamente. Crear un clon de ensayo.
4. Antes de capturar la plantilla, retirar credenciales temporales, certificados de instancia, enrolamientos y estados que no deban compartirse. Guardar evidencia de construcción fuera de la imagen. No sanear nunca un servidor productivo como si fuese una plantilla.
5. Preparar machine-id, estado D-Bus, claves SSH de host, cloud-init, concesiones DHCP y semilla aleatoria según la herramienta de construcción. Asegurar regeneración y entropía disponible; no basta eliminar archivos sin verificar el siguiente arranque.
6. Apagar y convertir en template. No arrancar otra vez la imagen sellada: volvería a consumir parte de su inicialización. Para actualizar, reconstruir una nueva edición o usar una copia de construcción y repetir todo el ciclo.
7. Clonar con MAC/UUID propios. Configurar FQDN/IP/DNS y llaves públicas antes del primer arranque; iniciar en red aislada. Si se usan clones enlazados, documentar dependencia de almacenamiento; un clon completo simplifica independencia a mayor costo de espacio.
8. Validar identidad y acceso; aplicar perfil de servicio, secretos y agentes. Actualizar la información central y los certificados que dependan del nombre.
9. Validar dos clones simultáneamente; comprobar que no comparten identidades de agente ni se sustituyen en las consolas.
10. Probar reinicio, servicio, alertas y restauración. Habilitar el tráfico productivo solo después de superar aceptación.

Cloud-init ofrece limpieza para imágenes y regeneración de machine-id; su comportamiento de primer arranque debe verificarse en la versión instalada. systemd puede tomar un identificador D-Bus existente, por lo que no debe revisarse `/etc/machine-id` de manera aislada. [Cloud-init CLI](https://cloudinit.readthedocs.io/en/latest/reference/cli.html), [machine-id en Debian 13](https://manpages.debian.org/trixie/systemd/machine-id.5.en.html).

No se incluye un comando genérico de borrado/sellado: falta implementar y probar su ciclo completo con la imagen elegida. La documentación de Proxmox permite configurar red y claves de acceso con cloud-init antes del arranque del clon. [Proxmox, fuente oficial](https://github.com/proxmox/pve-docs/blob/master/qm-cloud-init.adoc).

### Qué conservar y qué individualizar

| Elemento | Compartible en plantilla | Tratamiento por clon |
|---|---|---|
| Paquetes SO y reglas generales | Sí | Actualizar y verificar versión |
| CA pública de la organización | Sí, si corresponde | Validar cadena y propósito; ninguna clave privada de CA |
| machine-id/D-Bus, MAC, UUID | No como identidad final | Regenerar/comprobar unicidad |
| Claves privadas SSH del servidor | No | Generar en cada instancia y registrar huellas |
| Llaves administrativas públicas | Solo según política de acceso | Revisar autorización; nunca copiar llaves privadas |
| Contraseña local de emergencia | No compartida | Secreto individual custodiado, acceso y recuperación probados |
| Certificados TLS y claves | No certificados/claves de otra instancia | Emitir para identidad y servicio finales |
| Wazuh client.keys | No | Nuevo enrolamiento; no editar claves a mano |
| Zabbix PSK/identidad/host | No | Secreto individual y registro concordante en servidor/proxy |
| IDs/licencias/estado EDR y AV | No presumir compartibles | Instalar/registrar o usar procedimiento de imagen autorizado por fabricante |
| AIDE | Política sí; base final cambia | Generar/verificar tras personalización sin aceptar cambios ajenos |
| Docker | Configuración validada opcional | Sin cargas, volúmenes, registros de acceso o identidades Swarm heredadas |
| Logs/cache de construcción | No datos confidenciales | Conservar evidencia fuera y sanear imagen según procedimiento |

Al cambiar posteriormente IP o hostname de un servidor ya operativo, ejecutar un procedimiento de cambio: DNS, certificados, inventario, reglas por origen, listeners, registros de agentes, respaldos y validación funcional. No volver a sellarlo ni regenerar indiscriminadamente sus claves.

## 7. Agentes: instalación, identidad y verificación

| Producto | Parte común | Parte individual | Evidencia mínima |
|---|---|---|---|
| Wazuh | Versión aprobada, CA, manager/grupos previstos y política SCA/FIM | Nombre e ID únicos, credenciales de registro y client key | Connected, recepción reciente, inventario, SCA y evento de prueba visible |
| Zabbix Agent 2 | Plantilla de parámetros y política TLS | Hostname exacto, proxy/server, PSK identity y secreto único, macros del host | Último dato reciente, disponibilidad y disparador de prueba |
| FortiEDR | Build compatible, política y conectividad aprobadas | Tenant/organización, grupo, identidad del Collector y registro | Collector sano, política aplicada y detección de prueba autorizada |
| G DATA | Producto/build con soporte confirmado y política de escaneo | Management Server, autorización e identidad del cliente | Firmas recientes, protección según funciones disponibles y prueba acordada |

### Wazuh

Usar el paquete y repositorio oficiales con validación de confianza, y una versión de agente compatible con el manager. Definir FQDN y grupo antes del registro. Proteger la inscripción mediante las opciones de autenticación y verificación de identidad del manager aplicables. No dejar una contraseña de enrolamiento embebida en todas las imágenes.

Conservar `agent.conf` como configuración central gestionada. Wazuh documenta una política `cis_debian13`; registrar versión y hash del archivo realmente utilizado para comparar evaluaciones. El número de controles y la edición de referencia pueden cambiar. [Instalación Linux](https://documentation.wazuh.com/current/installation-guide/wazuh-agent/wazuh-agent-package-linux.html), [políticas SCA](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/available-sca-policies.html).

No llamar antivirus a la mera presencia de Wazuh. Delimitar funciones de inventario, logs, FIM, SCA, detección y respuesta; coordinar sus acciones automáticas con FortiEDR y Fail2ban.

### Zabbix Agent 2

Preferir chequeos activos si cubren la necesidad: la VM se conecta a server/proxy y puede evitarse la escucha pasiva. `ServerActive` y `Hostname` deben coincidir con el diseño central; para solo activo no definir `Server`. Si son necesarios chequeos pasivos, restringir TCP/10050 a los servidores/proxies autorizados y exigir TLS. No usar `StartAgents=0` como receta para Agent 2.

Usar PSK única o certificado individual; definir TLSConnect/TLSAccept según el modo y verificar permisos para el usuario real del servicio. Probar el flujo hasta el dato y la alerta. [Parámetros oficiales de Agent 2](https://www.zabbix.com/documentation/7.4/en/manual/appendix/config/zabbix_agent2).

La ficha entregada registra PSK con modo 644. Verificar usuario, grupo, ACL y permisos de directorios; restringir lectura sin impedir al agente funcionar. Evaluar y planificar rotación si estuvo accesible a otros usuarios; no declarar compromiso sin evidencia.

### FortiEDR

La matriz oficial consultada incluye Debian 13 y exige Collector 5.1.16 o posterior para Debian 12/13. Eso es un mínimo publicado, no una elección de versión recomendada para hoy: confirmar build aprobado, kernel exacto, arquitectura, funciones Linux y modo de ejecución con soporte. No confundir FortiEDR con FortiClient. [Requisitos FortiEDR](https://docs.fortinet.com/document/fortiedr/7.2.3/collector-system-requirements/633631/supported-operating-systems).

Obtener el instalador del tenant y la documentación correspondiente desde Fortinet; registrar firma/hash y procedencia. La guía muestra instaladores personalizados y un asistente `fortiedrconfig.sh`; no convertir su ejemplo Ubuntu antiguo en un paquete Debian inventado. Instalar después de individualizar el clon y verificar estado central. [Instalación Linux](https://docs.fortinet.com/document/fortiedr/6.2.0/administration-guide/551398/installing-a-fortiedr-collector-on-linux).

### G DATA

La matriz pública consultada enumera Debian 11/12 para Security Client Linux y no confirma Debian 13. Por tanto, el módulo queda **pendiente de confirmación del fabricante para el producto, versión y kernel**, no declarado incompatible de forma absoluta. Obtener también alcance real de protección Linux, coexistencia con FortiEDR, actualización y procedimiento de clonación. [Requisitos G DATA](https://www.gdata.de/en/business/endpoint-security-software/technical-information).

El manual histórico describe generar un instalador Linux desde G DATA Administrator y autorizar el cliente en la consola. No trasladar ese comando a Debian 13 sin una guía vigente del build suministrado. [Manual oficial histórico 14.1](https://www.gdata.de/fileadmin/web/de/documents/manuals/G_DATA_Business_Solutions_Handbuch_Version_14-1.pdf).

Si G DATA es obligatorio y no existe soporte para la combinación elegida, hay una decisión pendiente del propietario del servicio: producto soportado alternativo, excepción temporal con medidas compensatorias o plataforma compatible. No presentar un instalador que termina sin error como acreditación de soporte.

### Coexistencia y rendimiento

No sumar indiscriminadamente escaneos de AIDE, FIM, antivirus y EDR sobre cada archivo de una base de datos o volumen Docker. Definir cobertura y horario por herramienta, medir CPU, memoria, IOPS y latencia, y probar backup/restauración. Documentar exclusiones mínimas recomendadas por fabricantes; no excluir directorios completos de datos o contenedores sin análisis y compensación. Ensayar cómo evitar cuarentenas o aislamiento que rompan una aplicación crítica.

## 8. Perfil Docker

Docker soporta Debian 13, pero su red modifica el tratamiento de puertos publicados. Instalar desde el repositorio oficial siguiendo la variante correspondiente a Trixie y fijar el conjunto de versiones validado. [Instalación Docker Debian](https://docs.docker.com/engine/install/debian/).

**Decisión inicial propuesta:** backend tradicional de Docker con `iptables-nft`, documentando restricciones en el mecanismo compatible `DOCKER-USER`. No aplicar el firewall nftables general del script original sobre este perfil. `iptables-nft` y el backend nativo nftables de Docker son alternativas distintas.

La página específica de Docker todavía marca experimental su backend nativo nftables e indica que no tiene DOCKER-USER. Exige un diseño de tablas/hooks propio y comprobar forwarding. La guía general de instalación conserva advertencias sobre reglas creadas directamente con nft: fijar versión y backend y comprobar el comportamiento real, sin combinar recetas de ambos modos. [Backend nftables de Docker](https://docs.docker.com/engine/network/firewall-nftables/).

Controles del perfil:

- Acceso al socket Docker solo para administradores autorizados; no montarlo en aplicaciones por comodidad. Evaluar rootless cuando la carga lo permita.
- No publicar puertos en todas las interfaces por defecto. Cuando el proxy está en el host, valorar escucha en loopback y probar acceso desde redes externas. Una BD no debe publicarse globalmente.
- Separar redes de frontend, backend y datos. Probar flujos permitidos y prohibidos entre segmentos.
- Evitar privileged, host PID/network y montajes del sistema anfitrión salvo excepción concreta.
- Contenedores con usuario no root cuando sea posible; mínimos capabilities, no-new-privileges, seccomp/AppArmor, raíz de solo lectura y volúmenes explícitos según compatibilidad.
- Límites de memoria/CPU/PIDs y rotación de logs; controlar espacio del almacenamiento de Docker.
- Imágenes por digest verificable, mantenimiento de dependencias, escaneo y reconstrucción periódica. Un digest da reproducibilidad, no garantiza confianza por sí mismo.
- Secretos por mecanismo protegido; evitar incluirlos en imágenes, archivos Compose versionados o volcados de `docker inspect`.
- Verificar protección de host y contenedores con las capacidades concretas del EDR; no asumir visibilidad completa del contenido de imágenes.

El control del daemon puede permitir modificar el host; el grupo Docker merece tratamiento de acceso privilegiado. [Modelo de seguridad Docker](https://docs.docker.com/engine/security/).

## 9. Perfiles por aplicación

| Perfil | Condiciones adicionales para liberación |
|---|---|
| Proxy/frontend | TLS y renovación probados, exposición 80/443 justificada, rutas/hosts esperados, límites, permisos de certificados, upstreams y cabeceras según aplicación |
| Backend | Cuenta de servicio, escucha interna, autenticación/autorización, secretos externos, dependencias mantenidas, límites y logs sin datos sensibles |
| Base de datos | Solo redes de aplicación/administración, roles mínimos, cifrado según necesidad, consistencia de copias y recuperación puntual cuando proceda |
| Docker | Controles de sección 8, volúmenes respaldados, pruebas de publicación de puertos y recuperación de cargas |

Cada motor y aplicación exige una guía específica para su versión. El hardening del SO no corrige inyección SQL, autenticación deficiente ni dependencias vulnerables del software.

## 10. Métricas y CIS

Registrar benchmark, versión, perfil, herramienta, hash de política, fecha e inventario. Distinguir APROBADO, FALLIDO, NO APLICA, NO EVALUADO y EXCEPCIÓN. Una excepción aceptada sigue siendo una excepción; no se convierte en aprobado.

Propuesta de indicadores complementarios:

- Controles aplicables aprobados / controles aplicables evaluados, manteniendo visibles los no evaluados.
- Controles críticos pendientes, con exposición y plazo de corrección.
- Instancias con identidad única y agentes que realmente reportan.
- Parches pendientes y antigüedad del kernel en ejecución.
- Restauraciones satisfactorias y tiempos medidos frente a RTO/RPO acordados.
- Diferencias entre estado deseado y estado real detectadas y resueltas.

La ficha registra 117/72/18 y 116/73/18, y 61 % mostrado en ambos. Es evidencia histórica de una evaluación parcial, no porcentaje de resistencia a ataques. Para analizar discrepancias se requiere exportación por ID y política exacta.

## 11. GitHub o GitLab

Git es el control de versiones; GitHub y GitLab son plataformas de alojamiento y colaboración. Preferir el servicio privado ya aprobado y mantenido por la institución. Si existe GitLab institucional con acceso, respaldos y runners gestionados, es mi primera opción. En ausencia de él, GitHub privado puede cumplir el objetivo. Montar un GitLab nuevo solo para este proyecto agrega operación y no aumenta automáticamente la seguridad.

Proteger ramas, revisar cambios, exigir pruebas y limitar credenciales del runner. Separar código reutilizable de inventario confidencial y secretos; el runner de pruebas no debe disponer de credenciales productivas por defecto. Mantener derechos de uso y avisos de componentes reutilizados; no redistribuir el PDF CIS o texto normativo sin comprobar sus condiciones.

No se ha publicado nada. Esta carpeta contiene ejemplos, sin IP institucional ni credenciales. El nombre y ubicación del repositorio remoto se decidirán al integrar la implementación.

## 12. Orden de implementación

1. Validar diagnóstico en una VM de laboratorio; exportar SCA por ID y fijar versión de benchmark.
2. Implementar roles de base, SSH/firewall y auditoría con pruebas/reversión.
3. Implementar sellado y personalización; aprobar dos clones sin identidades compartidas.
4. Incorporar Wazuh y Zabbix con registro y pruebas centrales.
5. Incorporar FortiEDR validado y resolver soporte G DATA.
6. Validar perfil Docker y un perfil de aplicación representativo.
7. Publicar internamente una release con guía, código, manifiesto y acta de aceptación.
8. Reconstruir/revalidar ante cambios de SO, kernel, agentes, benchmark o aplicación.

La fase de laboratorio es una comprobación técnica necesaria: todavía no se dispone aquí de una VM Debian accesible ni de los instaladores/licencias empresariales. El trabajo actual fija el diseño y permite iniciar la recolección, sin afirmar resultados productivos inexistentes.
