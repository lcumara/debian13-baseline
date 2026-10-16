# 8. Cómo aprovechamos los proyectos existentes

**Objetivo:** ampliar controles sin introducir cambios desconocidos ni declarar cumplimiento no comprobado.

## 8.1 Proyecto elegido como referencia principal

[Ansible Lockdown DEBIAN13-CIS](https://github.com/ansible-lockdown/DEBIAN13-CIS), release **1.0.3**, commit:

```text
f9d8dbf5ecdbe0b4955209b4f35d67a727d95052
```

Se descargó esa versión y se revisaron puntos de entrada, variables, tareas preliminares, tareas de red y acciones posteriores. **No se auditó todo su código ni se ejecutó en Debian.** No copiamos su contenido dentro de nuestro ejecutor ni aplicamos su rol automáticamente.

La revisión encontró nivel 2 habilitado por defecto, tareas preliminares que instalan/modifican componentes y acciones posteriores capaces de solicitar/requerir reinicio. Seleccionar una etiqueta no equivale a eliminar todos los efectos auxiliares. Su README también limita la confianza en check mode.

El proyecto declara CIS 1.0.0; el catálogo CIS consultado ya publica Debian 13 1.1.0. Antes de reportar cumplimiento necesitamos comparar las reglas contra la versión realmente adoptada.

## 8.2 Descargar exactamente la referencia, sin ejecutarla

En una máquina de trabajo Linux con Git, fuera de servidores productivos:

```bash
mkdir -p ~/revision-seguridad
cd ~/revision-seguridad
git clone --branch 1.0.3 --depth 1 https://github.com/ansible-lockdown/DEBIAN13-CIS.git
cd DEBIAN13-CIS
git rev-parse HEAD
git diff --exit-code
```

**Esperado:** SHA exacto indicado arriba y árbol limpio. Una etiqueta podría cambiar; el commit esperado es nuestra referencia. No ejecutes todavía `site.yml`.

## 8.3 Orden de incorporación

| Grupo | Antes de habilitarlo |
|---|---|
| Permisos y servicios innecesarios | Identificar archivos/cuentas reales; no aplicar chmod recursivo genérico |
| Auditoría y logs | Acordar retención, capacidad y respuesta a disco lleno |
| SSH, sudo y PAM | Acceso alternativo, cuentas de servicio y prueba de nueva sesión |
| Particiones/montajes | Diseño durante creación; probar instaladores, Docker y BD con noexec |
| Firewall y sysctl de red | Inventario IPv4/IPv6, Docker, routing y dueño de reglas |
| Arranque/GRUB | Consola y recuperación, impacto en reinicios desatendidos |
| AppArmor de aplicaciones | Perfil real y pruebas con carga de la aplicación |

Por control: registrar versión/ID, efecto, archivos que cambia, dependencias, prueba, reversión y excepción si corresponde. Una misma política debe tener un único responsable de escritura; al migrar al rol Ansible se retira o integra nuestro ajuste equivalente, no se apilan configuraciones contradictorias.

## 8.4 Qué tomamos de los otros proyectos

- [OVH debian-cis](https://github.com/ovh/debian-cis): organización por control y separación entre auditoría/aplicación. Su adaptación a Debian 13 necesita revisión por regla.
- [DevSec Hardening](https://github.com/dev-sec/ansible-collection-hardening): patrones y roles de servicios, evitando que dos roles administren el mismo archivo.
- [Wazuh SCA](https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/available-sca-policies.html): seguimiento periódico desde la consola, corroborando hallazgos.

Las licencias se conservan si se reutiliza código: MIT para el repositorio Lockdown consultado y Apache-2.0 para los proyectos OVH/DevSec consultados. Esta edición usa referencias y código propio; no incluye una copia de los benchmarks CIS ni de instaladores comerciales.

## 8.5 Alcance real de esta edición

Tenemos guía operativa, diagnóstico, instalación de componentes y cinco ajustes kernel con recuperación. La integración automática completa del rol CIS, el firewall por inventario, PAM, auditoría detallada y los instaladores empresariales siguen pendientes de implementación/validación. No se presenta este piloto como “CIS completo” ni como plantilla ya aprobada.

Fuentes: [release fijada](https://github.com/ansible-lockdown/DEBIAN13-CIS/releases/tag/1.0.3), [catálogo CIS](https://www.cisecurity.org/benchmark/debian_linux), [fuentes del proyecto](fuentes.md).
