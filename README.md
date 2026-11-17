# `orphan-disease-opportunity-mcp` (`v1.6.0`)

[![License: MIT](https://img.shields.io/badge/Code_License-MIT-blue.svg)](./LICENSE)
[![Data License: CC BY 4.0](https://img.shields.io/badge/Data_License-CC_BY_4.0-emerald.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B%20(Zero%20Deps)-3776AB.svg)](./pyproject.toml)
[![MCP 2026-07-28](https://img.shields.io/badge/MCP_Protocol-2026--07--28_%7C_2025--11--25-0F766E.svg)](https://registry.modelcontextprotocol.io)
[![SLSA Provenance](https://img.shields.io/badge/SLSA_Provenance-Attested-16A34A.svg)](https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp/attestations)
[![Live Atlas](https://img.shields.io/badge/Live_Atlas-rare--disease--atlas.github.io-4F46E5.svg)](https://rare-disease-atlas.github.io)

**Open Venture & Translational Opportunity Atlas — Read-Only Model Context Protocol (`MCP 2026-07-28`) Server**  
**Flagship #1:** Clonal `JAK2 V617F+` Primary Myelofibrosis (`jak2-myelofibrosis`) • **Flagship #2:** Reversible Autoimmune Myelofibrosis & Iron/Hepcidin Axis (`autoimmune-myelofibrosis`) • **Web Dossier:** <https://rare-disease-atlas.github.io>

`mcp-name: io.github.rare-disease-atlas/orphan-disease-opportunity-mcp`

An open, **zero-third-party-dependency**, **100% read-only** Python STDIO + **zero-auth Remote Streamable HTTP** MCP server (`2026-07-28` `server/discover` + `2025-11-25` `initialize` + MCP Apps `ui://rare-disease-atlas/venture-card`) and OpenAPI 3.1 toolkit designed for technical founders (**Computational / AI-Bio**, **Public Health Systems**, **Venture / Novel Financing**) and autonomous AI research agents evaluating high-tractability orphan disease startups, drug-repurposing wedges, 30/60/90-day diligence roadmaps, non-dilutive SBIR/venture-philanthropy grants, and ethical clinical validation guardrails.

---

## Option A: Zero-Install Remote Streamable HTTP MCP (Cloud & Hosted Agents)

Connect immediately over HTTPS with **zero local installation and zero API keys**:

- **Remote MCP Endpoint (`streamable-http`):** `https://api.rare-disease-atlas.workers.dev/mcp`
- **A2A Peer Agent Card:** `https://rare-disease-atlas.github.io/.well-known/agent.json`

```bash
claude mcp add --transport http orphan-disease-opportunities https://api.rare-disease-atlas.workers.dev/mcp
```

---

## Option B: Instant 1-Command Local STDIO Execution (`uvx` or Attested `.mcpb`)

Run directly from GitHub via [`uvx`](https://docs.astral.sh/uv/) with **zero external runtime dependencies** (pure Python >= 3.10 standard library):

```bash
uvx --from git+https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp orphan-disease-opportunity-mcp
```

Or download the cryptographically attested `orphan-disease-opportunity-mcp.mcpb` desktop bundle from [GitHub Releases](https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp/releases) and verify its SLSA build provenance:

```bash
gh attestation verify orphan-disease-opportunity-mcp.mcpb --repo rare-disease-atlas/orphan-disease-opportunity-mcp
```

### Add to Claude Code (1 Command)

```bash
claude mcp add orphan-disease-opportunities -- uvx --from git+https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp orphan-disease-opportunity-mcp
```

### Add to Claude Desktop / Cursor / Windsurf / Cline / Antigravity

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

## Paired Myelofibrosis Flagships (`jak2-myelofibrosis` & `autoimmune-myelofibrosis`)

Over 7,000 rare diseases carry **FDA Orphan Drug Act** structural advantages (7-year US market exclusivity, 100% waiver of the **$4,682,003 FY2026 PDUFA filing fee**, 25% qualified clinical trial tax credit, and N=120–350 pivotal trials). Our Atlas anchors every tool on a paired positive/negative translational control in human bone marrow fibrosis:

1. **Flagship #1 — Clonal `JAK2 V617F+` Primary Myelofibrosis (`jak2-myelofibrosis`):**
   - Single somatic `JAK2 V617F` mutation in the **JH2 pseudokinase** domain drives ~50–60% of Primary Myelofibrosis (`ORPHA:824`, ~15,000–25,000 US patients).
   - All 4 approved Type I `JH1` JAK inhibitors (*ruxolitinib, fedratinib, pacritinib, momelotinib*) inhibit wild-type JAK2 alongside V617F—causing cytopenias, <15% marrow fibrosis reversal, and **11–23 month median survival post-ruxolitinib failure**.
   - High-conviction wedges: mutant-selective `JH2` allosteric/PROTAC design (`PDB: 6E2Q/8BAK` vs `4FVP`), Type II persistence breakers, mutant `CALR` biologics, spatial marrow pathology surrogates, and no-washout RWE trial matching.
2. **Flagship #2 — Reversible Autoimmune Myelofibrosis (`autoimmune-myelofibrosis`, *Nature's Positive Control*):**
   - `JAK2/CALR/MPL`-negative lupus/SLE-spectrum marrow fibrosis with dual transfusional + `IL-6 -> hepcidin -> ferroportin` iron block where human `MF-2/MF-3` reticulin fibrosis **physically resolves in 74–80% of patients** on targeted immunomodulation (*Gangat et al., Mayo Clinic 2024*).

---

## Exposed Read-Only MCP Capabilities (`v1.6.0`)

Supports **MCP `2026-07-28` (`server/discover`)** and **`2025-11-25` (`initialize`)**, structured `outputSchema` + `structuredContent`, input `examples`, and MCP Apps UI (`ui://rare-disease-atlas/venture-card`).

### Canonical Read-Only Tools (`tools/list` & `tools/call`)
| Tool | Parameters | Capability |
| :--- | :--- | :--- |
| **`search_founder_opportunities`** *(alias: `match_founder_opportunities`)* | `background`, `capital_tier`, `wet_lab_required`, `disease_id` | Searches startup blueprints anchored on Clonal `JAK2+` & Autoimmune Myelofibrosis (plus 4 adjacent cohorts) by founder track, capital tier, and wet-lab requirement. |
| **`get_disease_case_study`** | `disease_id` (default `"jak2-myelofibrosis"`) | Retrieves curated biology, NCT trials, `GEO`/`PDB` datasets, failure modes, and FDA Orphan Drug unit economics (`jak2-myelofibrosis`, `autoimmune-myelofibrosis`, `vexas-syndrome`, `castleman-disease`, `systemic-mastocytosis`, `telomere-biology-disorders`). |
| **`list_non_dilutive_grants`** *(alias: `find_non_dilutive_grants`)* | `track` (`all`, `sbir-sttr`, `foundation`, `venture-philanthropy`, `regulatory-orphan`, `federal-translational`) | Lists NIH/NCI SBIR, MPNRF, LLS TAP, CDCN, ARPA-H, and FDA Orphan grants for Myelofibrosis and rare disease ventures. |
| **`get_validation_communities`** | `disease_id` (default `"jak2-myelofibrosis"`) | Retrieves registries, biobanks, patient foundations, and non-extractive research guardrails for Myelofibrosis and rare diseases. |
| **`get_90_day_validation_plan`** *(alias: `generate_90_day_validation_plan`)* | `disease_id`, `background`, `capital_tier` | Retrieves a structured 30/60/90-day diligence roadmap contrasting Clonal `JAK2+` vs Autoimmune Myelofibrosis (plus 4 adjacent cohorts). |
| **`search_any_orphan_indication`** *(alias: `analyze_any_orphan_indication`)* | `disease_query`, `founder_background` | Searches live OpenTargets, ClinicalTrials.gov v2, and PubMed evidence for any of 7,000+ rare diseases, benchmarked against `JAK2+` & Autoimmune Myelofibrosis. |

### Resources (`resources/list` & `resources/read`)
- `briefing://rare-disease-playbook/jak2-myelofibrosis` — Clonal `JAK2 V617F+` Myelofibrosis playbook (`text/markdown`)
- `briefing://rare-disease-playbook/autoimmune-myelofibrosis` — Reversible Autoimmune Myelofibrosis & iron triage playbook (`text/markdown`)
- `briefing://rare-disease-playbook/hematology-immunology-expansion` — VEXAS, Castleman, Mastocytosis & Telomere cohorts (`text/markdown`)
- `briefing://rare-disease-playbook/non-dilutive-grants` — Non-dilutive SBIR/ARPA-H/MPNRF/LLS TAP grant stack (`text/markdown`)
- `briefing://rare-disease-playbook/validation-ethics` — Registries, biobanks & ethical discovery guardrails (`text/markdown`)
- `ui://rare-disease-atlas/venture-card` — Interactive MCP App HTML card (`text/html;profile=mcp-app`)

### Prompt (`prompts/get`)
- **`evaluate-rare-disease-venture`** — Read-only 90-day diligence workflow (`founder_background`, `capital_budget`, `wet_lab_access`).

---

## Verification & Quality Assurance

```bash
PYTHONDONTWRITEBYTECODE=1 python3 test_mcp.py
```

## License

- **MCP Server Code:** [MIT License](./LICENSE) (`Copyright (c) 2026 Rare Disease Venture Atlas`)
- **Opportunity & Case-Study Dataset (`opportunities.json`):** [Creative Commons Attribution 4.0 International (`CC-BY-4.0`)](https://creativecommons.org/licenses/by/4.0/)
