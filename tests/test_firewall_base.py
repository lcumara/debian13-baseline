from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'bin'))
import firewall_base as fw


class FirewallTests(unittest.TestCase):
    def test_rejects_bad_ports_and_injected_origins(self):
        for port, origin in [(22, 'cualquiera'), (0, 'cualquiera'), (65536, 'cualquiera'),
                             (5432, ''), (5432, '0.0.0.0/0; flush ruleset'), (5432, '192.0.2.4/24')]:
            with self.assertRaises(ValueError):
                fw.port_entry(port, origin)

    def test_scoped_rules_precede_final_drop_and_preserve_ssh(self):
        state = {'permisos_tcp': [fw.port_entry(5432, '192.0.2.10'), fw.port_entry(443, '2001:db8::/64')]}
        rules = fw.render(state)
        self.assertIn('ip saddr 192.0.2.10/32 tcp dport 5432', rules)
        self.assertIn('ip6 saddr 2001:db8::/64 tcp dport 443', rules)
        self.assertLess(rules.index('tcp dport 5432'), rules.rindex('counter drop'))
        self.assertIn('tcp dport 22', rules)

    def test_public_permission_requires_explicit_origin(self):
        rules = fw.render({'permisos_tcp': [fw.port_entry(443, 'cualquiera')]})
        self.assertIn('        tcp dport 443 ct state new counter accept', rules)

    def test_plan_does_not_apply(self):
        with patch.object(fw, 'apply') as apply, patch.object(fw.core, 'environment') as env:
            self.assertEqual(fw.main([]), 0)
            apply.assert_not_called()
            env.assert_not_called()

    def test_transaction_only_replaces_own_table(self):
        self.assertNotIn('flush ruleset', fw.transaction(True))
        self.assertTrue(fw.transaction(True).startswith('delete table inet baseline_host\n'))
        self.assertNotIn('delete table', fw.transaction(False))
        self.assertNotIn('hook forward', fw.RULES)

    def test_syntax_checked_before_apply(self):
        with patch.object(fw, 'exists', return_value=True), patch.object(fw.core, 'atomic_write'), patch.object(fw.core, 'run') as run:
            fw.install_rules(Path('/private'))
            self.assertEqual(run.call_args_list[0].args[0], ['nft', '-c', '-f', str(Path('/private/load.nft'))])
            self.assertEqual(run.call_args_list[1].args[0], ['nft', '-f', str(Path('/private/load.nft'))])

    def test_rules_cover_both_ip_families_and_only_ssh_tcp(self):
        self.assertIn('table inet', fw.RULES)
        self.assertIn('policy drop', fw.RULES)
        self.assertIn('ipv6-icmp', fw.RULES)
        self.assertEqual(fw.RULES.count('tcp dport'), 1)
        self.assertIn('tcp dport 22', fw.RULES)

    def test_rollback_does_not_delete_other_tables(self):
        with patch.object(fw, 'exists', return_value=True), patch.object(fw.core, 'run') as run, patch.object(fw, 'save'):
            state = {'estado': 'PENDIENTE'}
            fw.restore(Path('/private'), state)
            self.assertEqual(run.call_args_list[0].args[0], ['nft', 'delete', 'table', 'inet', 'baseline_host'])
            self.assertEqual(state['estado'], 'REVERTIDO')
