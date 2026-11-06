# Cambios y validación

## 0.4 — 06/11/2026 — Soporte UFW e integración Fail2ban

- Estandarización de Firewall: reemplazo de `firewall_base.py` por **UFW** (usando backend `iptables-nft`), manteniendo `nftables.conf` en configuración limpia por defecto.
- Configuración de Fail2ban con `banaction = ufw` en `bin/configurar_base.py`, integrando el bloqueo de ataques SSH directamente en las reglas de UFW.
- Desactivación de IPv6 en UFW (`IPV6=no`) para concentrar la administración perimetral exclusivamente en IPv4.
- Incorporación de paquete `ufw` en la lista de paquetes base de `configurar_base.py`.
- Nueva guía operativa: `docs/12-firewall-ufw.md` con procedimiento de despliegue y reglas específicas para arquitectura Frontend y Backend (Nginx).

## 0.3 — 18/10/2026 — Perfil general agrupado

- Nuevo `bin/configurar_base.py` y capítulo 9: configuración por etapas, verificación final y registro explícito de ausencia de snapshot.
- Conserva NTP existente y contraseña SSH según decisión del operador. Evita recomendaciones opcionales y eliminaciones APT. No instala Chrony, agentes, Docker ni BD en la base.
- Amplía reglas audit para autenticación/configuración; incorpora rotación, journal persistente limitado, sudo con pseudoterminal/log, actualizaciones automáticas de seguridad sin reboot automático, Fail2ban y política AIDE propia con timer diario.
- Valida SSH efectivo para usuario/IP y programa una reversión a los 20 minutos; requiere confirmar desde una conexión nueva. No promete que el timer sobreviva a un reinicio.
- No aplica un firewall general, no modifica PAM/GRUB/red ni fuerza perfiles AppArmor. Las políticas por función siguen pendientes antes de producción. No sella la VM ni inicializa una base AIDE destinada a heredarse entre clones.
- El verificador distingue comprobaciones locales del envío de alertas, pruebas funcionales y aceptación. No entrega score CIS.

### Evidencia del piloto y límites

El operador reportó en Debian 13.7 amd64: instalación de paquetes sin Chrony/recomendaciones; servicios activos y hora sincronizada; ocho reglas de identidad, un evento de prueba y persistencia tras reinicio; recarga exitosa de retención audit; kptr_restrict=2 aplicado/guardado; Fail2ban leyendo journal y prueba manual de ban/unban reflejada en nftables. Esto valida esas acciones manuales, no el nuevo ejecutor completo. No se publican nombres, IP ni registros del servidor.

26 pruebas unitarias locales pasaron (las 14 anteriores y 12 nuevas). Las nuevas cubren plan sin efectos, ausencia de snapshot no ficticia, validación de contexto SSH, duplicados de auditd, rutas existentes, variantes de arquitectura, configuración SSH efectiva, temporizador antes de escrituras, recuperación ante error y aislamiento de grupos de respaldo. Los comandos del sistema se simulan; el temporizador, AIDE, servicios y APT requieren validación Linux real.

Persisten límites: no se ejecutó esta automatización completa en una VM desde el entorno de desarrollo; los backups son locales y no revierten paquetes; la configuración preparada de AIDE necesita referencia por clon; el firewall por función, sellado, identidades y agentes tienen aceptación separada.

## 0.2 — 16/10/2026 — Piloto operativo

- Portada con un único recorrido de ocho capítulos: laboratorio, base, acceso/red, plantilla/clones, agentes, Docker, aceptación e incorporación de CIS.
- Nuevo `bin/baseline.py`: plan sin ejecutar por defecto, comprobación Debian 13/KVM/QEMU/root, declaración de laboratorio/snapshot, instalación de componentes y cinco parámetros kernel.
- Registro privado por ejecución, exclusión de ejecuciones simultáneas, respaldo del archivo y valores kernel, comprobación posterior y recuperación ante errores controlados.
- Reversión explícita de kernel con detección de cambios posteriores en archivo/valores. Los paquetes requieren recuperación mediante snapshot/respaldo si hay fallos parciales.
- Referencia Ansible Lockdown fijada a release 1.0.3, commit `f9d8dbf5ecdbe0b4955209b4f35d67a727d95052`. Revisión parcial de código; no se incorpora ni ejecuta el rol automáticamente.
- Separación de configuración común y registros/secretos por clon; G DATA continúa pendiente de soporte confirmado para Debian 13.

### Validación realizada

14 pruebas unitarias en Windows con Python: 6 del diagnóstico y 8 del ejecutor. Se simularon comandos del sistema. Cubren ausencia de herramientas, errores/timeouts, filtrado de salida, rechazo de entornos, plan sin efectos, barreras de aplicación, discrepancia de valores, recuperación parcial y recuperación fallida.

Los tests usan archivos temporales dentro del directorio de pruebas. No ejecutan APT, sysctl, agentes ni cambios reales en servidores. La primera ejecución encontró una restricción del directorio temporal del sandbox; se ajustó la ubicación temporal y las 14 pruebas finalizaron correctamente.

### Pendiente antes de producción

- Ejecución y reinicio en VM Debian 13 representativa; verificar permisos y bloqueo de concurrencia en Linux.
- Probar instalación parcial, fallos de persistencia y restauración real desde Proxmox.
- Validar el procedimiento SSH, cloud-init y dos clones independientes.
- Implementar y probar firewall de invitado con redes reales y variantes Docker/IPv6.
- Configurar/auditar retención, reglas auditd, perfiles AppArmor, AIDE y políticas de cuentas según servicio.
- Validar versiones/instaladores y convivencia de agentes; resolver soporte G DATA.
- Integrar los controles CIS seleccionados con pruebas funcionales; comparar 1.0.0/1.1.0 y no atribuir equivalencia automática.

No se cambió ninguna VM ni se verificó un score CIS real durante esta edición.

## 0.1 — Diseño y diagnóstico

Investigación inicial, revisión del script aportado, modelo de inventario, catálogo de aceptación y recopilador de diagnóstico de solo lectura.
# Complemento del piloto — 2026-10-18

- Añade `completar_base.py` y capítulo 10: PAM para cuentas locales (calidad, historial, yescrypt y bloqueo), rsyslog, needrestart, restricciones core/red y auditoría adicional.
- Recuperación temporal de archivos y valores sysctl; confirmación tras nueva sesión SSH. No desinstala paquetes ni garantiza recuperación ante apagado.
- Rechaza proveedores PAM no reconocidos; no instala Chrony ni modifica routing para Docker.
- 35 pruebas unitarias locales pasan, incluidas 9 nuevas. Sin ejecución Linux local: PAM, reinicio, logs y cambios de contraseña requieren las pruebas funcionales del capítulo 10 en la VM.
- No declara CIS completo. Registra controles pendientes y aclara que la ruta Cloud-Init no corresponde al clonado manual elegido.
