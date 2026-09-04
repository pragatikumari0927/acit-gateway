---
name: tavily-skills
description: Web search and content extraction using Tavily. Provides powerful search, crawl, map, extract, and deep research capabilities for current information, page content, site mapping, and comprehensive research.
version: 1.0.0
---

# tavily-skills

Web search and content extraction for the ACIT Gateway project and general research needs.

## When to use
- Need up-to-date information beyond model knowledge cutoff (news, facts, pricing, documentation).
- Extract full page content or structured data from specific URLs.
- Map or crawl entire websites for structure and relevant pages.
- Perform deep research on a topic that requires synthesizing multiple sources.
- Complement Firecrawl when Tavily's research or search depth is preferred.

## Available Tools (via connected Tavily MCP)

After using `search_tool` to discover, call with `use_tool`:

- `tavily__tavily_search`: Web search with advanced options (depth, time range, domains, images, raw content).
- `tavily__tavily_extract`: Pull clean markdown/text content from one or more URLs (basic or advanced depth).
- `tavily__tavily_crawl`: Crawl a site with depth/breadth controls and instructions.
- `tavily__tavily_map`: Discover URL structure of a site.
- `tavily__tavily_research`: Multi-source deep research on a question (mini / pro / auto).

## Workflow

1. Discovery
   ``` 
   search_tool with query containing "tavily"
   ```

2. Search example
   ```
   use_tool with tool_name is tavily__tavily_search
   tool_input is {"query": "Razorpay test mode API limits 2026", "max_results": 5, "search_depth": "advanced"}
   ```

3. Content extraction
   ```
   use_tool with tool_name is tavily__tavily_extract
   tool_input is {"urls": ["https://example.com/docs"], "extract_depth": "advanced", "format": "markdown"}
   ```

4. Research
   ```
   use_tool with tool_name is tavily__tavily_research
   tool_input is {"input": "Compare agentic commerce protocols for payment gateways", "model": "pro"}
   ```

## Integration Notes
- Tavily MCP server is already connected (5 tools).
- Use for defense-only research (Track 02). No offensive tooling.
- Combine with local project knowledge from mempalace / ai-memory and grok-build-cli-utilities.
- Rate limits apply (e.g., research tool ~20 req/min).

## npm / CLI Note
The command `npm install -g @tavily/cli` was attempted but the package is not available on the public registry in this environment. Primary access is through the Tavily MCP server and skills.

For local CLI usage if available in your environment:
- Install via official Tavily methods (check https://docs.tavily.com)
- Set `TAVILY_API_KEY` in environment or config.

## Related Skills
- firecrawl (alternative scraping/crawling)
- research-agent
- mempalace / ai-memory (to persist research results)
