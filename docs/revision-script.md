# Revisión del script proporcionado

Análisis estático del texto adjunto, contrastado con la ficha de continuidad del 13/10/2026. No se ejecutó el script. Las observaciones del PDF son históricas, no comprobaciones actuales de los servidores.

## Dictamen

El script reúne componentes útiles, pero no constituye todavía una base universal, un cumplimiento CIS demostrado ni una herramienta segura de construcción de imágenes. Conviene conservar su intención y convertir cada etapa en un módulo idempotente con validación y reversión. El asistente ya existente en el directorio contiene ideas aprovechables de preservación de reglas y reversión temporizada; también requiere pruebas reales y adaptación para Docker.

## Hallazgos y correcciones

| Prioridad | Hallazgo verificable en el texto | Impacto | Corrección de diseño |
|---|---|---|---|
| Alta | `flush ruleset` en nftables | Borra reglas ajenas, incluidas las de otras herramientas | Administrar solo reglas propias; detectar propietarios y migrar explícitamente |
| Alta | TCP 22, 80, 443 y 10050 permitidos sin origen | Política de proxy aplicada a cualquier servidor; monitoreo y administración expuestos según red superior | Matriz origen/destino/puerto por perfil, incluidos IPv6 y pasivos Zabbix |
| Alta | `forward policy drop` universal | Puede impedir red de contenedores o flujos de enrutamiento legítimos | Firewall específico para Docker, backend probado y pruebas desde otras redes |
| Alta | No hay respaldo ni reversión automática de SSH/firewall | `sshd -t`/`nft -c` aceptan configuraciones que pueden dejar sin acceso | Candidato, copia privada, rollback probado, conexión nueva y confirmación efectiva |
| Alta | Archivo SSH denominado `99-cis.conf` | Puede no establecer los valores efectivos si otros archivos los fijan antes | Revisar Include y primera asignación, `sshd -T -C`, usuario/origen y conflictos |
| Alta | Contraseñas SSH habilitadas sin política transitoria; no fija root SSH | No expresa la política final de acceso | Primero probar llaves/sudo/consola; definir root SSH y transición explícitas |
| Alta | `|| true` en PAM/AIDE/timer y otras acciones | Fallos silenciados seguidos por mensajes de éxito | Estados OK/FAIL/SKIP/PENDING por módulo y retorno significativo |
| Alta | `aideinit` se intenta en cada ejecución y luego se copia la nueva base | Riesgo de aceptar alteraciones como referencia confiable | Inicialización solo en fase autorizada; actualización con revisión de diferencias |
| Alta | Reglas audit sobre archivos que pueden no existir | Carga fallida o parcial y cobertura distinta de la pretendida | Detectar rutas reales, arquitectura y mecanismo de sesiones de Debian 13 |
| Alta | No separa imagen e identidad de instancia | Un clon puede heredar secretos, claves y registros de agentes | Fases de construcción, sellado, personalización y registro |
| Media | Instala chrony pero no hace upgrade del sistema | No resuelve parches del SO/kernel | Política de actualización, reinicio y evaluación del kernel efectivo |
| Media | No verifica Debian 13, arquitectura, VM, dependencias o espacio | Se puede aplicar sobre un entorno no previsto | Preflight con requisitos, incompatibilidades y detención clara |
| Media | Usa `nft`, `sshd`, `visudo` sin instalar/verificar todas las dependencias | Puede fallar en una instalación mínima | Verificar herramientas/paquetes y versiones antes de modificar |
| Media | chown/chmod asumen backups de cuentas y cron presentes | Un archivo opcional ausente puede detener el proceso después de cambios parciales | Tratar cada ruta por existencia/tipo; no seguir enlaces inesperados |
| Media | Sobrescribe `pwquality.conf`, sudoers y reglas de auditoría | Elimina personalizaciones sin revisión | Fragmentos gestionados donde estén soportados; detectar conflictos |
| Media | Cambia ENCRYPT_METHOD en login.defs mediante sed | No prueba el método efectivo de PAM ni cambia hashes existentes | Inspeccionar pila PAM y verificar una contraseña de prueba sin registrar hash |
| Media | No demuestra pwquality activo; oculta error de pam-auth-update | Paquete instalado puede no aplicar política | Verificar integración y probar rechazo/aceptación con usuario de prueba |
| Media | Mezcla arquitectura b32 y b64 sin detección | No es una receta portable entre arquitecturas | Generar por arquitectura y compatibilidad requerida; UID mínimo desde política real |
| Media | Vigila sudo.log/opasswd sin asegurar existencia y semántica | Regla puede no cargarse o no cubrir lo esperado | Validar archivos reales y eventos generados; no crear registros ficticios solo para el score |
| Media | No dimensiona retención, espacio ni salida central de audit/logs | Registro disponible localmente no asegura evidencia utilizable | Prueba end-to-end y política de capacidad/alertas/rotación |
| Media | Instalar AppArmor y cambiar GRUB se presenta como bastionado | No prueba que Nginx u otras aplicaciones estén confinadas | Verificar LSM y perfiles reales; no modificar arranque si ya funciona |
| Media | Fuerza timezone sin variable por entorno | Mezcla decisión operativa con control de seguridad | Zona horaria configurable; sincronización y marcas temporales consistentes |
| Media | Cambia locale del agente Wazuh como corrección general | No corrige errores de lógica del evaluador | Usar solo con caso reproducible; registrar versión/hash de política y evidencia |
| Media | Declara éxito CIS al final | No se evaluaron todos los controles ni el funcionamiento | Informar módulos aplicados y pruebas pendientes sin certificación implícita |
| Media | No tiene bloqueo de ejecución ni estado transaccional | Ejecuciones simultáneas o repetidas pueden dejar estado incoherente | Lock, operaciones atómicas y manifiesto de cambios, sin aceptar AIDE de nuevo |
| Media | No discrimina configuraciones de aplicaciones futuras | Un despliegue posterior puede reabrir puertos o debilitar permisos | Aplicar perfil y repetir aceptación cuando se instala/cambia una carga |

`ClientAliveInterval`/`ClientAliveCountMax` detectan clientes que no responden; no son por sí solos un cierre de sesión por ausencia de actividad humana. Si se requiere timeout de canales, analizar `ChannelTimeout` y su efecto sobre sesiones y túneles. OpenSSH usa normalmente el primer valor obtenido para una opción y procesa Includes en orden lexical. [sshd_config Debian 13](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html).

Debian 13 reemplaza mecanismos históricos relacionados con last/lastb/lastlog. Por eso no se debe copiar sin comprobación una lista fija de wtmp/btmp/lastlog/faillog de una versión anterior. [Notas de versión](https://www.debian.org/releases/trixie/release-notes/issues.en.html).

## Hallazgos de la ficha que merecen prioridad

1. **PSK Zabbix root:root 644:** corregir acceso de lectura después de verificar identidad del proceso y ACL; evaluar rotación. No mostrar ni copiar el secreto.
2. **Acceso:** root SSH con llave permitido, contraseñas de usuario y reenvíos TCP/agente/X11 activos. Evaluar necesidad real y probar transición antes de deshabilitar.
3. **Firewall:** las reglas mostradas permiten los cuatro puertos sin origen. No acredita exposición a Internet: faltan perímetro, segmentación y prueba desde redes pertinentes.
4. **AppArmor:** siete perfiles enforce no incluyen Nginx según la ficha. Eso requiere examinar cobertura del proceso, no sumar paquetes instalados.
5. **AIDE:** base y timer presentes, sin evidencia de última comprobación. Solicitar resultado y proceso de tratamiento de diferencias.
6. **Auditoría:** retención observada de 8 MB por archivo y cinco archivos, con SUSPEND ante determinados problemas. Medir duración real retenida y probar alertas por espacio/pérdida.
7. **Nginx:** HTTP en 80 y HTTPS todavía por incorporar. Completar TLS y rutas antes de un corte productivo que dependa de ellos.

No alterar los nodos de continuidad como parte automática de la construcción de la nueva plantilla. Una corrección en esos nodos necesita su propia validación y ventana, dentro de la autorización operativa que corresponda.

## Qué aprovechar del trabajo previo

- `diagnostico-debian.sh`: inventario local como referencia.
- `validar-cis-debian13.sh`: recolección dirigida; no equivale a certificación CIS.
- `seguridad-debian-interactiva.sh`: tratamiento de red administrativa y reversión, sujeto a sus limitaciones documentadas.
- Nuevo `bin/auditar.py`: recolección estructurada, dirigida a este diseño y sin leer logs de aplicaciones o secretos.

No ejecutar los cuatro como si cada uno añadiera automáticamente una capa independiente. Documentar quién es propietario de cada archivo y política; migrar hacia una única fuente de configuración.
