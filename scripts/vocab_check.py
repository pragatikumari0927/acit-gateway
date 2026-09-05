#!/usr/bin/env python3
"""Vocabulary check hook - enforces CONTEXT.md terminology."""

import os
import sys

# Terms to flag (CONTEXT.md "Avoid" list)
PATTERNS = [
    "price",
    "intent",
    "order",
    "charge",
    "checkout",
    "transaction",
    "filter",
    "webhook",
    "trace",
    "inventory",
    "menu",
    "product feed",
    "permission slip",
    "consent blob",
    "secrets manager",
    "keychain",
    "auth service",
    "WAF",
    "moderator",
    "guard",
    "jailbreak",
    "rule",
]

# Exclusions - these patterns in the same file are OK
EXCLUSIONS = [
    "unit_amount_paise",
    "ProtocolParseError",
    "VaultError",
    "reason_code",
    "test_",
]


def check_file(path: str) -> list[str]:
    """Check a single file for vocabulary violations."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    violations = []
    for p in PATTERNS:
        if p in content:
            # Check if any exclusion is present in the file
            if not any(ex in content for ex in EXCLUSIONS):
                violations.append(f'{path}: found "{p}"')
    return violations


def main():
    violations = []

    for root, dirs, files in os.walk("src"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                violations.extend(check_file(path))

    for root, dirs, files in os.walk("tests"):
        for f in files:
            if f.endswith((".py", ".json")):
                path = os.path.join(root, f)
                violations.extend(check_file(path))

    if violations:
        for v in violations:
            print(v, file=sys.stderr)
        print("VOCAB VIOLATIONS FOUND - use CONTEXT.md terms", file=sys.stderr)
        return 1

    print("Vocabulary check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())