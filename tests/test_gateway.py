#!/usr/bin/env python3
"""Real HTTP + native bridge + isolated qxctl fixture; no installed state."""
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import unittest

GATEWAY = str(Path(sys.argv.pop(2)).resolve())
import test_mcp as fixture


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class GatewayTest(unittest.TestCase):
    def setUp(self):
        self.f = fixture.MCPIntegration()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.port = free_port()
        self.credentials = {}
        clients = []
        for name in ("reader", "writer"):
            tok = secrets.token_urlsafe(48)
            self.credentials[name] = tok
            path = self.root / (name + ".token")
            path.write_text(tok)
            path.chmod(0o600)
            tools = ["symphony_connection", "symphony_discover", "symphony_describe", "symphony_read"]
            if name == "writer":
                tools += ["symphony_prepare", "symphony_apply"]
            clients.append({"id": name, "token_file": str(path), "allowed_tools": tools,
                            "allowed_commands": [fixture.PREFIX + "status", fixture.PREFIX + "mutate"]})
        self.cfg = {"schema": "symphony.agent.gateway.v1", "installation_id": "fixture",
                    "connection_profile": str(self.f.profile), "port": self.port,
                    "allowed_hosts": [f"127.0.0.1:{self.port}"], "allowed_origins": ["https://www.notion.so"],
                    "clients": clients, "audit_file": str(self.root / "audit.jsonl"), "max_sessions": 8,
                    "session_ttl_seconds": 600}
        self.cfg_path = self.root / "gateway.json"
        self.process = None
        self.sequence = 10

    def start(self):
        self.cfg_path.write_text(json.dumps(self.cfg))
        self.cfg_path.chmod(0o600)
        self.process = subprocess.Popen([GATEWAY, "--config", str(self.cfg_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        for _ in range(100):
            if self.process.poll() is not None:
                self.fail(self.process.stderr.read().decode())
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.03)
        self.fail("Gateway did not listen")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process.stdout.close()
            self.process.stderr.close()
            self.process = None

    def send(self, body=None, sid=None, who="reader", method="POST", headers=None, path="/mcp"):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
             "Authorization": "Bearer " + self.credentials[who], "MCP-Protocol-Version": "2025-11-25"}
        if sid:
            h["Mcp-Session-Id"] = sid
        h.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, h)
            r = conn.getresponse()
            raw = r.read()
            return r.status, dict(r.getheaders()), json.loads(raw) if raw else None
        finally:
            conn.close()

    def initialize(self, who="reader"):
        status, headers, body = self.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}}, who=who)
        self.assertEqual(status, 200, body)
        sid = next(v for k, v in headers.items() if k.lower() == "mcp-session-id")
        self.assertEqual(self.send({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid, who)[0], 202)
        return sid

    def rpc(self, sid, method, params=None, who="reader", ident=None):
        self.sequence += 1
        return self.send({"jsonrpc": "2.0", "id": ident or self.sequence, "method": method, "params": params or {}}, sid, who)

    def tool(self, sid, name, args=None, who="reader", ident=None):
        return self.rpc(sid, "tools/call", {"name": name, "arguments": args or {}}, who, ident)

    def test_http_read_scope_and_audit(self):
        self.start()
        sid = self.initialize()
        status, _, body = self.rpc(sid, "tools/list")
        self.assertEqual(status, 200)
        self.assertNotIn("symphony_apply", [x["name"] for x in body["result"]["tools"]])
        _, _, body = self.tool(sid, "symphony_read", {"command_id": fixture.PREFIX + "status"})
        self.assertEqual(body["result"]["structuredContent"]["exit_code"], 0)
        self.assertEqual(len(self.f.calls()), 1)
        self.assertEqual(self.tool(sid, "symphony_read", {"command_id": fixture.PREFIX + "plain"})[0], 403)
        self.assertEqual(self.tool(sid, "symphony_prepare", {"command_id": fixture.PREFIX + "mutate"})[0], 403)
        _, _, body = self.tool(sid, "symphony_discover")
        self.assertTrue(all(c["command_id"] in self.cfg["clients"][0]["allowed_commands"] for c in body["result"]["structuredContent"]["commands"]))
        audit = (self.root / "audit.jsonl").read_text()
        self.assertIn("response_ready", audit)
        for secret in self.credentials.values():
            self.assertNotIn(secret, audit)
        self.assertNotIn("fixture_marker", audit)

    def test_auth_origin_host_version_and_missing_session(self):
        self.start()
        self.assertEqual(self.send(headers={"Authorization": "Bearer bad"})[0], 401)
        self.assertEqual(self.send(headers={"Host": "attacker.invalid"})[0], 403)
        self.assertEqual(self.send(headers={"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.send(headers={"Origin": "null"})[0], 403)
        self.assertEqual(self.send(headers={"MCP-Protocol-Version": "unsupported"})[0], 400)
        self.assertEqual(self.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})[0], 400)
        self.assertEqual(self.send(path="/mcp?token=bad")[0], 401)
        self.assertEqual(self.send(method="GET")[0], 405)

    def test_session_isolation_rotation_and_delete(self):
        self.start()
        sid = self.initialize()
        self.assertEqual(self.rpc(sid, "tools/list", who="writer")[0], 404)
        (self.root / "reader.token").write_text(secrets.token_urlsafe(48))
        self.assertEqual(self.rpc(sid, "tools/list")[0], 401)
        self.credentials["reader"] = (self.root / "reader.token").read_text()
        self.assertEqual(self.rpc(sid, "tools/list")[0], 404)
        new = self.initialize()
        self.assertEqual(self.send(sid=new, method="DELETE")[0], 204)
        self.assertEqual(self.rpc(new, "tools/list")[0], 404)

    def test_prepare_apply_replay_and_cross_session_plan(self):
        self.start()
        sid = self.initialize("writer")
        _, _, prepared = self.tool(sid, "symphony_prepare", {"command_id": fixture.PREFIX + "mutate"}, "writer")
        plan = prepared["result"]["structuredContent"]["plan_id"]
        other = self.initialize("writer")
        self.assertTrue(self.tool(other, "symphony_apply", {"plan_id": plan}, "writer")[2]["result"]["isError"])
        first = self.tool(sid, "symphony_apply", {"plan_id": plan}, "writer", 99)
        second = self.tool(sid, "symphony_apply", {"plan_id": plan}, "writer", 99)
        self.assertEqual(first[2], second[2])
        self.assertEqual(len(self.f.calls()), 1)
        self.assertEqual(self.rpc(sid, "ping", who="writer", ident=99)[0], 409)
        self.assertTrue(self.tool(sid, "symphony_apply", {"plan_id": plan}, "writer")[2]["result"]["isError"])

    def test_native_refusal_and_unknown_not_retried(self):
        self.start()
        sid = self.initialize("writer")
        _, _, prepared = self.tool(sid, "symphony_prepare", {"command_id": fixture.PREFIX + "mutate", "flags": {"mode": "failure"}}, "writer")
        plan = prepared["result"]["structuredContent"]["plan_id"]
        response = self.tool(sid, "symphony_apply", {"plan_id": plan}, "writer", 100)[2]
        self.assertEqual(response["result"]["structuredContent"]["transport_outcome"], "unknown_requires_owner_reconciliation")
        self.tool(sid, "symphony_apply", {"plan_id": plan}, "writer", 100)
        self.assertEqual(len(self.f.calls()), 1)

    def test_dropped_http_response_does_not_repeat_write(self):
        self.f.config["timeout_ms"] = 3000
        self.f.write_profile()
        self.start()
        sid = self.initialize("writer")
        _, _, prepared = self.tool(sid, "symphony_prepare", {"command_id": fixture.PREFIX + "mutate", "flags": {"mode": "timeout"}}, "writer")
        plan = prepared["result"]["structuredContent"]["plan_id"]
        body = {"jsonrpc": "2.0", "id": 900, "method": "tools/call", "params": {"name": "symphony_apply", "arguments": {"plan_id": plan}}}
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/mcp", json.dumps(body), {
            "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.credentials["writer"], "Mcp-Session-Id": sid,
            "MCP-Protocol-Version": "2025-11-25"})
        try:
            for _ in range(100):
                if self.f.calls():
                    break
                time.sleep(.01)
            self.assertEqual(len(self.f.calls()), 1)
        finally:
            conn.close()  # Intentionally lose the response after dispatch.
        status, _, reply = self.send(body, sid, "writer")
        self.assertEqual(status, 200)
        self.assertEqual(reply["result"]["structuredContent"]["exit_code"], 0)
        self.assertEqual(len(self.f.calls()), 1)

    def test_expiry_capacity_and_invalid_bodies(self):
        self.cfg["session_ttl_seconds"] = 1
        self.cfg["max_sessions"] = 1
        self.start()
        sid = self.initialize()
        self.assertEqual(self.send([])[0], 400)
        self.assertEqual(self.send(headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.send(headers={"Accept": "application/json"})[0], 406)
        self.assertEqual(self.send({"jsonrpc": "2.0", "method": "tools/call"}, sid)[0], 400)
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        self.assertEqual(self.send(req)[0], 429)
        time.sleep(1.05)
        self.assertEqual(self.rpc(sid, "ping")[0], 404)

    def test_existing_private_ipc(self):
        sock = self.root / "bridge.sock"
        local = subprocess.Popen([fixture.MCP, "--config", str(self.f.profile), "--listen", str(sock)], stderr=subprocess.PIPE)
        def cleanup():
            local.terminate()
            local.wait(timeout=5)
            local.stderr.close()
        self.addCleanup(cleanup)
        for _ in range(100):
            if sock.exists():
                break
            time.sleep(.02)
        self.cfg.pop("connection_profile")
        self.cfg.update(connect_socket=str(sock), max_sessions=1)
        self.start()
        sid = self.initialize()
        response = self.tool(sid, "symphony_read", {"command_id": fixture.PREFIX + "status"})
        self.assertEqual(response[2]["result"]["structuredContent"]["exit_code"], 0)
        self.assertEqual(len(self.f.calls()), 1)
        local.terminate()
        local.wait(timeout=5)
        self.assertEqual(self.tool(sid, "symphony_read", {"command_id": fixture.PREFIX + "status"})[0], 502)
        self.assertEqual(self.rpc(sid, "ping")[0], 404)
        self.assertEqual(len(self.f.calls()), 1)

    def test_unsafe_configuration_refused(self):
        self.cfg_path.write_text(json.dumps(self.cfg))
        self.cfg_path.chmod(0o644)
        p = subprocess.run([GATEWAY, "--config", str(self.cfg_path)], capture_output=True, timeout=5)
        self.assertEqual(p.returncode, 2)
        self.assertIn(b"0600", p.stderr)

    def test_generator_private_defaults_and_exclusive_creation(self):
        dest = self.root / "generated"
        script = Path(__file__).resolve().parents[1] / "scripts/configure_gateway.py"
        argv = [sys.executable, str(script), "--output", str(dest), "--installation", "fixture",
                "--connection", str(self.f.profile), "--host", "example.org", "--command", fixture.PREFIX + "status"]
        result = subprocess.run(argv, capture_output=True, text=True, check=True)
        cfg = json.loads((dest / "gateway.json").read_text())
        token = (dest / "notion-agent.token").read_text()
        self.assertNotIn(token, result.stdout)
        self.assertEqual(dest.stat().st_mode & 0o777, 0o700)
        self.assertEqual((dest / "gateway.json").stat().st_mode & 0o777, 0o600)
        self.assertNotIn("symphony_apply", cfg["clients"][0]["allowed_tools"])
        second = subprocess.run(argv, capture_output=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual((dest / "notion-agent.token").read_text(), token)

    def test_ambiguous_rotated_tokens_fail_closed(self):
        self.start()
        sid = self.initialize()
        (self.root / "writer.token").write_text(self.credentials["reader"])
        self.assertEqual(self.rpc(sid, "tools/list")[0], 401)

    def test_payload_limit_and_duplicate_headers(self):
        self.start()
        self.assertEqual(self.send({"large": "x" * (1024 * 1024)})[0], 413)
        raw = (f"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
               f"Authorization: Bearer {self.credentials['reader']}\r\n"
               f"Authorization: Bearer {self.credentials['writer']}\r\n"
               "Content-Length: 2\r\nConnection: close\r\n\r\n{}")
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall(raw.encode())
            response = sock.recv(8192)
        self.assertIn(b"401", response.split(b"\r\n")[0])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
