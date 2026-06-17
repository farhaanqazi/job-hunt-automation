"""Shared normalization helpers for source adapters.

Per-source ``_normalize`` methods live in their adapter modules. This module collects
cross-source helpers used while mapping raw payloads into :class:`CanonicalJob`.
"""

from hashlib import sha256
from typing import Any


def payload_hash(item: dict[str, Any]) -> str:
    """Stable hash of a raw source payload, used for change detection."""
    return sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
