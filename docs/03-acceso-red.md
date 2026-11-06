# 3. Proteger acceso y red

> Este capítulo describe el perfil por llave. Para el perfil acordado con **contraseña**, usa [9. Base en bloque](09-base-en-bloque.md); no ejecutes aquí el bloque que establece `PasswordAuthentication no`.

**Objetivo:** administración por llave y acceso a servicios solo desde redes autorizadas.

**Dónde:** Servidor Debian 13. Mantén una sesión activa de respaldo durante esta etapa.

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

Antes de aplicar cambios en SSH, respalda la configuración actual:

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

Aplica esta matriz en el firewall perimetral de la red y en el firewall del propio host.

## 3.4 Firewall del Servidor (UFW + Fail2ban)

El firewall del host se implementa mediante **UFW** (con backend nativo `iptables-nft`), con IPv6 desactivado y Fail2ban enlazado (`banaction = ufw`).

La política por defecto es **bloquear todo el tráfico entrante** y permitir el tráfico saliente:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment "SSH Administracion"
sudo ufw enable
```

Para la integración con Fail2ban, reglas por rol de servidor (Frontend, Backend, bases de datos) y verificación completa, consulta [12. Firewall UFW](12-firewall-ufw.md).

## 3.5 Probar desde dos orígenes autorizados para la prueba

Desde la red administrativa debe funcionar SSH. Desde una red sin permiso debe fallar una conexión nueva al mismo puerto. Prueba también IPv6 si existe. Haz la misma comprobación con cada puerto de servicio y después de reiniciar.

Desde Windows:

```powershell
Test-NetConnection IP_LAB -Port 22
```

**Evidencia:** origen, destino, puerto, fecha y resultado permitido/denegado. Si falla una aplicación, registra el flujo necesario; no abras todos los puertos para solucionar el síntoma.

Fuentes: [OpenSSH en Debian 13](https://manpages.debian.org/trixie/openssh-server/sshd_config.5.en.html), [Docker y firewall](https://docs.docker.com/engine/install/debian/).
