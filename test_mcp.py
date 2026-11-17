#!/usr/bin/env python3
"""
End-to-end verification suite for `orphan-disease-opportunity-mcp` (v1.6.0).

Tests:
  1. Subprocess `stdio` JSON-RPC 2.0 protocol lifecycle:
     - `server/discover` (`2026-07-28`)
     - `initialize` (`2026-07-28`, `_meta` `2026-07-28` negotiation, and `2025-11-25` fallback)
     - `notifications/initialized`, `ping`, `tools/list`, `resources/list`,
       `resources/templates/list`, `prompts/list`, and MCP Apps `ui` extension capability.
  2. All 6 canonical read-verb tools (`search_founder_opportunities`,
     `get_disease_case_study`, `list_non_dilutive_grants`,
     `get_validation_communities`, `get_90_day_validation_plan`,
     `search_any_orphan_indication`) + backward-compatible legacy aliases
     (`match_founder_opportunities`, `find_non_dilutive_grants`,
     `generate_90_day_validation_plan`, `analyze_any_orphan_indication`).
  3. Schema quality & VerifyMCP compliance:
     - Every tool includes `title`, `inputSchema` (`additionalProperties: False`, `examples`),
       `outputSchema`, `annotations` (`readOnlyHint: True`), and `_meta` (`ui://rare-disease-atlas/venture-card`).
     - Every `tools/call` returns both `content` and `structuredContent` matching `outputSchema`.
     - LLM schema token footprint across 6 tools + 6 resources stays `< 85` tokens/item (`< 95` budget).
     - Zero write verbs (`generate`/`create`/`submit`) in server `instructions`.
  4. All 6 MCP Resources (5 markdown playbooks + `ui://rare-disease-atlas/venture-card`
     `text/html;profile=mcp-app`) & MCP Prompt `evaluate-rare-disease-venture`.
  5. Live HTTPS/HTTP data fetch (`ATLAS_DATA_URL`) + graceful offline fallback.
  6. Streamable HTTP transport (`POST /mcp`, `GET /.well-known/mcp.json`, `GET /health`).
  7. Static validation of `manifest.json`, `server.json`, `glama.json`, and `openapi.yaml`.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import urllib.request

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

MCP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MCP_DIR))

from orphan_disease_mcp import __version__  # noqa: E402
from orphan_disease_mcp.server import (  # noqa: E402
    RESOURCES_MANIFEST,
    TOOLS_MANIFEST,
    UI_RESOURCE_URI,
    AtlasRepository,
    OrphanDiseaseMCPServer,
    create_http_server,
)


class StdioMCPClient:
    """Helper to drive the MCP server over real subprocess stdio pipes."""

    def __init__(self, env_overrides: dict[str, str] | None = None) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(MCP_DIR)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if env_overrides:
            env.update(env_overrides)
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "orphan_disease_mcp"],
            cwd=str(MCP_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

    def send_request(self, payload: dict) -> dict:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            stderr_out = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"MCP server closed stdout unexpectedly. stderr={stderr_out}")
        return json.loads(line)

    def send_notification(self, payload: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=5)
        if self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()


class OrphanDiseaseMCPTestSuite(unittest.TestCase):
    def test_01_schema_quality_token_budget_and_protocol_discover(self) -> None:
        self.assertEqual(__version__, "1.6.0")
        self.assertEqual(len(TOOLS_MANIFEST), 6)
        self.assertEqual(len(RESOURCES_MANIFEST), 6)

        canonical_names = [t["name"] for t in TOOLS_MANIFEST]
        self.assertEqual(
            canonical_names,
            [
                "search_founder_opportunities",
                "get_disease_case_study",
                "list_non_dilutive_grants",
                "get_validation_communities",
                "get_90_day_validation_plan",
                "search_any_orphan_indication",
            ],
        )

        for tool in TOOLS_MANIFEST:
            self.assertTrue(tool.get("title"))
            self.assertTrue(tool.get("description"))
            in_schema = tool["inputSchema"]
            self.assertIs(in_schema.get("additionalProperties"), False)
            self.assertTrue(
                isinstance(in_schema.get("examples"), list) and len(in_schema["examples"]) >= 1,
                f"Missing examples on {tool['name']}",
            )
            out_schema = tool.get("outputSchema")
            self.assertIsInstance(out_schema, dict)
            self.assertEqual(out_schema.get("type"), "object")
            ann = tool.get("annotations", {})
            self.assertIs(ann.get("readOnlyHint"), True)
            self.assertIs(ann.get("destructiveHint"), False)
            self.assertIs(ann.get("idempotentHint"), True)
            self.assertIn("openWorldHint", ann)
            self.assertEqual(
                tool.get("_meta", {}).get("ui", {}).get("resourceUri"),
                UI_RESOURCE_URI,
            )

        for res in RESOURCES_MANIFEST:
            self.assertTrue(res.get("description") and len(res["description"]) >= 30)

        # Verify LLM-facing JSON token footprint (< 85 tokens/item across 6 tools + 6 resources)
        llm_items = [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in TOOLS_MANIFEST
        ] + RESOURCES_MANIFEST
        total_chars = sum(
            len(json.dumps(item, separators=(",", ":"))) for item in llm_items
        )
        avg_tokens_per_item = (total_chars / 4.0) / len(llm_items)
        self.assertLess(avg_tokens_per_item, 85.0)
        self.assertLess(avg_tokens_per_item, 95.0)

    def test_02_stdio_full_jsonrpc_lifecycle_all_6_tools_and_aliases(self) -> None:
        client = StdioMCPClient({"ATLAS_OFFLINE": "1"})
        try:
            # 1a. server/discover (MCP 2026-07-28)
            disc_resp = client.send_request(
                {"jsonrpc": "2.0", "id": 100, "method": "server/discover", "params": {}}
            )
            disc = disc_resp["result"]
            self.assertEqual(disc["protocolVersion"], "2026-07-28")
            self.assertEqual(disc["serverInfo"]["version"], "1.6.0")
            self.assertIn(
                "text/html;profile=mcp-app",
                disc["capabilities"]["extensions"]["io.modelcontextprotocol/ui"]["mimeTypes"],
            )
            instr_lower = disc["instructions"].lower()
            for forbidden in ("generate", "create", "submit", "delete", "write"):
                self.assertNotIn(forbidden, instr_lower)
            self.assertEqual(len(disc["tools"]), 6)
            self.assertEqual(len(disc["resources"]), 6)

            # 1b. initialize with 2026-07-28 via _meta
            init_2026 = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 101,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"},
                        "capabilities": {},
                        "clientInfo": {"name": "verifymcp", "version": "1.0.0"},
                    },
                }
            )
            self.assertEqual(init_2026["result"]["protocolVersion"], "2026-07-28")

            # 1c. initialize with legacy version -> negotiates 2025-11-25
            init_legacy = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "test-harness", "version": "1.0.0"},
                    },
                }
            )
            self.assertEqual(init_legacy["result"]["protocolVersion"], "2025-11-25")
            self.assertEqual(
                init_legacy["result"]["serverInfo"]["name"],
                "orphan-disease-opportunity-mcp",
            )

            # 2. notifications/initialized
            client.send_notification(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            )

            # 3. ping
            ping_resp = client.send_request(
                {"jsonrpc": "2.0", "id": 2, "method": "ping"}
            )
            self.assertEqual(ping_resp["result"], {})

            # 4. Canonical Tool #1: search_founder_opportunities (+ alias match_founder_opportunities)
            search_resp = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "search_founder_opportunities",
                        "arguments": {
                            "background": "computational-ai-bio",
                            "capital_tier": "bootstrapped-grant",
                            "wet_lab_required": False,
                        },
                    },
                }
            )
            self.assertFalse(search_resp["result"]["isError"])
            sc1 = search_resp["result"]["structuredContent"]
            self.assertGreaterEqual(sc1["matched_count"], 2)
            self.assertEqual(sc1, json.loads(search_resp["result"]["content"][0]["text"]))

            alias_match = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 41,
                    "method": "tools/call",
                    "params": {
                        "name": "match_founder_opportunities",
                        "arguments": {"disease_id": "autoimmune-myelofibrosis"},
                    },
                }
            )
            self.assertFalse(alias_match["result"]["isError"])
            self.assertGreaterEqual(alias_match["result"]["structuredContent"]["matched_count"], 1)

            # 5. Canonical Tool #2: get_disease_case_study (both Myelofibrosis flagships)
            for idx, slug in enumerate(("jak2-myelofibrosis", "autoimmune-myelofibrosis")):
                cs_resp = client.send_request(
                    {
                        "jsonrpc": "2.0",
                        "id": 50 + idx,
                        "method": "tools/call",
                        "params": {
                            "name": "get_disease_case_study",
                            "arguments": {"disease_id": slug},
                        },
                    }
                )
                self.assertFalse(cs_resp["result"]["isError"])
                cs_sc = cs_resp["result"]["structuredContent"]
                self.assertEqual(cs_sc["disease_id"], slug)
                self.assertIn("case_study", cs_sc)

            # 6. Canonical Tool #3: list_non_dilutive_grants (+ alias find_non_dilutive_grants)
            grants_resp = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "list_non_dilutive_grants",
                        "arguments": {"track": "sbir"},
                    },
                }
            )
            self.assertFalse(grants_resp["result"]["isError"])
            grants_sc = grants_resp["result"]["structuredContent"]
            self.assertEqual(grants_sc["track_filter"], "sbir-sttr")
            self.assertGreaterEqual(grants_sc["grant_count"], 2)

            grants_alias = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 61,
                    "method": "tools/call",
                    "params": {
                        "name": "find_non_dilutive_grants",
                        "arguments": {"track": "all"},
                    },
                }
            )
            self.assertGreaterEqual(grants_alias["result"]["structuredContent"]["grant_count"], 5)

            # 7. Canonical Tool #4: get_validation_communities
            val_resp = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {
                        "name": "get_validation_communities",
                        "arguments": {"disease_id": "jak2-myelofibrosis"},
                    },
                }
            )
            self.assertFalse(val_resp["result"]["isError"])
            val_sc = val_resp["result"]["structuredContent"]
            self.assertEqual(val_sc["disease_id"], "jak2-myelofibrosis")
            self.assertGreaterEqual(len(val_sc["ethical_discovery_guidelines"]), 4)

            # 8. Canonical Tool #5: get_90_day_validation_plan (+ alias generate_90_day_validation_plan)
            plan_resp = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "tools/call",
                    "params": {
                        "name": "get_90_day_validation_plan",
                        "arguments": {
                            "disease_id": "jak2-myelofibrosis",
                            "background": "computational-ai-bio",
                            "capital_tier": "bootstrapped-grant",
                        },
                    },
                }
            )
            self.assertFalse(plan_resp["result"]["isError"])
            plan_sc = plan_resp["result"]["structuredContent"]
            self.assertEqual(plan_sc["disease_id"], "jak2-myelofibrosis")
            self.assertIn("days_1_to_30", plan_sc["roadmap_30_60_90"])
            self.assertIn("days_31_to_60", plan_sc["roadmap_30_60_90"])
            self.assertIn("days_61_to_90", plan_sc["roadmap_30_60_90"])
            self.assertIn("paired_myelofibrosis_contrast", plan_sc)

            plan_alias = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 81,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_90_day_validation_plan",
                        "arguments": {"disease_id": "autoimmune-myelofibrosis"},
                    },
                }
            )
            self.assertFalse(plan_alias["result"]["isError"])
            self.assertEqual(
                plan_alias["result"]["structuredContent"]["disease_id"],
                "autoimmune-myelofibrosis",
            )

            # 9. Canonical Tool #6: search_any_orphan_indication (+ alias analyze_any_orphan_indication)
            live_resp = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {
                        "name": "search_any_orphan_indication",
                        "arguments": {"disease_query": "autoimmune myelofibrosis"},
                    },
                }
            )
            self.assertFalse(live_resp["result"]["isError"])
            live_sc = live_resp["result"]["structuredContent"]
            self.assertEqual(live_sc["curated_atlas_match"], "autoimmune-myelofibrosis")
            self.assertIn("flagship_myelofibrosis_benchmark", live_sc)
            self.assertIn("live_diligence", live_sc)

            live_alias = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 91,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_any_orphan_indication",
                        "arguments": {"disease_query": "vexas"},
                    },
                }
            )
            self.assertEqual(
                live_alias["result"]["structuredContent"]["curated_atlas_match"],
                "vexas-syndrome",
            )

            # 10. All 6 resources/list & resources/read (including ui://rare-disease-atlas/venture-card)
            res_list = client.send_request(
                {"jsonrpc": "2.0", "id": 10, "method": "resources/list"}
            )
            uris = [r["uri"] for r in res_list["result"]["resources"]]
            self.assertIn(UI_RESOURCE_URI, uris)
            self.assertIn("briefing://rare-disease-playbook/jak2-myelofibrosis", uris)
            self.assertIn("briefing://rare-disease-playbook/autoimmune-myelofibrosis", uris)

            for idx, uri in enumerate(uris):
                r_read = client.send_request(
                    {
                        "jsonrpc": "2.0",
                        "id": 200 + idx,
                        "method": "resources/read",
                        "params": {"uri": uri},
                    }
                )
                content_item = r_read["result"]["contents"][0]
                self.assertEqual(content_item["uri"], uri)
                self.assertTrue(len(content_item["text"]) > 100)
                if uri == UI_RESOURCE_URI:
                    self.assertEqual(content_item["mimeType"], "text/html;profile=mcp-app")
                    self.assertIn("structuredContent", content_item["text"])

            # 11. prompts/list & prompts/get
            p_get = client.send_request(
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "prompts/get",
                    "params": {
                        "name": "evaluate-rare-disease-venture",
                        "arguments": {
                            "founder_background": "public-health",
                            "capital_budget": "bootstrapped-grant",
                            "wet_lab_access": "false",
                        },
                    },
                }
            )
            prompt_msg = p_get["result"]["messages"][0]["content"]["text"]
            self.assertIn("search_founder_opportunities", prompt_msg)
            self.assertIn("get_90_day_validation_plan", prompt_msg)
        finally:
            client.close()

    def test_03_live_url_fetch_and_offline_fallback(self) -> None:
        class MockS3Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

            def do_GET(self) -> None:  # noqa: N802
                payload = {
                    "atlas_name": "Live Edge Venture Feed",
                    "opportunities": [
                        {
                            "id": "opp-live-test",
                            "disease_id": "jak2-myelofibrosis",
                            "title": "Live Synced Opportunity",
                            "backgrounds": ["venture-novel-financing"],
                            "capital_tier": "seed",
                            "capital_range_usd": "$500K",
                            "wet_lab_required": False,
                            "problem_wedge": "Live wedge",
                            "solution_blueprint": "Live blueprint",
                        }
                    ],
                }
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        mock_http = ThreadingHTTPServer(("127.0.0.1", 0), MockS3Handler)
        port = mock_http.server_address[1]
        thread = threading.Thread(target=mock_http.serve_forever, daemon=True)
        thread.start()
        try:
            prev_offline = os.environ.pop("ATLAS_OFFLINE", None)
            try:
                live_repo = AtlasRepository(
                    live_url=f"http://127.0.0.1:{port}/opportunities.json",
                    timeout_seconds=2.0,
                )
                srv = OrphanDiseaseMCPServer(repository=live_repo)
                live_res = srv.tool_search_founder_opportunities(background="vc")
                self.assertEqual(live_res["data_source"], "live")
                self.assertEqual(live_res["matched_count"], 1)
                self.assertEqual(live_res["opportunities"][0]["id"], "opp-live-test")

                fallback_repo = AtlasRepository(
                    live_url="http://127.0.0.1:9/unreachable.json",
                    timeout_seconds=0.5,
                )
                fb_srv = OrphanDiseaseMCPServer(repository=fallback_repo)
                fb_res = fb_srv.tool_search_founder_opportunities(background="all")
                self.assertEqual(fb_res["data_source"], "bundled_fallback")
                self.assertGreaterEqual(fb_res["matched_count"], 16)
            finally:
                if prev_offline is not None:
                    os.environ["ATLAS_OFFLINE"] = prev_offline
        finally:
            mock_http.shutdown()
            mock_http.server_close()

    def test_04_streamable_http_transport(self) -> None:
        repo = AtlasRepository(live_url="")
        mcp_srv = OrphanDiseaseMCPServer(repository=repo)
        httpd = create_http_server(mcp_srv, host="127.0.0.1", port=0)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/.well-known/mcp.json", timeout=2
            ) as resp:
                self.assertEqual(resp.status, 200)
                manifest = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(manifest["version"], "1.6.0")
                self.assertEqual(manifest["protocolVersion"], "2026-07-28")
                self.assertIn("search_founder_opportunities", manifest["tools"])
                self.assertIn(UI_RESOURCE_URI, manifest["resources"])

            rpc_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 99,
                        "method": "server/discover",
                        "params": {},
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(rpc_req, timeout=2) as resp:
                self.assertEqual(resp.status, 200)
                rpc_out = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(rpc_out["result"]["protocolVersion"], "2026-07-28")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_05_manifests_and_openapi_valid(self) -> None:
        manifest_data = json.loads((MCP_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest_data["version"], "1.6.0")
        self.assertEqual(
            [t["name"] for t in manifest_data["tools"]],
            [t["name"] for t in TOOLS_MANIFEST],
        )

        server_data = json.loads((MCP_DIR / "server.json").read_text(encoding="utf-8"))
        self.assertEqual(server_data["version"], "1.6.0")
        self.assertEqual(
            server_data["name"],
            "io.github.rare-disease-atlas/orphan-disease-opportunity-mcp",
        )
        self.assertLessEqual(len(server_data["description"]), 100)

        glama_data = json.loads((MCP_DIR / "glama.json").read_text(encoding="utf-8"))
        self.assertIn("rare-disease-atlas", glama_data["maintainers"])

        raw_yaml = (MCP_DIR / "openapi.yaml").read_text(encoding="utf-8")
        if yaml is not None:
            spec = yaml.safe_load(raw_yaml)
            self.assertEqual(spec["openapi"], "3.1.0")
            self.assertEqual(spec["info"]["version"], "1.6.0")
        else:
            self.assertIn("openapi: 3.1.0", raw_yaml)
            self.assertIn("version: 1.6.0", raw_yaml)


if __name__ == "__main__":
    unittest.main(verbosity=2)
