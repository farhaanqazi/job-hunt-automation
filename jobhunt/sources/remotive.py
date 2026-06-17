from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class RemotiveSource:
    source_id = "remotive"
    endpoint = "https://remotive.com/api/remote-jobs"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        response = self.client.get(self.endpoint)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("jobs", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("candidate_required_location")
        description_text = item.get("description")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["url"],
            title=item["title"],
            company=item["company_name"],
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=item.get("job_type"),
            tags=[item.get("category", "")],
            published_at=_parse_datetime(item.get("publication_date")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Remotive",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=UTC)
