# Patterns for mempalace (ACIT Gateway)

## Core Commands

- `mempalace init <dir> --yes`
- `mempalace mine <dir> [--wing acit-gateway]`
- `mempalace search "..." [--wing acit-gateway]`
- `mempalace status`
- `mempalace wake-up [--wing acit-gateway]`
- `mempalace mcp`

## Daily Rhythm

1. Start: wake-up + mem_context
2. Work: search before acting on decisions
3. End: mine .
4. After big docs changes (AGENTS, RULES, PHASES, README, ARCHITECTURE): mine immediately.

## Windows / pwsh Notes

- Always use `(Get-Location).Path` or quoted paths.
- OneDrive paths contain spaces — quote them.
- Prefer `--wing acit-gateway` to scope results.

## Integration with Engram MCP

MemPalace (CLI mining) + engram (MCP tools) = complete memory layer.
Use `mem_save` proactively for decisions, bugs, architecture choices.

## Project Constraints (always respect)

- No LLM on money path (ADR-0002).
- Defense-only (Track 02).
- Inject `db_path` everywhere for Vault / audit.
- Use CONTEXT vocabulary.

## When to Mine

- After editing any guidance file
- After completing a phase or major plan
- Before handing off work
- End of every coding session

## Output Format Preference

Always include:
- Exact command(s)
- Expected output snippet when known
- Next recommended command
- Link back to README "Memory & Recall" when appropriate.