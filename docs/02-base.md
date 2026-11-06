# 2. Instalar y comprobar la seguridad común

> Piloto actualizado con contraseña SSH y sin acceso a snapshots: seguir [9. Base en bloque](09-base-en-bloque.md). Esa ruta conserva el cliente NTP y evita instalar recomendaciones de correo; sustituye los comandos de aplicación de este capítulo para ese perfil.

**Objetivo:** preparar los componentes comunes y aplicar un primer grupo de controles verificables.

**Dónde:** únicamente la VM Debian 13 de laboratorio. Ejecuta una sección cada vez.

## 2.1 Ver el plan

```bash
python3 bin/baseline.py paquetes
python3 bin/baseline.py kernel
```

Sin `--aplicar`, estas etapas solo imprimen el plan y no invocan comandos del sistema.

## 2.2 Instalar componentes

```bash
sudo python3 bin/baseline.py paquetes --aplicar --laboratorio --snapshot antes-baseline
```

| Componente | Para qué lo instalamos | Lo que falta comprobar |
|---|---|---|
| AppArmor | Limitar acciones de servicios mediante perfiles | Perfiles cargados y aplicación realmente cubierta |
| auditd | Auditoría de eventos del sistema | Reglas, retención y envío de alertas |
| Chrony | Sincronizar la hora | Fuentes NTP institucionales y sincronización |
| AIDE | Detectar cambios en archivos | Crear referencia después de configurar servicios finales |
| unattended-upgrades | Aplicar actualizaciones según política | Ventana, orígenes y reinicios acordados |
| debian-security-support | Informar limitaciones de soporte de paquetes | Revisar resultados y paquetes afectados |

APT puede arrancar servicios durante la instalación. `--no-remove` detiene resoluciones que requieran eliminar paquetes; por ejemplo, un conflicto con otro servicio NTP. No se fuerza su eliminación: revisa el conflicto en el piloto.

Si Chrony entra en conflicto con el cliente NTP existente, revisa primero `sudo apt-get -s install chrony`. Cuando confirmes que el único reemplazo esperado es ese cliente, realiza la instalación de Chrony como cambio separado, verifica la hora y repite la etapa. No elimines paquetes en bloque para hacer pasar el ejecutor.

**Esperado:** código 0 y una carpeta privada en `/var/lib/debian13-baseline/paquetes-...`. Si falla APT puede haber instalado parte de los paquetes; no se promete una desinstalación automática segura. Recupera el snapshot o corrige la causa documentando el cambio.

## 2.3 Aplicar cinco controles del kernel

```bash
sudo python3 bin/baseline.py kernel --aplicar --laboratorio --snapshot antes-baseline
sudo python3 bin/baseline.py verificar
```

| Ajuste | Efecto |
|---|---|
| `kernel.randomize_va_space=2` | Aleatoriza ubicaciones de memoria |
| `kernel.kptr_restrict=2` | Restringe exposición de direcciones del kernel |
| `kernel.dmesg_restrict=1` | Restringe lectura del registro del kernel |
| `fs.protected_hardlinks=1` | Restringe enlaces duros abusivos |
| `fs.protected_symlinks=1` | Restringe seguimiento inseguro de enlaces simbólicos |

Escribe `/etc/sysctl.d/90-debian13-baseline.conf`, guarda el archivo anterior y los valores efectivos, aplica y comprueba. Ante un fallo controlado intenta recuperar todos los valores; informa si la recuperación queda incompleta. Un corte eléctrico o SIGKILL puede interrumpir esa recuperación: queda el registro y el snapshot.

No modifica forwarding ni IPv6: la red de Docker y las aplicaciones se tratan por separado. Algunas herramientas de diagnóstico necesitan privilegios tras restringir dmesg/direcciones del kernel.

**Revertir esta etapa:** sustituye la ruta por la última ejecución kernel aplicada, mostrada por el programa:

```bash
sudo python3 bin/baseline.py revertir --aplicar --laboratorio --snapshot antes-baseline --registro /var/lib/debian13-baseline/kernel-ID_REAL
```

Si otra herramienta cambió después la política o los valores efectivos, la reversión se detiene para no sobreescribir esos cambios. Revisa el registro o recupera la VM. La reversión de kernel no desinstala paquetes.

## 2.4 Comprobar servicios y hora

```bash
sudo systemctl enable --now chrony auditd
systemctl is-active chrony auditd
chronyc tracking
chronyc sources -v
sudo aa-status
sudo auditctl -s
sudo auditctl -l
check-support-status
```

Configura servidores NTP autorizados en `/etc/chrony/chrony.conf`; evita mezclar fuentes institucionales con pools no autorizados. Tras editar:

```bash
sudo systemctl restart chrony
chronyc tracking
```

**Esperado:** hora sincronizada, servicios activos y AppArmor habilitado. `auditctl -l` vacío significa que faltan reglas; paquete instalado no equivale a auditoría completa.

## 2.5 Política de actualizaciones

En el piloto puedes configurar la opción ofrecida por Debian:

```bash
sudo dpkg-reconfigure unattended-upgrades
sudo unattended-upgrade --dry-run --debug
systemctl list-timers 'apt-*'
```

Revisa los orígenes permitidos y la política de reinicio en `/etc/apt/apt.conf.d/50unattended-upgrades`. No habilites reinicios automáticos de BD/aplicaciones sin ventana y prueba. La simulación no instala actualizaciones, pero puede generar logs/locks.

## 2.6 Reiniciar y repetir comprobaciones

```bash
sudo reboot
```

Reconecta y ejecuta:

```bash
cd ~/trabajo/debian13-baseline-main
sudo python3 bin/baseline.py verificar
sudo python3 bin/auditar.py --recopilar --salida /root
systemctl --failed
```

**Esperado:** los cinco valores se conservan. Si otro archivo sysctl los sobrescribe al arrancar, la verificación falla; resuelve el conflicto, no lo ocultes.

**Fase base inicial completada:** continúa con [3. Acceso y red](03-acceso-red.md) o con la aplicación en bloque de PAM, auditoría y firewall.

Referencia de los parámetros: [kernel](https://docs.kernel.org/admin-guide/sysctl/kernel.html) y [filesystem](https://docs.kernel.org/admin-guide/sysctl/fs.html).
