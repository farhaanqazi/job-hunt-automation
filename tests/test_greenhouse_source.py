from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.greenhouse import GreenhouseSource


def test_greenhouse_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/greenhouse_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = GreenhouseSource(board_token="stripe", company_name="Stripe", client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "greenhouse"
    assert jobs[0].company == "Stripe"
    assert jobs[0].remote_category == RemoteCategory.UNKNOWN
