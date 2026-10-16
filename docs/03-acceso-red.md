# 3. Proteger acceso y red

**Objetivo:** administración por llave y acceso a servicios solo desde redes autorizadas.

**Dónde:** VM de laboratorio. Mantén abierta la consola de Proxmox durante esta etapa.

## 3.1 Probar el acceso por llave antes de cerrar contraseñas

En tu PC, utiliza tu llave administrativa y comprueba su huella con el responsable. Si todavía no tienes una, créala con una frase de paso; no sobrescribas una llave existente:

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\infra_debian13"
```

Instala únicamente la clave **pública** en `~/.ssh/authorized_keys` del usuario de la VM. Directorio modo 0700, archivo 0600 y propietario el usuario. Nunca copies la clave privada a la VM ni al repositorio.

Desde una segunda terminal de tu PC:

```powershell
ssh -i "$env:USERPROFILE\.ssh\infra_debian13" -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no operador@IP_LAB
```

Dentro de esa sesión:

```bash
sudo -v
```

**Esperado:** acceso por llave y sudo operativo. Si falla cualquiera, no continúes.

## 3.2 Aplicar un perfil SSH sin túneles

Desde la consola de Proxmox, respalda la configuración. Usa un nombre nuevo si ese respaldo ya existe:

```bash
sudo install -d -m 0700 /root/respaldo-baseline
sudo cp -a /etc/ssh /root/respaldo-baseline/ssh-antes
sudo grep -nE '^[[:space:]]*(Include|Match)' /etc/ssh/sshd_config
sudo ls -l /etc/ssh/sshd_config.d/
```

Comprueba que el archivo principal incluye `/etc/ssh/sshd_config.d/*.conf` fuera de bloques `Match`. Si no, adapta primero su estructura. OpenSSH suele usar el primer valor encontrado; llamar a un archivo `99-...` no garantiza que prevalezca.

```bash
sudo tee /etc/ssh/sshd_config.d/00-baseline.conf >/dev/null <<'EOF'
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
DisableForwarding yes
X11Forwarding no
PermitUserEnvironment no
MaxAuthTries 3
LoginGraceTime 30
LogLevel VERBOSE
EOF
sudo chmod 0644 /etc/ssh/sshd_config.d/00-baseline.conf
sudo /usr/sbin/sshd -t
```

Este perfil deshabilita túneles SSH. Si tu operación utiliza saltos, túneles de BD o despliegues que los requieren, documenta una excepción específica antes de aplicarlo.

Comprueba la configuración efectiva; sustituye usuario, nombre e IP de la estación administrativa:

```bash
sudo /usr/sbin/sshd -T -C user=operador,host=pc-admin,addr=IP_ADMIN | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|disableforwarding|x11forwarding) '
```

**Esperado:** root/password/keyboard-interactive/X11 en `no`, publickey y disableforwarding en `yes`. Si difiere, resuelve precedencia/Match antes de recargar.

```bash
sudo systemctl reload ssh
```

Abre **otra conexión nueva** por llave y prueba `sudo -v`. La sesión anterior abierta no demuestra que una nueva conexión funcione.

**Si falla:** desde la consola retira únicamente el archivo creado y vuelve a comprobar/recargar:

```bash
sudo mv /etc/ssh/sshd_config.d/00-baseline.conf /root/respaldo-baseline/00-baseline-fallido.conf
sudo /usr/sbin/sshd -t
sudo systemctl reload ssh
```

Si modificaste otros archivos, recupera sus versiones del respaldo. No cambies permisos/PAM/caducidad de todas las cuentas en esta misma etapa.

## 3.3 Definir los accesos por función

| Servicio | Origen permitido | Destino |
|---|---|---|
| SSH | VPN / bastión / red administrativa | TCP 22 de la VM |
| Web público | Clientes previstos | TCP 443 del proxy; 80 solo si hace falta |
| Backend | Proxy autorizado | Puerto de la aplicación |
| BD | Servidores de aplicación autorizados | Puerto específico de la BD |
| Zabbix activo | Salida de la VM hacia servidor/proxy | TCP 10051 habitualmente |
| Zabbix pasivo, si se elige | Solo servidor/proxy | TCP 10050 de la VM |
| Wazuh | Salida a manager/enrollment | Según configuración real, no asumir puertos universales |
| EDR/antivirus | Salida a servicios del fabricante/tenant | Según matriz oficial del producto |

Para el piloto aplica primero esta matriz en el firewall de Proxmox o en el firewall de la red. Verifica que realmente esté habilitado en los niveles necesarios del entorno y en la interfaz de la VM. No cambies el firewall del host Proxmox desde scripts de Debian.

## 3.4 Elegir el firewall del invitado

**VM sin Docker:** nftables es el candidato. **VM que tendrá Docker:** sigue [6. Docker](06-docker.md) antes de definir reglas. No lleves una política de forwarding DROP de una plantilla genérica a un host de contenedores sin adaptarla.

Inventario de reglas y escuchas:

```bash
sudo nft list ruleset
sudo ss -lntup
sudo systemctl is-active nftables ufw firewalld
```

Si hay reglas existentes, identifica quién las administra. Evita que Ansible Lockdown, scripts locales, Docker y un servicio de firewall reescriban la misma política.

**La automatización de firewall queda pendiente del inventario de redes y del perfil.** No se incluye una regla de ejemplo que permita SSH desde todo Internet ni un `flush ruleset`. Hasta validar el firewall del invitado, limita la exposición desde Proxmox/red y mantén el piloto aislado; esta limitación impide declararlo terminado para producción.

## 3.5 Probar desde dos orígenes autorizados para la prueba

Desde la red administrativa debe funcionar SSH. Desde una red sin permiso debe fallar una conexión nueva al mismo puerto. Prueba también IPv6 si existe. Haz la misma comprobación con cada puerto de servicio y después de reiniciar.

Desde Windows:

```powershell
Test-NetConnection IP_LAB -Port 22
```

**Evidencia:** origen, destino, puerto, fecha y resultado permitido/denegado. Si falla una aplicación, registra el flujo necesario; no abras todos los puertos para solucionar el síntoma.

Fuentes: [OpenSSH en Debian 13](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html), [Docker y firewall](https://docs.docker.com/engine/install/debian/).
