from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'bin'))
import sellar_identidad as seal


class SealTests(unittest.TestCase):
    def test_plan_is_not_destructive(self):
        with patch.object(seal, 'seal') as apply, patch.object(seal, 'preflight') as check:
            self.assertEqual(seal.main([]), 0)
            apply.assert_not_called()
            check.assert_not_called()

    def test_preflight_failure_prevents_sealing_commands(self):
        with patch.object(seal, 'preflight', side_effect=ValueError('credential')), patch.object(seal.core, 'run') as run:
            self.assertEqual(seal.main(['--sellar-y-apagar']), 1)
            run.assert_not_called()

    def test_secret_check_reports_paths_not_contents(self):
        home = Path('/fixture-home')
        with patch.object(Path, 'exists', lambda p: p.name in ('.git-credentials', '.ssh')), \
             patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(Path, 'glob', return_value=[home / '.ssh/id_ed25519', home / '.ssh/id_ed25519.pub']), \
             patch.object(Path, 'read_text') as read:
            result = seal.secret_candidates([home])
            self.assertEqual(len(result), 2)
            read.assert_not_called()

    def test_keygen_conditions_reset_and_reinstate_path_checks(self):
        self.assertIn('ConditionFirstBoot=\n', seal.KEYGEN)
        self.assertNotIn('ConditionFirstBoot=yes', seal.KEYGEN)
        self.assertIn('ConditionPathIsReadWrite=/etc/ssh', seal.KEYGEN)
        self.assertIn('ConditionPathIsSymbolicLink=!/etc/ssh', seal.KEYGEN)
