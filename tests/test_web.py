from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from jobhunt.jobs.models import CanonicalJob, RemoteCategory
from jobhunt.profile import store
from jobhunt.settings import Settings
from jobhunt.storage.repositories import JobRepository
from jobhunt.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db = tmp_path / "web.db"
    profile = tmp_path / "candidate_profile.yaml"
    return create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite:///{db.as_posix()}",
            profile_path=str(profile),
        )
    )


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


def test_profile_and_onboarding_pages_load(client):
    assert client.get("/profile").status_code == 200
    assert client.get("/onboarding").status_code == 200


def test_onboarding_analyze_offline_returns_questions(client):
    resp = client.post(
        "/onboarding/analyze",
        data={"cv_text": "Senior Python Developer. Skills: Python, FastAPI, AWS."},
    )
    assert resp.status_code == 200
    assert "Continue" in resp.text  # questions form rendered
    assert "Python" in resp.text  # grounded skill shown


def test_onboarding_finalize_and_save_writes_profile(app, client):
    import json

    draft = {"target_titles": ["Backend Engineer"], "preferred_skills": ["Python"]}
    questions = [{"id": "q_remote", "field": "remote_only", "kind": "yesno", "prompt": "Remote?"}]
    resp = client.post(
        "/onboarding/finalize",
        data={
            "cv_text": "Backend Engineer with Python experience.",
            "draft_json": json.dumps(draft),
            "questions_json": json.dumps(questions),
            "ans_q_remote": "yes",
        },
    )
    assert resp.status_code == 200
    assert "Save profile" in resp.text  # review screen

    profile = {
        "target_titles": ["Backend Engineer"],
        "preferred_skills": ["python"],
        "strong_skills": ["python"],
        "learning_skills": [],
        "excluded_keywords": [],
        "preferred_locations": ["remote"],
        "timezone": "Asia/Calcutta",
        "remote_only": True,
        "allow_contract": True,
        "allow_internship": False,
        "min_salary": None,
        "salary_currency": None,
    }
    saved = client.post("/onboarding/save", data={"profile_json": json.dumps(profile)})
    assert saved.status_code == 200  # followed redirect to /profile
    assert "saved" in saved.text.lower()
    # The personal profile file now exists and is used.
    assert store.profile_exists(app.state.settings) is True
