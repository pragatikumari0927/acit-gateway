---
name: ai-memory
description: Persistent cross-session context using ai-memory patterns. Provides durable memory across Grok sessions via MemPalace + Engram + grok-utils memory explorer. Complements session monitoring and worktree tracking.
version: 1.0.0
---

# ai-memory

Persistent cross-session context for the ACIT Gateway project.

## When to use
- At the start of any development session to recall prior decisions, architecture, and context.
- When resuming work across multiple days or after context resets.
- To store important outcomes, mandates, design decisions, or test results durably.
- Before large refactors or phase transitions to ensure continuity.

## Core Capabilities
- Local-first persistent memory (MemPalace rooms + wings).
- Token-efficient recall via Engram MCP (`mem_*` tools).
- Cross-session memory explorer via `grok-utils memory`.
- Works alongside grok-build-cli-utilities for sessions and worktrees.

## Workflow

1. Session start
   - `mempalace wake-up --wing acit-gateway` or use engram `mem_context`.
   - `grok-utils memory list` or `grok-utils sessions list --limit 5`.

2. Capture context
   - After meaningful work: `mempalace mine .`
   - Or use Engram: `mem_save` for key decisions.

3. Search & resume
   - `mempalace search "firewall IDPI" --wing acit-gateway`
   - `grok-utils memory search "vault mandate"`
   - `grok-utils sessions search "parser" --limit 5`

4. End of session
   - Mine updates: `mempalace mine .`
   - Optionally prune old sessions with `grok-utils sessions prune --dry-run`.

## Integration with grok-build-cli-utilities

This skill pairs with the installed grok-build-cli-utilities (see `.grok/skills/cli-utilities`):

- Session monitoring: `grok-utils sessions list | info | analyze | export`
- Worktree tracking: `grok-utils worktree list | stats | prune-orphaned`
- Memory curation: `grok-utils memory list | search | stats | paths`

## Providers

`providers.json`:
```json
{"providers": {"mempalace": {"enabled": true}, "ai-memory": {"enabled": true}}}
```

## Commands (pwsh)

```pwsh
# Memory
grok-utils memory --help
grok-utils memory list
grok-utils memory search "C4 Firewall"

# Sessions (monitoring)
grok-utils sessions list --limit 10
grok-utils sessions stats

# Worktree (tracking)
grok-utils worktree list
grok-utils worktree stats
```

See also: mempalace skill, cli-utilities docs/commands/memory.md, sessions.md, worktree.md, and README "Memory & Recall" section.
```

## Output format
Markdown summaries, JSON for machine use (`--json`), and durable storage in the palace + session logs.
