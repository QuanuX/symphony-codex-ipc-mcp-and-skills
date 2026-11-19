#!/usr/bin/env python3
"""Exercise package provenance, fail-closed selection and deterministic artifacts."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import package_beta_review as packager
import package_release


class BetaReviewPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        self.client = self.base / 'released'
        self.root.mkdir()
        self.client.mkdir()
        self.profile = 'ubuntu24.04-amd64'
        catalog = json.loads((REPO / 'catalog/tools.json').read_text())
        source = {'core': {'commit': 'native-reviewed'},
                  'client_dependency': {'commit': 'client-reviewed'},
                  'observed_registry_digest': catalog['source_registry_digest'],
                  'qxctl_build': {'executable_sha256': 'ab' * 32}}
        released = {'bin/symphony-mcp': b'released fixture binary',
                    'catalog/tools.json': packager.json_bytes(catalog),
                    'catalog/stamped-owner-delta.json': b'{}\n'}
        source['catalog_sha256'] = packager.digest(released['catalog/tools.json'])
        released['catalog/beta-source.json'] = packager.json_bytes(source)
        for name, data in released.items():
            self.write(self.client, name, data)
        pins = {'files': {name: packager.digest(data) for name, data in released.items()},
                'bindings': {'observed_registry_digest': source['observed_registry_digest'],
                             'qxctl_sha256': 'sha256:' + source['qxctl_build']['executable_sha256']}}
        self.inputs = {'package_version': '0.2.0-beta.2',
                       'bridge_runtime_version': '0.2.0-alpha.1',
                       'release': {'version': '0.2.0-beta.2'},
                       'native_source': source['core'],
                       'released_client_source': source['client_dependency'],
                       'native_files': {'src/fixture.cpp': packager.digest(b'int fixture;\n')},
                       'profiles': {self.profile: pins}}
        files = {'plugin.json': b'{"name":"symphony","version":"0.2.0-beta.2"}\n',
                 'mcp.json': b'{}\n', 'INTENT.md': b'Fixture review source.\n',
                 'src/fixture.cpp': b'int fixture;\n',
                 'skills/symphony-admin/SKILL.md': b'Fixture admin skill.\n',
                 'skills/symphony-setup/SKILL.md': b'Fixture setup skill.\n',
                 packager.INPUTS: packager.json_bytes(self.inputs)}
        for name, data in files.items():
            self.write(self.root, name, data)
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'Package test')
        self.run_git('config', 'user.email', 'package-test@example.invalid')
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'Fixture source')

    @staticmethod
    def write(root, name, data):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def run_git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def verify(self, profile=None):
        return packager.verify_inputs(self.root, self.client, profile or self.profile, self.inputs)

    def test_deterministic_archive_has_exact_inputs_permissions_and_provenance(self):
        identity = packager.source_identity(self.root)
        entries = packager.build_entries(self.root, self.client, self.profile, self.inputs, identity)
        first, second = self.base / 'one.zip', self.base / 'two.zip'
        result = package_release.write_archive(first, entries)
        package_release.write_archive(second, entries)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(result['sha256'], hashlib.sha256(first.read_bytes()).hexdigest())
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(archive.read('bin/symphony-mcp'), (self.client / 'bin/symphony-mcp').read_bytes())
            mode = archive.getinfo('bin/symphony-mcp').external_attr >> 16
            self.assertEqual(stat.S_IMODE(mode), 0o755)
            metadata = json.loads(archive.read('package-profile.json'))
            self.assertEqual(metadata['profile'], self.profile)
            self.assertEqual(metadata['package_version'], '0.2.0-beta.2')
            self.assertEqual(metadata['bridge_runtime_version'], '0.2.0-alpha.1')
            self.assertEqual(metadata['review_source'], identity)
            self.assertEqual(set(metadata['files']), set(archive.namelist()) - {'package-profile.json'})
            for name, expected in metadata['files'].items():
                self.assertEqual(packager.digest(archive.read(name)), expected)

    def test_rejects_wrong_profile_and_tampered_released_files(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported beta profile'):
            self.verify('macos-intel')
        other = copy.deepcopy(self.inputs['profiles'][self.profile])
        other['files']['bin/symphony-mcp'] = 'sha256:' + '00' * 32
        self.inputs['profiles']['ubuntu26.04-amd64'] = other
        with self.assertRaisesRegex(ValueError, 'hash/profile mismatch'):
            self.verify('ubuntu26.04-amd64')
        for name in packager.REPLACED:
            path = self.client / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'hash/profile mismatch'):
                self.verify()
            path.write_bytes(original)

    def test_rejects_native_source_drift_and_dirty_checkout(self):
        (self.root / 'src/fixture.cpp').write_text('int changed;\n')
        with self.assertRaisesRegex(ValueError, 'Native source differs'):
            self.verify()
        with self.assertRaisesRegex(ValueError, 'Commit the review source'):
            packager.source_identity(self.root)
        self.assertFalse(packager.source_identity(self.root, require_clean=False)['clean'])
        self.write(self.root, 'src/new.cpp', b'int unexpected;\n')
        with self.assertRaisesRegex(ValueError, 'Native source file set differs'):
            self.verify()

    def test_rejects_symlinks_private_state_and_extra_plugin_roots(self):
        path = self.client / 'bin/symphony-mcp'
        original = path.read_bytes()
        path.unlink()
        target = self.base / 'binary'
        target.write_bytes(original)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            self.verify()
        path.unlink()
        path.write_bytes(original)
        for name in ('docs/connection.json', 'docs/nested/plugin.json'):
            with self.subTest(name=name):
                self.write(self.root, name, b'{}\n')
                self.run_git('add', name)
                self.run_git('commit', '-qm', 'Forbidden fixture')
                with self.assertRaisesRegex(ValueError, 'Private state or additional plugin root'):
                    packager.build_entries(self.root, self.client, self.profile, self.inputs,
                                           packager.source_identity(self.root))
                self.run_git('rm', '-q', name)
                self.run_git('commit', '-qm', 'Remove forbidden fixture')


if __name__ == '__main__':
    unittest.main()
