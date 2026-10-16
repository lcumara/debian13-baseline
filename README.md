# Base de seguridad Debian 13 para Proxmox

**Edición 0.1 — investigación, diseño y diagnóstico. 16 de octubre de 2026.**

Objetivo: construir y mantener una plantilla Debian 13 reproducible para máquinas virtuales Proxmox, con una base común de seguridad, perfiles por función y personalización individual antes de habilitar cada clon en producción.

Esta entrega contiene una propuesta técnica y un recolector ejecutable de evidencia local. **Todavía no es un instalador completo ni una plantilla certificada o probada en Debian.** No se realizaron cambios en servidores, hipervisor, agentes ni repositorios remotos.

## Recorrido de lectura

1. [Manual y arquitectura](docs/manual.md): decisiones, capas, controles, agentes, Docker, clonación, operación y formato recomendado.
2. [Revisión del script entregado](docs/revision-script.md): problemas concretos y correcciones que debe incorporar la implementación.
3. [Aceptación y prioridades](docs/aceptacion.md): pruebas, evidencias, responsables propuestos y condiciones de liberación.
4. [Fuentes y proyectos comparados](docs/fuentes.md): documentación oficial consultada y límites de la investigación.
5. [Inventario de ejemplo](inventario.ejemplo.yml): separación entre valores generales y datos individuales. Es un esquema de diseño; no lo consume todavía un playbook.

## Primer ejecutor: diagnóstico local

Requiere Python 3. En Debian 13, desde una copia revisada de esta carpeta:

```bash
python3 bin/auditar.py --listar
sudo python3 bin/auditar.py --recopilar --salida /root
```

El primer comando muestra lo que consultará. El segundo crea una carpeta privada nueva, con `evidencia.json` y `resumen.md`. Consulta solo el equipo local; no instala paquetes, no actualiza APT, no cambia archivos de configuración, no reinicia servicios y no realiza escaneos de red.

Las evidencias contienen información interna: versiones, nombres, rutas, puertos y reglas de red. Deben quedar fuera de Git y revisarse antes de compartir. El recolector no abre archivos de contraseñas, PSK, claves privadas ni configuraciones de agentes. Los nombres de unidades/paquetes de G DATA y FortiEDR se incluyen en el inventario general, sin inventarlos ni ejecutar sus instaladores. No puede garantizar que una configuración externa haya evitado introducir datos sensibles en nombres o comentarios de reglas.

Un código de salida 0 significa que se completó la recolección prevista, **no que el servidor sea seguro**. Código 2 indica consultas ausentes, con error o con resultado no cero que requieren interpretación; por ejemplo, `systemctl is-active` puede devolver un estado inactivo legítimo. Código 1 indica un error de uso o entorno. Las comprobaciones por contexto SSH, recepción central, restauración y exposición externa son adicionales.

## Producto final recomendado

- Manual vivo en Markdown, publicable como documentación interna y exportable a PDF por cada versión.
- Ansible como motor de cambios por roles, con inventario, validación previa y secretos externos.
- Cloud-init para primera identidad del clon; no como depósito permanente de credenciales.
- Diagnóstico, plan, aplicación por etapas y validación como operaciones distintas.
- Versiones exactas y artefactos identificables en cada liberación; selección desde canales estables compatibles, sin una dependencia flotante de `latest`.

La meta inicial propuesta es CIS Debian 13 Level 1 Server adaptado, más controles Level 2 elegidos por riesgo. La correspondencia exacta por ID requiere revisar la edición oficial elegida y la política SCA realmente instalada. Las excepciones se documentan y revisan; no se ocultan para mejorar el porcentaje.

## Estado de esta entrega

Se revisaron el texto Bash adjunto, las dos páginas de la ficha de continuidad y material previo del directorio. Se consultaron fuentes oficiales y repositorios originales. El recolector se valida localmente en Windows por sintaxis Python, interfaz y manejo de resultados simulados; falta ejecutarlo en Debian 13. La guía no afirma compatibilidad de G DATA con Debian 13: la matriz pública consultada no la confirma.

No ejecutar en serie el script original, el asistente previo y futuros roles sin una migración explícita: pueden administrar los mismos archivos con políticas diferentes.
