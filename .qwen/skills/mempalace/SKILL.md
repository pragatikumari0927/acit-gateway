---
name: mempalace
description: Persistent local-first memory using MemPalace + Engram. Use for session context (wake-up), recalling decisions, mining the ACIT Gateway project, searching past work, and end-of-day memory workflows. Complements the connected engram MCP.
---

# mempalace

MemPalace + Engram provides persistent, local-first, token-efficient memory for the ACIT Gateway project.

## Key Commands (PowerShell / Windows)

```pwsh
mempalace --version
mempalace status
mempalace mcp

$proj = (Get-Location).Path
mempalace init $proj --yes
mempalace mine $proj --wing acit-gateway

mempalace wake-up --wing acit-gateway
mempalace search "mandate vault architecture"
mempalace search "query"
```

## Daily Usage

- Session start: `mempalace wake-up` (or engram `mem_context`)
- Remember decisions: `mempalace mine .` after work (or `mem_save`)
- Search past work: `mempalace search "query"`
- End of day: `mempalace mine .`

See the "## Memory & Recall" section added to README.md.

## Providers & Engram Integration

`providers.json` at project root:

```json
{"providers": {"mempalace": {"enabled": true}}}
```

Complements the live `engram` MCP tools (`mem_save`, `mem_search`, `mem_context`, `mem_session_summary`).

## ACIT Gateway Rules

- Defense-only (Track 02). No LLM on the runtime path (Parser, Vault, Firewall, Guardrails, Money actions).
- Mine after edits to AGENTS.md, RULES.md, PHASES.md, CONTEXT.md, docs/, or architecture.
- Quote paths containing spaces on Windows.
- Prefer `--wing acit-gateway` for targeted results.

## Operating Rules

- Be precise with the actual commands the user types.
- Always provide ready-to-run pwsh snippets.
- Prefer read-only first (`status`, `search`, `wake-up`).
- Redact secrets and PII.
- Follow project conventions.

## Workflow

1. Session start → `mempalace wake-up` or `mem_context`.
2. Before major work → search for prior decisions.
3. After completing work (docs, plans, code) → `mempalace mine .`
4. Inspect state → `mempalace status`.
5. Maintain this skill → use the forge validate command.

## References

- README.md (Memory & Recall section)
- AGENTS.md, CONTEXT.md, RULES.md, PHASES.md, MEMORY.md
- `mempalace --help`

Load [references/patterns.md](references/patterns.md) for additional patterns.