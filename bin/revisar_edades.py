#!/usr/bin/python3
"""Aviso local diario de contraseñas humanas con antigüedad >= 1825 días."""
import time


def aged_accounts(users, shadow_text, today):
    eligible = {u.pw_name for u in users if 1000 <= u.pw_uid < 65534
                and u.pw_shell.rsplit('/', 1)[-1] not in ('nologin', 'false', '')}
    result = []
    for line in shadow_text.splitlines():
        fields = line.split(':')
        if len(fields) != 9 or fields[0] not in eligible:
            continue
        if not fields[1] or fields[1].startswith(('!', '*')) or not fields[2].isdigit():
            continue
        age = today - int(fields[2])
        if age >= 1825:
            result.append((fields[0], age))
    return result


def main():
    import pwd
    import syslog
    from pathlib import Path
    notices = aged_accounts(pwd.getpwall(), Path('/etc/shadow').read_text(), int(time.time() // 86400))
    syslog.openlog('baseline-password-review', syslog.LOG_PID, syslog.LOG_AUTHPRIV)
    for user, age in notices:
        message = f'Revision administrativa pendiente: usuario={user}, antiguedad_clave_dias={age}; sin bloqueo ni cambio automatico.'
        syslog.syslog(syslog.LOG_WARNING, message)
        print(message)
    if not notices:
        print('Sin contraseñas humanas elegibles con 1825 días de antigüedad.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
