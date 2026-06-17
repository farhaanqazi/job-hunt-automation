from jobhunt.jobs.models import RemoteCategory

GLOBAL_REMOTE_TERMS = (
    "remote - worldwide",
    "remote worldwide",
    "work from anywhere",
    "anywhere in the world",
    "globally remote",
)

INDIA_REMOTE_TERMS = (
    "remote - india",
    "remote india",
    "based in india",
    "india remote",
)

COUNTRY_RESTRICTED_TERMS = (
    "us only",
    "united states only",
    "uk only",
    "must be based in",
    "only candidates based in",
)

HYBRID_ONSITE_TERMS = (
    "hybrid",
    "in office",
    "onsite",
    "on-site",
    "office-based",
)


def classify_remote(location_text: str | None, description_text: str | None) -> RemoteCategory:
    text = f"{location_text or ''} {description_text or ''}".lower()

    if any(term in text for term in HYBRID_ONSITE_TERMS):
        return RemoteCategory.HYBRID_OR_ONSITE

    if any(term in text for term in INDIA_REMOTE_TERMS):
        return RemoteCategory.INDIA_REMOTE

    if any(term in text for term in GLOBAL_REMOTE_TERMS):
        return RemoteCategory.GLOBAL_REMOTE

    if "remote" in text and any(term in text for term in COUNTRY_RESTRICTED_TERMS):
        return RemoteCategory.COUNTRY_RESTRICTED_REMOTE

    if "remote" in text:
        return RemoteCategory.UNKNOWN

    return RemoteCategory.UNKNOWN
