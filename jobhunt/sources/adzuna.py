from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class AdzunaSource:
    source_id = "adzuna"

    def __init__(
        self,
        app_id: str,
        app_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_key = app_key
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self, country: str, query: str, page: int = 1) -> list[CanonicalJob]:
        endpoint = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        response = self.client.get(
            endpoint,
            params={
                "app_id": self.app_id,
                "app_key": self.app_key,
                "what": query,
                "results_per_page": 20,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("results", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location", {}).get("display_name")
        description_text = item.get("description")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["redirect_url"],
            title=item["title"],
            company=item.get("company", {}).get("display_name", "Unknown company"),
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=None,
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            salary_currency=None,
            tags=[item.get("category", {}).get("label", "")],
            published_at=_parse_datetime(item.get("created")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Adzuna",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
