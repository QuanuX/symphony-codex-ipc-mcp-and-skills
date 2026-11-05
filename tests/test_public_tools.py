"""Process-level checks of the versioned operation-specific public interface."""
import json
from pathlib import Path
import sys
import unittest

import test_mcp as fixture
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_tool_catalog as catalog


class PublicTools(unittest.TestCase):
    def setUp(self):
        self.f = fixture.MCPIntegration()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.path = self.f.root / "tools.json"
        self.data = catalog.build({"commands": fixture.RECORDS, "registry_digest": self.f.config["registry_digest"]})
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data))

    def start(self):
        s = fixture.Session(self.f.profile, ["--tool-catalog", str(self.path)])
        self.addCleanup(s.close)
        s.initialize()
        return s

    def test_every_operation_exposed_without_generic_executors(self):
        s = self.start()
        tools = s.rpc("tools/list")["result"]["tools"]
        self.assertEqual(len(tools), 11)
        names = {t["name"] for t in tools}
        self.assertIn("symphony_status", names)
        self.assertIn("symphony_mutate_apply", names)
        for name in ("symphony_discover", "symphony_describe", "symphony_read", "symphony_prepare", "symphony_apply"):
            self.assertNotIn(name, names)
            self.assertTrue(s.tool(name, {"command_id": fixture.PREFIX + "status"})["isError"])
        self.assertEqual(self.f.calls(), [])
        for t in tools:
            self.assertFalse(t["inputSchema"]["additionalProperties"])
            for field in ("readOnlyHint", "destructiveHint", "openWorldHint"):
                self.assertIsInstance(t["annotations"][field], bool)

    def test_typed_input_dispatch_and_unknown_argument_refusal(self):
        s = self.start()
        result = s.tool("symphony_status", {"quiet": True, "mode": "ok"})
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["parsed_stdout"]["argv"], ["status", "--mode=ok", "--quiet=true", "--json"])
        for args in ({"command_id": fixture.PREFIX + "mutate"}, {"json": True}, {"quiet": "true"}, {"mode": ["ok"]}):
            self.assertTrue(s.tool("symphony_status", args)["isError"])
        self.assertEqual(len(self.f.calls()), 1)
        good = s.tool("symphony_module_inspect", {"arg_module_name": "research", "tag": ["a", "b"]})
        self.assertFalse(good["isError"])
        self.assertTrue(s.tool("symphony_module_inspect", {})["isError"])

    def test_operation_bound_one_use_preview(self):
        s = self.start()
        preview = s.tool("symphony_mutate_preview", {"mode": "ok"})["structuredContent"]
        self.assertEqual(self.f.calls(), [])
        args = {"plan_id": preview["plan_id"]}
        self.assertTrue(s.tool("symphony_evidence_apply", args)["isError"])
        self.assertFalse(s.tool("symphony_mutate_apply", args)["isError"])
        self.assertTrue(s.tool("symphony_mutate_apply", args)["isError"])
        self.assertEqual(len(self.f.calls()), 1)

    def test_disabled_operation_and_contract_drift_fail_closed(self):
        self.f.config["enabled_nonread_commands"] = []
        self.f.write_profile()
        for entry in self.data["entries"]:
            if entry["binding"]["command_id"] == fixture.PREFIX + "status":
                entry["binding"]["record"]["authority_mode"] = "changed-contract"
        self.save()
        s = self.start()
        self.assertTrue(s.tool("symphony_mutate_preview", {})["isError"])
        self.assertTrue(s.tool("symphony_status", {})["isError"])
        self.assertEqual(self.f.calls(), [])

    def test_installed_but_unreviewed_commands_are_not_callable(self):
        self.data["entries"] = [e for e in self.data["entries"] if e["binding"]["command_id"] != fixture.PREFIX + "status"]
        self.save()
        s = self.start()
        self.assertTrue(s.tool("symphony_status", {})["isError"])
        self.assertTrue(s.tool("symphony_read", {"command_id": fixture.PREFIX + "status"})["isError"])
        self.assertEqual(self.f.calls(), [])

    def test_catalogue_pagination_is_complete_and_stable(self):
        records = [fixture.record("item"+str(i), "item"+str(i)) for i in range(107)]
        self.data = catalog.build({"commands": records, "registry_digest": self.f.config["registry_digest"]})
        self.save()
        s = self.start()
        tools, params = [], {}
        while True:
            page = s.rpc("tools/list", params)["result"]
            tools.extend(page["tools"])
            if "nextCursor" not in page:
                break
            params = {"cursor": page["nextCursor"]}
        self.assertEqual(len(tools), 108)
        self.assertEqual(len({t["name"] for t in tools}), 108)
        self.assertIn("error", s.rpc("tools/list", {"cursor": "-1"}))
        self.assertIn("error", s.rpc("tools/list", {"cursor": "999999"}))
        # Listed but not installed operations report unavailable, never substitute.
        self.assertTrue(s.tool("symphony_item0", {})["isError"])

    def test_malformed_catalogue_annotation_rejected_at_startup(self):
        self.data["entries"][0]["tool"]["annotations"]["readOnlyHint"] = "true"
        self.save()
        with self.assertRaisesRegex(AssertionError, "annotation"):
            self.start()


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
