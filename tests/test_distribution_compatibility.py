"""Synthetic D06/D07 proof regressions; these fixtures are not client acceptance."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_distribution_compatibility as v

spec = importlib.util.spec_from_file_location('legacy_fixtures', Path(__file__).with_name('test_beta_compatibility.py'))
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)


class DistributionCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.packet = fixtures.CompatibilityTests(methodName='runTest')
        self.packet.setUp(); self.addCleanup(self.packet.doCleanups)
        self.root = self.packet.root
        self.cohort = self.root / 'cohort'; self.round = self.cohort / 'round-1'
        self.payload = self.round / 'relocated-prefix'; self.payload.mkdir(parents=True)
        self.export = self.root / 'export'; (self.export / 'source').mkdir(parents=True)
        (self.cohort / 'source').mkdir()
        source = b'// synthetic reviewed source\n'
        for root in (self.export / 'source', self.cohort / 'source'):
            (root / 'source.go').write_bytes(source); (root / 'source.go').chmod(0o644)
        source_sha = v.base.sha(source)[7:]
        export_digest = v.base.sha(v.canonical([{'path': 'source.go', 'mode': '100644', 'sha256': source_sha}]))
        self.manifest = {'protocol': 'symphony.public-source-export.v2', 'is_original_git_tree': False,
            'origin_commit': '1' * 40, 'origin_tree': '2' * 40, 'derived_export_digest': export_digest[7:],
            'release_acceptance_complete': False, 'publication_authorized': False,
            'source_files': [{'path': 'source.go', 'mode': '100644', 'export_sha256': source_sha, 'export_size': len(source)}]}
        self.write(self.export / 'SOURCE-EXPORT.json', self.manifest)
        (self.export / 'symphony-source.tar').write_bytes(b'synthetic selected source archive')
        archive_sha = v.hash_file(self.export / 'symphony-source.tar')['sha256']
        self.native, self.commands, self.go_artifacts = [], [], []
        for index in range(51):
            cid = 'native-' + str(index)
            path = self.payload / 'share/symphony/receipts' / cid / '1.0/install-receipt.json'
            path.parent.mkdir(parents=True); self.write(path, {'synthetic_owner': cid}); path.chmod(0o644)
            self.native.append({'component_id': cid, 'version': '1.0', 'receipt_sha256': v.hash_file(path)['sha256']})
        for cid in ('qxctl', 'go1', 'go2', 'go3', 'go4', 'go5'):
            rel = 'go/' + cid + '/bin/' + cid; path = self.payload / rel; path.parent.mkdir(parents=True)
            path.write_bytes(self.packet.blobs['qxctl'] if cid == 'qxctl' else cid.encode()); path.chmod(0o755)
            sha = v.hash_file(path)['sha256']
            self.commands.append({'component_id': cid, 'version': '0.1.0-dev', 'sha256': sha})
            self.go_artifacts.append({'id': 'go:' + cid, 'version': '0.1.0-dev', 'path': rel, 'sha256': sha,
                'go_version': 'go1.26.5', 'main_module': {'Path': 'github.com/QuanuX/Symphony/tools/qxctl'},
                'settings': [{'Key': '-trimpath', 'Value': 'true'}, {'Key': 'CGO_ENABLED', 'Value': '0'}]})
        self.completed = {'state': 'built_and_sdk_checked', 'native_count': 51, 'go_commands': self.commands,
            'native_receipts': self.native, 'payload_inventory': v.inventory(self.payload, links=True),
            'sdk_audit': {'status': 'passed'}, 'installed_owner_audit': {'status': 'passed'}, 'loader_audit': {'status': 'passed'},
            'publication_authorized': False, 'fresh_whole_cohort_build': True}
        self.aggregate = {'protocol': 'symphony.distribution.clean-cohort.v1', 'state': 'built_and_sdk_checked',
            'source_commit': '1' * 40, 'source_tree': '2' * 40, 'acceptance_complete': False, 'publication_authorized': False,
            'source_input': {'kind': 'verified_reviewed_derived_export', 'verified': True, 'export_digest': export_digest[7:], 'archive_sha256': archive_sha},
            'host': {'os': 'macos', 'architecture': 'amd64'}, 'fresh_whole_cohort_build': True,
            'builder_sha256': '3' * 64, 'build_helpers': {'build.py': '3' * 64}, 'imported_helpers': {'original-helper.py': '4' * 64}}
        self.delivery = {'protocol': 'symphony.distribution.d06-delivery-record.v1', 'state': 'inventory_complete_publisher_review_pending',
            'source_binding': {'commit': '1' * 40, 'tree': '2' * 40}, 'publication_authorized': False,
            'release_ready': False, 'fresh_host_accepted': False, 'fresh_whole_cohort_build': True,
            'payload_files': self.completed['payload_inventory'], 'go_artifacts': self.go_artifacts,
            'source': {'mode': 'verified_derived_public_export', 'matching_build_install_source_prepared': True,
                       'origin_commit': '1' * 40, 'origin_tree': '2' * 40, 'derived_export_digest': export_digest[7:], 'export_archive_sha256': archive_sha}}
        self.delivery_path = self.root / 'delivery.json'
        self.wrapper = {'schema': 'symphony.distribution-client.requirements.v1', 'compatibility': self.packet.req,
            'owner_build_evidence': {'kind': 'd06-external-cohort', 'round': 'round-1',
                                    'derived_source_export_digest': export_digest, 'qxctl_payload_path': 'go/qxctl/bin/qxctl'}}
        self.version = {'protocol': 'symphony.qxctl.build-info.v1', 'component_id': 'qxctl', 'version': '0.1.0-dev',
            'source_state': 'unavailable', 'source_commit': None, 'source_tree': None, 'source_date_epoch': None,
            'dependency_map_sha256': None, 'build_recipe': None, 'go_version': 'go1.26.5', 'goos': 'darwin', 'goarch': 'amd64',
            'executable_sha256': self.packet.bindings['qxctl_sha256'][7:]}
        self.packet.put('qxctl_version', self.version)
        self.rebind()

    @staticmethod
    def write(path, data): path.write_text(json.dumps(data, indent=2) + '\n')

    def rebind(self):
        self.write(self.round / 'result.json', self.completed)
        round_sha = v.hash_file(self.round / 'result.json')['sha256']
        self.aggregate['rounds'] = [{'directory': 'round-1', 'result_sha256': round_sha, 'native_count': 51, 'go_count': 6}]
        self.write(self.cohort / 'result.json', self.aggregate)
        aggregate_sha = v.hash_file(self.cohort / 'result.json')['sha256']
        self.delivery.update(build_result_sha256=aggregate_sha, round_result_sha256=round_sha)
        self.write(self.delivery_path, self.delivery)
        self.wrapper['owner_build_evidence'].update(cohort_result_sha256='sha256:' + aggregate_sha,
            round_result_sha256='sha256:' + round_sha, delivery_record_sha256=v.base.sha(self.delivery_path.read_bytes()))
        self.repack()

    def repack(self, change=None):
        selected = self.wrapper['owner_build_evidence']
        source = {'schema': 'symphony.beta-catalog-source.v1', 'core': self.packet.sources['core'], 'qxctl_build': self.version,
            **{key: self.packet.bindings[key] for key in ('expected_registry_digest', 'observed_registry_digest', 'catalog_sha256')},
            'distribution_source_binding': {'kind': 'verified_d06_derived_source_and_exact_payload',
                **{key: selected[key] for key in ('cohort_result_sha256', 'round_result_sha256', 'delivery_record_sha256', 'qxctl_payload_path')},
                'derived_source_export_digest': selected['derived_source_export_digest'][7:], 'self_stamp': 'unavailable',
                'legacy_w13_source_stamp_gate': 'not_passed', 'release_acceptance_complete': False}, 'publication_authorized': False}
        if change: change(source)
        with zipfile.ZipFile(io.BytesIO(self.packet.blobs['package'])) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files.update({'catalog/beta-source.json': json.dumps(source).encode(),
                      'scripts/verify_distribution_compatibility.py': b'# synthetic distribution verifier',
                      'schemas/distribution-client-v1.schema.json': b'{}'})
        source_files = {name: v.base.sha(raw) for name, raw in files.items() if name != 'bin/symphony-mcp'}
        self.packet.put('source_inventory', {'source': self.packet.sources['plugin'], 'files': source_files})
        self.packet.put('package_inventory', {name: v.base.sha(raw) for name, raw in files.items()})
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name); info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, data)
        self.packet.blobs['package'] = raw.getvalue()
        self.packet.bindings['package_sha256'] = v.base.sha(raw.getvalue())
        self.packet.obs['bindings'] = copy.deepcopy(self.packet.bindings)
        for name in ('stdio', 'same_user_ipc'):
            report = json.loads(self.packet.blobs[name]); report['bindings'] = self.packet.bindings
            self.packet.put(name, report)
        self.packet.sync()

    def check(self):
        return v.verify(self.wrapper, self.packet.obs, self.root, self.cohort, self.delivery_path, self.export)

    def test_exact_external_proof_never_invents_a_stamp_or_approval(self):
        report = self.check()
        self.assertEqual(report['status'], 'engineering_review_ready')
        self.assertEqual(report['legacy_w13_source_stamp_gate'], 'unavailable_not_passed')
        self.assertEqual(report['owner_build_evidence']['verified_payload_entries'], 57)
        self.assertFalse(report['publication_authorized']); self.assertFalse(report['release_acceptance_complete'])
        self.assertEqual(report['publisher_authentication'], 'not_established')
        with self.assertRaisesRegex(ValueError, 'Unstamped owner'):
            self.packet.check()

    def test_each_independently_selected_evidence_digest_is_required(self):
        for path in (self.cohort / 'result.json', self.round / 'result.json', self.delivery_path):
            original = path.read_bytes(); path.write_bytes(original + b' ')
            with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, 'digest mismatch'):
                self.check()
            path.write_bytes(original)

    def test_payload_bytes_mode_missing_and_extra_files_are_rejected(self):
        path = self.payload / 'go/qxctl/bin/qxctl'; original = path.read_bytes()
        path.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'payload inventory'): self.check()
        path.write_bytes(original); path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'payload inventory'): self.check()
        path.chmod(0o755); path.unlink()
        with self.assertRaisesRegex(ValueError, 'payload inventory'): self.check()
        path.write_bytes(original); path.chmod(0o755)
        (self.payload / 'unlisted').write_bytes(b'unlisted')
        with self.assertRaisesRegex(ValueError, 'payload inventory'): self.check()

    def test_built_source_mode_and_additional_file_cannot_hide_behind_export(self):
        path = self.cohort / 'source/source.go'; path.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'Built source bytes or modes'): self.check()
        path.chmod(0o644); (self.cohort / 'source/extra.go').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'Built source bytes or modes'): self.check()

    def test_source_path_ordering_does_not_change_exact_membership(self):
        for name in ('dir/inside.go', 'dir-file.go'):
            raw = ('// fixture ' + name).encode()
            for root in (self.cohort / 'source', self.export / 'source'):
                path = root / name; path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw); path.chmod(0o644)
            self.manifest['source_files'].append({'path': name, 'mode': '100644',
                'export_sha256': v.base.sha(raw)[7:], 'export_size': len(raw)})
        rows = sorted(self.manifest['source_files'], key=lambda row: row['path'])
        digest = v.base.sha(v.canonical([{'path': row['path'], 'mode': row['mode'], 'sha256': row['export_sha256']} for row in rows]))
        self.manifest.update(source_files=rows, derived_export_digest=digest[7:])
        self.write(self.export / 'SOURCE-EXPORT.json', self.manifest)
        self.aggregate['source_input']['export_digest'] = self.delivery['source']['derived_export_digest'] = digest[7:]
        self.wrapper['owner_build_evidence']['derived_source_export_digest'] = digest
        self.rebind()
        self.assertEqual(self.check()['status'], 'engineering_review_ready')

    def test_source_and_payload_symlink_escape_refused(self):
        path = self.cohort / 'source/source.go'; path.unlink(); path.symlink_to(self.root / 'bridge')
        with self.assertRaisesRegex(ValueError, 'unselected source link'): self.check()
        path.unlink(); path.write_bytes((self.export / 'source/source.go').read_bytes())
        (self.payload / 'escape').symlink_to(self.root / 'bridge')
        with self.assertRaisesRegex(ValueError, 'Escaping'): self.check()

    def test_rehashed_wrong_source_and_approval_claims_are_rejected(self):
        self.aggregate['source_commit'] = '3' * 40; self.rebind()
        with self.assertRaisesRegex(ValueError, 'core source differs'): self.check()
        self.aggregate['source_commit'] = '1' * 40; self.aggregate['acceptance_complete'] = True; self.rebind()
        with self.assertRaisesRegex(ValueError, 'unselected approval'): self.check()

    def test_fabricated_stamp_and_packaged_legacy_gate_upgrade_are_rejected(self):
        changed = dict(self.version, source_state='stamped', source_commit='1' * 40)
        self.packet.put('qxctl_version', changed); self.packet.sync()
        with self.assertRaisesRegex(ValueError, 'actual unstamped'): self.check()
        self.packet.put('qxctl_version', self.version); self.packet.sync()
        self.repack(lambda source: source['distribution_source_binding'].update(legacy_w13_source_stamp_gate='passed'))
        with self.assertRaisesRegex(ValueError, 'misrepresents owner'): self.check()
        self.repack(lambda source: source['qxctl_build'].update(source_state='stamped'))
        with self.assertRaises(ValueError): self.check()

    def test_missing_owner_and_client_attachments_are_incomplete(self):
        original = (self.cohort / 'result.json').read_bytes(); (self.cohort / 'result.json').unlink()
        report = self.check()
        self.assertEqual(report['status'], 'incomplete'); self.assertIn('missing owner evidence: aggregate', report['pending'])
        (self.cohort / 'result.json').write_bytes(original)
        for name in ('stdio-config', 'readonly', 'assertions'):
            path = self.root / name; raw = path.read_bytes(); path.unlink()
            report = self.check(); self.assertEqual(report['status'], 'incomplete')
            self.assertIn('missing artifact: ' + name, report['pending']); path.write_bytes(raw)

    def test_missing_owner_does_not_hide_invalid_present_client_report(self):
        (self.cohort / 'result.json').unlink()
        report = json.loads(self.packet.blobs['stdio']); report['transcripts'][0] = 'undeclared'
        self.packet.put('stdio', report); self.packet.sync()
        with self.assertRaisesRegex(ValueError, 'Unbound session transcripts'): self.check()

    def test_repair_inheritance_is_preserved_and_wrong_origin_refused(self):
        provenance = [{'component_id': row['component_id'], 'kind': 'rebuilt_from_exact_origin_source' if index < 8 else
                       'inherited_native_receipt_and_bytes'} for index, row in enumerate(self.native)]
        repair = {'origin_tool_commit': '5' * 40, 'origin_payload_inventory_sha256': '6' * 64,
                  'source_inventory_sha256': self.manifest['derived_export_digest'], 'inherited_native_count': 43,
                  'inherited_go_count': 6, 'rebuild_ids': [row['component_id'] for row in provenance[:8]]}
        self.aggregate.update(repair_provenance=repair, fresh_whole_cohort_build=False, original_evidence_unchanged=True,
                              repeated_payload_bytes_equal=False)
        for doc in (self.completed, self.delivery):
            doc.update(fresh_whole_cohort_build=False, native_unit_provenance=provenance, repaired_native_count=8,
                       inherited_native_count=43, inherited_go_count=6)
        self.delivery.update(repair_provenance=repair, repeated_payload_bytes_equal=False)
        go = next(row for row in self.go_artifacts if row['id'] == 'go:qxctl')
        go['build_provenance'] = {'kind': 'inherited_exact_origin_bytes', 'origin_tool_commit': repair['origin_tool_commit'],
                                  'origin_payload_inventory_sha256': repair['origin_payload_inventory_sha256']}
        self.rebind(); report = self.check()
        self.assertEqual(report['owner_build_evidence']['repair_provenance'], repair)
        self.assertFalse(report['owner_build_evidence']['fresh_whole_cohort_build'])
        go['build_provenance']['origin_tool_commit'] = '7' * 40; self.rebind()
        with self.assertRaisesRegex(ValueError, 'Inherited qxctl provenance'): self.check()

    def test_cli_exit_codes_and_existing_report_preservation(self):
        req, obs, out = [self.root / name for name in ('requirements.json', 'observations.json', 'report.json')]
        self.write(req, self.wrapper); self.write(obs, self.packet.obs)
        command = [sys.executable, str(ROOT / 'scripts/verify_distribution_compatibility.py'), '--requirements', str(req),
                   '--observations', str(obs), '--evidence-root', str(self.root), '--cohort-root', str(self.cohort),
                   '--delivery-record', str(self.delivery_path), '--export', str(self.export), '--output', str(out)]
        def run(): return subprocess.run(command, capture_output=True)
        first = run(); self.assertEqual(first.returncode, 0, first.stderr)
        raw = out.read_bytes(); self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
        self.assertEqual(run().returncode, 1); self.assertEqual(out.read_bytes(), raw)
        out.unlink(); (self.root / 'stdio-config').unlink(); self.assertEqual(run().returncode, 2)


if __name__ == '__main__': unittest.main()
