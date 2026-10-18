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

```bash
sudo python3 bin/firewall_base.py --restaurar
```

Retira la tabla propia y deshabilita el servicio; deja los archivos para diagnóstico. El aplicador rechaza sobreescribir un servicio o tabla ya existentes. Si se restauró, revisar el registro antes de preparar otra aplicación; no repetir borrando archivos a ciegas.

## Estado de cierre

Esta etapa termina la implementación del firewall de entrada del host. **No termina CIS completo ni el sellado.** Continúan pendientes opciones de montaje, revisión de módulos y arranque, controles restantes de auditoría/cuentas, pruebas funcionales de PAM, evaluación por ID, agentes y regeneración de identidades. Las excepciones de contraseña y separación de particiones constan en el capítulo 11.

Fuentes: [nftables](https://netfilter.org/projects/nftables/manpage.html), [Docker y nftables](https://docs.docker.com/engine/network/firewall-nftables/).
