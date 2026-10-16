"""Pruebas de barreras y recuperación. Nunca invocan APT ni sysctl reales."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("baseline", Path(__file__).parents[1] / "bin" / "baseline.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class GuardTests(unittest.TestCase):
    def test_plan_never_executes_or_writes(self):
        with patch.object(base, "run") as run, patch.object(base, "atomic_write") as write:
            for stage in ("paquetes", "kernel", "revertir"):
                self.assertEqual(base.main([stage]), 0)
            run.assert_not_called()
            write.assert_not_called()

    def test_apply_requires_explicit_lab_and_snapshot(self):
        with patch.object(base, "environment") as environment, patch.object(base, "apply") as apply:
            self.assertEqual(base.main(["kernel", "--aplicar"]), 1)
            self.assertEqual(base.main(["kernel", "--aplicar", "--laboratorio"]), 1)
            self.assertEqual(base.main(["kernel", "--aplicar", "--laboratorio", "--snapshot", "x;reboot"]), 1)
            environment.assert_not_called()
            apply.assert_not_called()

    def test_rejects_windows_without_subprocess(self):
        with patch.object(base.platform, "system", return_value="Windows"), patch.object(base, "run") as run:
            with self.assertRaises(ValueError):
                base.environment()
            run.assert_not_called()

    def test_rejects_other_debian(self):
        with patch.object(base.platform, "system", return_value="Linux"), patch.object(base.platform, "freedesktop_os_release", return_value={"ID": "debian", "VERSION_ID": "12"}), patch.object(base, "run") as run:
            with self.assertRaises(ValueError):
                base.environment()
            run.assert_not_called()

    def test_unexpected_effective_value_fails(self):
        with patch.object(base, "run", return_value="0\n"):
            with self.assertRaises(ValueError):
                base.check_kernel()


class RecoveryTests(unittest.TestCase):
    def test_partial_sysctl_failure_restores_every_previous_value(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            policy = root / "policy.conf"
            calls = []

            def fake_run(argv, capture=True):
                calls.append(argv)
                if argv[1] == "-n":
                    return "0\n"
                if argv[1] == "-p":
                    raise subprocess.CalledProcessError(1, argv)
                return ""

            def write(path, data, mode=0o600):
                path.write_bytes(data)

            state = {"etapa": "kernel", "estado": "INICIADO"}
            with patch.object(base, "POLICY", policy), patch.object(base, "run", side_effect=fake_run), patch.object(base, "atomic_write", side_effect=write):
                with self.assertRaises(subprocess.CalledProcessError):
                    base.apply_kernel(root, state)
            self.assertFalse(policy.exists())
            self.assertEqual(state["estado"], "REVERTIDO")
            for key in base.SETTINGS:
                self.assertIn(["sysctl", "-w", f"{key}=0"], calls)

    def test_failed_recovery_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            state = {"existia": False, "valores_anteriores": {key: "0" for key in base.SETTINGS}}
            with patch.object(base, "POLICY", root / "policy"), patch.object(base, "save"), patch.object(base, "run", side_effect=OSError("fallo")) as run:
                with self.assertRaises(ValueError):
                    base.restore_kernel(root, state)
            self.assertEqual(run.call_count, len(base.SETTINGS))
            self.assertEqual(state["estado"], "REVERSION_INCOMPLETA")

    def test_restore_previous_file_and_values(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            (root / "anterior.conf").write_bytes(b"# anterior\n")
            state = {"existia": True, "modo": 0o644, "valores_anteriores": {key: "0" for key in base.SETTINGS}}
            with patch.object(base, "POLICY", root / "policy"), patch.object(base, "save"), patch.object(base, "run"), patch.object(base, "atomic_write") as write:
                base.restore_kernel(root, state)
                write.assert_called_once_with(root / "policy", b"# anterior\n", 0o644)
            self.assertEqual(state["estado"], "REVERTIDO")


if __name__ == "__main__":
    unittest.main()
