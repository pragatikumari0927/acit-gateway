"""PromptFirewall for C4 IDPI sanitization.

Deterministic static patterns only. No LLM.
sanitize(payload) -> (safe: bool, sanitized_or_none: dict | None, reason: str | None)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# IDPI patterns per query + design
_BAD_KEYS = {"instructions", "system", "tool_description", "developer_message"}
_IDPI_PHRASES = (
    "ignore previous",
    "ignore all previous",
    "you are now",
    "new instructions",
    "bypass",
    "exfiltrate",
)
# Zero-width, bidi-control and other invisible formatting code points. All of
# them are stripped before phrase matching so they cannot split a denylisted
# phrase.
_INVISIBLE_CHARS = frozenset(
    "\u00ad"  # soft hyphen
    "\u061c"  # arabic letter mark
    "\u180e"  # mongolian vowel separator
    "\u200b\u200c\u200d"  # zero width space / non-joiner / joiner
    "\u200e\u200f"  # left-to-right / right-to-left mark
    "\u202a\u202b\u202c\u202d\u202e"  # bidi embedding / pop / override
    "\u2060"  # word joiner
    "\u2066\u2067\u2068\u2069"  # bidi isolates
    "\ufeff"  # zero width no-break space (BOM)
)
_ZW_TABLE = {ord(c): None for c in _INVISIBLE_CHARS}
# Except for the soft hyphen, none of them have a legitimate use in envelope
# content, so their presence is itself IDPI: a bidi override can visually
# reorder an amount or SKU without changing the bytes, and silently stripping
# would mutate untrusted input with no Refusal. U+00AD is an optional
# line-break hint that occurs in real Catalog product text (German compounds),
# so it is normalised away rather than refused.
_SOFT_HYPHEN = "\u00ad"
_REFUSED_CHARS = _INVISIBLE_CHARS - {_SOFT_HYPHEN}


def _strip_zw(text: str) -> str:
    return text.translate(_ZW_TABLE)


def _has_invisible(text: str) -> bool:
    return any(c in _REFUSED_CHARS for c in text)


def _contains_idpi(text: str) -> bool:
    t = text.lower()
    if "<!--" in t:
        return True
    if any(p in t for p in _IDPI_PHRASES):
        return True
    return False


def _walk(obj: Any) -> bool:
    """Return True if IDPI patterns detected anywhere."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _BAD_KEYS:
                return True
            if _walk(v):
                return True
        return False
    if isinstance(obj, list):
        return any(_walk(x) for x in obj)
    if isinstance(obj, str):
        if _has_invisible(obj):
            return True
        return _contains_idpi(_strip_zw(obj))
    return False


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if k not in _BAD_KEYS}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, str):
        return _strip_zw(obj)
    return obj


class PromptFirewall:
    """Deterministic Prompt Firewall (C4). Static validation + pattern detection + sanitisation."""

    def sanitize(self, payload: dict) -> tuple[bool, Optional[dict], Optional[str]]:
        if not isinstance(payload, dict):
            logger.warning("idpi_detected: non-dict payload")
            return False, None, "idpi_detected"
        if _walk(payload):
            logger.warning("idpi_detected")
            return False, None, "idpi_detected"
        cleaned = _sanitize(payload)
        return True, cleaned, None
