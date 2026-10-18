"""Pruebas de controles y recuperación; no sustituyen PAM real en Debian."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'bin'))
import completar_base as mod


class ComplementTests(unittest.TestCase):
    def test_plan_does_not_modify(self):
        with patch.object(mod.core, 'environment') as env, patch.object(mod, 'apply') as apply:
            self.assertEqual(mod.main([]), 0)
            env.assert_not_called()
            apply.assert_not_called()

    def test_custom_provider_rejected(self):
        for name in mod.PAM:
            with self.assertRaises(ValueError):
                mod.local_stack(name, 'auth sufficient pam_sss.so\n')

    def test_custom_jump_rejected(self):
        text = 'auth [success=3 default=ignore] pam_unix.so\nauth requisite pam_deny.so\nauth required pam_permit.so\n'
        with self.assertRaises(ValueError):
            mod.local_stack('common-auth', text)

    def test_stock_stack_and_own_stack_accepted(self):
        text = 'auth [success=1 default=ignore] pam_unix.so nullok\nauth requisite pam_deny.so\nauth required pam_permit.so\nauth optional pam_cap.so\n'
        mod.local_stack('common-auth', text)
        for name, value in mod.PAM.items():
            mod.local_stack(name, value)
        mod.local_stack('common-auth', mod.PAM['common-auth'].replace('auth sufficient', 'auth optional pam_cap.so\nauth sufficient'))

    def test_password_order_and_no_empty_passwords(self):
        value = mod.PAM['common-password']
        self.assertLess(value.index('pam_pwquality'), value.index('pam_pwhistory'))
        self.assertLess(value.index('pam_pwhistory'), value.index('pam_unix'))
        self.assertNotIn('nullok', '\n'.join(mod.PAM.values()))
        self.assertIn('remember=24 enforce_for_root use_authtok', value)

    def test_auth_success_skips_only_failure_recorder(self):
        lines = mod.PAM['common-auth'].splitlines()
        i = next(i for i, line in enumerate(lines) if 'pam_unix' in line)
        self.assertIn('success=1', lines[i])
        self.assertIn('authfail', lines[i + 1])
        self.assertIn('authsucc', lines[i + 2])
        self.assertIn('default=die', lines[i + 1])

    def test_audit_does_not_freeze_and_filters_unset_users(self):
        with patch.object(mod.Path, 'exists', return_value=False):
            rules = mod.audit_rules()
        self.assertNotIn('-e 2', rules)
        self.assertIn('auid!=unset', rules)
        self.assertIn('arch=b32 -S stime', rules)
        self.assertNotIn('arch=b64 -S stime', rules)

    def test_docker_routing_preserved(self):
        self.assertFalse(any('forward' in key or 'rp_filter' in key for key in mod.SYSCTL))

    def test_recovery_restores_files_before_runtime(self):
        calls = []
        state = {'sysctl_antes': {'fs.suid_dumpable': '2'}}
        with patch.object(mod.base, 'restore_group', side_effect=lambda *a: calls.append('files')), patch.object(mod.core, 'run', side_effect=lambda args: calls.append(args)), patch.object(mod.base, 'state_write'):
            mod.recover(Path('/unused'), state)
        self.assertEqual(calls[0], 'files')
        self.assertEqual(calls[1], ['sysctl', '-w', 'fs.suid_dumpable=2'])
        self.assertEqual(state['estado'], 'REVERTIDO')


if __name__ == '__main__':
    unittest.main()
