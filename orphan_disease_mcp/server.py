#!/usr/bin/env python3
"""
Orphan Disease Opportunity MCP Server (Flagships: Clonal JAK2 V617F+ & Autoimmune Myelofibrosis).

Zero-dependency, read-only Model Context Protocol (MCP 2026-07-28 & 2025-11-25) server supporting:
  1. Standard MCP `stdio` JSON-RPC 2.0 transport (default; works out of the box
     in Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Antigravity, etc.)
  2. MCP `Streamable HTTP` transport (`--transport http --port 8080`), exposing
     `POST /mcp`, `GET /.well-known/mcp.json`, and `GET /health`.

Data source strategy:
  Attempts a fast read-only HTTPS GET from `https://api.rare-disease-atlas.workers.dev/opportunities.json`
  (overridable via `ATLAS_DATA_URL`, disable via `ATLAS_OFFLINE=1`) with TTL caching,
  merging/falling back cleanly to the bundled `data/opportunities.json`.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

SERVER_NAME = "orphan-disease-opportunity-mcp"
SERVER_TITLE = "Orphan Disease Opportunity Atlas MCP"
DEFAULT_LIVE_URL = "https://api.rare-disease-atlas.workers.dev/opportunities.json"
CURRENT_PROTOCOL_VERSION = "2026-07-28"
DEFAULT_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = (
    "2026-07-28",
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)

UI_RESOURCE_URI = "ui://rare-disease-atlas/venture-card"

SERVER_CAPABILITIES: dict[str, Any] = {
    "tools": {"listChanged": False},
    "resources": {"subscribe": False, "listChanged": False},
    "prompts": {"listChanged": False},
    "extensions": {
        "io.modelcontextprotocol/ui": {
            "mimeTypes": ["text/html;profile=mcp-app"],
        }
    },
}

SERVER_INSTRUCTIONS = (
    "Read-only Orphan Disease Venture & Myelofibrosis Opportunity Server "
    "(Flagships: Clonal JAK2 V617F+ Primary Myelofibrosis 'jak2-myelofibrosis' "
    "and Reversible Autoimmune Myelofibrosis 'autoimmune-myelofibrosis'). "
    "Start with search_founder_opportunities, get_disease_case_study, "
    "get_90_day_validation_plan, or search_any_orphan_indication."
)

BACKGROUND_ALIASES: dict[str, str] = {
    "computational-ai-bio": "computational-ai-bio",
    "computational": "computational-ai-bio",
    "ai-bio": "computational-ai-bio",
    "ai": "computational-ai-bio",
    "ml": "computational-ai-bio",
    "bioinformatics": "computational-ai-bio",
    "comp-bio": "computational-ai-bio",
    "techbio": "computational-ai-bio",
    "public-health": "public-health",
    "public_health": "public-health",
    "health-systems": "public-health",
    "clinical": "public-health",
    "epidemiology": "public-health",
    "digital-health": "public-health",
    "rwe": "public-health",
    "venture-novel-financing": "venture-novel-financing",
    "venture": "venture-novel-financing",
    "vc": "venture-novel-financing",
    "novel-financing": "venture-novel-financing",
    "finance": "venture-novel-financing",
    "studio": "venture-novel-financing",
    "biotech-vc": "venture-novel-financing",
    "all": "all",
    "any": "all",
}

CAPITAL_TIER_ALIASES: dict[str, str] = {
    "bootstrapped-grant": "bootstrapped-grant",
    "bootstrap": "bootstrapped-grant",
    "bootstrapped": "bootstrapped-grant",
    "grant": "bootstrapped-grant",
    "low": "bootstrapped-grant",
    "<250k": "bootstrapped-grant",
    "pre-seed": "bootstrapped-grant",
    "seed": "seed",
    "medium": "seed",
    "series-a-platform": "series-a-platform",
    "series-a": "series-a-platform",
    "platform": "series-a-platform",
    "high": "series-a-platform",
    "all": "all",
    "any": "all",
}

DISEASE_ID_ALIASES: dict[str, str] = {
    "jak2-myelofibrosis": "jak2-myelofibrosis",
    "myelofibrosis": "jak2-myelofibrosis",
    "jak2": "jak2-myelofibrosis",
    "jak2-v617f": "jak2-myelofibrosis",
    "pmf": "jak2-myelofibrosis",
    "mpn": "jak2-myelofibrosis",
    "autoimmune-myelofibrosis": "autoimmune-myelofibrosis",
    "aimf": "autoimmune-myelofibrosis",
    "lupus-myelofibrosis": "autoimmune-myelofibrosis",
    "sle-myelofibrosis": "autoimmune-myelofibrosis",
    "vexas-syndrome": "vexas-syndrome",
    "vexas": "vexas-syndrome",
    "uba1": "vexas-syndrome",
    "castleman-disease": "castleman-disease",
    "castleman": "castleman-disease",
    "imcd": "castleman-disease",
    "tafro": "castleman-disease",
    "systemic-mastocytosis": "systemic-mastocytosis",
    "mastocytosis": "systemic-mastocytosis",
    "kit-d816v": "systemic-mastocytosis",
    "telomere-biology-disorders": "telomere-biology-disorders",
    "telomere": "telomere-biology-disorders",
    "tbd": "telomere-biology-disorders",
    "dyskeratosis-congenita": "telomere-biology-disorders",
    "papd5": "telomere-biology-disorders",
    "all": "all",
    "any": "all",
}

GRANT_TRACK_ALIASES: dict[str, str] = {
    "all": "all",
    "any": "all",
    "sbir-sttr": "sbir-sttr",
    "sbir": "sbir-sttr",
    "sttr": "sbir-sttr",
    "nih": "sbir-sttr",
    "foundation": "foundation",
    "philanthropy": "foundation",
    "mpnrf": "foundation",
    "venture-philanthropy": "venture-philanthropy",
    "lls": "venture-philanthropy",
    "lls-tap": "venture-philanthropy",
    "federal-translational": "federal-translational",
    "arpa-h": "federal-translational",
    "regulatory-orphan": "regulatory-orphan",
    "fda": "regulatory-orphan",
    "orphan": "regulatory-orphan",
}

_UI_META: dict[str, Any] = {"ui": {"resourceUri": UI_RESOURCE_URI}}
_ANNOTATIONS_CURATED: dict[str, Any] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
_ANNOTATIONS_LIVE: dict[str, Any] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

VENTURE_CARD_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rare Disease Venture Atlas — Myelofibrosis &amp; Orphan Diligence Card</title>
<style>
  body{margin:0;padding:14px;font:13px/1.45 system-ui,-apple-system,sans-serif;background:#0b1120;color:#e2e8f0}
  .hdr{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:8px;margin-bottom:10px}
  .badge{background:#0f766e;color:#ccfbf1;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
  .card{background:#111827;border:1px solid #1f2937;border-radius:8px;padding:10px;margin-bottom:8px}
  .title{font-weight:600;color:#38bdf8;margin-bottom:4px}
  .meta{font-size:11px;color:#94a3b8}
</style></head>
<body>
  <div class="hdr"><strong>Rare Disease Venture Atlas (JAK2+ &amp; Autoimmune MF)</strong><span class="badge" id="status">Ready</span></div>
  <div id="root"><div class="meta">Awaiting read-only MCP tool structuredContent…</div></div>
  <script>
    function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
    function render(data){
      const el=document.getElementById("root"),st=document.getElementById("status");
      if(!data||typeof data!=="object")return;
      if(Array.isArray(data.opportunities)){
        st.textContent=data.matched_count+" Blueprints";
        el.innerHTML=data.opportunities.slice(0,6).map(o=>'<div class="card"><div class="title">'+esc(o.title)+'</div><div class="meta">'+esc(o.disease_id)+' · '+esc(o.capital_range_usd)+' · wet_lab='+esc(o.wet_lab_required)+'</div></div>').join("");
      }else if(data.roadmap_30_60_90){
        st.textContent=data.disease_id||"90-Day Plan";
        const r=data.roadmap_30_60_90;
        el.innerHTML=["days_1_to_30","days_31_to_60","days_61_to_90"].map(k=>'<div class="card"><div class="title">'+esc(k.replace(/_/g," ").toUpperCase())+'</div><div class="meta">'+esc((r[k]||[]).join(" • "))+'</div></div>').join("");
      }else if(data.live_diligence){
        const d=data.live_diligence;
        st.textContent=d.mondo_id||"Live 7K Scan";
        const t=(d.top_associated_targets||[]).map(x=>esc(x.symbol)+" ("+esc(x.score)+")").join(", ")||"Curated benchmark";
        const tr=(d.clinical_trials||[]).slice(0,4).map(c=>'<div class="card"><div class="title">'+esc(c.nct_id)+' ['+esc(c.status)+']</div><div class="meta">'+esc(c.title)+'</div></div>').join("");
        el.innerHTML='<div class="card"><div class="title">'+esc(d.resolved_name||data.query)+'</div><div class="meta">Top Targets: '+t+' · PubMed: '+esc(d.pubmed_total_count??"N/A")+'</div></div>'+tr;
      }else if(data.case_study){
        st.textContent=data.disease_id||"Case Study";
        el.innerHTML='<div class="card"><div class="title">'+esc(data.case_study.name||data.disease_id)+'</div><div class="meta">'+esc(data.case_study.biological_tractability?.causal_mechanism||"")+'</div></div>';
      }else if(Array.isArray(data.grants)){
        st.textContent=data.grant_count+" Grants";
        el.innerHTML=data.grants.slice(0,6).map(g=>'<div class="card"><div class="title">'+esc(g.name)+'</div><div class="meta">'+esc(g.typical_award_usd)+' · '+esc(g.equity_dilution)+'</div></div>').join("");
      }else if(Array.isArray(data.ethical_discovery_guidelines)){
        st.textContent=data.disease_id||"Validation";
        el.innerHTML=data.ethical_discovery_guidelines.slice(0,5).map(g=>'<div class="card"><div class="meta">'+esc(g)+'</div></div>').join("");
      }
    }
    window.addEventListener("message",ev=>{
      const m=ev.data;
      const sc=m?.params?.structuredContent||m?.structuredContent||m?.result?.structuredContent||window.openai?.toolOutput;
      if(sc)render(sc);
    });
    if(window.openai?.toolOutput)render(window.openai.toolOutput);
  </script>
</body></html>
"""


class AtlasRepository:
    """Loads opportunity & disease briefing data with live fetch + bundled fallback."""

    def __init__(
        self,
        bundled_path: Path | None = None,
        live_url: str | None = None,
        cache_ttl_seconds: float = 300.0,
        timeout_seconds: float = 2.5,
    ) -> None:
        if bundled_path is None:
            repo_data = Path(__file__).resolve().parent.parent / "data" / "opportunities.json"
            pkg_data = Path(__file__).resolve().parent / "data" / "opportunities.json"
            bundled_path = repo_data if repo_data.exists() else pkg_data
        self.bundled_path = bundled_path
        self.live_url = DEFAULT_LIVE_URL if live_url is None else live_url
        if live_url is None and "ATLAS_DATA_URL" in os.environ:
            self.live_url = os.environ["ATLAS_DATA_URL"]
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cached_payload: dict[str, Any] | None = None
        self._cached_source: str = "bundled_fallback"
        self._cache_timestamp: float = 0.0

    def load_bundled(self) -> dict[str, Any]:
        with self.bundled_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def get_atlas(self) -> tuple[dict[str, Any], str]:
        now = time.monotonic()
        if (
            self._cached_payload is not None
            and (now - self._cache_timestamp) < self.cache_ttl_seconds
        ):
            return self._cached_payload, self._cached_source

        bundled = self.load_bundled()
        offline_mode = os.environ.get("ATLAS_OFFLINE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if offline_mode or not self.live_url:
            self._cached_payload = bundled
            self._cached_source = "bundled_fallback"
            self._cache_timestamp = now
            return bundled, "bundled_fallback"

        try:
            req = urllib.request.Request(
                self.live_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"{SERVER_NAME}/{__version__} (+https://rare-disease-atlas.github.io)",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if 200 <= resp.status < 300:
                    raw = json.loads(resp.read().decode("utf-8"))
                    merged = self._merge_live_with_bundled(raw, bundled)
                    self._cached_payload = merged
                    self._cached_source = "live"
                    self._cache_timestamp = now
                    return merged, "live"
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            pass

        self._cached_payload = bundled
        self._cached_source = "bundled_fallback"
        self._cache_timestamp = now
        return bundled, "bundled_fallback"

    @staticmethod
    def _merge_live_with_bundled(
        live_raw: Any, bundled: dict[str, Any]
    ) -> dict[str, Any]:
        """Normalizes live JSON while preserving rich bundled sections if omitted."""
        merged = dict(bundled)
        if isinstance(live_raw, list):
            merged["opportunities"] = live_raw
            return merged
        if isinstance(live_raw, dict):
            for key, value in live_raw.items():
                if value is not None:
                    merged[key] = value
        return merged


TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "search_founder_opportunities",
        "title": "Search Orphan Venture Blueprints",
        "description": (
            "Search startup blueprints anchored on Clonal JAK2+ & Autoimmune Myelofibrosis "
            "(plus 4 adjacent cohorts) by track, capital, and wet-lab need."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "background": {
                    "type": "string",
                    "description": "Founder track",
                    "default": "all",
                },
                "capital_tier": {
                    "type": "string",
                    "description": "Budget tier",
                    "default": "all",
                },
                "wet_lab_required": {
                    "type": "boolean",
                    "description": "Wet-lab filter",
                },
                "disease_id": {
                    "type": "string",
                    "description": "Disease slug",
                    "default": "all",
                },
            },
            "additionalProperties": False,
            "examples": [
                {"background": "computational-ai-bio", "wet_lab_required": False}
            ],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "matched_count": {"type": "integer"},
                "opportunities": {"type": "array"},
            },
            "required": ["matched_count", "opportunities"],
        },
        "annotations": _ANNOTATIONS_CURATED,
        "_meta": _UI_META,
    },
    {
        "name": "get_disease_case_study",
        "title": "Get Myelofibrosis & Orphan Case Study",
        "description": (
            "Retrieve curated biology, NCT trials, GEO/PDB datasets, and failure modes "
            "(Flagships: 'jak2-myelofibrosis' and 'autoimmune-myelofibrosis')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease slug",
                    "default": "jak2-myelofibrosis",
                }
            },
            "additionalProperties": False,
            "examples": [{"disease_id": "jak2-myelofibrosis"}],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {"type": "string"},
                "case_study": {"type": "object"},
            },
            "required": ["disease_id"],
        },
        "annotations": _ANNOTATIONS_CURATED,
        "_meta": _UI_META,
    },
    {
        "name": "list_non_dilutive_grants",
        "title": "List Non-Dilutive Orphan Grants",
        "description": (
            "List NIH/NCI SBIR, MPNRF, LLS TAP, CDCN, ARPA-H, and FDA Orphan grants "
            "for Myelofibrosis and rare disease ventures."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "track": {
                    "type": "string",
                    "description": "Grant track",
                    "default": "all",
                }
            },
            "additionalProperties": False,
            "examples": [{"track": "sbir-sttr"}],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "grant_count": {"type": "integer"},
                "grants": {"type": "array"},
            },
            "required": ["grant_count", "grants"],
        },
        "annotations": _ANNOTATIONS_CURATED,
        "_meta": _UI_META,
    },
    {
        "name": "get_validation_communities",
        "title": "Get Validation Registries & Guardrails",
        "description": (
            "Retrieve registries, biobanks, patient foundations, and non-extractive "
            "research guardrails for Myelofibrosis and rare diseases."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease slug",
                    "default": "jak2-myelofibrosis",
                }
            },
            "additionalProperties": False,
            "examples": [{"disease_id": "autoimmune-myelofibrosis"}],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {"type": "string"},
                "ethical_discovery_guidelines": {"type": "array"},
            },
            "required": ["disease_id"],
        },
        "annotations": _ANNOTATIONS_CURATED,
        "_meta": _UI_META,
    },
    {
        "name": "get_90_day_validation_plan",
        "title": "Get 90-Day Diligence Roadmap",
        "description": (
            "Retrieve a structured 30/60/90-day diligence roadmap contrasting "
            "Clonal JAK2+ vs Autoimmune Myelofibrosis (plus 4 adjacent cohorts)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease slug",
                    "default": "jak2-myelofibrosis",
                },
                "background": {
                    "type": "string",
                    "description": "Founder track",
                    "default": "computational-ai-bio",
                },
                "capital_tier": {
                    "type": "string",
                    "description": "Budget tier",
                    "default": "bootstrapped-grant",
                },
            },
            "additionalProperties": False,
            "examples": [{"disease_id": "jak2-myelofibrosis"}],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "disease_id": {"type": "string"},
                "roadmap_30_60_90": {"type": "object"},
            },
            "required": ["disease_id", "roadmap_30_60_90"],
        },
        "annotations": _ANNOTATIONS_CURATED,
        "_meta": _UI_META,
    },
    {
        "name": "search_any_orphan_indication",
        "title": "Search Any of 7,000+ Orphan Diseases (Live)",
        "description": (
            "Search live OpenTargets, ClinicalTrials.gov v2, and PubMed evidence "
            "for any rare disease, benchmarked against JAK2+ & Autoimmune Myelofibrosis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "disease_query": {
                    "type": "string",
                    "description": "Disease query",
                },
                "founder_background": {
                    "type": "string",
                    "description": "Founder track",
                    "default": "all",
                },
            },
            "required": ["disease_query"],
            "additionalProperties": False,
            "examples": [{"disease_query": "autoimmune myelofibrosis"}],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "live_diligence": {"type": "object"},
            },
            "required": ["query", "live_diligence"],
        },
        "annotations": _ANNOTATIONS_LIVE,
        "_meta": _UI_META,
    },
]

RESOURCES_MANIFEST: list[dict[str, Any]] = [
    {
        "uri": "briefing://rare-disease-playbook/jak2-myelofibrosis",
        "name": "JAK2+ Myelofibrosis",
        "description": "Clonal JAK2 V617F JH2 biology, trials, and wedges.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "briefing://rare-disease-playbook/autoimmune-myelofibrosis",
        "name": "Autoimmune Myelofibrosis",
        "description": "Reversible lupus/AIMF fibrosis and iron triage.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "briefing://rare-disease-playbook/hematology-immunology-expansion",
        "name": "Adjacent Orphan Cohorts",
        "description": "VEXAS, Castleman, Mastocytosis, and Telomere wedges.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "briefing://rare-disease-playbook/non-dilutive-grants",
        "name": "Non-Dilutive Grants",
        "description": "SBIR, ARPA-H, MPNRF, LLS TAP, and FDA Orphan grants.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "briefing://rare-disease-playbook/validation-ethics",
        "name": "Validation Guardrails",
        "description": "Registries, biobanks, and ethical discovery rules.",
        "mimeType": "text/markdown",
    },
    {
        "uri": UI_RESOURCE_URI,
        "name": "Orphan Venture Card",
        "description": "Interactive MCP App HTML card for venture results.",
        "mimeType": "text/html;profile=mcp-app",
    },
]

RESOURCE_TEMPLATES_MANIFEST: list[dict[str, Any]] = [
    {
        "uriTemplate": "briefing://rare-disease-playbook/{disease_id}",
        "name": "Rare Disease Venture Playbook by Indication",
        "description": "Retrieve the markdown venture briefing for any curated disease_id (Flagships: jak2-myelofibrosis, autoimmune-myelofibrosis).",
        "mimeType": "text/markdown",
    }
]

PROMPTS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "evaluate-rare-disease-venture",
        "description": (
            "Retrieve a 90-day orphan venture diligence workflow anchored on "
            "Clonal JAK2 V617F+ and Autoimmune Myelofibrosis."
        ),
        "arguments": [
            {
                "name": "founder_background",
                "description": "computational-ai-bio, public-health, or venture-novel-financing",
                "required": False,
            },
            {
                "name": "capital_budget",
                "description": "bootstrapped-grant, seed, or series-a-platform",
                "required": False,
            },
            {
                "name": "wet_lab_access",
                "description": "'true' or 'false' for internal wet-lab access",
                "required": False,
            },
        ],
    }
]


class OrphanDiseaseMCPServer:
    """Core read-only MCP protocol handler independent of wire transport."""

    def __init__(self, repository: AtlasRepository | None = None) -> None:
        self.repo = repository or AtlasRepository()

    def handle_jsonrpc(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single JSON-RPC 2.0 request or notification."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._error_response(
                message.get("id") if isinstance(message, dict) else None,
                -32600,
                "Invalid JSON-RPC 2.0 request.",
            )

        method = message.get("method")
        req_id = message.get("id")
        is_notification = "id" not in message
        params = message.get("params") or {}

        if is_notification:
            return None

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "server/discover":
                result = self._handle_discover()
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS_MANIFEST}
            elif method == "tools/call":
                result = self._handle_tool_call(params)
            elif method == "resources/list":
                result = {"resources": RESOURCES_MANIFEST}
            elif method == "resources/templates/list":
                result = {"resourceTemplates": RESOURCE_TEMPLATES_MANIFEST}
            elif method == "resources/read":
                result = self._handle_resource_read(params)
            elif method == "prompts/list":
                result = {"prompts": PROMPTS_MANIFEST}
            elif method == "prompts/get":
                result = self._handle_prompt_get(params)
            else:
                return self._error_response(
                    req_id, -32601, f"Method not found: {method}"
                )
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except ValueError as exc:
            return self._error_response(req_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._error_response(req_id, -32603, f"Internal error: {exc}")

    @staticmethod
    def _error_response(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
        requested = params.get("protocolVersion")
        if (
            requested == CURRENT_PROTOCOL_VERSION
            or meta.get("io.modelcontextprotocol/protocolVersion")
            == CURRENT_PROTOCOL_VERSION
        ):
            negotiated = CURRENT_PROTOCOL_VERSION
        else:
            negotiated = DEFAULT_PROTOCOL_VERSION

        return {
            "protocolVersion": negotiated,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": {
                "name": SERVER_NAME,
                "title": SERVER_TITLE,
                "version": __version__,
            },
            "instructions": SERVER_INSTRUCTIONS,
        }

    def _handle_discover(self) -> dict[str, Any]:
        return {
            "protocolVersion": CURRENT_PROTOCOL_VERSION,
            "serverInfo": {
                "name": SERVER_NAME,
                "title": SERVER_TITLE,
                "version": __version__,
            },
            "capabilities": SERVER_CAPABILITIES,
            "instructions": SERVER_INSTRUCTIONS,
            "tools": TOOLS_MANIFEST,
            "resources": RESOURCES_MANIFEST,
            "prompts": PROMPTS_MANIFEST,
        }

    def _handle_tool_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise ValueError("Tool 'arguments' must be a JSON object.")

        if name in ("search_founder_opportunities", "match_founder_opportunities"):
            payload = self.tool_search_founder_opportunities(
                background=args.get("background", "all"),
                capital_tier=args.get("capital_tier", "all"),
                wet_lab_required=args.get("wet_lab_required"),
                disease_id=args.get("disease_id", "all"),
            )
        elif name == "get_disease_case_study":
            payload = self.tool_get_disease_case_study(
                disease_id=args.get("disease_id", "jak2-myelofibrosis")
            )
        elif name in ("list_non_dilutive_grants", "find_non_dilutive_grants"):
            payload = self.tool_list_non_dilutive_grants(
                track=args.get("track", "all")
            )
        elif name == "get_validation_communities":
            payload = self.tool_get_validation_communities(
                disease_id=args.get("disease_id", "jak2-myelofibrosis")
            )
        elif name in ("get_90_day_validation_plan", "generate_90_day_validation_plan"):
            payload = self.tool_get_90_day_validation_plan(
                disease_id=args.get("disease_id", "jak2-myelofibrosis"),
                background=args.get(
                    "background",
                    args.get("founder_background", "computational-ai-bio"),
                ),
                capital_tier=args.get(
                    "capital_tier",
                    args.get("capital_budget", "bootstrapped-grant"),
                ),
            )
        elif name in (
            "search_any_orphan_indication",
            "analyze_any_orphan_indication",
        ):
            payload = self.tool_search_any_orphan_indication(
                disease_query=str(
                    args.get("disease_query") or args.get("disease_id") or ""
                ),
                founder_background=str(
                    args.get("founder_background", args.get("background", "all"))
                ),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        is_err = bool(payload.get("error"))
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2),
                }
            ],
            "structuredContent": payload,
            "isError": is_err,
        }

    # ------------------------------------------------------------------
    # Tool implementations (100% read-only)
    # ------------------------------------------------------------------

    @staticmethod
    def _scrub_pii(text: str) -> str:
        """Strip accidental email addresses or phone numbers from search strings."""
        cleaned = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "[redacted-email]",
            text,
        )
        cleaned = re.sub(
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "[redacted-phone]",
            cleaned,
        )
        return cleaned.strip()[:200]

    @staticmethod
    def _paired_myelofibrosis_benchmark() -> dict[str, Any]:
        return {
            "clonal_jak2_myelofibrosis": {
                "disease_id": "jak2-myelofibrosis",
                "driver": "Somatic JAK2 V617F JH2 pseudokinase mutation (~50-60% of PMF)",
                "key_gap": "Type I JH1 JAK inhibitors cause cytopenias with <15% marrow fibrosis reversal and 11-23 month post-ruxolitinib median survival.",
            },
            "reversible_autoimmune_myelofibrosis": {
                "disease_id": "autoimmune-myelofibrosis",
                "driver": "JAK2/CALR/MPL-negative lupus/autoimmune marrow fibrosis + IL-6/hepcidin/ferroportin iron block",
                "positive_control": "74-80% human MF-2/MF-3 reticulin resolution on targeted immunomodulation (Gangat et al., Mayo Clinic 2024).",
            },
        }

    def tool_search_founder_opportunities(
        self,
        background: str = "all",
        capital_tier: str = "all",
        wet_lab_required: bool | None = None,
        disease_id: str = "all",
    ) -> dict[str, Any]:
        atlas, data_source = self.repo.get_atlas()
        raw_opps = atlas.get("opportunities", [])

        norm_bg = BACKGROUND_ALIASES.get(
            str(background).strip().lower(), str(background).strip().lower()
        )
        norm_cap = CAPITAL_TIER_ALIASES.get(
            str(capital_tier).strip().lower(), str(capital_tier).strip().lower()
        )
        norm_dis = DISEASE_ID_ALIASES.get(
            str(disease_id).strip().lower(), str(disease_id).strip().lower()
        )

        matched: list[dict[str, Any]] = []
        for opp in raw_opps:
            opp_bgs = [b.lower() for b in opp.get("backgrounds", [])]
            if norm_bg not in ("all", "") and opp_bgs and norm_bg not in opp_bgs:
                continue

            opp_cap = str(opp.get("capital_tier", "")).lower()
            if norm_cap not in ("all", "") and opp_cap and opp_cap != norm_cap:
                continue

            if norm_dis not in ("all", ""):
                if str(opp.get("disease_id", "")).lower() != norm_dis:
                    continue

            if wet_lab_required is not None:
                opp_wet = bool(opp.get("wet_lab_required", False))
                if opp_wet != bool(wet_lab_required):
                    continue

            matched.append(opp)

        flagship_count = sum(
            1
            for o in matched
            if o.get("disease_id")
            in ("jak2-myelofibrosis", "autoimmune-myelofibrosis")
        )

        return {
            "atlas_name": atlas.get("atlas_name"),
            "data_source": data_source,
            "canonical_url": atlas.get("canonical_url", DEFAULT_LIVE_URL),
            "filters_applied": {
                "background": norm_bg,
                "capital_tier": norm_cap,
                "wet_lab_required": wet_lab_required,
                "disease_id": norm_dis,
            },
            "flagship_myelofibrosis_count": flagship_count,
            "matched_count": len(matched),
            "opportunities": matched,
            "next_recommended_calls": [
                "get_disease_case_study(disease_id='jak2-myelofibrosis')",
                "get_disease_case_study(disease_id='autoimmune-myelofibrosis')",
                "get_90_day_validation_plan(disease_id='jak2-myelofibrosis')",
                "list_non_dilutive_grants(track='all')",
            ],
        }

    tool_match_founder_opportunities = tool_search_founder_opportunities

    def tool_get_disease_case_study(
        self, disease_id: str = "jak2-myelofibrosis"
    ) -> dict[str, Any]:
        atlas, data_source = self.repo.get_atlas()
        norm_id = DISEASE_ID_ALIASES.get(
            str(disease_id).strip().lower(), str(disease_id).strip().lower()
        )
        studies = atlas.get("case_studies", {})
        study = studies.get(norm_id)
        if not study:
            return {
                "disease_id": norm_id,
                "error": f"Disease '{disease_id}' is not in the curated case studies.",
                "available_disease_ids": list(studies.keys()),
                "tip": "Call search_any_orphan_indication(disease_query=...) to query live OpenTargets, ClinicalTrials.gov v2, and PubMed for any of 7,000+ orphan diseases.",
            }
        return {
            "disease_id": norm_id,
            "data_source": data_source,
            "case_study": study,
        }

    def tool_list_non_dilutive_grants(self, track: str = "all") -> dict[str, Any]:
        atlas, data_source = self.repo.get_atlas()
        norm_track = GRANT_TRACK_ALIASES.get(
            str(track).strip().lower(), str(track).strip().lower()
        )
        all_grants = atlas.get("non_dilutive_grants", [])
        if norm_track in ("all", ""):
            filtered = all_grants
        else:
            filtered = [
                g
                for g in all_grants
                if str(g.get("track", "")).lower() == norm_track
            ]
        return {
            "data_source": data_source,
            "track_filter": norm_track,
            "available_tracks": [
                "sbir-sttr",
                "foundation",
                "venture-philanthropy",
                "regulatory-orphan",
                "federal-translational",
            ],
            "grant_count": len(filtered),
            "grants": filtered,
            "capital_stacking_strategy": (
                "Pair an MPNRF Challenge Grant ($100K-$300K) + NCI/NHLBI Phase I SBIR "
                "($400K, 0% dilution) on JAK2 V617F JH2 or AIMF fibrosis-reversal data "
                "before scaling via LLS TAP or ARPA-H."
            ),
        }

    tool_find_non_dilutive_grants = tool_list_non_dilutive_grants

    def tool_get_validation_communities(
        self, disease_id: str = "jak2-myelofibrosis"
    ) -> dict[str, Any]:
        atlas, data_source = self.repo.get_atlas()
        norm_id = DISEASE_ID_ALIASES.get(
            str(disease_id).strip().lower(), str(disease_id).strip().lower()
        )
        communities_map = atlas.get("validation_communities", {})
        entry = communities_map.get(norm_id)
        if not entry:
            return {
                "disease_id": norm_id,
                "ethical_discovery_guidelines": [],
                "error": f"No validation communities found for '{disease_id}'.",
                "available_disease_ids": list(communities_map.keys()),
            }
        return {
            "data_source": data_source,
            "disease_id": norm_id,
            **entry,
        }

    def tool_get_90_day_validation_plan(
        self,
        disease_id: str = "jak2-myelofibrosis",
        background: str = "computational-ai-bio",
        capital_tier: str = "bootstrapped-grant",
    ) -> dict[str, Any]:
        atlas, data_source = self.repo.get_atlas()
        norm_id = DISEASE_ID_ALIASES.get(
            str(disease_id).strip().lower(), str(disease_id).strip().lower()
        )
        if norm_id in ("all", ""):
            norm_id = "jak2-myelofibrosis"

        norm_bg = BACKGROUND_ALIASES.get(
            str(background).strip().lower(), "computational-ai-bio"
        )
        norm_cap = CAPITAL_TIER_ALIASES.get(
            str(capital_tier).strip().lower(), "bootstrapped-grant"
        )

        studies = atlas.get("case_studies", {})
        study = studies.get(norm_id)
        if not study:
            return {
                "disease_id": norm_id,
                "roadmap_30_60_90": {},
                "error": f"Disease '{disease_id}' is not in the curated 6-cohort atlas.",
                "available_disease_ids": list(studies.keys()),
            }

        disease_opps = [
            o
            for o in atlas.get("opportunities", [])
            if o.get("disease_id") == norm_id
        ]
        track_opps = [
            o
            for o in disease_opps
            if norm_bg == "all" or norm_bg in [b.lower() for b in o.get("backgrounds", [])]
        ] or disease_opps

        raw_ds = study.get("open_datasets_and_tools") or study.get(
            "open_data_infrastructure", []
        )
        datasets = [
            (ds.get("accession") or ds.get("name")) if isinstance(ds, dict) else str(ds)
            for ds in raw_ds[:4]
        ]
        blueprint_milestones: list[str] = []
        for opp in track_opps[:2]:
            for ms in opp.get("first_90_days_milestones", [])[:2]:
                blueprint_milestones.append(ms)

        grants = [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "typical_award_usd": g.get("typical_award_usd"),
                "track": g.get("track"),
            }
            for g in atlas.get("non_dilutive_grants", [])[:4]
        ]
        val_entry = atlas.get("validation_communities", {}).get(norm_id, {})
        guardrails = val_entry.get("ethical_discovery_guidelines", [])[:4]

        roadmap = {
            "days_1_to_30": [
                f"Benchmark {study.get('name')} causal mechanism against Paired Myelofibrosis Flagships (Clonal JAK2 V617F+ PMF vs Reversible Autoimmune MF).",
                f"Ingest and audit open datasets ({', '.join(str(x) for x in datasets if x)}) with zero PHI.",
                blueprint_milestones[0]
                if blueprint_milestones
                else "Execute zero-wet-lab computational or RWE feasibility screen.",
            ],
            "days_31_to_60": [
                blueprint_milestones[1]
                if len(blueprint_milestones) > 1
                else "Complete orthogonal benchmark against Standard-of-Care failure modes and CRO assay quotes.",
                "Conduct clinician & scientific advisory discovery interviews strictly following non-extractive patient guardrails.",
            ],
            "days_61_to_90": [
                "Lock non-dilutive grant aims (NIH SBIR/STTR, MPNRF, LLS TAP, or ARPA-H) and FDA Orphan Designation (OOPD) regulatory briefing.",
                "Evaluate 90-day technical kill/go gates before committing seed dilution.",
            ],
        }

        return {
            "disease_id": norm_id,
            "disease_name": study.get("name"),
            "founder_track": norm_bg,
            "capital_tier": norm_cap,
            "data_source": data_source,
            "paired_myelofibrosis_contrast": self._paired_myelofibrosis_benchmark(),
            "roadmap_30_60_90": roadmap,
            "matched_blueprints": [
                {
                    "id": o.get("id"),
                    "title": o.get("title"),
                    "capital_range_usd": o.get("capital_range_usd"),
                    "wet_lab_required": o.get("wet_lab_required"),
                }
                for o in track_opps[:4]
            ],
            "recommended_grants": grants,
            "ethical_guardrails": guardrails,
        }

    tool_generate_90_day_validation_plan = tool_get_90_day_validation_plan

    def tool_search_any_orphan_indication(
        self,
        disease_query: str,
        founder_background: str = "all",
    ) -> dict[str, Any]:
        q = self._scrub_pii(disease_query)[:120].strip()
        if not q:
            return {
                "query": "",
                "live_diligence": {},
                "error": "Parameter 'disease_query' must not be empty.",
            }

        atlas, data_source = self.repo.get_atlas()
        norm_key = DISEASE_ID_ALIASES.get(q.lower())
        curated_match = (
            norm_key
            if (norm_key and norm_key in atlas.get("case_studies", {}))
            else None
        )
        if not curated_match:
            ql = q.lower()
            for slug, cs in atlas.get("case_studies", {}).items():
                if ql in slug or ql in str(cs.get("name", "")).lower():
                    curated_match = slug
                    break

        offline_mode = os.environ.get("ATLAS_OFFLINE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        live_diligence: dict[str, Any] = {
            "resolved_name": q,
            "mondo_id": None,
            "top_associated_targets": [],
            "total_clinical_trials": 0,
            "clinical_trials": [],
            "pubmed_total_count": 0,
            "recent_pubmed_ids": [],
        }

        if not offline_mode:
            # 1. OpenTargets Platform v4 read-only query
            try:
                ot_query = (
                    "query SearchDisease($q: String!) {"
                    ' search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 1}) {'
                    " hits { id name object { ... on Disease {"
                    " associatedTargets(page: {index: 0, size: 5}) {"
                    " rows { score target { approvedSymbol approvedName } } } } } } } }"
                )
                ot_req = urllib.request.Request(
                    "https://api.platform.opentargets.org/api/v4/graphql",
                    data=json.dumps(
                        {"query": ot_query, "variables": {"q": q}}
                    ).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": f"{SERVER_NAME}/{__version__}",
                    },
                )
                with urllib.request.urlopen(ot_req, timeout=3.0) as resp:
                    ot_data = json.loads(resp.read().decode("utf-8"))
                    hits = (
                        ot_data.get("data", {})
                        .get("search", {})
                        .get("hits", [])
                    )
                    if hits:
                        top_hit = hits[0]
                        live_diligence["mondo_id"] = top_hit.get("id")
                        live_diligence["resolved_name"] = (
                            top_hit.get("name") or q
                        )
                        rows = (
                            (top_hit.get("object") or {})
                            .get("associatedTargets", {})
                            .get("rows", [])
                        )
                        live_diligence["top_associated_targets"] = [
                            {
                                "symbol": r.get("target", {}).get(
                                    "approvedSymbol"
                                ),
                                "name": r.get("target", {}).get("approvedName"),
                                "score": round(float(r.get("score", 0.0)), 3),
                            }
                            for r in rows
                        ]
            except Exception:
                pass

            # 2. ClinicalTrials.gov v2 read-only GET
            try:
                ct_url = (
                    "https://clinicaltrials.gov/api/v2/studies?"
                    f"query.cond={urllib.parse.quote(q)}&pageSize=5&countTotal=true"
                )
                req = urllib.request.Request(
                    ct_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": f"{SERVER_NAME}/{__version__}",
                    },
                )
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    ct = json.loads(resp.read().decode("utf-8"))
                    live_diligence["total_clinical_trials"] = ct.get(
                        "totalCount", len(ct.get("studies", []))
                    )
                    live_diligence["clinical_trials"] = [
                        {
                            "nct_id": s.get("protocolSection", {})
                            .get("identificationModule", {})
                            .get("nctId"),
                            "status": s.get("protocolSection", {})
                            .get("statusModule", {})
                            .get("overallStatus"),
                            "title": s.get("protocolSection", {})
                            .get("identificationModule", {})
                            .get("briefTitle"),
                        }
                        for s in ct.get("studies", [])
                    ]
            except Exception:
                pass

            # 3. PubMed E-utilities read-only GET
            try:
                pm_url = (
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
                    f"db=pubmed&retmode=json&retmax=5&sort=relevance&term={urllib.parse.quote(q)}"
                )
                pm_req = urllib.request.Request(
                    pm_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": f"{SERVER_NAME}/{__version__}",
                    },
                )
                with urllib.request.urlopen(pm_req, timeout=3.0) as resp:
                    pm = json.loads(resp.read().decode("utf-8")).get(
                        "esearchresult", {}
                    )
                    live_diligence["pubmed_total_count"] = int(
                        pm.get("count", 0) or 0
                    )
                    live_diligence["recent_pubmed_ids"] = pm.get("idlist", [])
            except Exception:
                pass

        norm_bg = BACKGROUND_ALIASES.get(founder_background.strip().lower(), "all")
        grants = [
            g
            for g in atlas.get("non_dilutive_grants", [])
            if norm_bg == "all"
            or not g.get("best_for_backgrounds")
            or norm_bg in g.get("best_for_backgrounds", [])
        ]
        return {
            "query": q,
            "data_source": data_source,
            "curated_atlas_match": curated_match,
            "curated_case_study": (
                atlas.get("case_studies", {}).get(curated_match)
                if curated_match
                else None
            ),
            "flagship_myelofibrosis_benchmark": self._paired_myelofibrosis_benchmark(),
            "live_diligence": live_diligence,
            "fda_orphan_unit_economics": {
                "market_exclusivity": "7 years FDA Orphan Drug exclusivity (10 years EMA)",
                "fy2026_pdufa_fee_waiver_usd": "$4,682,003 (100% waived)",
                "clinical_trial_tax_credit": "25% federal QCTE tax credit",
            },
            "matched_grants": grants[:5],
        }

    tool_analyze_any_orphan_indication = tool_search_any_orphan_indication

    # ------------------------------------------------------------------
    # Resources & Prompts
    # ------------------------------------------------------------------

    def _handle_resource_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = str(params.get("uri", "")).strip()
        if uri == UI_RESOURCE_URI:
            return {
                "contents": [
                    {
                        "uri": UI_RESOURCE_URI,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": VENTURE_CARD_HTML,
                        "_meta": {
                            "ui": {
                                "csp": {
                                    "connectDomains": [],
                                    "resourceDomains": [],
                                }
                            }
                        },
                    }
                ]
            }

        prefix = "briefing://rare-disease-playbook/"
        if not uri.startswith(prefix):
            raise ValueError(f"Unsupported resource URI: {uri}")

        slug = uri[len(prefix) :].strip("/") or "jak2-myelofibrosis"
        atlas, data_source = self.repo.get_atlas()

        if slug == "hematology-immunology-expansion":
            md = self._render_expansion_markdown(atlas, data_source)
        elif slug == "non-dilutive-grants":
            md = self._render_grants_markdown(atlas, data_source)
        elif slug == "validation-ethics":
            md = self._render_validation_markdown(atlas, data_source)
        else:
            norm_id = DISEASE_ID_ALIASES.get(slug.lower(), slug.lower())
            study = atlas.get("case_studies", {}).get(norm_id)
            if not study:
                available = list(atlas.get("case_studies", {}).keys())
                raise ValueError(
                    f"Playbook not found for '{slug}'. Available: {', '.join(available)}"
                )
            md = self._render_playbook_markdown(atlas, study, data_source)

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/markdown",
                    "text": md,
                }
            ]
        }

    @staticmethod
    def _render_expansion_markdown(atlas: dict[str, Any], data_source: str) -> str:
        lines = [
            "# Adjacent Orphan Hematology & Immunology Cohorts (Benchmarked vs Myelofibrosis Flagships)",
            f"_Source: {atlas.get('canonical_url', DEFAULT_LIVE_URL)} ({data_source})_",
            "",
            "Anchored on Flagships **Clonal JAK2 V617F+ Primary Myelofibrosis (`jak2-myelofibrosis`)** and **Reversible Autoimmune Myelofibrosis (`autoimmune-myelofibrosis`)**, this playbook summarizes the 4 adjacent comparative cohorts:",
            "",
        ]
        for slug in (
            "vexas-syndrome",
            "castleman-disease",
            "systemic-mastocytosis",
            "telomere-biology-disorders",
        ):
            cs = atlas.get("case_studies", {}).get(slug, {})
            if cs:
                epi = cs.get("epidemiology", {})
                prev = epi.get("us_prevalence_estimate") or epi.get("us_prevalence", "")
                lines.append(f"## {cs.get('name', slug)} (`{slug}`)")
                lines.append(
                    f"- **Causal Mechanism:** {cs.get('biological_tractability', {}).get('causal_mechanism', '')}"
                )
                lines.append(f"- **US Prevalence:** {prev}")
                lines.append("")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_grants_markdown(atlas: dict[str, Any], data_source: str) -> str:
        lines = [
            "# Orphan Disease Non-Dilutive Capital Stack (Myelofibrosis & Rare Hematology)",
            f"_Source: {atlas.get('canonical_url', DEFAULT_LIVE_URL)} ({data_source})_",
            "",
        ]
        for g in atlas.get("non_dilutive_grants", []):
            lines.append(
                f"- **{g.get('name')}** (`{g.get('track')}`): {g.get('typical_award_usd')} — {g.get('equity_dilution')}"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_validation_markdown(atlas: dict[str, Any], data_source: str) -> str:
        lines = [
            "# Validation Registries, Biobanks & Non-Extractive Research Guardrails",
            f"_Source: {atlas.get('canonical_url', DEFAULT_LIVE_URL)} ({data_source})_",
            "",
        ]
        for slug, entry in atlas.get("validation_communities", {}).items():
            lines.append(f"## `{slug}`")
            for rule in entry.get("ethical_discovery_guidelines", []):
                lines.append(f"- {rule}")
            lines.append("")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_playbook_markdown(
        atlas: dict[str, Any], study: dict[str, Any], data_source: str
    ) -> str:
        opps = [
            o
            for o in atlas.get("opportunities", [])
            if o.get("disease_id") == study.get("disease_id")
        ]
        grants = atlas.get("non_dilutive_grants", [])
        val = atlas.get("validation_communities", {}).get(study.get("disease_id"), {})

        epi = study.get("epidemiology", {})
        bio = study.get("biological_tractability", {})
        soc = study.get("standard_of_care_failure_modes", {})
        reg = study.get("regulatory_and_commercial_incentives") or {}
        us_prev = epi.get("us_prevalence_estimate") or epi.get("us_prevalence", "Rare orphan cohort")

        lines = [
            f"# {study.get('name', study.get('disease_id'))} — Venture & Translational Playbook",
            f"_Source: {atlas.get('canonical_url', DEFAULT_LIVE_URL)} ({data_source})_",
            "",
            "## 1. Why This Orphan Indication Is Uniquely Tractable Right Now",
            f"- **Causal Driver:** {bio.get('causal_mechanism', '')}",
            f"- **US Prevalence:** {us_prev}",
            f"- **Clinical Trajectory:** {epi.get('median_survival', 'High unmet need')}",
            "",
            "### Structural & Translational Anchors",
        ]
        tract_bullets = bio.get("why_highly_tractable_now") or bio.get(
            "why_invaluable_for_builders", []
        )
        if isinstance(tract_bullets, str):
            lines.append(f"- {tract_bullets}")
        else:
            for bullet in tract_bullets:
                lines.append(f"- {bullet}")

        lines.extend(["", "## 2. Standard-of-Care Failure Modes"])
        for mode in soc.get("core_failure_mechanisms", []):
            lines.append(f"- {mode}")

        lines.extend(["", "## 3. FDA Orphan Drug & Commercial Economics"])
        fda_bullets = reg.get("fda_orphan_drug_act") or [
            "7-year US FDA Orphan Drug market exclusivity (10 years EMA)",
            "100% waiver of FY2026 PDUFA application fee ($4,682,003) + 25% federal QCTE clinical trial tax credit",
        ]
        for inc in fda_bullets:
            lines.append(f"- {inc}")
        if reg.get("trial_efficiency"):
            lines.append(f"- **Pivotal Trial Efficiency:** {reg['trial_efficiency']}")
        if reg.get("commercial_precedents"):
            lines.append(f"- **M&A Benchmarks:** {reg['commercial_precedents']}")

        lines.extend(["", "## 4. High-Conviction Founder Blueprints"])
        for opp in opps:
            lines.append(
                f"### {opp['title']} (`{opp['id']}`)\n"
                f"- **Tracks:** {', '.join(opp['backgrounds'])} | **Capital Tier:** `{opp['capital_tier']}` ({opp['capital_range_usd']}) | **Internal Wet Lab Required:** `{opp['wet_lab_required']}`\n"
                f"- **Wedge:** {opp['problem_wedge']}\n"
                f"- **Blueprint:** {opp['solution_blueprint']}"
            )

        lines.extend(["", "## 5. Non-Dilutive & Venture-Philanthropy Capital Stack"])
        for g in grants:
            lines.append(
                f"- **{g['name']}** (`{g['track']}`): {g['typical_award_usd']} — {g['equity_dilution']}"
            )

        lines.extend(["", "## 6. Ethical Patient & Clinical Validation Rules"])
        for rule in val.get("ethical_discovery_guidelines", []):
            lines.append(f"- {rule}")

        return "\n".join(lines) + "\n"

    def _handle_prompt_get(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if name != "evaluate-rare-disease-venture":
            raise ValueError(f"Unknown prompt: {name}")

        args = params.get("arguments") or {}
        bg = args.get("founder_background", "computational-ai-bio")
        budget = args.get("capital_budget", "bootstrapped-grant")
        wet_lab = args.get("wet_lab_access", "false")

        prompt_text = (
            f"You are evaluating a high-impact biotech, AI-bio, or public-health orphan venture "
            f"for a founder team with background='{bg}', capital_budget='{budget}', and "
            f"internal_wet_lab_access={wet_lab}.\n\n"
            f"Step 1: Call `search_founder_opportunities(background='{bg}', capital_tier='{budget}', "
            f"wet_lab_required={str(wet_lab).lower() == 'true'})` to retrieve tailored startup blueprints.\n"
            f"Step 2: Call `get_disease_case_study(disease_id='jak2-myelofibrosis')` and "
            f"`get_disease_case_study(disease_id='autoimmune-myelofibrosis')` to contrast Clonal JAK2 V617F+ "
            f"JH2 biology against Reversible Autoimmune Myelofibrosis (74-80% human reticulin resolution).\n"
            f"Step 3: Call `get_90_day_validation_plan(disease_id='jak2-myelofibrosis', background='{bg}', capital_tier='{budget}')`, "
            f"`list_non_dilutive_grants(track='all')`, and `get_validation_communities(disease_id='jak2-myelofibrosis')`.\n"
            f"Step 4: Present a concise 30/60/90-day diligence summary respecting non-extractive patient discovery guardrails."
        )
        return {
            "description": "90-day translational & venture diligence workflow for JAK2+ & Autoimmune Myelofibrosis",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_text,
                    },
                }
            ],
        }


# ----------------------------------------------------------------------
# Transports: 1) stdio (newline-delimited + Content-Length compatible)
#             2) Streamable HTTP (POST /mcp + GET /.well-known/mcp.json)
# ----------------------------------------------------------------------


def run_stdio(mcp_server: OrphanDiseaseMCPServer) -> None:
    """Run standard MCP stdio loop supporting newline-delimited JSON-RPC 2.0."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        line = stdin.readline()
        if not line:
            break

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower().startswith(b"content-length:"):
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                hdr = stdin.readline()
                if not hdr or hdr in (b"\r\n", b"\n"):
                    break
            body = stdin.read(length)
            raw_text = body.decode("utf-8")
        else:
            raw_text = stripped.decode("utf-8")

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            stdout.write((json.dumps(err) + "\n").encode("utf-8"))
            stdout.flush()
            continue

        if isinstance(payload, list):
            responses = [
                r for item in payload if (r := mcp_server.handle_jsonrpc(item)) is not None
            ]
            if responses:
                stdout.write((json.dumps(responses) + "\n").encode("utf-8"))
                stdout.flush()
        else:
            response = mcp_server.handle_jsonrpc(payload)
            if response is not None:
                stdout.write((json.dumps(response) + "\n").encode("utf-8"))
                stdout.flush()


def create_http_server(
    mcp_server: OrphanDiseaseMCPServer, host: str = "127.0.0.1", port: int = 8080
) -> ThreadingHTTPServer:
    """Create a Streamable HTTP MCP server exposing POST /mcp & /.well-known/mcp.json."""

    class MCPHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if os.environ.get("MCP_HTTP_VERBOSE"):
                super().log_message(format, *args)

        def _send_json(self, status: int, body: Any) -> None:
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Accept, Mcp-Session-Id",
            )
            self.end_headers()
            self.wfile.write(encoded)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Accept, Mcp-Session-Id",
            )
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "server": SERVER_NAME,
                        "version": __version__,
                        "protocolVersion": CURRENT_PROTOCOL_VERSION,
                    },
                )
            elif self.path == "/.well-known/mcp.json":
                self._send_json(
                    200,
                    {
                        "name": SERVER_NAME,
                        "title": SERVER_TITLE,
                        "version": __version__,
                        "protocolVersion": CURRENT_PROTOCOL_VERSION,
                        "description": "Orphan Disease Venture & Myelofibrosis Opportunity MCP Server (Flagships: Clonal JAK2 V617F+ & Reversible Autoimmune Myelofibrosis)",
                        "homepage": "https://rare-disease-atlas.github.io",
                        "transport": {
                            "type": "streamable-http",
                            "endpoint": "/mcp",
                        },
                        "tools": [t["name"] for t in TOOLS_MANIFEST],
                        "resources": [r["uri"] for r in RESOURCES_MANIFEST],
                        "prompts": [p["name"] for p in PROMPTS_MANIFEST],
                    },
                )
            else:
                self._send_json(
                    404,
                    {
                        "error": "Not found. Send JSON-RPC 2.0 POST requests to /mcp or GET /.well-known/mcp.json"
                    },
                )

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in ("/mcp", "/"):
                self._send_json(404, {"error": "MCP endpoint is POST /mcp"})
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json(
                    400,
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    },
                )
                return

            if isinstance(payload, list):
                responses = [
                    r
                    for item in payload
                    if (r := mcp_server.handle_jsonrpc(item)) is not None
                ]
                if not responses:
                    self.send_response(202)
                    self.end_headers()
                    return
                self._send_json(200, responses)
            else:
                response = mcp_server.handle_jsonrpc(payload)
                if response is None:
                    self.send_response(202)
                    self.end_headers()
                    return
                self._send_json(200, response)

    return ThreadingHTTPServer((host, port), MCPHTTPHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orphan-disease-mcp",
        description="Orphan Disease Opportunity MCP Server (Flagships: Clonal JAK2+ & Autoimmune Myelofibrosis)",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport mode: 'stdio' (default) or Streamable 'http'",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host when --transport http is selected (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port when --transport http is selected (default: 8080)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use bundled data/opportunities.json without attempting live HTTPS fetch",
    )
    args = parser.parse_args(argv)

    if args.offline:
        os.environ["ATLAS_OFFLINE"] = "1"

    server = OrphanDiseaseMCPServer()
    if args.transport == "http":
        httpd = create_http_server(server, host=args.host, port=args.port)
        sys.stderr.write(
            f"[{SERVER_NAME}] Streamable HTTP listening on http://{args.host}:{args.port}/mcp\n"
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
        return 0

    run_stdio(server)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
