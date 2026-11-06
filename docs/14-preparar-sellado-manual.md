# 14. Limpieza y Verificación Previa a Producción

**Objetivo:** Asegurar que el servidor no conserve credenciales temporales, historiales de consola, archivos de instalación huérfanos ni tokens antes de ser incorporado formalmente a producción.

> **Nota:** Se eliminó el procedimiento de sellado para plantillas y clonación. Cada servidor se endurece y asegura de forma directa e independiente.

---

## 14.1 Verificación de Agentes y Secretos del Servidor

En la terminal del servidor:

```bash
# Verificar estado de los servicios de seguridad
sudo systemctl is-active ufw fail2ban rsyslog auditd

# Comprobar que los agentes corporativos cuentan con sus llaves únicas
sudo test -s /var/ossec/etc/client.keys && echo "Wazuh enrolado OK" || echo "Falta enrolar Wazuh"
sudo test -e /etc/zabbix/zabbix_agent2.psk && echo "PSK Zabbix presente OK" || echo "Falta PSK Zabbix"

# Verificar que los puertos en escucha corresponden estrictamente al rol del servidor
sudo ss -lntup
```

---

## 14.2 Limpieza de Datos Temporales y Credenciales

Antes de dar el pase final a producción:

1. **Eliminar herramientas de desarrollo si no son necesarias:**
   Si se utilizó `git` o compiladores temporalmente para el despliegue del repositorio o herramientas, y el servidor es un proxy productivo:
   ```bash
   # Opcional: remover herramientas que no deben estar en un frontend público
   sudo apt purge --autoremove -y git
   ```

2. **Limpiar archivos temporales y caché de paquetes:**
   ```bash
   sudo apt clean
   sudo rm -rf /tmp/* /var/tmp/*
   ```

3. **Sanitizar historiales de comandos administrativos:**
   Para evitar que queden registradas contraseñas, tokens o comandos sensibles ejecutados durante la instalación:
   ```bash
   history -c
   cat /dev/null > ~/.bash_history
   sudo cat /dev/null > /root/.bash_history
   ```

4. **Reiniciar y comprobar persistencia:**
   ```bash
   sudo reboot
   ```
   Tras el reinicio, verificar que UFW, Fail2ban, Nginx y los agentes inicien automáticamente sin fallos:
   ```bash
   systemctl --failed
   sudo ufw status verbose
   ```
