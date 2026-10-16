# 7. Aceptar el servidor y mantenerlo

**Objetivo:** demostrar que las protecciones funcionan y que el servicio se puede recuperar.

**Dónde:** cada clon y las consolas de monitoreo/seguridad. Guarda evidencias fuera del repositorio.

## 7.1 Recoger evidencia final

```bash
sudo python3 bin/baseline.py verificar
sudo python3 bin/auditar.py --recopilar --salida /root
systemctl --failed
sudo ss -lntup
sudo aa-status
sudo auditctl -s
sudo auditctl -l
chronyc tracking
```

El código 0 de `verificar` solo acredita cinco valores kernel. El diagnóstico no calcula cumplimiento CIS. Conserva informes inicial/final, versión del repositorio, kernel, paquetes y perfil.

## 7.2 Crear referencia AIDE por clon

Después de instalar/personalizar y revisar que el estado es confiable:

```bash
sudo aideinit
sudo ls -lh /var/lib/aide/
systemctl list-timers '*aide*'
```

Sigue los mensajes del empaquetado Debian para activar la base generada; confirma en su configuración las rutas de base de entrada/salida. No copies una ruta de otra distribución. Ejecuta la comprobación mediante el servicio/script que proporcione el paquete y revisa su resultado y su programación.

Una base AIDE inicializada sobre archivos ya comprometidos los aceptaría como referencia. No repitas `aideinit` para silenciar diferencias: investiga y aprueba cambios antes de actualizar la referencia. Las comprobaciones deben producir resultados revisados, no solamente un timer instalado.

## 7.3 Lista de aprobación

| Prueba | Resultado necesario |
|---|---|
| Nueva conexión SSH y sudo | Funciona desde red autorizada, por llave |
| Conexión desde red no autorizada | Se deniega, también por IPv6 si existe |
| Arranque de la VM | Servicios y protecciones persisten |
| Dos clones | Identidades, IP, MAC y llaves distintas |
| AppArmor | Perfiles relevantes en enforce; excepciones justificadas |
| Auditoría | Reglas necesarias, evento de prueba recibido, sin pérdida silenciosa |
| Logs | Rotación/espacio/retención y alertas probadas |
| Agentes | Datos recientes y alerta de prueba en las consolas |
| Aplicación/BD | Login, consultas, escrituras y dependencias funcionan |
| Docker, si aplica | Puertos, persistencia, reinicio y reglas probados |
| Backup | Restauración ensayada y datos verificados |
| Parches | Ventana, responsable y reinicio coordinados |
| CIS/SCA | Política/versiones identificadas; fallos revisados uno a uno |
| Excepciones | Motivo, responsable, mitigación y fecha de revisión |

El detalle ampliado está en [aceptacion.md](aceptacion.md). Un resultado **pendiente** no se marca como aprobado. El score SCA es una medida de controles de esa política, no un porcentaje de protección contra ataques.

## 7.4 Registro de entrega

Copia este bloque a tu sistema privado de cambios:

```text
Servidor / VMID / perfil:
Versión de plantilla / commit:
Debian / kernel / paquetes relevantes:
Operador / responsable del servicio:
Fecha y ventana:
Snapshot y respaldo probado:
Política CIS/SCA / versión / hash:
Resultados iniciales y finales:
Prueba de acceso y puertos:
Prueba de aplicación y restauración:
Prueba de agentes y alertas:
Excepciones y vencimientos:
Pendientes que impiden producción:
Decisión y responsable de aceptación:
```

## 7.5 Operación posterior

Revisa fallos de servicios, retraso de agentes, almacenamiento de logs, actualizaciones y alertas según la frecuencia institucional. Cada cambio importante de kernel, Docker, EDR, política CIS o aplicación requiere volver a ejecutar las pruebas afectadas.

Las correcciones deben llegar tanto a servidores existentes como a una nueva versión de plantilla. Una plantilla antigua sigue creando servidores con sus paquetes antiguos hasta que se actualiza y prueba.
