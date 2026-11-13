"""Client fragment behavior; no host installation or runtime is required."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_clients.py"


class AdapterTests(unittest.TestCase):
    def test_public_catalogue_survives_all_client_formats(self):
        catalog = '/opt/Review Build/catalog/tools.json'
        for client in ('codex', 'claude', 'antigravity', 'generic'):
            result = self.invoke(client, '--binary', '/opt/bridge', '--config', '/tmp/config.json', '--tool-catalog', catalog)
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = tomllib.loads(result.stdout) if client == 'codex' else json.loads(result.stdout)
            server = parsed['mcp_servers' if client == 'codex' else 'mcpServers']['symphony']
            self.assertEqual(server['args'], ['--config', '/tmp/config.json', '--tool-catalog', catalog])
        rejected = self.invoke('generic', '--binary', '/opt/bridge', '--connect-socket', '/tmp/socket', '--tool-catalog', catalog)
        self.assertNotEqual(rejected.returncode, 0)

    def test_wsl_examples_preserve_explicit_owner_and_catalog(self):
        for file in ('adapters/codex/windows-wsl2.toml.example', 'adapters/generic/windows-wsl2.json.example'):
            content = (ROOT / file).read_text()
            parsed = tomllib.loads(content) if '.toml.' in file else json.loads(content)
            server = parsed.get('mcp_servers', parsed.get('mcpServers'))['symphony']
            self.assertTrue(server['command'].lower().endswith('wsl.exe'))
            for flag in ('--distribution', '--user', '--cd', '--exec', '--config', '--tool-catalog'):
                self.assertEqual(server['args'].count(flag), 1)
            self.assertNotIn('sh', server['args'])

    def test_wsl_public_smoke_rejects_legacy_or_error_results(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('wsl_smoke', ROOT / 'ci/wsl_stdio_smoke.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        tools = [{'name': 'symphony_status'}] + [{'name': 'fixture_' + str(i)} for i in range(10)]
        rows = [{'id': 1, 'result': {'protocolVersion': '2025-11-25'}},
                {'id': 2, 'result': {'tools': tools}},
                {'id': 3, 'result': {'isError': False, 'structuredContent': {}}}]
        def encoded(): return '\n'.join(json.dumps(r) for r in rows)
        module.validate(encoded(), public=True)
        rows.append(rows[0])
        with self.assertRaises(AssertionError): module.validate(encoded(), public=True)
        rows.pop(); rows[2]['result']['isError'] = True
        with self.assertRaises(AssertionError): module.validate(encoded(), public=True)
        rows[2]['result']['isError'] = False; tools[0]['name'] = 'symphony_read'
        with self.assertRaises(AssertionError): module.validate(encoded(), public=True)

    def test_unadvertised_client_and_platform_not_inferred(self):
        result = self.invoke('claude-desktop', '--binary', '/opt/bridge', '--config', '/tmp/config')
        self.assertNotEqual(result.returncode, 0)
        result = self.invoke('codex', '--binary', 'C:\\bridge.exe', '--config', '/tmp/config')
        self.assertNotEqual(result.returncode, 0)

    def invoke(self, client, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--client", client, *extra],
            text=True, capture_output=True, check=False,
        )

    def test_json_profiles_preserve_arguments_as_data(self):
        binary = '/opt/Alpha Build/quo"te/$literal/symphony-mcp'
        config = '/tmp/input $(literal)/connection.json'
        for client in ("claude", "antigravity", "generic"):
            with self.subTest(client=client):
                result = self.invoke(client, "--binary", binary, "--config", config)
                self.assertEqual(result.returncode, 0, result.stderr)
                server = json.loads(result.stdout)["mcpServers"]["symphony"]
                self.assertEqual(server["command"], binary)
                self.assertEqual(server["args"], ["--config", config])
                self.assertEqual(server.get("type"), "stdio" if client == "claude" else None)

    def test_toml_roundtrip_and_socket_selection(self):
        binary = '/opt/Native "Build"/symphony-mcp'
        socket = "/tmp/alpha IPC/bridge.sock"
        result = self.invoke("codex", "--binary", binary, "--connect-socket", socket)
        self.assertEqual(result.returncode, 0, result.stderr)
        server = tomllib.loads(result.stdout)["mcp_servers"]["symphony"]
        self.assertEqual(server["command"], binary)
        self.assertEqual(server["args"], ["--connect-socket", socket])
        self.assertEqual(server["default_tools_approval_mode"], "writes")

    def test_reject_ambiguous_or_unsafe_paths(self):
        for path in ("relative/binary", "/", "/a/../b", "/a\nb", "/a\x00b"):
            # NUL cannot be passed through the OS argv boundary.
            if "\x00" in path:
                continue
            with self.subTest(path=path):
                result = self.invoke("generic", "--binary", path, "--config", "/tmp/config.json")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
        result = self.invoke("generic", "--binary", "/opt/bridge", "--config", "/tmp/config", "--connect-socket", "/tmp/socket")
        self.assertNotEqual(result.returncode, 0)

    def test_exclusive_private_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "client.json"
            args = ("--binary", "/opt/bridge", "--config", "/tmp/config", "--output", str(output))
            result = self.invoke("generic", *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            original = output.read_bytes()
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            repeated = self.invoke("generic", *args)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            link = Path(directory) / "link.json"
            os.symlink(output, link)
            rejected = self.invoke("generic", *args[:-1], str(link))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
