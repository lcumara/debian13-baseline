"""Pruebas aisladas del perfil agrupado. No aplican configuración al equipo."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "bin"))
import configurar_base as general


class ProfileTests(unittest.TestCase):
    def test_plan_has_no_side_effects(self):
        with patch.object(general.core, "environment") as env, patch.object(general, "configure") as apply:
            self.assertEqual(general.main([]), 0)
            env.assert_not_called()
            apply.assert_not_called()

    def test_no_false_snapshot_is_invented(self):
        with patch.object(general.core, "environment"), patch.object(general, "configure") as apply:
            self.assertEqual(general.main(["--aplicar"]), 1)
            apply.assert_not_called()

    def test_connection_validation_rejects_root_and_injection(self):
        for user, connection in [("root", "192.0.2.1 1000 192.0.2.2 22"),
                                 ("admin,host=other", "192.0.2.1 1000 192.0.2.2 22"),
                                 ("admin", "192.0.2.1 99999 192.0.2.2 22"),
                                 ("admin", "not-an-ip 1234 192.0.2.2 22")]:
            with self.assertRaises(ValueError):
                general.connection_context(user, connection)

    def test_connection_keeps_actual_server_port_and_ipv6(self):
        value = general.connection_context("admin", "2001:db8::1 1000 2001:db8::2 2222")
        self.assertIn("lport=2222", value)
        self.assertIn("addr=2001:db8::1", value)

    def test_audit_duplicate_setting_is_rejected(self):
        with self.assertRaises(ValueError):
            general.replace_options("num_logs = 5\nnum_logs = 8\n", {"num_logs": "10"})

    def test_audit_preserves_unrelated_configuration(self):
        value = general.replace_options("# note\nlog_file = /var/log/audit/audit.log\nnum_logs = 5\n", {"num_logs": "10"})
        self.assertIn("num_logs = 10", value)
        self.assertIn("log_file = /var/log/audit/audit.log", value)

    def test_ssh_checks_effective_values_and_authentication_methods(self):
        values = {**general.SSH_EXPECTED, "authenticationmethods": "any"}
        with patch.object(general, "ssh_values", return_value=values):
            general.check_ssh("context")
        for key, val in [("passwordauthentication", "no"), ("authenticationmethods", "publickey,password")]:
            with patch.object(general, "ssh_values", return_value={**values, key: val}):
                with self.assertRaises(ValueError):
                    general.check_ssh("context")

    def test_audit_paths_must_exist_before_generation(self):
        with patch.object(general.Path, "exists", return_value=False):
            with self.assertRaises(ValueError):
                general.rules_for([("/etc/missing", "path", "test")])

    def test_both_architectures_are_generated_without_immutable_setting(self):
        with patch.object(general.Path, "exists", return_value=True):
            value = general.rules_for([("/etc/passwd", "path", "identidad")])
        self.assertIn("arch=b64", value)
        self.assertIn("arch=b32", value)
        self.assertNotIn("-e 2", value)

    def test_ssh_timer_is_scheduled_before_any_ssh_write(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            folder = Path(directory) / "general-test"
            folder.mkdir()
            main = folder / "sshd_config"
            main.write_text("# original\n")
            events = []
            with patch.object(general, "SSH_MAIN", main), patch.object(general, "remember"), \
                 patch.object(general, "state_write"), patch.object(general.core, "atomic_write"), \
                 patch.object(general, "put", side_effect=lambda *a, **k: events.append("write")), \
                 patch.object(general, "command", side_effect=lambda cmd: events.append(cmd[0])), \
                 patch.object(general, "check_ssh"):
                general.configure_ssh(folder, {"archivos": {}}, "context")
            self.assertLess(events.index("systemd-run"), events.index("write"))
            self.assertLess(events.index("sshd"), events.index("systemctl"))

    def test_invalid_ssh_is_restored_before_returning_error(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            folder = Path(directory) / "general-test"
            folder.mkdir()
            main = folder / "sshd_config"
            main.write_text("# original\n")
            state = {"archivos": {}}
            with patch.object(general, "SSH_MAIN", main), patch.object(general, "remember"), \
                 patch.object(general, "state_write"), patch.object(general.core, "atomic_write"), \
                 patch.object(general, "put"), patch.object(general, "command"), \
                 patch.object(general, "check_ssh", side_effect=ValueError("invalid")), \
                 patch.object(general, "restore_group") as restore:
                with self.assertRaises(ValueError):
                    general.configure_ssh(folder, state, "context")
                restore.assert_called_once_with(folder, state, "ssh")
            self.assertEqual(state["ssh"], "REVERTIDO")

    def test_restore_does_not_touch_other_groups(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            folder = Path(directory)
            other = folder / "audit"
            other.write_text("keep")
            ssh = folder / "ssh"
            ssh.write_text("new")
            state = {"archivos": {str(other): {"grupo": "audit", "existia": False},
                                  str(ssh): {"grupo": "ssh", "existia": False}}}
            general.restore_group(folder, state, "ssh")
            self.assertEqual(other.read_text(), "keep")
            self.assertFalse(ssh.exists())


if __name__ == "__main__":
    unittest.main()
