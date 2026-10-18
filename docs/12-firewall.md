# 12. Firewall de entrada de la plantilla

**Objetivo:** denegar entrada no autorizada al host IPv4/IPv6, conservando SSH/22 y las tablas de Fail2ban. Perfil inicial con SSH como único servicio publicado.

## Aplicar

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
sudo python3 bin/firewall_base.py --aplicar
```

Mantén abierta la sesión. Abre **otra conexión SSH** y, desde ella, confirma antes de 20 minutos:

```bash
sudo -v
cd ~/trabajo/debian13-baseline
sudo python3 bin/firewall_base.py --confirmar
sudo python3 bin/firewall_base.py --verificar
sudo fail2ban-client status sshd
```

Sin confirmación, el timer retira únicamente la tabla propia y deshabilita el servicio propio. No reiniciar antes de confirmar: el timer es transitorio. La persistencia se habilita después de confirmar el acceso.

## Política

- Tabla propia `inet baseline_host`, cadena INPUT con política drop.
- Permite loopback, conexiones establecidas/relacionadas, ICMP/ICMPv6 (incluye diagnóstico y control de red), respuestas DHCPv4/v6 y nuevas conexiones SSH TCP/22.
- Descarta origen loopback recibido por otra interfaz y estados inválidos.
- SSH permitido desde cualquier origen; la restricción a redes administrativas se define por clon sin publicar IP en Git.
- No borra ni guarda las tablas dinámicas de Fail2ban. No utiliza `flush ruleset`.
- Salida sin restricciones adicionales. No crea cadena FORWARD ni afirma proteger puertos publicados por Docker. Estos son límites expresos respecto de una política CIS completa.

El servicio propio es `baseline-firewall.service`; no habilitar además nftables.service con su configuración genérica, que puede borrar tablas ajenas. El código de arranque y su estado quedan bajo `/var/lib/debian13-baseline/firewall-*`, root:root y privado. **No borrar ese directorio al limpiar la plantilla**: contiene el ejecutor requerido por systemd, no solo un respaldo. Las reglas no contienen identidades ni IP propias del servidor.

Después de confirmar puedes reiniciar y repetir la verificación. Prueba desde otra máquina autorizada que SSH funciona y que un puerto temporal con un servicio realmente escuchando resulta bloqueado; un puerto sin servicio no demuestra filtrado. Esa prueba externa no está automatizada aquí. Las pruebas locales del repositorio son simuladas; `nft -c` se ejecuta en la VM antes de activar reglas.

## Recuperar

## Abrir servicios después de clonar

Actualiza el repositorio del clon. No repitas `--aplicar`: el firewall ya existe.

```bash
cd ~/trabajo/debian13-baseline
git -c credential.helper= pull --ff-only
```

Ejemplos: ejecutar solo los correspondientes a servicios reales. HTTPS público en IPv4 e IPv6:

```bash
sudo python3 bin/firewall_base.py --permitir-tcp 443 --origen cualquiera
```

HTTP, si el despliegue lo requiere (redirección o validación de certificados):

```bash
sudo python3 bin/firewall_base.py --permitir-tcp 80 --origen cualquiera
```

PostgreSQL, únicamente desde la IP de la aplicación. El dato se introduce localmente, no se comparte en el chat:

```bash
read -r -p 'IP o red CIDR autorizada de la aplicación: ' RED_APP
sudo python3 bin/firewall_base.py --permitir-tcp 5432 --origen "$RED_APP"
```

Usar 3306 para MySQL/MariaDB si corresponde. Una IP IPv4 autoriza únicamente esa familia; para IPv6 añadir su IP/red explícitamente. Los permisos son acumulativos: agregar un origen restringido no elimina un permiso previo para `cualquiera`.

Para retirar exactamente un permiso:

```bash
sudo python3 bin/firewall_base.py --cerrar-tcp 5432 --origen "$RED_APP"
sudo python3 bin/firewall_base.py --verificar
sudo nft list table inet baseline_host
```

Las conexiones ya establecidas pueden seguir hasta cerrarse. Estos comandos no permiten modificar SSH/22. Guardan permisos de forma privada en el estado y actualizan el ejecutor de arranque; comprueban sintaxis y reemplazan solo la tabla propia mediante una transacción nft. El verificador comprueba presencia del puerto, no prueba exhaustivamente origen/destino; comprobar desde un origen permitido y otro no permitido y después de reiniciar. Al producirse un error se intenta restaurar la política previa.

Abrir el firewall no instala el servicio ni configura autenticación, TLS o la interfaz de escucha de la base de datos. Si aplicación y base se comunican por localhost o socket Unix, no abras el puerto de la base a la red. Los backends detrás de un proxy local tampoco necesitan un puerto público propio.

**Docker:** estos permisos cubren INPUT del host. Un puerto publicado por Docker normalmente utiliza FORWARD y sus reglas propias; no asumir que este bloqueo lo protege. Para un backend accesible solo por un proxy local, publicar explícitamente en loopback, por ejemplo `127.0.0.1:8080:8080`, y verificar el despliegue real. Las bases entre contenedores pueden usar una red interna sin publicar el puerto al host. El perfil Docker completo sigue pendiente.

## Recuperación del firewall completo

```bash
sudo python3 bin/firewall_base.py --restaurar
```

Retira la tabla propia y deshabilita el servicio; deja los archivos para diagnóstico. El aplicador rechaza sobreescribir un servicio o tabla ya existentes. Si se restauró, revisar el registro antes de preparar otra aplicación; no repetir borrando archivos a ciegas.

## Estado de cierre

Esta etapa termina la implementación del firewall de entrada del host. **No termina CIS completo ni el sellado.** Continúan pendientes opciones de montaje, revisión de módulos y arranque, controles restantes de auditoría/cuentas, pruebas funcionales de PAM, evaluación por ID, agentes y regeneración de identidades. Las excepciones de contraseña y separación de particiones constan en el capítulo 11.

Fuentes: [nftables](https://netfilter.org/projects/nftables/manpage.html), [Docker y nftables](https://docs.docker.com/engine/network/firewall-nftables/).
