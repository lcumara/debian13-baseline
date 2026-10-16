# Debian 13 seguro: empieza aquí

Queremos construir una **guía paso a paso con comandos que puedas ejecutar** para preparar servidores Debian 13 en Proxmox. Después podremos guardar un servidor preparado como plantilla y crear nuevos servidores a partir de ella.

**Estado actual: el instalador automático todavía no está construido.** Este repositorio contiene la investigación, la revisión de tu script y una herramienta que recoge información del servidor. Subir estos archivos a GitHub no instaló ni configuró nada en tus servidores.

## 1. Lo que vamos a hacer, en orden

### Primero: preparar el servidor que servirá de modelo

Trabajaremos con una máquina virtual Debian 13 de laboratorio en Proxmox. En ella instalaremos y probaremos la seguridad común: actualizaciones, acceso administrativo, firewall, registros, auditoría y protección de archivos y servicios.

**Resultado esperado:** un servidor de prueba con una configuración de seguridad comprobada y una guía que permita repetirla.

### Segundo: convertir ese servidor en una plantilla

Una plantilla es el modelo desde el que Proxmox crea nuevos servidores. Antes de guardarla, hay que prepararla para que los nuevos equipos no hereden la misma identidad ni los mismos secretos.

**Resultado esperado:** una plantilla reutilizable que permita crear servidores independientes.

### Tercero: crear un servidor nuevo y darle su identidad

Al crear una copia de la plantilla, le asignaremos nombre, IP, DNS y claves propias. También elegiremos para qué se usará: una aplicación, una base de datos, un proxy o un servidor con Docker.

**Resultado esperado:** un servidor individual, con los ajustes y puertos que necesita su función. Cambiar solo el nombre y la IP no completa este paso.

### Cuarto: conectar los agentes y comprobar el servicio

Con el nombre y la red definitivos, instalaremos o registraremos Wazuh, Zabbix, FortiEDR y G DATA según su compatibilidad. Cada servidor tendrá su propio registro y sus propios secretos.

Comprobaremos que los agentes reportan, que la aplicación funciona, que el servidor reinicia correctamente y que se puede recuperar una copia de respaldo.

**Resultado esperado:** un servidor listo para su aceptación y entrada en producción. Los agentes deben quedar comprobados antes de recibir tráfico productivo.

## 2. Cómo será la guía que usarás

Cada paso tendrá siempre esta forma:

| Lo que verás | Para qué sirve |
|---|---|
| Qué vamos a hacer | Explicación breve del cambio |
| Dónde hacerlo | VM de laboratorio, plantilla o servidor nuevo |
| Datos que necesitas | Por ejemplo, nombre del equipo o dirección del servidor de monitoreo |
| Comando o acción | Lo que debes ejecutar |
| Qué resultado esperar | Cómo reconocer que funcionó |
| Qué hacer si falla | Cómo detenerse o recuperar la configuración anterior |

Las acciones se automatizarán después de probarlas. Docker tendrá instrucciones propias porque necesita un tratamiento distinto de la red y los permisos.

## 3. Qué hay realmente disponible hoy

| Elemento | Estado |
|---|---|
| Investigación y propuesta del orden de trabajo | Preparadas |
| Revisión de problemas de tu script original | Preparada |
| Programa que recoge información del servidor | Creado; probado localmente con simulaciones, pendiente de probar en Debian 13 |
| Guía completa de instalación paso a paso | Pendiente de desarrollar y probar |
| Programa que instala y aplica toda la seguridad | Pendiente de construir |
| Plantilla Proxmox lista para clonar | Pendiente de construir y probar |
| Instalación de agentes por servidor | Pendiente; G DATA requiere confirmar soporte para Debian 13 |

**El siguiente paso práctico será trabajar sobre una VM Debian 13 de laboratorio.** No hace falta comprender ni editar todos los archivos del repositorio para empezar. Esta portada es el punto de entrada; los documentos de abajo guardan el detalle técnico para desarrollar el proyecto.

## 4. Para qué sirve GitHub en este proyecto

GitHub guarda los archivos y su historial: permite saber qué cambió, revisar una versión anterior y mantener la guía junto con los programas. No administra ni protege automáticamente las máquinas virtuales.

Este repositorio es privado. Los informes reales de servidores y las credenciales deben mantenerse fuera de él.

<details>
<summary><strong>Ver los documentos técnicos y para qué sirve cada uno</strong></summary>

- [manual.md](docs/manual.md): diseño técnico del proyecto. Todavía no es la guía completa de instalación.
- [revision-script.md](docs/revision-script.md): qué problemas encontramos en tu script y cómo corregirlos.
- [aceptacion.md](docs/aceptacion.md): pruebas que debe superar un servidor antes de usarlo en producción.
- [fuentes.md](docs/fuentes.md): documentación oficial y proyectos consultados.
- [inventario.ejemplo.yml](inventario.ejemplo.yml): ejemplo de los datos que tendrá cada servidor. Todavía no configura equipos.
- [bin/auditar.py](bin/auditar.py): programa que recoge información local; no aplica correcciones.
- [tests/test_auditar.py](tests/test_auditar.py): pruebas del programa de diagnóstico; no configura servidores.
- `.gitignore` y `.gitattributes`: archivos auxiliares para gestionar el repositorio.

</details>

<details>
<summary><strong>Ver cómo se usa el diagnóstico disponible</strong></summary>

Requiere Python 3. Estos comandos se ejecutan dentro de una copia de esta carpeta en la VM Debian 13; no en la página de GitHub ni en Windows.

Mostrar las consultas que realizará, sin ejecutarlas:

```bash
python3 bin/auditar.py --listar
```

Recoger información local y guardarla en una carpeta privada nueva dentro de `/root`:

```bash
sudo python3 bin/auditar.py --recopilar --salida /root
```

El programa muestra la ruta de los archivos `resumen.md` y `evidencia.json`. Consulta el estado del equipo; no instala paquetes, actualiza APT, cambia configuraciones, reinicia servicios ni realiza escaneos de red.

Los informes contienen información interna y deben revisarse antes de compartir. El programa no abre archivos de contraseñas, PSK, claves privadas ni configuraciones de agentes; una configuración externa podría haber incluido datos sensibles en nombres o comentarios de reglas.

Código de salida 0: consultas terminadas, no aprobación de seguridad. Código 2: hay resultados que revisar, herramientas ausentes o consultas fallidas. Código 1: error de uso o entorno. La comprobación de agentes en sus consolas, la restauración y la evaluación CIS son trabajos adicionales.

</details>

Edición inicial de diseño y diagnóstico. Actualizada el 16 de octubre de 2026.
