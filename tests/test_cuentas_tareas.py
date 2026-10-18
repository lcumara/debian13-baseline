from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'bin'))
import cuentas_tareas as mod
import revisar_edades as ages
from types import SimpleNamespace


class AccountDefaultsTests(unittest.TestCase):
    def test_review_threshold_and_no_hash_exposure(self):
        users = [SimpleNamespace(pw_name='admin', pw_uid=1000, pw_shell='/bin/bash')]
        shadow = 'admin:$hash:100:1:3650:365:::\n'
        self.assertEqual(ages.aged_accounts(users, shadow, 1924), [])
        self.assertEqual(ages.aged_accounts(users, shadow, 1925), [('admin', 1825)])

    def test_review_excludes_locked_system_and_nologin(self):
        users = [SimpleNamespace(pw_name='admin', pw_uid=1000, pw_shell='/bin/bash'),
                 SimpleNamespace(pw_name='root', pw_uid=0, pw_shell='/bin/bash'),
                 SimpleNamespace(pw_name='service', pw_uid=1001, pw_shell='/usr/sbin/nologin')]
        shadow = 'admin:!$hash:100:1:3650:365:::\nroot:$hash:100:1:3650:365:::\nservice:$hash:100:1:3650:365:::\n'
        self.assertEqual(ages.aged_accounts(users, shadow, 3000), [])

    def test_duplicate_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.set_defaults('PASS_MAX_DAYS 99999\nPASS_MAX_DAYS 100\n')

    def test_comments_and_unrelated_settings_preserved(self):
        value = mod.set_defaults('# PASS_MIN_DAYS 0\nUID_MIN 1000\nPASS_MAX_DAYS 99999\n')
        self.assertIn('UID_MIN 1000\n', value)
        self.assertIn('# PASS_MIN_DAYS 0\n', value)
        self.assertIn('PASS_MAX_DAYS 3650\n', value)
        self.assertEqual(mod.set_defaults(value), value)

    def test_plan_no_environment_or_mutation(self):
        with patch.object(mod.core, 'environment') as env, patch.object(mod, 'apply') as apply:
            self.assertEqual(mod.main([]), 0)
            env.assert_not_called()
            apply.assert_not_called()

    def test_recovery_preserves_original_directory_modes(self):
        with patch.object(mod.base, 'restore_group') as files, patch.object(mod.Path, 'is_symlink', return_value=False), patch.object(mod.Path, 'chmod') as chmod, patch.object(mod.base, 'state_write'):
            state = {'modos': {'/etc/cron.daily': 0o755}}
            mod.restore(Path('/unused'), state)
            files.assert_called_once()
            chmod.assert_called_once_with(0o755)
            self.assertEqual(state['estado'], 'REVERTIDO')
