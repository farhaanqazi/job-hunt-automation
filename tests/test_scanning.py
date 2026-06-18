from pathlib import Path

import pytest

from jobhunt.scanning import ScanError, perform_scan
from jobhunt.settings import Settings
from jobhunt.storage.database import create_schema, get_engine, session_scope
from jobhunt.storage.repositories import JobRepository


def _memory_engine():
    engine = get_engine("sqlite:///:memory:")
    create_schema(engine)
    return engine


def test_perform_scan_fetches_scores_and_stores(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://remotive.com/api/remote-jobs",
        content=Path("tests/fixtures/remotive_jobs.json").read_text(encoding="utf-8"),
        headers={"content-type": "application/json"},
    )
    engine = _memory_engine()
    with session_scope(engine) as session:
        count = perform_scan(session, "remotive", settings=Settings(_env_file=None))
        rows = JobRepository(session).query()

        assert count == 1
        assert rows[0].source_id == "remotive"
        assert rows[0].fit_score is not None


def test_perform_scan_raises_for_adzuna_without_credentials():
    engine = _memory_engine()
    with session_scope(engine) as session:
        with pytest.raises(ScanError):
            perform_scan(
                session,
                "adzuna",
                settings=Settings(_env_file=None, adzuna_app_id="", adzuna_app_key=""),
            )


def test_perform_scan_rejects_unknown_source():
    engine = _memory_engine()
    with session_scope(engine) as session:
        with pytest.raises(ScanError):
            perform_scan(session, "nope", settings=Settings(_env_file=None))
