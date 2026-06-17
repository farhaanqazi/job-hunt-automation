from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class LeverSource:
    source_id = "lever"

    def __init__(
        self,
        handle: str,
        company_name: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.handle = handle
        self.company_name = company_name
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        endpoint = f"https://api.lever.co/v0/postings/{self.handle}"
        response = self.client.get(endpoint, params={"mode": "json"})
        response.raise_for_status()
        return [self._normalize(item) for item in response.json()]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        categories = item.get("categories", {})
        location_text = categories.get("location")
        description_text = item.get("descriptionPlain")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["hostedUrl"],
            title=item["text"],
            company=self.company_name,
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=categories.get("commitment"),
            tags=[categories.get("team", "")],
            published_at=_from_epoch_millis(item.get("createdAt")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Lever",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _from_epoch_millis(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)
