# Cambios y validación

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
