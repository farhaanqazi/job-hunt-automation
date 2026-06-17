from datetime import UTC, datetime

from jobhunt.jobs.models import CanonicalJob, JobStatus, RemoteCategory


def test_canonical_job_model_accepts_required_fields():
    job = CanonicalJob(
        source_id="remotive",
        source_job_id="123",
        source_url="https://example.com/job/123",
        title="Python Backend Engineer",
        company="Example Co",
        location_text="Remote",
        remote_category=RemoteCategory.GLOBAL_REMOTE,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="abc123",
        attribution="Remotive",
    )

    assert job.status == JobStatus.FOUND
    assert job.remote_category == RemoteCategory.GLOBAL_REMOTE
