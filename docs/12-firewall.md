# 12. Firewall del Host con UFW y Fail2ban

> **Actualización v0.4:** El proyecto estandariza el uso de **UFW** (con backend nativo `iptables-nft`), manteniendo `/etc/nftables.conf` en configuración limpia por defecto y vinculando las acciones de baneo de **Fail2ban** directamente con UFW en IPv4. Se reemplaza el ejecutor anterior `firewall_base.py` por la gestión nativa del paquete del sistema.

**Objetivo:** Establecer una política de firewall sencilla, robusta y estandarizada en Debian 13 (Trixie), denegando entrada no autorizada y conservando SSH/22 coordinado con Fail2ban.

---

## 1. Arquitectura y Fundamentos

1. **UFW sobre `nf_tables`:** En Debian 13, UFW opera sobre el subsistema moderno `nf_tables` del kernel Linux a través de la capa `iptables-nft`, garantizando alto rendimiento y control perimetral sin scripts propietarios.
2. **Coexistencia con `nftables`:** Mantener `/etc/nftables.conf` con las tablas limpias por defecto evita colisiones de reglas y previene que un reinicio de `nftables` borre las cadenas de UFW.
3. **Gestión de ataques con Fail2ban:** Con `banaction = ufw`, cualquier IP que acumule intentos fallidos de autenticación SSH es bloqueada directamente en UFW y visible con `sudo ufw status`.

---

## 2. Procedimiento de Configuración Paso a Paso

### 2.1 Restaurar `nftables.conf` al estándar limpio
Asegurar que `/etc/nftables.conf` contenga únicamente la tabla base oficial de Debian:

```nft
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
	chain input {
		type filter hook input priority filter;
	}
	chain forward {
		type filter hook forward priority filter;
	}
	chain output {
		type filter hook output priority filter;
	}
}
```

Aplicar y activar:
```bash
sudo systemctl restart nftables
```

### 2.2 Instalar UFW y desactivar IPv6
```bash
sudo apt update && sudo apt install -y ufw
sudo sed -i 's/IPV6=yes/IPV6=no/' /etc/default/ufw
```

### 2.3 Políticas Base y SSH
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment "SSH Administrativo"
sudo ufw --force enable
```

### 2.4 Integración de Fail2ban
En `/etc/fail2ban/jail.d/90-baseline-sshd.local`:
```ini
[sshd]
enabled = true
backend = systemd
port = 22
filter = sshd
maxretry = 5
findtime = 10m
bantime = 10m
usedns = no
banaction = ufw
```

Reiniciar Fail2ban:
```bash
sudo systemctl restart fail2ban
```

---

## 3. Comprobaciones

1. **Acción de Fail2ban vinculada a UFW:**
   ```bash
   sudo fail2ban-client get sshd actions
   # Salida esperada: ufw
   ```

2. **Estado del firewall:**
   ```bash
   sudo ufw status verbose
   ```

---

## 4. Gestión de Servicios por Función (Frontend y Backend)

* **Proxy Frontend (Web público):**
  ```bash
  sudo ufw allow 443/tcp comment "HTTPS Nginx"
  # 80/tcp solo si se requiere redirección
  sudo ufw allow 80/tcp comment "HTTP Nginx"
  ```

* **Proxy Backend (Restringido solo al Frontend):**
  ```bash
  sudo ufw allow from <IP_FRONTEND> to any port 80 proto tcp comment "HTTP desde Frontend"
  sudo ufw allow from <IP_FRONTEND> to any port 443 proto tcp comment "HTTPS desde Frontend"
  ```

* **Eliminar una regla:**
  ```bash
  sudo ufw status numbered
  sudo ufw delete <número_regla>
  ```
