# Agent Setup (Cursor / Grok Build / Qwen Code)

This project ships the [ECC](https://github.com/affaan-m/ECC) (v2.2.1) multi-agent harness so Cursor, Grok Build, and Qwen Code share one canonical skill set and one rule pack, kept in sync by a single script.

## Layout

| Path | Purpose | Consumed by |
| --- | --- | --- |
| `.agents/skills/` | Canonical ECC skills (one folder per skill, `SKILL.md` inside) | Cursor (auto), source of truth |
| `.qwen/skills/` | Mirror of `.agents/skills/` | Qwen Code (`/skills`) |
| `.grok/skills/` | Mirror of `.agents/skills/` | Grok Build |
| `.agents/rules/ecc/` | Canonical ECC rule packs (`common/`, `python/`) | Any agent, on demand |
| `.cursor/rules/500-ecc-python.mdc` | Python + FastAPI standards (glob `**/*.py`) | Cursor (auto) |
| `.cursor/rules/510-ecc-security.mdc` | Security rules (agent-requested) | Cursor |
| `.cursor/rules/520-ecc-workflow.mdc` | Git / workflow / review (agent-requested) | Cursor |
| `AGENTS.md` | ECC instructions block (managed between `<!-- ECC:BEGIN -->` / `<!-- ECC:END -->`) | Cursor, any agent |
| `QWEN.md` | Same managed block | Qwen Code |
| `.grok/config.toml` | Grok Build permission denies (no MCP/plugins) | Grok Build |
| `scripts/sync-skills.sh` | Mirror `.agents/skills/` → `.qwen/skills/` + `.grok/skills/` (idempotent) | Maintainer |

## Update path

1. Add/modify a skill under `.agents/skills/<name>/SKILL.md`.
2. Run `bash scripts/sync-skills.sh` — mirrors into `.qwen/skills/` and `.grok/skills/`, prunes stale ECC-managed skills, preserves any foreign (non-ECC) skills.
3. Reload the agent window so the new skill is picked up.

To refresh the whole ECC bundle: shallow-clone ECC again, `cp -rn` into `.agents/skills/`, then run the sync script. The script is idempotent.

## Lean build (optional)

If 336 skills is too noisy, keep only the core 6: `tdd-workflow`, `verification-loop`, `security-review`, `search-first`, `python-patterns`, `backend-patterns`. Delete the other folders from `.agents/skills/`, then run `scripts/sync-skills.sh` to prune the mirrors. Ask before doing this — it is destructive.

## Notes

- ECC skills are prompt/context techniques only — no API keys, no runtime deps, no code mutation.
- No LLM on the money path (see `.cursor/rules/200-money-path-security.mdc`). ECC skills are tools for the agent, not for payment code.
- `.grok/` and `.qwen/` are listed in `.cursorignore` so they do not pollute Cursor's index; the sync script writes to them via shell, which is not restricted by `.cursorignore`.
