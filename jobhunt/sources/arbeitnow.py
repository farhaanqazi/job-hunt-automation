from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class ArbeitnowSource:
    source_id = "arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        response = self.client.get(self.endpoint)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("data", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location")
        description_text = item.get("description")
        if item.get("remote") is True:
            location_text = f"{location_text or ''} remote".strip()

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=item["slug"],
            source_url=item["url"],
            title=item["title"],
            company=item["company_name"],
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=", ".join(item.get("job_types", [])) or None,
            tags=item.get("tags", []),
            published_at=_from_epoch_seconds(item.get("created_at")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Arbeitnow",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _from_epoch_seconds(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)
