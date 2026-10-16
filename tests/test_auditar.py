"""Pruebas aisladas de manejo de fallos; no llaman comandos del sistema."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("auditar", Path(__file__).parents[1] / "bin" / "auditar.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditorTests(unittest.TestCase):
    def test_missing_command_is_not_pass(self):
        with patch.object(audit.shutil, "which", return_value=None), patch.object(audit.subprocess, "run") as run:
            result = audit.collect_one("prueba", ("nft", "list", "ruleset"))
            self.assertEqual(result["estado"], "NO_DISPONIBLE")
            self.assertIsNone(result["codigo"])
            run.assert_not_called()

    def test_nonzero_result_requires_review(self):
        completed = subprocess.CompletedProcess([], 3, "inactive\n")
        with patch.object(audit.shutil, "which", return_value="/usr/bin/systemctl"), patch.object(audit.subprocess, "run", return_value=completed) as run:
            result = audit.collect_one("servicio", ("systemctl", "is-active", "auditd"))
            self.assertEqual(result["estado"], "REVISAR")
            self.assertEqual(result["codigo"], 3)
            self.assertFalse(run.call_args.kwargs["shell"])

    def test_timeout_keeps_partial_output(self):
        error = subprocess.TimeoutExpired(["aa-status"], 30, output=b"partial")
        with patch.object(audit.shutil, "which", return_value="/usr/sbin/aa-status"), patch.object(audit.subprocess, "run", side_effect=error):
            result = audit.collect_one("apparmor", ("aa-status",))
            self.assertEqual(result["estado"], "TIEMPO_EXCEDIDO")
            self.assertEqual(result["salida"], "partial")

    def test_ssh_output_excludes_unneeded_command_arguments(self):
        completed = subprocess.CompletedProcess([], 0, "permitrootlogin no\nauthorizedkeyscommand /bin/helper sensitive-argument\n")
        with patch.object(audit.shutil, "which", return_value="/usr/sbin/sshd"), patch.object(audit.subprocess, "run", return_value=completed):
            result = audit.collect_one("ssh_efectivo_sin_match", ("sshd", "-T"))
            self.assertEqual(result["salida"], "permitrootlogin no\n")

    def test_other_os_rejected(self):
        with patch.object(audit.platform, "system", return_value="Windows"):
            with self.assertRaises(ValueError):
                audit.validate_environment()

    def test_wrong_debian_release_rejected(self):
        with patch.object(audit.platform, "system", return_value="Linux"), patch.object(audit.platform, "freedesktop_os_release", return_value={"ID": "debian", "VERSION_ID": "12"}):
            with self.assertRaises(ValueError):
                audit.validate_environment()


if __name__ == "__main__":
    unittest.main()
