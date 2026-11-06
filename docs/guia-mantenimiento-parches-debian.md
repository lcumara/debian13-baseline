# Guía Operativa de Buenas Prácticas: Actualización, Mantenimiento y Mitigación de Vulnerabilidades en Debian

**Objetivo:** Establecer un protocolo estandarizado, seguro y auditable para actualizar servidores Debian en producción, mitigar alertas de vulnerabilidades en **Wazuh** y gestionar el ciclo de vida del kernel y paquetes sin provocar caídas de servicios ni pérdida de configuraciones.

---

## 1. Fundamentos y Reglas de Oro en Producción

1. **Simular antes de ejecutar (`Dry-Run`):** Nunca ejecutar actualizaciones mayores a ciegas con `-y`. Siempre simular con el parámetro `-s` para inspeccionar qué paquetes se actualizarán y, fundamentalmente, **cuáles se pretenden eliminar**.
2. **La Regla del Kernel en Ejecución:** **NUNCA** eliminar paquetes de kernel antiguos mientras la máquina esté corriendo con esa versión. Si se eliminan los módulos de `/lib/modules/<version-en-ejecucion>` en caliente, pueden fallar adaptadores de red, UFW o módulos del sistema. **Primero se reinicia para cargar el kernel nuevo, y luego se sanean los viejos.**
3. **Respeto a los archivos de configuración (`conffile`):** Si APT consulta si se desea reemplazar un archivo de configuración modificado (ej: `/etc/nginx/nginx.conf`), se debe conservar la versión local (`N`) a menos que expresamente se requiera migrar directivas.
4. **Relación con Wazuh:** El detector de vulnerabilidades de Wazuh analiza la base de datos de paquetes (`dpkg`). Un kernel o librería antigua en el disco **seguirá generando alertas de seguridad** aunque exista una versión más moderna instalada, hasta que el paquete vulnerable sea purgado.

---

## 2. Catálogo de Comandos y su Propósito

| Comando | Función en el Sistema | Impacto y Nivel de Riesgo |
|---|---|---|
| `apt update` | Descarga y actualiza los índices de repositorios. No instala nada. | Inocuo. Seguro de ejecutar siempre. |
| `apt -s upgrade` / `full-upgrade` | **Simulación:** Muestra exactamente qué se instalaría, actualizaría o eliminaría sin tocar el disco. | Inocuo (0% riesgo). Paso obligatorio. |
| `apt upgrade` | Actualiza paquetes a versiones superiores **sin desinstalar nunca** ningún paquete existente. | Muy bajo. Conservador para producción. |
| `apt full-upgrade` / `dist-upgrade` | Actualiza paquetes resolviendo dependencias complejas; **tiene permiso para desinstalar paquetes obsoletos** e instalar nuevos kernels. | Moderado. Requiere simulación previa obligatoria. |
| `apt autoremove --purge` | Elimina paquetes que se instalaron como dependencias y que ya no son requeridos por ningún software activo, purgando sus archivos de configuración. | Bajo, si se ejecuta tras haber reiniciado al nuevo kernel. |
| `apt clean` | Vacía la caché local de paquetes descargados (`/var/cache/apt/archives/`), liberando espacio en disco. | Inocuo. Muy recomendado para optimizar disco. |

---

## 3. Procedimiento Estándar de Mantenimiento Seguro (Paso a Paso)

### PASO 1: Simulación y Diagnóstico Preventivo

1. Actualizar la lista de repositorios:
   ```bash
   sudo apt update
   ```

2. Simular la actualización básica:
   ```bash
   sudo apt -s upgrade
   ```

3. Simular la actualización de dependencias y kernel:
   ```bash
   sudo apt -s full-upgrade
   ```
   > **Qué revisar en la salida:**  
   > Observar la línea `REMOVING:` o `Los siguientes paquetes se ELIMINARÁN:`. Si no elimina servicios críticos (como Nginx, UFW o SSH), el procedimiento es seguro.

---

### PASO 2: Aplicación de Parches

1. Aplicar las actualizaciones validadas:
   ```bash
   sudo apt upgrade
   ```
   *(Si la simulación de `full-upgrade` demostró ser limpia y requerida para dependencias o nuevos kernels, ejecutar `sudo apt full-upgrade`)*.

2. **Atención a preguntas sobre archivos de configuración:**  
   Si APT se detiene mostrando una pantalla interactiva sobre un archivo modificado por el operador:
   ```text
   Configuration file '/etc/nginx/nginx.conf'
   ==> File on system was created by you or by a script.
   What would you like to do about it ? [default=N]
   ```
   * **Acción correcta:** Presionar `Enter` o escribir `N` para mantener tu configuración en producción.

---

### PASO 3: Detección de Kernel Pendiente y Reinicio

1. Comprobar si el kernel en memoria coincide con el último instalado:
   ```bash
   uname -r
   dpkg -l | grep linux-image
   ```

2. Comprobar servicios que requieren reinicio con `needrestart`:
   ```bash
   sudo needrestart -r l
   ```
   Si la herramienta indica `Pending kernel upgrade` o un kernel más reciente:

3. **Reiniciar el servidor:**
   ```bash
   sudo reboot
   ```

---

### PASO 4: Limpieza Segura de Kernels y Paquetes Obsoletos

Una vez reiniciada la máquina y reconectado por SSH:

1. Confirmar que el servidor levantó con el kernel más reciente:
   ```bash
   uname -r
   ```

2. **Eliminar los paquetes viejos y huérfanos:**
   ```bash
   sudo apt autoremove --purge -y
   ```
   *(Esto borrará de forma segura los núcleos antiguos que ya no están en uso).*

3. **Vaciar la caché de paquetes:**
   ```bash
   sudo apt clean
   ```

4. Verificar que solo quede el kernel activo:
   ```bash
   dpkg -l | grep linux-image
   ```

---

## 4. Impacto en Wazuh (Vulnerability Detector)

### ¿Cómo interpreta Wazuh las vulnerabilidades?
* **Base de datos de paquetes:** Wazuh no mide si un servicio está encendido; revisa las versiones de paquetes registradas en el gestor `dpkg`.
* **Estados en el Panel:**
  * `Active`: Paquete instalado en el sistema con versión afectada por un CVE no resuelto.
  * `Solved`: Vulnerabilidad que ya fue parchada mediante actualización o mitigada en el inventario.
* **Por qué quedan vulnerabilidades activas si ya se actualizó:**
  Si el kernel `6.12.107` o `6.12.113` permanece en disco, Wazuh seguirá reportando los CVEs asociados a esos binarios antiguos.
* **Resultado tras ejecutar `autoremove --purge`:**
  En el siguiente ciclo de escaneo del agente Wazuh, los paquetes obsoletos eliminados desaparecerán del inventario y el reporte de vulnerabilidades activas se reducirá a cero.

---

## 5. Medidas Preventivas Específicas para Proxies Nginx

En entornos de proxy inverso con Frontend y Backend:

1. **Actualización Escalonada (Rolling Updates):**
   - Actualizar primero el **Proxy Backend**. Probar su estabilidad.
   - Actualizar posteriormente el **Proxy Frontend**.
   - Nunca reiniciar o actualizar ambos servidores al mismo tiempo.
2. **Validación de Sintaxis Previa:**
   Antes y después de cualquier actualización que toque Nginx o librerías del sistema, verificar la configuración:
   ```bash
   sudo nginx -t
   ```
3. **Recarga limpia sin desconexión de clientes:**
   Si solo se modifican configuraciones de Nginx (sin cambio de librerías del sistema), preferir la recarga suave de procesos worker:
   ```bash
   sudo systemctl reload nginx
   ```
