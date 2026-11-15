"""Focused distribution tests; fake executables test routing, not C++ qualification."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_mcpb", ROOT / "scripts/package_mcpb.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def executable_header(target):
    data = bytearray(64)
    if target.startswith("darwin"):
        data[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", data, 4, 0x01000007 if target.endswith("x86_64") else 0x0100000C)
        struct.pack_into("<I", data, 12, 2)
    else:
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 16, 3)
        struct.pack_into("<H", data, 18, 62 if target.endswith("x86_64") else 183)
    return bytes(data)


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="symphony bundle ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(ROOT / "packaging/mcpb/launcher.sh", self.root / "launcher.sh")
        fakebin = self.root / "fake tools"
        fakebin.mkdir()
        uname = fakebin / "uname"
        uname.write_text('#!/bin/sh\ncase "$1" in -s) printf "%s\\n" "$TEST_SYSTEM";; -m) printf "%s\\n" "$TEST_MACHINE";; *) exit 1;; esac\n')
        uname.chmod(0o755)
        self.env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"))
        for target in pack.TARGETS:
            binary = self.root / "bin" / target / "symphony-mcp"
            binary.parent.mkdir(parents=True)
            binary.write_text(f'#!{sys.executable}\nimport json,sys\nprint(json.dumps({{"target":{target!r},"argv":sys.argv[1:]}}))\n')
            binary.chmod(0o755)

    def run_target(self, system, machine, arguments=()):
        return subprocess.run(["/bin/sh", str(self.root / "launcher.sh"), *arguments], env=dict(self.env, TEST_SYSTEM=system, TEST_MACHINE=machine), capture_output=True, text=True)

    def test_all_routes_and_arm_alias(self):
        cases = [("Darwin", "x86_64", "darwin-x86_64"), ("Darwin", "arm64", "darwin-arm64"), ("Linux", "x86_64", "linux-x86_64"), ("Linux", "aarch64", "linux-aarch64"), ("Linux", "arm64", "linux-aarch64")]
        for system, machine, target in cases:
            with self.subTest(system=system, machine=machine):
                result = self.run_target(system, machine, ["--config", "/private/profile.json"])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"target": target, "argv": ["--config", "/private/profile.json"]})

    def test_manifest_config_resolution_preserves_argv(self):
        manifest = json.loads((ROOT / "packaging/mcpb/manifest.json").read_text())
        config = manifest["server"]["mcp_config"]
        profile = str(self.root / 'a $dollar; "quoted" $(touch injected).json')
        args = [value.replace("${__dirname}", str(self.root)).replace("${user_config.connection_profile}", profile) for value in config["args"]]
        result = subprocess.run([config["command"], *args], env=dict(self.env, TEST_SYSTEM="Linux", TEST_MACHINE="x86_64"), capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["argv"], ["--config", profile, "--tool-catalog", str(self.root / "catalog/tools.json")])
        self.assertFalse((self.root / "injected").exists())
        self.assertTrue(manifest["user_config"]["connection_profile"]["required"])
        self.assertNotIn("win32", manifest["compatibility"]["platforms"])

    def test_missing_or_nonexecutable_binary(self):
        binary = self.root / "bin/linux-x86_64/symphony-mcp"
        binary.chmod(0o644)
        result = self.run_target("Linux", "x86_64")
        self.assertEqual(result.returncode, 66)
        self.assertIn("not executable", result.stderr)
        binary.unlink()
        self.assertEqual(self.run_target("Linux", "x86_64").returncode, 66)

    def test_unsupported_platform_fails_closed(self):
        for system, machine in [("Windows_NT", "x86_64"), ("Linux", "riscv64"), ("Darwin", "i386")]:
            with self.subTest(system=system, machine=machine):
                result = self.run_target(system, machine)
                self.assertEqual(result.returncode, 64)
                self.assertEqual(result.stdout, "")
                self.assertIn("unsupported platform", result.stderr)


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="symphony mcpb test ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        files = ["README.md", "LICENSE", "CMakeLists.txt", "src/main.cpp", "src/transport.cpp", "include/symphony/transport.hpp", "third_party/nlohmann/json.hpp", "third_party/nlohmann/LICENSE.MIT", "scripts/configure_connection.py", "skills/symphony-admin/SKILL.md", "skills/symphony-setup/SKILL.md", "docs/mcp-registry.md", "catalog/tools.json"]
        for name in files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("tracked fixture " + name + "\n")
        shutil.copytree(ROOT / "packaging", self.root / "packaging")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
        self.binaries = []
        for target in pack.TARGETS:
            path = self.base / target
            path.write_bytes(executable_header(target))
            path.chmod(0o755)
            self.binaries.append(target + "=" + str(path))
        self.args = types.SimpleNamespace(source_root=self.root, binary=self.binaries, output=self.base / "test.mcpb", release_url=pack.REPOSITORY + "/releases/download/v0.2.0-alpha.1/symphony.mcpb")

    def track(self, name):
        subprocess.run(["git", "-C", str(self.root), "add", "--", name], check=True)

    def test_deterministic_archive_hash_modes_and_untracked_exclusion(self):
        (self.root / "untracked-private.txt").write_text("must not ship")
        first = pack.build(self.args)
        archive_bytes = self.args.output.read_bytes()
        self.assertEqual(first["sha256"], hashlib.sha256(archive_bytes).hexdigest())
        server = json.loads(self.args.output.with_suffix(".server.json").read_text())
        self.assertEqual(server["packages"][0]["fileSha256"], first["sha256"])
        with zipfile.ZipFile(self.args.output) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("catalog/tools.json", archive.namelist())
            self.assertEqual(json.loads(archive.read("manifest.json"))["version"], pack.VERSION)
            self.assertNotIn("untracked-private.txt", archive.namelist())
            self.assertEqual(archive.read("skills/symphony-admin/SKILL.md"), (self.root / "skills/symphony-admin/SKILL.md").read_bytes())
            self.assertEqual(archive.read("manifest.json"), archive.read("packaging/mcpb/manifest.json"))
            for target in pack.TARGETS:
                member = archive.getinfo("bin/" + target + "/symphony-mcp")
                self.assertEqual(stat.S_IMODE(member.external_attr >> 16), 0o755)
                self.assertEqual(archive.read(member), executable_header(target))
            self.assertEqual(stat.S_IMODE(archive.getinfo("launcher.sh").external_attr >> 16), 0o755)
            self.assertTrue(all(not name.startswith("/") and ".." not in Path(name).parts for name in archive.namelist()))
        self.args.output = self.base / "again.mcpb"
        self.assertEqual(pack.build(self.args)["sha256"], first["sha256"])

    def test_refuses_overwrite(self):
        pack.build(self.args)
        original = self.args.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            pack.build(self.args)
        self.assertEqual(self.args.output.read_bytes(), original)

    def test_rejects_symlink_source(self):
        path = self.root / "docs/leak.txt"
        path.symlink_to(self.base / "darwin-arm64")
        self.track("docs/leak.txt")
        with self.assertRaisesRegex(ValueError, "symlink"):
            pack.build(self.args)
        self.assertFalse(self.args.output.exists())

    def test_rejects_tracked_profile_even_when_renamed(self):
        path = self.root / "docs/renamed.txt"
        path.write_text(json.dumps({"schema": "symphony.agent.connection.v1", "qxctl": "/private/tool"}))
        self.track("docs/renamed.txt")
        with self.assertRaisesRegex(ValueError, "Connection profile"):
            pack.build(self.args)

    def test_rejects_pem_keys_without_rejecting_scanner_source(self):
        shutil.copyfile(ROOT / "scripts/package_mcpb.py", self.root / "scripts/package_mcpb.py")
        self.track("scripts/package_mcpb.py")
        pack.collect_source(self.root)
        path = self.root / "docs/secret.txt"
        path.write_text("-----BEGIN RSA PRIVATE KEY-----\nfixture\n-----END RSA PRIVATE KEY-----\n")
        self.track("docs/secret.txt")
        with self.assertRaisesRegex(ValueError, "Private key"):
            pack.build(self.args)

    def test_rejects_unsafe_paths_and_release_url(self):
        for name in ["../escape", "/absolute", "docs/../private", "docs\\secret", "docs/private/key.txt", "connection.json", "docs/key.pem"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                pack.safe_member(name)
        for url in ["https://evil.example/a.mcpb", pack.REPOSITORY + "/releases/download/v1/x.mcpb?token=private", pack.REPOSITORY + "/releases/download/v1/x.zip"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                pack.registry_metadata(url, "0" * 64)

    def test_rejects_missing_duplicate_wrong_arch_and_symlink_binaries(self):
        with self.assertRaisesRegex(ValueError, "All four"):
            pack.binary_inputs(self.binaries[:-1])
        with self.assertRaisesRegex(ValueError, "exactly once"):
            pack.binary_inputs(self.binaries + [self.binaries[0]])
        wrong = self.base / "darwin-x86_64"
        wrong.write_bytes(executable_header("darwin-arm64"))
        with self.assertRaisesRegex(ValueError, "Mach-O"):
            pack.binary_inputs(self.binaries)
        wrong.unlink()
        wrong.symlink_to(self.base / "darwin-arm64")
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            pack.binary_inputs(self.binaries)


if __name__ == "__main__":
    unittest.main()
