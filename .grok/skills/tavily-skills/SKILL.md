---
name: tavily-skills
description: Web search and content extraction. Tavily-powered tools for search, crawl, map, extract, and deep research. Complements Firecrawl and local memory skills.
---

# tavily-skills

See the canonical skill at `.grok/skills/tavily-skills/SKILL.md`.

This copy provides compatibility for other agent frameworks.

## Key Capabilities
- Web search (tavily_search)
- Site crawling and mapping (tavily_crawl, tavily_map)
- Content extraction (tavily_extract)
- Deep research (tavily_research)

Tavily MCP server is connected. Use `search_tool` then `use_tool` with qualified names like `tavily__tavily_search`.

## Recommended Usage
- Current events, documentation lookup, competitive research, page content harvesting.
- Pair results with `mempalace` or `ai-memory` for persistence.
- Use `research-agent` skill for higher-level orchestration.
