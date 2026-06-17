from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.remotive import RemotiveSource


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
