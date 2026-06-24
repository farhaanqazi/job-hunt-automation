from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx
import nh3

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


def reconstruct_and_sanitize_lever_html(item: dict[str, Any]) -> str:
    html_pieces = []
    intro_html = item.get("descriptionHtml", "")
    if intro_html:
        html_pieces.append(f'<div class="lever-intro">{intro_html}</div>')

    for section in item.get("lists", []):
        title = section.get("text", "")
        content = section.get("content", "")
        if title or content:
            section_html = '<div class="lever-section">'
            if title:
                section_html += f'<h3>{title}</h3>'
            if content:
                section_html += content
            section_html += '</div>'
            html_pieces.append(section_html)

    raw_html = "\n".join(html_pieces)
    safe_tags = {"p", "br", "strong", "em", "h3", "h4", "ul", "ol", "li", "div", "a"}
    return nh3.clean(raw_html, tags=safe_tags)


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
        description_text = reconstruct_and_sanitize_lever_html(item)

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
