from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RemoteCategory(StrEnum):
    GLOBAL_REMOTE = "global_remote"
    INDIA_REMOTE = "india_remote"
    TIMEZONE_COMPATIBLE = "timezone_compatible"
    COUNTRY_RESTRICTED_REMOTE = "country_restricted_remote"
    HYBRID_OR_ONSITE = "hybrid_or_onsite"
    UNKNOWN = "unknown_remote_status"


class JobStatus(StrEnum):
    FOUND = "found"
    SHORTLISTED = "shortlisted"
    ARCHIVED = "archived"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFER = "offer"
    EXPIRED = "expired"


class CanonicalJob(BaseModel):
    source_id: str
    source_job_id: str
    source_url: str
    title: str
    company: str
    location_text: str | None = None
    remote_category: RemoteCategory = RemoteCategory.UNKNOWN
    description_text: str | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    tags: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime
    attribution: str | None = None
    raw_payload_hash: str
    fit_score: int | None = None
    fit_reasons: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.FOUND
    raw: dict[str, Any] = Field(default_factory=dict)
