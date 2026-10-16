# 6. Perfil Docker

**Objetivo:** instalar Docker en los clones que lo necesitan, conservando el control de puertos y privilegios.

**Dónde:** clon de laboratorio dedicado a contenedores. No en todas las plantillas.

## 6.1 Comprobar antes

```bash
cat /etc/os-release
sudo nft list ruleset
sudo iptables-save
sysctl net.ipv4.ip_forward
dpkg-query -W docker.io docker-ce containerd containerd.io runc 2>/dev/null
```

Si ya existen contenedores, datos o reglas administradas por otro producto, no ejecutes una instalación limpia encima. Inventaría y prepara una migración.

La propuesta inicial usa Docker con backend iptables y herramientas iptables-nft, sin mezclarlo con reglas nftables propias generadas por el baseline. El backend nativo nftables requiere una validación separada; su comportamiento y cadenas no son equivalentes.

## 6.2 Instalar desde el repositorio oficial

Sigue la sección **Install using the apt repository** de [Docker para Debian](https://docs.docker.com/engine/install/debian/). Usa la clave y el repositorio `stable` para Trixie; no el script de conveniencia canalizado a una shell.

Con ese repositorio ya configurado:

```bash
sudo apt-get update
apt-cache madison docker-ce
```

Elige la versión estable ensayada. Este comando pide el texto exacto mostrado por APT:

```bash
read -r -p 'Version exacta de docker-ce probada: ' VERSION_DOCKER
test -n "$VERSION_DOCKER" && sudo apt-get install --no-remove "docker-ce=$VERSION_DOCKER" "docker-ce-cli=$VERSION_DOCKER" containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl is-active docker
sudo docker version
sudo docker info
sudo iptables -S DOCKER-USER
```

Guarda también las versiones resueltas de containerd y plugins. Fijar solo docker-ce no fija todo el conjunto. Las actualizaciones se vuelven a probar; congelar indefinidamente paquetes vulnerables tampoco es una solución.

## 6.3 Publicar solo donde hace falta

Para una aplicación que recibe tráfico desde un proxy instalado en la misma VM, publica en loopback:

```yaml
services:
  aplicacion:
    image: REGISTRO/IMAGEN@sha256:DIGEST_REAL
    ports:
      - "127.0.0.1:8080:8080"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=64m,mode=1777
    pids_limit: 256
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Es un **ejemplo a adaptar**, no un despliegue funcional: falta imagen/digest, usuario admitido por ella, secretos, almacenamiento, límites y healthcheck de la aplicación. Un filesystem de solo lectura o eliminar capacidades puede impedir que una imagen mal preparada arranque. Comprueba su documentación y ajusta lo mínimo necesario.

Si el proxy está en otra VM, loopback no sirve: publica en la IP privada prevista y restringe el origen. Evita publicar la BD si basta una red interna entre contenedores. No montes `/var/run/docker.sock` ni uses `privileged: true` en aplicaciones sin una necesidad revisada.

## 6.4 Proteger puertos de contenedores

Los puertos publicados atraviesan forwarding/NAT y pueden evitar reglas pensadas solo para INPUT. El perfil necesita reglas revisadas en `DOCKER-USER` para el backend elegido, tanto IPv4 como IPv6 cuando aplique.

No se entrega un `DROP` universal: faltan interfaces, redes y flujos permitidos. Mientras se desarrolla esa política, restringe desde Proxmox/red y no expongas el piloto a producción.

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
sudo iptables -vnL DOCKER-USER
sudo ip6tables -S
sudo ss -lntup
```

`ss` solo no demuestra qué publica Docker: contrasta con Docker y conexiones desde otros equipos. Prueba desde un origen permitido y otro denegado, antes y después de reiniciar Docker y la VM.

## 6.5 Aceptar el perfil

- Aplicación y persistencia funcionan después de recrear contenedores y reiniciar.
- Solo los puertos previstos son accesibles; la BD no queda abierta accidentalmente.
- Ningún usuario recibe acceso al grupo/socket Docker por comodidad: equivale a una capacidad administrativa muy elevada.
- Logs tienen límites; backups incluyen datos persistentes y se restaura un caso real de prueba.
- Wazuh, Zabbix, EDR y antivirus conservan funcionamiento y rendimiento aceptable.

Fuentes: [instalación Docker](https://docs.docker.com/engine/install/debian/), [seguridad del daemon](https://docs.docker.com/engine/security/), [backend nftables](https://docs.docker.com/engine/network/firewall-nftables/).
