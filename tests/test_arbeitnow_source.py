from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.arbeitnow import ArbeitnowSource


def test_arbeitnow_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/arbeitnow_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://www.arbeitnow.com/api/job-board-api",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = ArbeitnowSource(client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "arbeitnow"
    assert jobs[0].company == "Berlin Example"
    assert jobs[0].remote_category == RemoteCategory.UNKNOWN
