# 4. Convertir la base en plantilla y crear clones

**Objetivo:** compartir configuración, conservando una identidad y secretos distintos por servidor.

**Dónde:** primero VM de preparación; luego Proxmox; finalmente cada clon aislado.

**Piloto actual:** se eligió personalización manual, sin Cloud-Init. Las secciones 4.2–4.5 describen otra ruta: no ejecutes su limpieza sobre el piloto manual. El sellado manual con regeneración de identidades todavía está pendiente de implementación y prueba. Los agentes podrán preinstalarse únicamente cuando se haya resuelto su compatibilidad y preparación sin identidad; su registro será por clon.

## 4.1 Qué pertenece a cada etapa

| Puede ir en la plantilla | Se genera o configura en cada clon |
|---|---|
| Paquetes comunes y políticas revisadas | Hostname, IP, DNS y función |
| Configuración SSH común | Llaves SSH del servidor |
| Configuración común de logs/auditoría | `machine-id`, MAC y UUID de la VM |
| Herramientas de diagnóstico | Registro e identidad de cada agente |
| Repositorios públicos aprobados | PSK, certificados, tokens y contraseñas |
| Cloud-init preparado y probado | Referencia AIDE final y credenciales de aplicaciones |

**Decisión de este proyecto:** instalar/enrolar agentes después de clonar. Un cambio de nombre no cambia automáticamente sus identidades internas.

## 4.2 Preparar cloud-init

Preferencia para futuras construcciones: imagen oficial Debian genericcloud verificada y versionada. Si el piloto se instaló desde ISO, prueba la adaptación a cloud-init antes de convertirlo en plantilla; una configuración de red del instalador puede interferir con la que genere cloud-init.

En la VM de preparación:

```bash
sudo apt-get install --no-remove cloud-init
cloud-init --version
sudo cloud-init status --long
```

En Proxmox, con la VM apagada, añade una unidad Cloud-Init desde Hardware. Configura un usuario administrativo no root, su **llave pública**, IP/DNS de laboratorio y QEMU Guest Agent. No pongas contraseñas o tokens en snippets ni comandos compartidos.

Arranca y verifica desde otra terminal que el usuario, sudo, red y llave funcionan. Si cloud-init queda `disabled`, falla o no controla la red, resuelve esa integración antes de limpiar identidades.

## 4.3 Revisar antes de sellar

```bash
sudo cloud-init status --long
sudo find /var/lib/cloud -maxdepth 2 -type f -name '*user-data*' -printf '%p\n'
sudo test ! -s /var/ossec/etc/client.keys
sudo test ! -e /etc/zabbix/zabbix_agent2.psk
sudo ss -lntup
```

Los `test` deben devolver 0; puedes comprobar inmediatamente con `echo $?`. No muestran secretos. Estos dos archivos no detectan todas las identidades posibles: revisa también FortiEDR, G DATA, certificados, credenciales APT/Git, cuentas de instalación, historial, `/tmp`, `/root` y homes. Si la VM ya estuvo enrolada, preferimos reconstruirla limpia; no borrar a ciegas archivos internos de productos.

Retira credenciales/cuentas de construcción que el clon no deba heredar. Asegura que cloud-init volverá a crear el acceso administrativo autorizado. Exporta evidencia a un lugar privado y retírala de la imagen. `cloud-init clean` no es un borrado seguro del disco ni una limpieza universal de secretos.

## 4.4 Sellar desde la consola, al final

Prerequisitos: integración cloud-init probada, creación de llaves de host habilitada en su módulo SSH y respaldo disponible. Estos comandos eliminan llaves **de host** de la VM de preparación; no los ejecutes sobre un servidor en servicio:

```bash
sudo cloud-init clean --logs --machine-id --seed
sudo rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub
sudo poweroff
```

No vuelvas a arrancar esta VM para “ver si quedó bien”: arrancar vuelve a generar estado. En Proxmox, conviértela en plantilla. Guarda fecha, commit del proyecto, lista de paquetes/kernel, perfil, resultados y excepciones de esa versión.

El contenido o enlace de `/var/lib/dbus/machine-id` también debe revisarse: no conservar una segunda copia estática de una identidad anterior. En caso de duda sobre la imagen, valida dos clones antes de aprobar el sellado.

## 4.5 Crear dos clones de prueba

En Proxmox crea dos clones con VMID, nombre, IP y MAC diferentes, en la red aislada. Configura Cloud-Init **antes de encenderlos**. No arranques clones con las IP de producción de otro equipo.

En cada clon:

```bash
hostnamectl
ip -br address
ip route
sudo cloud-init status --wait --long
sha256sum /etc/machine-id
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
sudo -v
systemctl --failed
```

**Esperado:** nombre/red correctos, cloud-init sin errores, hashes de machine-id distintos y huellas SSH distintas entre los clones. Verifica también UUID/MAC desde Proxmox. Si son iguales, no inscribas agentes: corrige la preparación y vuelve a generar la plantilla.

Un cambio legítimo de huella SSH se confirma desde la consola. No desactives `StrictHostKeyChecking` ni borres todas las huellas guardadas para silenciar la advertencia.

## 4.6 Personalizar y aceptar

Configura el perfil, instala agentes y aplicación con identidad definitiva, verifica alertas y crea la referencia AIDE. Reinicia y ejecuta [7. Aceptación](07-aceptacion-operativa.md). Solo después se conecta al tráfico productivo.

Si necesitas modificar la base, genera una **nueva versión de plantilla** y repite las pruebas. Los clones existentes no se actualizan automáticamente al cambiar la plantilla.

Fuentes: [Proxmox Cloud-Init](https://github.com/proxmox/pve-docs/blob/master/qm-cloud-init.adoc), [limpieza cloud-init](https://cloudinit.readthedocs.io/en/latest/reference/cli.html), [machine-id](https://manpages.debian.org/trixie/systemd/machine-id.5.en.html).
