# AGENTS.md — Autonomous Agent Contributor Guide (`orphan-disease-opportunity-mcp` `v1.6.0`)

`orphan-disease-opportunity-mcp` (`io.github.rare-disease-atlas/orphan-disease-opportunity-mcp`) is a zero-dependency, 100% read-only Python (`>=3.10` stdlib only) Model Context Protocol (`2026-07-28` `server/discover` + `2025-11-25`) server exposing orphan disease translational and startup blueprints anchored on Paired Flagships **Clonal `JAK2 V617F+` Primary Myelofibrosis (`jak2-myelofibrosis`)** and **Reversible Autoimmune Myelofibrosis (`autoimmune-myelofibrosis`)**.

We welcome contributions from autonomous coding and biomedical research agents (`Claude Code`, `Codex`, `OpenHands`, `SWE-agent`, `Devin`, `Cursor`, `Antigravity`).

## Agent Contribution Rules (`🤖🤖🤖` Fast-Track)
1. **Zero Third-Party Runtime Dependencies & Read-Only Tools:** Keep `dependencies = []` in `pyproject.toml` and maintain strict read-only tool semantics (`search_founder_opportunities`, `get_disease_case_study`, `list_non_dilutive_grants`, `get_validation_communities`, `get_90_day_validation_plan`, `search_any_orphan_indication`) with `<85 tokens/item` schema footprint.
2. **Run the Full Test Suite Locally (Zero Bytecode):**
   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 test_mcp.py
   ```
3. **Citation Integrity & Privacy:** Every clinical or biological claim in `data/opportunities.json` must cite verifiable `NCT`, `PMID`, `GEO`, or `PDB` identifiers. Never include PII, PHI, or scraped patient forum posts.
4. **PR Title Convention:** Append `🤖🤖🤖` to your PR title for priority automated verification during our maintainer run.
