from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class USAJobsSource:
    source_id = "usajobs"

    def __init__(
        self,
        email: str,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.email = email
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self, query: str = "") -> list[CanonicalJob]:
        endpoint = "https://data.usajobs.gov/api/Search"
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": self.email,
            "Authorization-Key": self.api_key,
        }
        params = {"RemoteIndicator": "true", "ResultsPerPage": 100}
        if query:
            params["Keyword"] = query

        response = self.client.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()

        items = payload.get("SearchResult", {}).get("SearchResultItems", [])
        return [self._normalize(item.get("MatchedObjectDescriptor", {})) for item in items]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        
        locations = item.get("PositionLocation", [])
        location_text = locations[0].get("LocationName") if locations else "United States"
        
        description_text = item.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
        if not description_text:
            description_text = item.get("QualificationSummary", "")
            
        salary_min = None
        salary_max = None
        salary_currency = "USD"
        
        remuneration = item.get("PositionRemuneration", [])
        if remuneration:
            salary_min_str = remuneration[0].get("MinimumRange")
            salary_max_str = remuneration[0].get("MaximumRange")
            try:
                salary_min = int(float(salary_min_str)) if salary_min_str else None
                salary_max = int(float(salary_max_str)) if salary_max_str else None
            except ValueError:
                pass
                
        tags = []
        for cat in item.get("JobCategory", []):
            if cat.get("Name"):
                tags.append(cat.get("Name"))

        company = item.get("OrganizationName", item.get("DepartmentName", "US Government"))
        
        employment_type = "Full-time"
        offering_type = item.get("PositionOfferingType", [])
        if offering_type:
            employment_type = offering_type[0].get("Name", "Full-time")
            
        source_id = item.get("PositionID", "")
        
        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(source_id),
            source_url=item.get("PositionURI", ""),
            title=item.get("PositionTitle", "Unknown Title"),
            company=company,
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=employment_type,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            tags=tags,
            published_at=_parse_datetime(item.get("PublicationStartDate")),
            fetched_at=datetime.now(tz=UTC),
            attribution="USAJOBS",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
