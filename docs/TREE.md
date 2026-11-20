# ACIT Gateway layout

Layout contract for what is on disk today. Not a migrate-now checklist.
Docs live under `docs/` (not the repo root). Do not recurse `.claude/skills/` or `data/skills/` — those are junction farms (Known-Broken).

```
ACIT_GATEWAY
├── .grok/
│   ├── config.toml
│   ├── hooks/
│   │   ├── mempalace-mine.json
│   │   ├── mempalace-wake.json
│   │   ├── security.json
│   │   └── validate-command.sh
│   └── skills/                    # ECC-managed subset
├── .agents/
│   ├── rules/ecc/
│   └── skills/                    # canonical ECC subset (sync source)
├── .cursor/
│   ├── skills/                    # full skill set
│   ├── hooks/
│   │   ├── guard-secrets.sh
│   │   └── guard-shell.sh
│   ├── hooks.json
│   ├── mcp.json
│   ├── settings.json
│   └── rules/
│       ├── 000-project.mdc
│       ├── 00-project.mdc
│       ├── 10-coding.mdc
│       ├── 20-no-llm-money-path.mdc
│       ├── 30-graphify.mdc
│       ├── 100-python-fastapi.mdc
│       ├── 200-money-path-security.mdc
│       ├── 300-testing.mdc
│       ├── 400-git-workflow.mdc
│       ├── 500-ecc-python.mdc
│       ├── 510-ecc-security.mdc
│       └── 520-ecc-workflow.mdc
├── .qwen/
│   └── skills/                    # synced copies
├── .claude/                       # junction farm — do not recurse
├── .grokignore
├── .cursorignore
├── .agentignore
├── .qwenignore
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md
├── README.md
├── SECURITY.md
├── QWEN.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── uv.lock
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry; /health lives here
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   └── models.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── mandate.py             # Mandate, OrderItem, Protocol, InternalMandate
│   │   ├── catalog.py
│   │   ├── audit.py
│   │   ├── agent.py
│   │   └── proposal.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── protocol_parser.py
│   │   ├── firewall.py
│   │   ├── vault.py
│   │   ├── catalog.py
│   │   ├── policy.py
│   │   ├── checkout.py            # run_execute — money-path hub
│   │   ├── executor.py
│   │   ├── audit.py
│   │   └── chaos.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── catalog.py
│   │       ├── mandates.py
│   │       ├── checkout.py        # thin HTTP adapter for run_execute
│   │       └── audit.py
│   └── utils/
│       ├── __init__.py
│       └── crypto.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_protocol_parser.py
│   │   ├── test_firewall.py
│   │   ├── test_vault.py
│   │   ├── test_policy.py
│   │   ├── test_audit.py
│   │   ├── test_catalog.py
│   │   ├── test_checkout.py
│   │   ├── test_executor.py
│   │   ├── test_chaos.py
│   │   └── test_dependencies.py
│   ├── integration/
│   │   ├── test_routes.py
│   │   └── test_webhooks.py
│   └── fixtures/
│       ├── catalogs.json
│       └── idpi_payloads.json
├── data/                          # junction farm under data/skills/ — do not recurse
├── scripts/
│   ├── sync-skills.sh
│   └── vocab_check.py
├── docs/
│   ├── README.md
│   ├── AGENTS.md
│   ├── AGENT-SETUP.md
│   ├── CONTEXT.md
│   ├── DECISIONS.md
│   ├── MEMORY.md
│   ├── PHASES.md
│   ├── RULES.md
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── design.md
│   ├── PRD.md
│   ├── SOUL.md
│   ├── TROUBLESHOOTING.md
│   ├── TREE.md                    # this file
│   ├── adr/
│   │   ├── 0001-canonical-mandate.md
│   │   ├── 0002-no-llm-on-money-path.md
│   │   ├── 0003-sqlite-hash-chain-audit.md
│   │   └── 0004-refuse-invisible-characters.md
│   ├── agents/
│   │   ├── domain.md
│   │   ├── issue-tracker.md
│   │   └── triage-labels.md
│   └── reviews/
│       └── graphify-triage-20260905.md
└── graphify-out/                  # generated; gitignored
    ├── graph.json
    ├── GRAPH_REPORT.md
    ├── GRAPH_REPORT.html
    └── graph.html
```

## Not present yet

Desired in an earlier template, not on disk. Do not treat as shipping paths.

- `src/api/routes/health.py` — health is `src/main.py`
- `src/api/routes/ui.py`, `src/ui/`, `src/ui/templates/`
- `src/models/protocol.py` — `Protocol` is in `src/models/mandate.py`
- `src/utils/logging.py`, `src/utils/exceptions.py`
- `tests/unit/test_dark_patterns.py`
- `tests/integration/test_executor.py`, `tests/integration/test_chaos.py` — those tests are under `tests/unit/`
- `scripts/init_db.py`, `scripts/seed_data.py`, `scripts/demo.py`
- `docs/api_reference.md`, `docs/deployment.md`, `docs/demo_script.md`, `docs/domain/`
- `docs/architecture.md` (lowercase) — file is `docs/ARCHITECTURE.md`
- Root `CONTEXT.md` / `DECISIONS.md` / `MEMORY.md` / `PHASES.md` / `RULES.md` / `SPEC.md` — those live under `docs/`
- `.cursor/config/settings.json` — file is `.cursor/settings.json`
