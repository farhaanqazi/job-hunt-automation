from datetime import UTC, datetime

from jobhunt.jobs.models import CanonicalJob, RemoteCategory
from jobhunt.storage.database import create_schema, get_engine, session_scope
from jobhunt.storage.repositories import JobRepository


def test_job_repository_upserts_by_source_and_source_job_id():
    engine = get_engine("sqlite:///:memory:")
    create_schema(engine)

    job = CanonicalJob(
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

    with session_scope(engine) as session:
        repo = JobRepository(session)
        repo.upsert(job)
        repo.upsert(job)
        rows = repo.list_jobs()

        assert len(rows) == 1
        assert rows[0].title == "Python Backend Engineer"
