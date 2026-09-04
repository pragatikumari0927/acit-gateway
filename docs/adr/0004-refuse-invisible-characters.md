---
status: accepted
---

# Refuse invisible characters instead of stripping them

C4 treats zero-width, bidi-control and other invisible formatting code points in a raw envelope as IDPI: `idpi_detected` Refusal plus an Audit event. Stripping them is retained, but only as normalisation in front of the substring denylist, so a phrase split by an invisible character (`ig<U+00AD>nore previous`) is still matched.

**Why:** The Firewall used to strip and pass. A payload whose only anomaly was a smuggled invisible character was silently repaired, so the tampering produced no Refusal and no entry in the hash chain — the one place we can prove the attack was seen. A bidi override can also reorder a displayed amount or SKU without changing a byte. Untrusted input is not ours to quietly rewrite: fail closed.

`\u00ad` (soft hyphen) is the documented exception. It is an optional line-break hint that appears in genuine merchant product text, notably German compounds, so refusing it is a false positive on the Catalog path. It stays in the strip table and out of the refusal set, which keeps the carve-out closed: it is removed from every string the Gateway forwards, and it cannot hide a denylisted phrase from the match.

**Considered:** keeping the silent strip, on the argument that a repaired envelope is a safe envelope. Rejected — a repaired envelope with no Refusal is indistinguishable from a clean one, and Track 02 is judged on the evidence, not the repair.

New invisible code points are refusals by default. Any further carve-out needs both halves: out of the refusal set, still in the strip table.
