<!-- ECC:BEGIN (managed block - edit files in .agents/, not here) -->
## ECC Agent Instructions
Workflow: plan -> test -> implement -> review -> verify -> remember.
- Test-driven: write/adjust tests with every behavior change; verify before declaring done.
- Security-first: validate all inputs; no LLM calls on the money path; payment gateways TEST MODE only.
- Plan complex features before writing code; use ECC skills (tdd-workflow, verification-loop, security-review, search-first, python-patterns, backend-patterns) instead of re-deriving process.
- Skills: `.agents/skills/` (canonical; Cursor) = `.qwen/skills/` (Qwen) = `.grok/skills/` (Grok). Sync via `scripts/sync-skills.sh`.
- Standards: `.cursor/rules/500-*.mdc` (Cursor) and `.agents/rules/ecc/` (any agent, on demand).
- Never commit secrets; all config via env vars.
<!-- ECC:END -->

Diagnosis: `docs/TROUBLESHOOTING.md`. Covenant: `docs/SOUL.md`.
