"""Review contracts for the complete beta catalog, independent of a live owner."""
import copy
import json
from pathlib import Path
import sys
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


if __name__ == '__main__': unittest.main()
