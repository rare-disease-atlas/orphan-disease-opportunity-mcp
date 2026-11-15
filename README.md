# `orphan-disease-opportunity-mcp`

[![License: MIT](https://img.shields.io/badge/Code_License-MIT-blue.svg)](./LICENSE)
[![Data License: CC BY 4.0](https://img.shields.io/badge/Data_License-CC_BY_4.0-emerald.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B%20(Zero%20Deps)-3776AB.svg)](./pyproject.toml)
[![Live Atlas](https://img.shields.io/badge/Live_Atlas-rare--disease--atlas.github.io-4F46E5.svg)](https://rare-disease-atlas.github.io)

**Open Venture & Translational Opportunity Atlas — Model Context Protocol (MCP) Server**  
**Flagship Deep-Dive #1:** `JAK2 V617F` Myelofibrosis (`jak2-myelofibrosis`) • **Web Dossier:** <https://rare-disease-atlas.github.io>

`mcp-name: io.github.rare-disease-atlas/orphan-disease-opportunity-mcp`

An open, **zero-third-party-dependency** Python MCP server and OpenAPI 3.1 toolkit designed for technical founders (**Computational / AI-Bio**, **Public Health Systems**, **Venture / Novel Financing**) and autonomous AI research agents evaluating high-tractability orphan disease startups, drug-repurposing wedges, non-dilutive SBIR/venture-philanthropy grants, and ethical clinical validation pathways.

---

## Instant 1-Command Installation (Zero PyPI Wait Required)

Run directly from GitHub via [`uvx`](https://docs.astral.sh/uv/) with **zero external runtime dependencies** (pure Python >= 3.10 standard library):

```bash
uvx --from git+https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp orphan-disease-opportunity-mcp
```

*(Once published to PyPI, `uvx orphan-disease-opportunity-mcp` also runs identically.)*

### Add to Claude Code (1 Command)

```bash
claude mcp add orphan-disease-opportunities -- uvx --from git+https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp orphan-disease-opportunity-mcp
```

### Add to Claude Desktop / Cursor / Windsurf / Cline / Antigravity

Add to `claude_desktop_config.json`, `.cursor/mcp.json`, or your MCP client settings:

```json
{
  "mcpServers": {
    "orphan-disease-opportunities": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp",
        "orphan-disease-opportunity-mcp"
      ]
    }
  }
}
```

---

## Why This Exists

Over 7,000 rare diseases carry **FDA Orphan Drug Act** structural advantages (7-year US market exclusivity, 100% waiver of the **$4,682,003 FY2026 PDUFA filing fee**, 25% qualified clinical trial tax credit, and N=120–350 pivotal trials), yet technical builders outside traditional wet-lab pharma rarely see where **single-mutation structural tractability** intersects **urgent standard-of-care failure**.

**Flagship Case Study #1 (`jak2-myelofibrosis`)** models this end-to-end:
- **Causal Precision:** A single somatic mutation (`JAK2 V617F` in the **JH2 pseudokinase** autoinhibitory domain) drives ~50–60% of Primary Myelofibrosis (`ORPHA:824`, ~15,000–25,000 US patients).
- **First-Gen SoC Failure Cliff:** All 4 FDA-approved JAK inhibitors (*ruxolitinib, fedratinib, pacritinib, momelotinib*) are Type I ATP-competitive binders of the conserved **JH1 catalytic domain**, inhibiting wild-type JAK2 alongside V617F—causing dose-limiting anemia/thrombocytopenia, ~50% discontinuation within 3 years, minimal clonal eradication, and **11–23 month median survival post-ruxolitinib failure**.
- **Zero-Wet-Lab & Low-Capital Wedges:** Structure-guided JH2 V617F vs WT (`PDB: 4FVR/6E2Q/8BAK/8EX2` vs `4FVP`) allosteric/PROTAC design + outsourced CRO screening; AI marrow fibrosis digital pathology (`MF-0..3` composite endpoints solving the Phase 3 SVR35/TSS50 crisis); single-cell megakaryocyte-stroma drug repurposing (`GSE144568`, `GSE156644`); no-washout RWE clinical trial matching; allo-HSCT timing CDS; and evergreen venture-philanthropy SPVs.

---

## Exposed MCP Capabilities

### Tools (`tools/list` & `tools/call`)
| Tool | Parameters | Capability |
| :--- | :--- | :--- |
| **`match_founder_opportunities`** | `background` (`computational-ai-bio`, `public-health`, `venture-novel-financing`, `all`), `capital_tier` (`bootstrapped-grant`, `seed`, `series-a-platform`, `all`), `wet_lab_required` (`true`/`false`), `disease_id` | Filters startup & translational blueprints with unit economics, regulatory pathways, open datasets, and 90-day milestones. Syncs live from `https://rare-disease-atlas.github.io/opportunities.json` with automatic fallback to bundled `opportunities.json`. |
| **`get_disease_case_study`** | `disease_id` (default `"jak2-myelofibrosis"`) | Returns causal JH2 vs JH1 biology, Type I JAKi failure modes, FDA Orphan Drug economics, $1.7B–$2.9B M&A comps, and open `PDB`/`GEO`/`ChEMBL`/`ClinicalTrials.gov` accessions. |
| **`find_non_dilutive_grants`** | `track` (`all`, `sbir-sttr`, `foundation`, `venture-philanthropy`, `regulatory-orphan`, `federal-translational`) | Maps NCI/NHLBI SBIR, MPN Research Foundation (`MPN Challenge`), Blood Cancer United (`TAP`), Harrington Discovery Institute, FDA OOPD, and ARPA-H awards. |
| **`get_validation_communities`** | `disease_id` (default `"jak2-myelofibrosis"`) | Maps institutional registries (`MPN PROGRESSion Registry NCT07362225`, `HealthTree`, `Blood Cancer United CTSC`, `MPN Voice`) paired with strict **non-extractive ethical patient engagement rules**. |

### Resource (`resources/read`)
- **`briefing://rare-disease-playbook/jak2-myelofibrosis`** — Complete Markdown venture & translational playbook.

### Prompt (`prompts/get`)
- **`evaluate-rare-disease-venture`** — Multi-step 90-day killer-experiment, non-dilutive grant-stacking, and ethical validation workflow (`founder_background`, `capital_budget`, `wet_lab_access`).

---

## Alternative Deployment Modes

### Docker (Hardened Non-Root Container)

```bash
docker build -t orphan-disease-opportunity-mcp .

# Stdio MCP transport
docker run -i --rm orphan-disease-opportunity-mcp

# Remote Streamable HTTP MCP server (exposes POST /mcp, GET /.well-known/mcp.json, GET /health)
docker run --rm -p 8080:8080 orphan-disease-opportunity-mcp --transport http --host 0.0.0.0 --port 8080
```

### Local Source Execution

```bash
git clone https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp.git
cd orphan-disease-opportunity-mcp
python3 -m orphan_disease_mcp
```

### Custom GPT Actions & OpenAPI 3.1 Agents

Import [`openapi.yaml`](./openapi.yaml) directly into **OpenAI Custom GPT Actions**, LangChain `OpenAPIToolkit`, or any OpenAPI 3.1 client to query `https://rare-disease-atlas.github.io/opportunities.json` over HTTPS with zero backend infrastructure.

---

## Environment Variables (Optional)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ATLAS_DATA_URL` | `https://rare-disease-atlas.github.io/opportunities.json` | Override URL for live JSON dataset sync. |
| `ATLAS_OFFLINE` | unset (`0`) | Set to `1` (`true`) to force deterministic offline execution from bundled `opportunities.json`. |

---

## Verification & Quality Assurance

Run the full zero-dependency end-to-end test suite (covers `stdio` JSON-RPC 2.0 lifecycle, all 4 tools, live HTTP mock sync + offline fallback, Streamable HTTP transport, and `server.json` / `glama.json` / `smithery.yaml` / `openapi.yaml` schema checks):

```bash
python3 test_mcp.py
```

## License

- **MCP Server Code:** [MIT License](./LICENSE) (`Copyright (c) 2026 Rare Disease Venture Atlas`)
- **Opportunity & Case-Study Dataset (`opportunities.json`):** [Creative Commons Attribution 4.0 International (`CC-BY-4.0`)](https://creativecommons.org/licenses/by/4.0/)
