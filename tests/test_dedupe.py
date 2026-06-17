from datetime import UTC, datetime

from jobhunt.jobs.dedupe import dedupe_key
from jobhunt.jobs.models import CanonicalJob


def make_job(title: str, company: str, url: str) -> CanonicalJob:
    return CanonicalJob(
        source_id="test",
        source_job_id=url,
        source_url=url,
        title=title,
        company=company,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
    )


def test_dedupe_key_normalizes_title_company_and_url():
    left = make_job(
        "Senior Python Engineer", "Example, Inc.", "https://example.com/jobs/123?utm=abc"
    )
    right = make_job("senior python engineer", "Example Inc", "https://example.com/jobs/123")

    assert dedupe_key(left) == dedupe_key(right)
