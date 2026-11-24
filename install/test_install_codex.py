import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('install_codex', Path(__file__).with_name('install-codex.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CodexInstallTests(unittest.TestCase):
    def test_preserve_existing_selection_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            expected = base / 'profile'
            expected.write_text('{"qxctl":"first"}')
            selected = installer.private_profile(base / 'data', expected)
            self.assertEqual(stat.S_IMODE(selected.stat().st_mode), 0o600)
            inode = selected.stat().st_ino
            installer.private_profile(base / 'data', expected)
            self.assertEqual(selected.stat().st_ino, inode)
            expected.write_text('{"qxctl":"second"}')
            with self.assertRaisesRegex(ValueError, 'existing connection differs'):
                installer.private_profile(base / 'data', expected)
            self.assertEqual(json.loads(selected.read_text()), {'qxctl': 'first'})

    def test_archive_pinning_precedes_extraction_and_existing_market_is_verified(self):
        profile = 'ubuntu26.04-amd64'
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = base / 'test.zip'
            with zipfile.ZipFile(archive, 'w') as zipout:
                info = zipfile.ZipInfo('package-profile.json')
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                zipout.writestr(info, json.dumps({'profile': profile, 'package_version': installer.VERSION,
                                                 'bridge_runtime_version': installer.VERSION}))
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                installer.prepare_marketplace(archive, profile, base / 'a')
            self.assertFalse((base / 'a').exists())
            with patch.dict(installer.ZIP_HASHES, {profile: installer.digest(archive)}):
                for name in ('a', 'b'):
                    installer.prepare_marketplace(archive, profile, base / name)
            installer.verify_existing_market(base / 'a', base / 'b')
            (base / 'b/plugin/package-profile.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'member differs'):
                installer.verify_existing_market(base / 'a', base / 'b')


if __name__ == '__main__':
    unittest.main()
