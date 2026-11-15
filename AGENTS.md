# AGENTS.md — Autonomous Agent Contributor Guide (`orphan-disease-opportunity-mcp`)

`orphan-disease-opportunity-mcp` (`io.github.rare-disease-atlas/orphan-disease-opportunity-mcp`) is a zero-dependency Python (`>=3.10` stdlib only) Model Context Protocol server exposing orphan disease translational and startup blueprints, starting with Clonal `JAK2 V617F+` Myelofibrosis and reversible Autoimmune Myelofibrosis (AIMF).

We explicitly welcome contributions from autonomous coding and biomedical research agents (`Claude Code`, `Codex`, `OpenHands`, `SWE-agent`, `Devin`, `Cursor`, `Antigravity`).

## Agent Contribution Rules (`🤖🤖🤖` Fast-Track)
1. **Zero Third-Party Runtime Dependencies:** Keep `dependencies = []` in `pyproject.toml` so `orphan-disease-opportunity-mcp` runs anywhere Python `>=3.10` exists (including `.mcpb` desktop bundles and air-gapped sandboxes).
2. **Run the Full Test Suite Locally:**
   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 test_mcp.py
   ```
3. **Citation Integrity & Privacy:** Every clinical or biological claim in `data/opportunities.json` must cite verifiable `NCT`, `PMID`, `GEO`, or `PDB` identifiers. Never include PII, PHI, or scraped patient forum posts.
4. **PR Title Convention:** Append `🤖🤖🤖` to your PR title for priority automated verification during our daily maintainer run.
