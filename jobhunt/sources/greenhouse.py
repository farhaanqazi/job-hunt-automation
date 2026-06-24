from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx
import nh3

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


def _sanitize_greenhouse_html(raw_html: str | None) -> str | None:
    if not raw_html:
        return raw_html
    safe_tags = {"p", "br", "strong", "em", "h3", "h4", "ul", "ol", "li", "div", "a"}
    return nh3.clean(raw_html, tags=safe_tags)


class GreenhouseSource:
    source_id = "greenhouse"

    def __init__(
        self,
        board_token: str,
        company_name: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.board_token = board_token
        self.company_name = company_name
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs"
        response = self.client.get(endpoint, params={"content": "true"})
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("jobs", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location", {}).get("name")
        description_text = _sanitize_greenhouse_html(item.get("content"))

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["absolute_url"],
            title=item["title"],
            company=self.company_name,
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            published_at=_parse_datetime(item.get("updated_at")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Greenhouse",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
