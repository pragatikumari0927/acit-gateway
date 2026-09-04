---
name: ai-memory
description: Persistent cross-session context. Durable memory across Grok sessions using MemPalace + Engram + grok-utils. Pairs with grok-build-cli-utilities for session monitoring and worktree tracking.
---

# ai-memory

See the canonical implementation in `.grok/skills/ai-memory/SKILL.md`.

This copy exists for compatibility with other agent runtimes (Claude Code, Cursor, etc.).

Key integrations:
- grok-build-cli-utilities (sessions, worktree, memory commands via grok-utils)
- mempalace + engram for persistent storage and recall
- Automatic session tracking for the current acit-gateway project
