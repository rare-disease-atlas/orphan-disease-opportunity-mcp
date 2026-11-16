# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :---: |
| `1.4.x` (Remote Streamable HTTP + Local `stdio`) | Yes |
| `< 1.4.0` | Upgrade to `>= 1.4.0` |

## Architecture & Security Posture

- **Zero Third-Party Runtime Dependencies:** The Python `stdio` / HTTP package uses 100% Python `>= 3.10` standard library modules (`json`, `urllib.request`, `http.server`, `argparse`), eliminating transitive PyPI supply-chain risk.
- **Read-Only Scientific Corpus + Non-Destructive Feedback:** All query tools (`match_founder_opportunities`, `get_disease_case_study`, `find_non_dilutive_grants`, `get_validation_communities`) are strictly read-only (`readOnlyHint: true`, `destructiveHint: false`), and `submit_atlas_feedback` scrubs email/phone PII while performing zero destructive mutations.
- **Transport Security:** The hosted Streamable HTTP endpoint (`https://api.rare-disease-atlas.workers.dev/mcp`) enforces TLS 1.3, `308` HTTPS redirection on plaintext HTTP, and `Strict-Transport-Security` (`HSTS` preload).

## Reporting a Vulnerability

Please **do not** report exploitable security vulnerabilities in public GitHub issues.

Instead, report vulnerabilities privately via **GitHub Private Vulnerability Reporting**:
- https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp/security/advisories/new

Please exclude all personal health information (PHI) and personal identifiers (PII) from reports. Validated security reports are triaged within 72 hours.
