# Troubleshooting — ACIT Gateway

Agents: read the matching section **before** diagnosing; cite the entry you used. Humans: same loops, same Proof anchors.

## Table of Contents

- [Environment & Setup](#environment--setup)
- [Agent Harness](#agent-harness)
- [Tests & CI](#tests--ci)
- [Service & Money Path](#service--money-path)
- [Common Error Messages](#common-error-messages)
- [Known-Broken / Known-Stale Registry](#known-broken--known-stale-registry)
- [Getting Help](#getting-help)
- [Unverified Suspicions](#unverified-suspicions)

---

## Environment & Setup

### `uv run pytest` cannot resolve

**Symptom:** `uv run pytest -q` exits with `No solution found when resolving dependencies` and names `python-multipart`.

**Cause:** [`pyproject.toml`](../pyproject.toml) pins `python-multipart==0.0.32` and `fastapi-users==12.1.0`; that package requires `python-multipart==0.0.6`. Resolver refuses `acit-gateway[dev]`.

**Proof:** Step 1 `uv run pytest -q --tb=no` (exit 1). Pins at `pyproject.toml` L7–L22.

**Fix:** Do not change pins in a diagnosis pass. Use the existing `.venv` interpreter.

**Verify:**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expect a pass count. Step 1 counted **98** `test_` functions under `tests/`.

### Python pin drift

**Symptom:** Docs say Python 3.11; `.venv` reports 3.14.x.

**Cause:** [`pyproject.toml`](../pyproject.toml) L6 is `requires-python = ">=3.11"`, not a 3.11-only pin. Local uv/Chocolatey defaulted to 3.14.

**Proof:** Step 1 `.venv\Scripts\python.exe` → `venv 3.14.6`. `uv python list` showed `C:\Python314\python.exe`.

**Fix:** Confirm the pin, then install 3.11 only if you need it:

```powershell
Select-String -Path pyproject.toml -Pattern 'requires-python'
uv python list
```

**Verify:** Interpreter major.minor matches what you intend (`3.11` vs `>=3.11` on 3.14).

### OneDrive broken junctions

**Symptom:** Recursion prints `Could not find a part of the path` or git `could not open directory '.claude/skills/...'` / `data/skills/...`.

**Cause:** Dangling reparse points. Step 1: **48** under `.claude/skills/`, **48** under `data/skills/` (96 total), first targets under `.agents/skills/`.

**Proof:** Step 1 `Get-ChildItem -Attributes ReparsePoint` count 96; `git status` warnings for those trees.

**Fix:** Scan `src/` and `tests/` only. Add `-ErrorAction SilentlyContinue` on repo-wide walks. **Do not** bulk-delete junctions as a casual fix (OneDrive + skill mirrors).

**Verify:**

```powershell
Get-ChildItem src,tests -Recurse -File -ErrorAction SilentlyContinue | Measure-Object
```

---

## Agent Harness

### Canonical ECC skills missing from `/`

**Symptom:** `/tdd-workflow` (and siblings) do not appear in Cursor skill search.

**Cause:** [`.cursorignore`](../.cursorignore) L57 ignores `.agents/`, the canonical tree.

**Proof:** `.cursorignore` L54–L58 (`.grok/`, `.qwen/`, `.agents/`, `.claude/`). Root [`AGENTS.md`](../AGENTS.md) names those six skills.

**Fix:** Invoke by name: `/tdd-workflow`, `/verification-loop`, `/security-review`, `/search-first`, `/python-patterns`, `/backend-patterns`. Sync mirrors with `scripts/sync-skills.sh` only.

**Verify:** Skill file exists at `.agents/skills/<name>/SKILL.md` (open by path, not `/` search).

### Duplicate `.cursor/rules` generations

**Symptom:** Two project-context files fire for the same topic; context cost rises; advice can conflict.

**Cause:** Overlapping generations both load: `00-project.mdc` + `000-project.mdc`; `20-no-llm-money-path.mdc` + `200-money-path-security.mdc`; `10-coding.mdc` + `500-ecc-python.mdc`; `400-git-workflow.mdc` + `520-ecc-workflow.mdc`.

**Proof:** Files on disk under `.cursor/rules/` (Step 1 inventory).

**Fix:** Keep both. Prefer money-path rules (`20` / `200`) over convenience. Do not delete a generation without a dedicated cleanup.

**Verify:** `Get-ChildItem .cursor/rules/*.mdc | Select-Object Name` still lists both prefixes.

### Stale `docs/AGENTS.md`

**Symptom:** File says runtime `src/` and `tests/` are empty stubs; no `run_execute`.

**Cause:** Text predates the checkout refactor. Live pipeline is Firewall → parsed Mandate → Guardrails → Vault → Money action → Audit.

**Proof:** [`docs/AGENTS.md`](AGENTS.md) L17 (stubs). Step 1: `run_execute` only in [`docs/MEMORY.md`](MEMORY.md):39, not in `AGENTS.md`. Implementation: [`src/services/checkout.py`](../src/services/checkout.py) L48–59.

**Fix:** Trust `run_execute` and `MEMORY.md`. Full `AGENTS.md` rewrite is a later task. Banner + pointers are the workaround.

**Verify:** `Select-String -Path docs/AGENTS.md -Pattern 'run_execute'` is empty; `Select-String -Path src/services/checkout.py -Pattern 'async def run_execute'` hits L48.

### Hooks not obvious

**Symptom:** Unsure which Cursor hooks run.

**Cause:** Hooks live in [`.cursor/hooks.json`](../.cursor/hooks.json), not in `docs/AGENTS.md`.

**Proof:** `.cursor/hooks.json`: `beforeReadFile` → `.cursor/hooks/guard-secrets.sh`; `beforeShellExecution` → `.cursor/hooks/guard-shell.sh`.

**Fix:** Read that JSON. Do not edit `.cursor/hooks/` from the agent (`.cursorignore`).

**Verify:** `Get-Content .cursor/hooks.json` shows those two commands.

---

## Tests & CI

### Looking for GitHub Actions failures

**Symptom:** Hunting a red `test.yml` / Actions run that does not exist.

**Cause:** Empty workflow was dropped. There is no `.github/workflows/` tree.

**Proof:** Step 1 glob: zero workflow files. Commit `5e7719b` (`chore(ci): drop empty workflow from initial push`).

**Fix:** Run tests locally. Do not diagnose CI.

**Verify:** `Test-Path .github/workflows` is `$false`.

### Shared Vault/Audit cache across tests

**Symptom:** Tests that share a process and `DATABASE_URL` see leftover Mandate / Audit rows.

**Cause:** `get_vault` and `get_audit` are `@lru_cache` on `db_path` ([`src/api/dependencies.py`](../src/api/dependencies.py) L61–70).

**Proof:** `src/api/dependencies.py` L61–70.

**Fix:** Point each test at its own SQLite path, or clear the cache in fixtures. Fixtures: [`tests/fixtures/catalogs.json`](../tests/fixtures/catalogs.json), [`tests/fixtures/idpi_payloads.json`](../tests/fixtures/idpi_payloads.json).

**Verify:** Fail a test that reuses `db_path`, then isolate the URL and re-run that test file.

---

## Service & Money Path

Refusal is a `PolicyResult` / `CheckoutExecuteResult`: `allowed`, `reason_code`, `violations`, `mandate_id` ([`src/models/proposal.py`](../src/models/proposal.py) L29–39). Caller next step: treat `allowed=False` as a completed Gateway outcome, not an HTTP crash (except store/webhook as below).

| `reason_code` | Meaning | Next step |
|---|---|---|
| `idpi_detected` | Firewall refused the Protocol envelope | Do not retry the same payload |
| `unknown_protocol` / `invalid_envelope` / `missing_required_field` / `missing_expires_at` | `ProtocolParseError` | Fix protocol id / envelope shape |
| `mandate_invalid` | Mandate missing, mismatch, or policy miss | Re-store / align ids |
| `over_limit` / `sku_not_allowed` / `invented_price` / `invented_discount` / `dark_pattern` | Guardrail | Change Proposal or Mandate bounds |
| `executor_failure` | Razorpay adapter / chaos raised | Check test keys and `CHAOS_ENABLED` |
| `mandate_revoked` / `unknown_agent` / `invalid_signature` | `VaultError` | Vault identity, not checkout HTTP |

### `VaultError` on `/v1/mandates/store` is HTTP 400

**Symptom:** Store returns 400 with `mandate_revoked`, `unknown_agent`, or `invalid_signature`.

**Cause:** Route maps `VaultError` to 400.

**Proof:** [`src/api/routes/mandates.py`](../src/api/routes/mandates.py) L37–38. Raises in [`src/services/vault.py`](../src/services/vault.py) L65, L90, L95–97.

**Fix:** Correct Agent JWT / Mandate state. Do not treat 400 as a malformed JSON-only error.

**Verify:** `Select-String -Path src/api/routes/mandates.py -Pattern 'status_code=400'`.

### Webhook signature fail (test mode)

**Symptom:** `400 Missing X-Razorpay-Signature header` or `401 Invalid webhook signature`.

**Cause:** HMAC-SHA256 over the raw body vs `RAZORPAY_WEBHOOK_SECRET`.

**Proof:** [`src/main.py`](../src/main.py) L46–60, L244, L248–255. Secret field: [`src/config.py`](../src/config.py) L22.

**Fix:** Set `RAZORPAY_WEBHOOK_SECRET` from the Razorpay **test** dashboard (never live). Sign the exact body. Handler after the check is a stub (`src/main.py` L286–288) — signature success ≠ Mandate update.

**Verify:** Integration tests in `tests/integration/test_webhooks.py` (`test_webhook_valid_signature`, `test_webhook_invalid_signature`, `test_webhook_missing_signature`).

### Idempotency miss after restart or `--workers`

**Symptom:** Same webhook accepted twice after process restart, or with multiple workers.

**Cause:** Module-global in-memory set.

**Proof:** [`src/main.py`](../src/main.py) L64 `_idempotency_keys: set[str] = set()`; L279–284 membership + add.

**Fix:** Safe envelope: **one worker**; after restart, reconcile in Razorpay test dashboard / Audit. An injectable store is planned, not present. Do not add Redis in a drive-by.

**Verify:** `Select-String -Path src/main.py -Pattern '_idempotency_keys'`.

### `ProtocolParseError` becomes a Refusal

**Symptom:** Execute returns `allowed=False` with a parse `reason_code`, no Razorpay call.

**Cause:** `run_execute` catches `ProtocolParseError`, writes Audit, returns `_refuse`.

**Proof:** [`src/services/protocol_parser.py`](../src/services/protocol_parser.py) L16–21, L33–85. [`src/services/checkout.py`](../src/services/checkout.py) L73–75. Test: `tests/integration/test_routes.py` `test_checkout_execute_parse_error_is_refusal`.

**Fix:** Repair the Protocol envelope; do not retry Money action on the same parse failure.

**Verify:** `.venv\Scripts\python.exe -m pytest -q tests/integration/test_routes.py::test_checkout_execute_parse_error_is_refusal`

### `idpi_detected` log lines

**Symptom:** Logs show `idpi_detected` or `idpi_detected: non-dict payload`.

**Cause:** Firewall rejected the envelope (IDPI / non-dict). Execute audits and refuses; no Money action.

**Proof:** [`src/services/firewall.py`](../src/services/firewall.py) L99–103. [`src/services/checkout.py`](../src/services/checkout.py) L63–67.

**Fix:** Strip hidden / bidi payload; re-send a clean Protocol envelope.

**Verify:** `.venv\Scripts\python.exe -m pytest -q tests/integration/test_routes.py::test_checkout_execute_firewall_refuses_no_money`

---

## Common Error Messages

| Literal | Meaning | Fix |
|---|---|---|
| `Missing X-Razorpay-Signature header` | No `X-Razorpay-Signature` | Send the header (`src/main.py` L244) |
| `Invalid webhook signature` | HMAC mismatch | Secret + exact body (`src/main.py` L255) |
| `Signature mismatch` | Inner `ValueError` before 401 | Same as above (`src/main.py` L253) |
| `merchant_not_found` / `sku_not_found` | Catalog 404 | Check merchant/SKU (`src/api/routes/catalog.py` L23, L36) |
| `mandate_not_found` | GET Mandate 404 | Store first (`src/api/routes/mandates.py` L50) |
| `Razorpay TEST MODE only` | `RAZORPAY_KEY_ID` not `rzp_test_` | Test keys only (`src/api/dependencies.py` L102–103) |
| `idpi_detected` | Firewall Refusal | See Firewall entry |
| `Could not find a part of the path` | Broken junction | See Environment |

---

## Known-Broken / Known-Stale Registry

| Item | Symptom | Status | Safe workaround |
|---|---|---|---|
| Junction farms | Path-not-found under `.claude/skills`, `data/skills` | Known (96 reparse points) | Scan `src`/`tests`; no bulk delete |
| Stale `docs/AGENTS.md` | Claims empty `src/`/`tests/`; no `run_execute` | Known stale | Use `checkout.py` + `MEMORY.md` |
| No CI workflow | No Actions runs | RESOLVED — `.github/workflows/test.yml` (SHA-pinned checkout + setup-uv, `uv sync --extra dev`, ruff, pytest) | Local `uv run pytest -q` still valid |
| Python drift | venv 3.14.6 vs docs 3.11 | Known | Read `requires-python`; `.venv` still runs tests |
| In-memory `_idempotency_keys` | Redelivery after restart / multi-worker | Known gap | Single worker; reconcile after restart |
| Duplicate rule generations | Two files per topic | Known | Keep both; money-path wins |
| `uv run pytest` unsatisfiable | `fastapi-users==12.1.0` METADATA `Requires-Dist: python-multipart==0.0.6` vs manifest `==0.0.32`; 0.0.6 is below CVE-2024-24762 (patched 0.0.7) | RESOLVED-BY-PIN (submission freeze): `python-multipart==0.0.6` matches fastapi-users' exact pin; `uv sync` restores. Known trade-off: CVE-2024-24762 ReDoS class in 0.0.6 — accepted for a test-mode gateway (DoS class only, no live keys); modernization (fastapi-users bump -> patched python-multipart) is a registered post-hackathon task. | `uv run pytest -q` |
| Graphify root leftovers | Working `.graphify_*` files land in repo root | Known — skill wrote CWD temps | Move them into `graphify-out/` after each run |

---

## Getting Help

- Security (webhook bypass, key leak, IDPI reaching a Money action, skill/hook tampering): [`SECURITY.md`](../SECURITY.md) — GitHub private advisory, **never** a public issue.
- Behavior / vocabulary / rules: `docs/CONTEXT.md`, `docs/SOUL.md`, this file, `.cursor/rules/`.
- Everything else: a normal GitHub issue with Proof (file:line) and the Verify command you ran.

---

## Unverified Suspicions

- Whether `get_vault` / `get_audit` `@lru_cache` has **already** caused a flake in CI-less local runs — **unproven**. Cache is real; a recorded flake is not.
- Whether OneDrive will repair the 96 junctions after a desktop restart — **unproven**.
