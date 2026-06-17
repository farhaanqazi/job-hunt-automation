def format_remote_label(value: str) -> str:
    labels = {
        "global_remote": "Global remote",
        "india_remote": "India remote",
        "timezone_compatible": "Timezone compatible",
        "country_restricted_remote": "Country restricted",
        "hybrid_or_onsite": "Hybrid or onsite",
        "unknown_remote_status": "Unknown",
    }
    return labels.get(value, value)
