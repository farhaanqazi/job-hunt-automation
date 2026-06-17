from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.lever import LeverSource


def test_lever_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/lever_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://api.lever.co/v0/postings/example?mode=json",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = LeverSource(
        handle="example", company_name="Example Lever Company", client=httpx.Client()
    )
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "lever"
    assert jobs[0].company == "Example Lever Company"
    assert jobs[0].remote_category == RemoteCategory.GLOBAL_REMOTE
