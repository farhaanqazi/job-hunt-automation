from datetime import UTC, datetime

import pytest

from jobhunt.applications.tracker import ApplicationTracker, JobNotFoundError
from jobhunt.jobs.models import CanonicalJob, JobStatus, RemoteCategory
from jobhunt.storage.database import create_schema, get_engine, session_scope
from jobhunt.storage.repositories import JobRepository


def _seed_job() -> CanonicalJob:
    return CanonicalJob(
        source_id="remotive",
        source_job_id="1",
        source_url="https://example.com/1",
        title="Python Backend Engineer",
        company="Example",
        remote_category=RemoteCategory.GLOBAL_REMOTE,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
        fit_score=90,
    )


def test_tracker_transitions_status_and_counts():
    engine = get_engine("sqlite:///:memory:")
    create_schema(engine)

    with session_scope(engine) as session:
        row = JobRepository(session).upsert(_seed_job())
        session.flush()
        job_id = row.id

        tracker = ApplicationTracker(session)
        tracker.shortlist(job_id)
        counts = tracker.status_counts()

        assert counts.get(JobStatus.SHORTLISTED.value) == 1


def test_tracker_raises_for_missing_job():
    engine = get_engine("sqlite:///:memory:")
    create_schema(engine)

    with session_scope(engine) as session:
        with pytest.raises(JobNotFoundError):
            ApplicationTracker(session).archive(999)
