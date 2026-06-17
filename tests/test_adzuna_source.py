from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.adzuna import AdzunaSource


def test_adzuna_source_uses_credentials_and_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/adzuna_jobs_in.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://api.adzuna.com/v1/api/jobs/in/search/1"
            "?app_id=app&app_key=key&what=python+remote&results_per_page=20"
        ),
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = AdzunaSource(app_id="app", app_key="key", client=httpx.Client())
    jobs = source.fetch(country="in", query="python remote")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_id == "adzuna"
    assert job.source_job_id == "adz-1"
    assert job.company == "Adzuna Example"
    assert job.remote_category == RemoteCategory.INDIA_REMOTE
    assert job.source_url == "https://www.adzuna.in/details/adz-1"
