# Aceptación, evidencias y plan de implementación

Roles propuestos, por asignar a personas: Infraestructura construye y aplica; Seguridad revisa controles y excepciones; responsables de monitoreo validan recepción y alertas; dueño de aplicación acepta función/rendimiento; autoridad de cambios autoriza liberación. No se presume que estos roles ya estén asignados.

## Matriz de pruebas

| ID propio | Etapa | Prueba | Aceptación y evidencia | Ejecutor propuesto |
|---|---|---|---|---|
| BAS-01 | Base | Identificar Debian/kernel/arquitectura/VM | Manifiesto de versión y compatibilidad de agentes | Infraestructura |
| BAS-02 | Base | Actualizar desde orígenes verificados | APT sin errores, paquetes pendientes analizados y kernel esperado tras reinicio | Infraestructura |
| BAS-03 | Base | Acceso administrativo nuevo | Llave/MFA si aplica, sudo y consola; probar origen permitido y denegado | Infraestructura |
| BAS-04 | Base | Revisar PAM con cuenta de laboratorio | Política aplicada sin bloquear accesos de recuperación | Infraestructura + Seguridad |
| BAS-05 | Base | Firewall IPv4/IPv6 desde dos redes | Solo flujos de la matriz; evidencia de prueba externa autorizada | Infraestructura |
| BAS-06 | Base | Confinamiento de servicio | Perfil efectivo y carga funcional sin denegaciones injustificadas | Seguridad + aplicación |
| BAS-07 | Base | Generar cambio benigno controlado | Evento local audit, recepción/indexación central y alerta cuando corresponda | Seguridad |
| BAS-08 | Base | Supervisar espacio y auditoría | Alertas y tratamiento acordados; sin pérdida de eventos durante prueba | Monitoreo |
| BAS-09 | Base | Verificar sincronización | Fuente confiable y desviación dentro de umbral acordado | Infraestructura |
| BAS-10 | Base | Ejecutar evaluación SCA | IDs/resultados/versiones exportados, fallos y excepciones trazables | Seguridad |
| IMG-01 | Imagen | Inspeccionar material sensible | Sin secretos de construcción ni identidades de agentes heredadas | Infraestructura + Seguridad |
| IMG-02 | Clones | Crear dos instancias simultáneas | MAC/UUID/machine-id y huellas SSH distintas; ningún registro central reemplazado | Infraestructura |
| IMG-03 | Clones | Inicialización y segundo reinicio | cloud-init terminado sin errores y sin repetir registros; acceso estable | Infraestructura |
| IMG-04 | Clones | Cambiar IP/nombre en clon de prueba | DNS, certificados, reglas y consolas coherentes; controles aplicables preservados | Infraestructura |
| AGT-01 | Wazuh | Evento de prueba y nuevo SCA | ID único; evento recibido, buscable y alerta prevista; inventario reciente | Seguridad |
| AGT-02 | Zabbix | Dato y disparador temporal | Host exacto, TLS, PSK individual y dato/alerta con hora reciente | Monitoreo |
| AGT-03 | FortiEDR | Validar build/kernel y política | Soporte documentado, Collector sano, prueba oficial autorizada | Seguridad |
| AGT-04 | G DATA | Validar soporte y firmas | Confirmación Debian 13/build/kernel; instalación y prueba oficial aprobadas | Seguridad |
| AGT-05 | Coexistencia | Carga con AV/EDR/FIM/backup | Latencia, CPU, memoria e IOPS dentro de umbrales acordados; sin exclusiones excesivas | Aplicación + Seguridad |
| DOC-01 | Docker | Publicar un servicio de laboratorio | Accesible solo desde redes previstas, tanto IPv4 como IPv6 | Infraestructura |
| DOC-02 | Docker | Reiniciar VM/daemon y volver a probar | Reglas persistentes, red y DNS correctos; sin exposición nueva | Infraestructura |
| DOC-03 | Docker | Examinar privilegios y secretos | Sin socket/privileged/host mounts innecesarios; secretos fuera de imagen/Git | Seguridad |
| DOC-04 | Docker | Restaurar volúmenes y servicio | Datos consistentes y recuperación funcional medida | Infraestructura + aplicación |
| APP-01 | Servicio | Recorridos críticos del usuario | Login, permisos, lecturas/escrituras y dependencias correctos | Dueño de aplicación |
| APP-02 | Servicio | TLS, caducidad y renovación | Identidad/cadena correctas y renovación comprobada | Infraestructura |
| OPS-01 | Operación | Aplicar misma configuración dos veces | Sin cambios inesperados ni reseteo de identidades/base AIDE | Infraestructura |
| OPS-02 | Operación | Provocar fallo de una etapa en laboratorio | Detención, registro y reversión; no mensaje global de éxito | Infraestructura |
| OPS-03 | Operación | Probar rollback de acceso/red | Recuperación verificable desde consola y sesión nueva | Infraestructura |
| OPS-04 | Operación | Restaurar una copia independiente | RTO/RPO acordados, consistencia de BD y acceso validado | Infraestructura + aplicación |
| OPS-05 | Operación | Introducir desviación inocua | Detectada y tratada por proceso de configuración | Seguridad |
| OPS-06 | Liberación | Revisar release y excepciones | Sin críticos aplicables pendientes; decisiones y evidencias completas | Autoridad de cambios |

Estos IDs son internos; **no son números de controles CIS**. Se mapearán cuando se disponga del benchmark y del archivo SCA exactos.

## Criterios de interrupción

Detener la etapa y preservar evidencia ante pérdida de acceso, cambio inesperado de identidad, agente duplicado, fallo de aplicación, degradación por encima del umbral acordado, pérdida de eventos o error de validación. La reversión debe restaurar los archivos y reglas pertinentes; no reinstalar paquetes o borrar datos de aplicación como respuesta automática.

Un rollback temporizado de SSH/firewall debe probarse con concurrencia, caducidad y persistencia. Una sesión SSH ya abierta no prueba capacidad de reconexión. Un temporizador transitorio no sobrevive necesariamente al reinicio: no reiniciar durante esa prueba.

## Evidencia por liberación

Conservar fuera de Git cuando contenga información interna: versión baseline, commit, checksum de imagen, ISO/origen, paquetes y kernel, configuraciones sanitizadas, matriz de puertos, resultados, registros centrales de agentes, pruebas de restauración, excepciones y aprobación. Mantener capturas solo como complemento de resultados exportables.

Plantilla mínima de excepción:

```yaml
id: EXC-000
control: PENDIENTE_DE_MAPEO
activos: []
motivo: ""
riesgo: ""
medidas_compensatorias: []
responsable: ""
autoriza: ""
fecha_revision: ""
fecha_vencimiento: ""
evidencias: []
```

## Información pendiente que resuelve decisiones concretas

- Release exacta de Proxmox y configuración de firmware/cloud-init de la VM: define construcción y sellado.
- Manager Wazuh y server/proxy Zabbix realmente desplegados: define agentes compatibles; lo más nuevo del agente no debe elegirse aisladamente.
- Producto/build G DATA y Collector/tenant FortiEDR disponibles: define soporte y método de instalación.
- Redes de administración/servicios/monitoreo, IPv6 y salida a Internet/proxy: define firewall y registro.
- Primera aplicación piloto, carga representativa y RTO/RPO: define pruebas, disco y recuperación.
- Exportación SCA por ID y versión/hash de política: define correcciones y excepciones sin perseguir falsos positivos.

Se puede avanzar con base, inventario y pruebas de clonación mientras se completan estos datos. El paso productivo de un agente obligatorio no puede darse por validado sin soporte e instalación comprobados.
