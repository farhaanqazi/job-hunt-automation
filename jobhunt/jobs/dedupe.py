import re
from urllib.parse import urlsplit, urlunsplit

from jobhunt.jobs.models import CanonicalJob


def dedupe_key(job: CanonicalJob) -> str:
    title = _normalize_text(job.title)
    company = _normalize_text(job.company)
    url = _normalize_url(job.source_url)
    return f"{company}|{title}|{url}"


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    lowered = re.sub(r"\b(inc|ltd|llc|plc|pvt)\b", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _normalize_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
