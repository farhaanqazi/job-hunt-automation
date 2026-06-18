from pathlib import Path

import httpx
import pytest

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.remotive import RemotiveSource, _parse_salary


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("$80000 - $120000", (80000, 120000, "USD")),
        ("$12K", (12000, 12000, "USD")),
        ("€90k - €110k", (90000, 110000, "EUR")),
        ("", (None, None, None)),
        (None, (None, None, None)),
        ("Competitive", (None, None, None)),
    ],
)
def test_parse_salary(raw, expected):
    assert _parse_salary(raw) == expected


def test_remotive_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/remotive_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://remotive.com/api/remote-jobs",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = RemotiveSource(client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_id == "remotive"
    assert job.source_job_id == "101"
    assert job.company == "Example Remote Co"
    assert job.remote_category == RemoteCategory.GLOBAL_REMOTE
    assert job.attribution == "Remotive"
    assert job.source_url.startswith("https://remotive.com/")
    # Salary "$80000 - $120000" is parsed into numbers.
    assert job.salary_min == 80000
    assert job.salary_max == 120000
    assert job.salary_currency == "USD"
