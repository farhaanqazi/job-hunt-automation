"""Verification layer: keep only items that actually appear in the source text.

This is the hard guarantee behind "the LLM is not allowed to hallucinate" — regardless of
what the model returns, an extracted skill/title/location survives only if it is present in
the CV or the user's typed answers.
"""

from __future__ import annotations

import re


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def is_grounded(item: str, source: str) -> bool:
    """True if ``item`` appears in ``source`` (whole-word for alphanumeric terms)."""
    term = _normalize(item)
    if not term:
        return False
    src = _normalize(source)
    if re.fullmatch(r"[a-z0-9 ]+", term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", src) is not None
    return term in src


def ground_filter(items: list[str], source: str) -> list[str]:
    """Drop items not supported by the source text; de-duplicate, preserve order."""
    kept: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = _normalize(item)
        if key and key not in seen and is_grounded(item, source):
            kept.append(item.strip())
            seen.add(key)
    return kept
