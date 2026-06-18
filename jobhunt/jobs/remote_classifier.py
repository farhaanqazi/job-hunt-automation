from jobhunt.jobs.models import RemoteCategory

GLOBAL_REMOTE_TERMS = (
    "remote - worldwide",
    "remote worldwide",
    "worldwide",
    "work from anywhere",
    "anywhere in the world",
    "globally remote",
    "global remote",
    "remote - anywhere",
    "anywhere",
)

INDIA_REMOTE_TERMS = (
    "remote - india",
    "remote india",
    "based in india",
    "india remote",
)

# Signals that a role is restricted to a specific country/region. Checked BEFORE the
# global terms so a "work from anywhere in Brazil" style listing is not mislabeled global.
COUNTRY_RESTRICTED_TERMS = (
    "us only",
    "usa only",
    "united states only",
    "uk only",
    "europe only",
    "emea only",
    "canada only",
    "must be based in",
    "only candidates based in",
    "candidates located in",
    "located in",
    "must reside",
    "authorized to work in",
    "authorised to work in",
    "eligible to work in",
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

    # Restriction takes precedence over a generic "global" signal: a role that says
    # "remote, but you must be located in Brazil" is country-restricted, not global.
    if any(term in text for term in COUNTRY_RESTRICTED_TERMS):
        return RemoteCategory.COUNTRY_RESTRICTED_REMOTE

    if any(term in text for term in GLOBAL_REMOTE_TERMS):
        return RemoteCategory.GLOBAL_REMOTE

    if "remote" in text:
        return RemoteCategory.UNKNOWN

    return RemoteCategory.UNKNOWN
