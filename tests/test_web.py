from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from jobhunt.jobs.models import CanonicalJob, RemoteCategory
from jobhunt.settings import Settings
from jobhunt.storage.repositories import JobRepository
from jobhunt.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db = tmp_path / "web.db"
    return create_app(Settings(_env_file=None, database_url=f"sqlite:///{db.as_posix()}"))


@pytest.fixture
def client(app):
    return TestClient(app)


def _seed(app) -> int:
    job = CanonicalJob(
        source_id="remotive",
        source_job_id="1",
        source_url="https://remotive.com/remote-jobs/python-backend-1",
        title="Python Backend Engineer",
        company="Example Remote Co",
        location_text="Remote India",
        remote_category=RemoteCategory.INDIA_REMOTE,
        description_text="Python API automation.",
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="h",
        fit_score=91,
        attribution="Remotive",
    )
    with app.state.session_factory() as session:
        row = JobRepository(session).upsert(job)
        session.flush()
        job_id = row.id
        session.commit()
    return job_id


def test_dashboard_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


def test_sources_page_lists_sources(client):
    resp = client.get("/sources")
    assert resp.status_code == 200
    assert "remotive" in resp.text


def test_jobs_fragment_reflects_filters(app, client):
    _seed(app)
    assert "Python Backend Engineer" in client.get("/jobs/fragment").text
    # A min_score above the job's score filters it out.
    assert "Python Backend Engineer" not in client.get("/jobs/fragment?min_score=99").text


def test_job_detail_and_status_change(app, client):
    job_id = _seed(app)

    detail = client.get(f"/jobs/{job_id}")
    assert detail.status_code == 200
    assert "Example Remote Co" in detail.text

    changed = client.post(
        f"/jobs/{job_id}/status", data={"value": "shortlisted", "fragment": "panel"}
    )
    assert changed.status_code == 200
    assert "Shortlisted" in changed.text

    assert "Shortlisted" in client.get(f"/jobs/{job_id}").text


def test_missing_job_returns_not_found_page(client):
    resp = client.get("/jobs/9999")
    assert resp.status_code == 200
    assert "not found" in resp.text.lower()


def test_export_download_returns_csv(app, client):
    _seed(app)
    resp = client.get("/export/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "source_url" in resp.text
    assert "https://remotive.com/remote-jobs/python-backend-1" in resp.text
