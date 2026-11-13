"""Synthetic packet regressions; no fixture is real-client qualification."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_beta_compatibility as v
import build_tool_catalog as generator


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = {k: {'repository': repo, 'commit': '1' * 40, 'tree': '2' * 40} for k, repo in [('core', 'QuanuX/Symphony'), ('plugin', 'QuanuX/symphony-codex-ipc-mcp-and-skills')]}
        self.blobs = {'qxctl': b'synthetic owner', 'bridge': b'synthetic bridge'}
        record = dict(command_id='qxcmd:symphony:status', grammar='qxctl status [--json]', mutability='read_only', visibility='public', noninteractive=True, status='experimental', authority_mode='target_host_permission')
        records = [record, dict(record, command_id='qxcmd:symphony:sov.target.invoke'), dict(record, command_id='qxcmd:symphony:stav.append', mutability='prohibited')]
        expected = dict(registry_kind='expected', registry_digest=v.sha(b'expected'), commands=records)
        observed = dict(registry_kind='observed', registry_digest=v.sha(b'observed'), commands=records, executable_digest=v.sha(self.blobs['qxctl']))
        catalog = generator.build(observed)
        self.put('expected_registry', expected); self.put('observed_registry', observed); self.put('catalog', catalog)
        self.put('qxctl_version', dict(protocol='symphony.qxctl.build-info.v1', source_state='stamped', build_recipe='symphony.qxctl.reproducible-build.v1', source_commit='1' * 40, source_tree='2' * 40, executable_sha256=v.sha(self.blobs['qxctl'])[7:]))
        files = {'src/main.cpp': b'synthetic source', 'schemas/beta-compatibility-v1.schema.json': b'{}', 'scripts/verify_beta_compatibility.py': b'# synthetic verifier', 'catalog/tools.json': self.blobs['catalog']}
        self.put('source_inventory', dict(source=self.sources['plugin'], files={k: v.sha(b) for k, b in files.items()}))
        files['bin/symphony-mcp'] = self.blobs['bridge']
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            for name, data in files.items():
                info = zipfile.ZipInfo(name); info.external_attr = (stat.S_IFREG | 0o644) << 16
                z.writestr(info, data)
        self.blobs['package'] = archive.getvalue()
        self.put('package_inventory', {k: v.sha(b) for k, b in files.items()})
        self.bindings = {k + '_sha256': v.sha(self.blobs[k]) for k in ('qxctl', 'bridge', 'catalog', 'package')}
        self.bindings.update(expected_registry_digest=expected['registry_digest'], observed_registry_digest=observed['registry_digest'])
        self.clients = [dict(id=mode, name='Codex', version='fixture-only', os='synthetic', architecture='fixture', mode=mode, config_sha256=v.sha(mode.encode())) for mode in ('stdio', 'same_user_ipc')]
        self.put('assertions', [dict(id=c, status='passed') for c in v.CASES])
        for phase in ('readonly', 'enabled', 'restarted'): self.blobs[phase] = b'synthetic transcript, not real client evidence'
        for target in self.clients:
            self.put(target['id'], dict(schema='symphony.beta-client-evidence.v1', sources=self.sources, bindings=self.bindings, client=target, cases=[dict(id=c, status='passed', evidence=['assertions']) for c in v.CASES], scope='deterministic_app_server_native_owner', transcripts=['readonly', 'enabled', 'restarted']))
        self.req = dict(schema='symphony.beta-compatibility.requirements.v1', sources=self.sources, bindings=self.bindings, artifacts={}, clients=self.clients)
        self.sync()
        self.obs = dict(schema='symphony.beta-compatibility.observations.v1', sources=copy.deepcopy(self.sources), bindings=copy.deepcopy(self.bindings), clients={c['id']: c['id'] for c in self.clients}, distribution='pending', release_acceptance_complete=False, publication_authorized=False)

    def put(self, key, value): self.blobs[key] = json.dumps(value).encode()

    def sync(self):
        for k, data in self.blobs.items():
            (self.root / k).write_bytes(data)
            self.req['artifacts'][k] = dict(path=k, sha256=v.sha(data))

    def check(self): return v.verify(self.req, self.obs, self.root)

    def test_coherent_packet_never_grants_release(self):
        result = self.check()
        self.assertEqual(result['status'], 'engineering_review_ready')
        self.assertFalse(result['release_acceptance_complete']); self.assertFalse(result['publication_authorized'])

    def test_independent_source_and_artifact_tampering(self):
        for role in ('core', 'plugin'):
            for field in ('repository', 'commit', 'tree'):
                with self.subTest(role=role, field=field):
                    obs = copy.deepcopy(self.obs); obs['sources'][role][field] = 'wrong'
                    with self.assertRaises(ValueError): v.verify(self.req, obs, self.root)
        for key in self.blobs:
            with self.subTest(artifact=key):
                p = self.root / key; original = p.read_bytes(); p.write_bytes(original + b'changed')
                with self.assertRaises(ValueError): self.check()
                p.write_bytes(original)
        for key in self.bindings:
            obs = copy.deepcopy(self.obs); obs['bindings'][key] = v.sha(b'wrong')
            with self.assertRaises(ValueError): v.verify(self.req, obs, self.root)

    def test_absent_and_failed_evidence_is_incomplete(self):
        self.obs['clients'].pop('stdio')
        self.assertEqual(self.check()['status'], 'incomplete')
        self.obs['clients']['stdio'] = 'stdio'
        r = json.loads(self.blobs['stdio']); r['cases'][0]['status'] = 'failed'
        self.put('stdio', r); self.sync()
        self.assertEqual(self.check()['status'], 'incomplete')
        r['cases'] = []; self.put('stdio', r); self.sync()
        self.assertEqual(self.check()['status'], 'incomplete')
        (self.root / 'package').unlink()
        self.assertEqual(self.check()['status'], 'incomplete')

    def test_wrong_client_and_duplicate_or_unbound_claims(self):
        original = self.blobs['stdio']
        for field in self.clients[0]:
            r = json.loads(original); r['client'][field] = 'wrong'
            self.put('stdio', r); self.sync()
            with self.subTest(field=field), self.assertRaises(ValueError): self.check()
        for mode in ('duplicate', 'unbound', 'missing', 'fixture'):
            r = json.loads(original)
            if mode == 'duplicate': r['cases'].append(r['cases'][0])
            elif mode == 'unbound': r['cases'][0]['evidence'] = ['unknown']
            elif mode == 'missing': r['cases'][0]['evidence'] = []
            else: r['scope'] = 'fixture'
            self.put('stdio', r); self.sync()
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.check()

    def test_rehashed_semantic_tampering_is_rejected(self):
        for key, field, value in [('qxctl_version', 'source_commit', '3' * 40), ('observed_registry', 'executable_digest', v.sha(b'other')), ('source_inventory', 'source', {}), ('package_inventory', 'src/main.cpp', v.sha(b'other'))]:
            original = self.blobs[key]; data = json.loads(original); data[field] = value
            self.put(key, data); self.sync()
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()
            self.blobs[key] = original; self.sync()

    def test_contradictory_assertion_rejected_even_when_rehashed(self):
        ledger = json.loads(self.blobs['assertions']); ledger[0]['status'] = 'failed'
        self.put('assertions', ledger); self.sync()
        with self.assertRaises(ValueError): self.check()

    def test_no_self_authorized_scope_or_acceptance(self):
        for flag in ('release_acceptance_complete', 'publication_authorized'):
            obs = copy.deepcopy(self.obs); obs[flag] = True
            with self.assertRaises(ValueError): v.verify(self.req, obs, self.root)
        self.req['clients'] = self.req['clients'][:1]
        with self.assertRaises(ValueError): self.check()

    def test_strict_bounded_inputs_and_paths(self):
        for value in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[' * 40 + b'0' + b']' * 40, b' ' * (v.JSON_LIMIT + 1)):
            with self.assertRaises(ValueError): v.strict_json(value)
        for name in ('../escape', '/tmp/escape', 'a/../b', './foo', 'a\\b'):
            with self.assertRaises(ValueError): v.attachment(self.root, name)
        (self.root / 'link').symlink_to(self.root / 'bridge')
        with self.assertRaises(ValueError): v.attachment(self.root, 'link')
        os.mkfifo(self.root / 'fifo')
        with self.assertRaises(ValueError): v.regular(self.root / 'fifo')

    def test_cli_exit_codes_and_immutable_private_report(self):
        req, obs, out = [self.root / x for x in ('requirements.json', 'observations.json', 'report.json')]
        req.write_text(json.dumps(self.req)); obs.write_text(json.dumps(self.obs))
        cmd = [sys.executable, str(ROOT / 'scripts/verify_beta_compatibility.py'), '--requirements', str(req), '--observations', str(obs), '--evidence-root', str(self.root), '--output', str(out)]
        def run(): return subprocess.run(cmd, capture_output=True).returncode
        self.assertEqual(run(), 0); original = out.read_bytes(); self.assertEqual(out.stat().st_mode & 0o777, 0o600)
        self.assertEqual(run(), 1); self.assertEqual(out.read_bytes(), original)
        out.unlink(); self.obs['clients'] = {}; obs.write_text(json.dumps(self.obs)); self.assertEqual(run(), 2)


if __name__ == '__main__': unittest.main()
