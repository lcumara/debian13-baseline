# 13. Lista consolidada para cerrar la plantilla

**Estado:** base funcional endurecida; todavía no es una plantilla con evaluación CIS completa. Los resultados compartidos por el operador confirman los verificadores aplicados, no todos los controles del benchmark.

## Excepciones ya decididas

- Caducidad de contraseña de 3650 días, aviso 365 días antes y sin bloqueo adicional por inactividad. Revisión local desde 1825 días. No declarar conformidad CIS de caducidad por aprobar la política local.
- Conservar distribución de volúmenes actual; no separar /home, /var/tmp, /var/log ni /var/log/audit.
- Mantener SSH con contraseña; sin forwarding; root sin acceso SSH. No convertir esta decisión automáticamente en un hallazgo CIS sin contrastar el control exacto.

## Trabajo técnico de cierre todavía no implementado o validado

| Bloque | Resultado necesario |
|---|---|
| Montajes | Revisar y aplicar opciones compatibles a /tmp, /dev/shm y /var/tmp; verificar persistencia. No aplicar noexec a todo /var. |
| Módulos y servicios | Inventario completo, deshabilitar solo módulos/protocolos y servicios innecesarios; conservar módulos de almacenamiento, virtualización y Docker necesarios. |
| Arranque | Evaluar audit=1, backlog, permisos de GRUB y recuperación por consola. No inmovilizar audit con -e 2 durante construcción. |
| Auditoría | Completar por ID la cobertura requerida: comandos privilegiados, sesiones, cambios de seguridad y retención/acciones; probar eventos y ausencia de pérdida bajo carga. |
| Cuentas y permisos | Revisar UID/GID duplicados, cuentas de sistema, archivos huérfanos/escribibles por otros, homes, cron/at y permisos; no aplicar chmod recursivo general. |
| Pruebas funcionales | Rechazo de contraseña débil/reutilizada, bloqueo y desbloqueo de cuenta temporal, logs de rsyslog, prueba externa del firewall con un servicio escuchando y reinicio. |
| Evaluación CIS | Fijar benchmark 1.1.0 y revisar cada ID de Level 1 Server, evidencias y excepciones. No se ha implementado esta evaluación completa ni existe porcentaje válido todavía. |
| Sellado manual | Preparar regeneración fiable de machine-id/llaves SSH, retiro de credenciales y cuentas temporales, limpieza de identidades de agentes y prueba de dos clones. Conservar los ejecutores privados requeridos por los servicios. |

## Trabajo por clon

- Nombre, red e identidades únicas; contraseña administrativa propia.
- Agentes compatibles con Debian/kernel/consolas: registro individual, PSK y certificados propios; recepción central y alertas comprobadas.
- Aplicación/BD/Docker: TLS, credenciales, permisos, puertos de orígenes autorizados y respaldo/restauración.
- Inicializar referencia AIDE tras personalización validada, comprobar temporizador y recepción de resultados.

**Criterio de cierre:** pruebas aplicables aprobadas, excepciones registradas y dos clones con identidades distintas que conservan acceso y seguridad. Esta lista es de trabajo pendiente, no un certificado de aceptación ni instrucciones para aplicar cambios sin revisar sus dependencias.
