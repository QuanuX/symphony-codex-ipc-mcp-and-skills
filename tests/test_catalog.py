"""Review contracts for the complete beta catalog, independent of a live owner."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_tool_catalog as generator
import verify_beta_compatibility as verifier


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / 'catalog/tools.json').read_text())
        self.expected = json.loads((ROOT / 'catalog/beta-expected-registry.json').read_text())
        self.observed = dict(self.expected, registry_kind='observed', registry_digest=self.catalog['source_registry_digest'])

    def test_all_native_identities_accounted_with_exact_contracts(self):
        records, tools = verifier.catalog_check(self.expected, self.observed, self.catalog)
        self.assertEqual(records, 525)
        self.assertEqual(tools, 743)
        self.assertFalse(self.catalog['native_help_unavailable'])
        for e in self.catalog['entries']:
            r, tool, kind = e['binding']['record'], e['tool'], e['binding']['kind']
            base = generator.descriptors(r)
            generated = next(x['tool'] for x in base if x['binding']['kind'] == kind)
            self.assertEqual(tool['name'], generated['name'])
            self.assertEqual(tool['annotations'], generated['annotations'])
            # Descriptions are enriched by exact native help; types/routes cannot drift.
            actual = copy.deepcopy(tool['inputSchema']); expected = copy.deepcopy(generated['inputSchema'])
            for schema in (actual, expected):
                for prop in schema['properties'].values(): prop.pop('description', None)
            self.assertEqual(actual, expected)
            self.assertIn('Authority: ' + r['authority_mode'], tool['description'])
            for protocol in r['input_protocols']: self.assertIn(protocol, tool['description'])
            if r['recovery_command_id']: self.assertIn(r['recovery_command_id'], tool['description'])
            self.assertLessEqual(len(tool['name']), 64)

    def test_deterministic_generation_and_collision_refusal(self):
        first = generator.build(self.expected)
        self.assertEqual(first, generator.build(self.expected))
        duplicate = copy.deepcopy(self.expected); duplicate['commands'].append(duplicate['commands'][0])
        with self.assertRaises(ValueError): generator.build(duplicate)
        records = [copy.deepcopy(first['entries'][0]['binding']['record']) for _ in range(2)]
        records[1]['command_id'] += '.different'
        with self.assertRaises(ValueError): generator.build(dict(self.expected, commands=records))

    def test_read_classification_preserves_native_authority(self):
        selected = [e for e in self.catalog['entries'] if 'cloudflare' in e['binding']['command_id'] and e['binding']['kind'] == 'read' and e['binding']['record']['authority_mode'] == 'target_host_permission']
        self.assertTrue(selected)
        for e in selected:
            self.assertTrue(e['tool']['annotations']['readOnlyHint'])
            self.assertIn('Authority: target_host_permission', e['tool']['description'])

    def test_source_pair_metadata_and_delta(self):
        source = json.loads((ROOT / 'catalog/beta-source.json').read_text())
        delta = json.loads((ROOT / 'catalog/beta-delta.json').read_text())
        self.assertEqual(source['expected_registry_digest'], self.expected['registry_digest'])
        self.assertEqual(source['observed_registry_digest'], self.catalog['source_registry_digest'])
        self.assertEqual(source['catalog_sha256'], verifier.sha((ROOT / 'catalog/tools.json').read_bytes()))
        self.assertEqual(len(delta['added']), 64); self.assertEqual(len(delta['changed']), 5)
        self.assertEqual(delta['removed'], [])
        self.assertEqual(len(delta['excluded']), 2)
        self.assertEqual(len(delta['native_help_repaired']), 6)
        self.assertFalse(source['publication_authorized'])

    def test_distribution_refresh_preserves_unavailable_self_stamp(self):
        source = json.loads((ROOT / 'catalog/beta-source.json').read_text())
        evidence = source['distribution_source_binding']
        self.assertEqual(source['qxctl_build']['source_state'], 'unavailable')
        for field in ('source_commit', 'source_tree', 'source_date_epoch',
                      'dependency_map_sha256', 'build_recipe'):
            self.assertIsNone(source['qxctl_build'][field])
        self.assertEqual(evidence['self_stamp'], 'unavailable')
        self.assertEqual(evidence['legacy_w13_source_stamp_gate'], 'not_passed')
        self.assertFalse(evidence['release_acceptance_complete'])
        for field in ('cohort_result_sha256', 'round_result_sha256', 'delivery_record_sha256'):
            verifier.digest(evidence[field])

    def test_scoped_lifecycle_arguments_reach_only_the_existing_contracts(self):
        delta = json.loads((ROOT / 'catalog/distribution-delta.json').read_text())
        expected = {'qxcmd:symphony:knowledge.lifecycle.' + x
                    for x in ('apply', 'apply-recover', 'apply-status')}
        self.assertEqual(set(delta['changed']), expected)
        self.assertEqual(delta['added'], [])
        self.assertEqual(delta['removed'], [])
        for entry in self.catalog['entries']:
            binding, shape = entry['binding'], entry['tool']['inputSchema']
            if binding['command_id'] not in expected:
                continue
            if binding['kind'] == 'apply':
                self.assertEqual(set(shape['properties']), {'plan_id'})
                continue
            self.assertEqual(shape['properties']['execution-scope']['type'], 'string')
            if binding['command_id'].endswith('.apply'):
                self.assertEqual(shape['properties']['native-owner']['type'], 'array')

    def test_windows_checkout_preserves_catalog_bytes(self):
        # WSL receives the Windows checkout, so core.autocrlf must not alter
        # catalog bytes after their source-bound digests have been sealed.
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            subprocess.run(['git', 'init', '-q', work], check=True)
            subprocess.run(['git', '-C', work, 'config', 'core.autocrlf', 'true'], check=True)
            (root / '.gitattributes').write_bytes((ROOT / '.gitattributes').read_bytes())
            (root / 'catalog').mkdir()
            original = {p.name: p.read_bytes() for p in (ROOT / 'catalog').glob('*.json')}
            for name, content in original.items():
                (root / 'catalog' / name).write_bytes(content)
            subprocess.run(['git', '-C', work, 'add', '.gitattributes', 'catalog'], check=True,
                           capture_output=True)
            for name in original:
                (root / 'catalog' / name).unlink()
            subprocess.run(['git', '-C', work, 'checkout-index', '--all', '--force'], check=True)
            for name, content in original.items():
                with self.subTest(file=name):
                    self.assertEqual(verifier.sha((root / 'catalog' / name).read_bytes()),
                                     verifier.sha(content))


if __name__ == '__main__': unittest.main()
