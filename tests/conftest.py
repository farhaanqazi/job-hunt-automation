"""Shared pytest fixtures and configuration.

Tests run from the project root (``pythonpath = ["."]`` in pyproject.toml), so source
adapters, fixtures, and config files resolve by relative path. The ``httpx_mock`` fixture
is provided by pytest-httpx and is used to stub all outbound HTTP in source tests; any
un-mocked request raises, keeping the suite fully offline.
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    """Return the text of a JSON fixture by file name."""

    def _read(name: str) -> str:
        return (FIXTURES_DIR / name).read_text(encoding="utf-8")

    return _read
