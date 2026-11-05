import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import io
from urllib.parse import urlsplit, parse_qs, urlencode
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("notion_publish", Path(__file__).resolve().parents[1] / "scripts/notion_publish.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class NotionPublishing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.root.chmod(0o700)
        self.c = {"schema": "symphony.notion.publisher.v1", "workspace_id": "selected-workspace",
                  "allowed_parent_pages": ["selected-page"], "client_id": "fixture-client",
                  "client_secret_file": str(self.root / "secret.json"),
                  "redirect_uri": "http://127.0.0.1:8766/notion/callback", "token_file": str(self.root / "token.json")}
        n.write_private(self.c["token_file"], {"access_token": "private-access", "refresh_token": "private-refresh", "workspace_id": "selected-workspace"})
        n.write_private(self.c["client_secret_file"], {"client_secret": "private-client-secret"})
        self.plan = self.root / "publication.json"

    def preview(self, kind="report"):
        return n.prepare(self.c, "selected-page", "Test report", "Synthetic content only.", kind, self.plan)

    def test_preview_never_publishes_and_preserves_unicode(self):
        with patch.object(n, "request") as req:
            n.prepare(self.c, "selected-page", "研究", "π" * 4000, "research", self.plan)
            req.assert_not_called()
        plan = n.read_private(self.plan)
        self.assertGreater(len(plan["payload"]["children"]), 2)
        self.assertEqual(self.plan.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("private-access", self.plan.read_text())

    def test_all_document_kinds(self):
        for kind in ("report", "incident", "research"):
            out = self.root / (kind + ".json")
            n.prepare(self.c, "selected-page", kind, "body", kind, out)
            self.assertIn("Symphony " + kind, n.read_private(out)["payload"]["children"][0]["paragraph"]["rich_text"][0]["text"]["content"])

    def test_publish_once_and_durable_receipt(self):
        p = self.preview()
        def remote(path, payload, auth):
            self.assertTrue(Path(str(self.plan) + ".receipt.json").exists())
            self.assertEqual(path, "/v1/pages")
            self.assertEqual(auth, "Bearer private-access")
            self.assertEqual(payload["parent"], {"page_id": "selected-page"})
            return {"object": "page", "id": "created", "url": "https://notion.so/created"}
        with patch.object(n, "request", side_effect=remote) as req:
            r = n.publish(self.c, self.plan, p["sha256"])
            self.assertEqual(r["outcome"], "published")
            with self.assertRaises(FileExistsError):
                n.publish(self.c, self.plan, p["sha256"])
            self.assertEqual(req.call_count, 1)

    def test_lost_response_never_replays(self):
        p = self.preview()
        with patch.object(n, "request", side_effect=TimeoutError) as req:
            with self.assertRaisesRegex(RuntimeError, "outcome unknown"):
                n.publish(self.c, self.plan, p["sha256"])
            with self.assertRaises(FileExistsError):
                n.publish(self.c, self.plan, p["sha256"])
            self.assertEqual(req.call_count, 1)
        r = n.read_private(str(self.plan) + ".receipt.json")
        self.assertEqual(r["outcome"], "unknown_requires_reconciliation")

    def test_destination_hash_expiry_and_token_binding(self):
        with self.assertRaisesRegex(ValueError, "scope"):
            n.prepare(self.c, "unapproved-page", "title", "body", "report", self.plan)
        p = self.preview()
        with patch.object(n, "request") as req:
            with self.assertRaisesRegex(ValueError, "checksum"):
                n.publish(self.c, self.plan, "incorrect")
            with patch.object(n.time, "time", return_value=10**12):
                with self.assertRaisesRegex(ValueError, "expired"):
                    n.publish(self.c, self.plan, p["sha256"])
            n.write_private(self.c["token_file"], {"workspace_id": "other", "access_token": "different"}, replace=True)
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                n.publish(self.c, self.plan, p["sha256"])
            req.assert_not_called()

    def test_refresh_rotation_invalidates_preview(self):
        p = self.preview()
        with patch.object(n, "request", return_value={"access_token": "rotated", "refresh_token": "rotated-refresh"}) as req:
            self.assertTrue(n.refresh(self.c)["refreshed"])
            self.assertEqual(req.call_args.args[1]["grant_type"], "refresh_token")
            with self.assertRaisesRegex(ValueError, "Connection changed"):
                n.publish(self.c, self.plan, p["sha256"])
            self.assertEqual(req.call_count, 1)

    def test_refresh_loss_and_revocation(self):
        with patch.object(n, "request", side_effect=TimeoutError) as req:
            with self.assertRaises(TimeoutError):
                n.refresh(self.c)
            with self.assertRaises(FileExistsError):
                n.refresh(self.c)
            self.assertEqual(req.call_count, 1)
        with patch.object(n, "request", return_value={}):
            self.assertTrue(n.revoke(self.c)["revoked"])
        self.assertFalse(Path(self.c["token_file"]).exists())

    def test_private_files_and_redirect_rejection(self):
        token = Path(self.c["token_file"])
        token.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "0600"):
            n.token(self.c)
        token.chmod(0o600)
        alias = self.root / "alias.json"
        alias.symlink_to(token)
        with self.assertRaises(OSError):
            n.read_private(alias)
        self.assertIsNone(n.NoRedirect().redirect_request(None, None, None, None, None, None))
        self.c["redirect_uri"] = "http://remote.example/notion/callback"
        with self.assertRaisesRegex(ValueError, "loopback"):
            n.authorize(self.c)

    def test_config_status_does_not_probe_remote(self):
        path = self.root / "publisher.json"
        n.write_private(path, self.c)
        with patch.object(n, "request") as req:
            c = n.config(path)
            self.assertEqual(n.token(c)["workspace_id"], "selected-workspace")
            req.assert_not_called()

    def test_oauth_state_and_workspace_bound_callback(self):
        Path(self.c["token_file"]).unlink()
        output = io.StringIO()
        responses = []
        owner = self

        class Server:
            def __init__(self, address, handler):
                owner.assertEqual(address, ("127.0.0.1", 8766))
                self.handler = handler
                self.turn = 0
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def handle_request(self):
                url = output.getvalue().splitlines()[-1]
                state = parse_qs(urlsplit(url).query)["state"][0]
                handler = object.__new__(self.handler)
                handler.path = "/notion/callback?" + urlencode({"state": "wrong" if self.turn == 0 else state, "code": "private-code"})
                handler.wfile = io.BytesIO()
                handler.send_response = responses.append
                handler.send_header = lambda *args: None
                handler.end_headers = lambda: None
                self.turn += 1
                handler.do_GET()

        with patch.object(n, "HTTPServer", Server), patch("sys.stdout", output), patch.object(n, "request", return_value={"workspace_id": "selected-workspace", "access_token": "new-token", "refresh_token": "new-refresh"}) as req:
            self.assertTrue(n.authorize(self.c)["connected"])
            self.assertEqual(req.call_count, 1)
            self.assertEqual(req.call_args.args[1]["code"], "private-code")
            self.assertEqual(responses, [400, 200])
        self.assertEqual(n.token(self.c)["access_token"], "new-token")
        self.assertNotIn("private-code", output.getvalue())
        self.assertNotIn("new-token", output.getvalue())
        Path(self.c["token_file"]).unlink()
        output = io.StringIO()
        responses.clear()
        with patch.object(n, "HTTPServer", Server), patch("sys.stdout", output), patch.object(n, "request", return_value={"workspace_id": "wrong-workspace", "access_token": "wrong-token"}):
            with self.assertRaisesRegex(ValueError, "Authorization failed"):
                n.authorize(self.c)
            self.assertEqual(responses, [400, 400])
        self.assertFalse(Path(self.c["token_file"]).exists())

    def test_http_client_pins_origin_version_and_bounded_payload(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'{"object":"page","id":"created"}'
        with patch.object(n, "build_opener") as factory:
            factory.return_value.open.return_value = Response()
            n.request("/v1/pages", {"text": "π"}, "Bearer private-token")
            req = factory.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url, "https://api.notion.com/v1/pages")
            self.assertEqual(req.get_header("Notion-version"), "2026-03-11")
            self.assertEqual(req.get_header("Authorization"), "Bearer private-token")
            self.assertEqual(json.loads(req.data), {"text": "π"})
            with self.assertRaisesRegex(ValueError, "500KB"):
                n.request("/v1/pages", {"text": "x" * 500001}, "Bearer private-token")
            self.assertEqual(factory.return_value.open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
