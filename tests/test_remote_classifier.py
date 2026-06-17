from jobhunt.jobs.models import RemoteCategory
from jobhunt.jobs.remote_classifier import classify_remote


def test_classifies_global_remote():
    result = classify_remote("Remote - Worldwide", "Work from anywhere in the world")
    assert result == RemoteCategory.GLOBAL_REMOTE


def test_classifies_india_remote():
    result = classify_remote("Remote - India", "This role is open to candidates based in India.")
    assert result == RemoteCategory.INDIA_REMOTE


def test_classifies_country_restricted_remote():
    result = classify_remote("Remote - US only", "Applicants must be based in the United States.")
    assert result == RemoteCategory.COUNTRY_RESTRICTED_REMOTE


def test_classifies_hybrid_as_not_remote_first():
    result = classify_remote("Bangalore hybrid", "Three days per week in office.")
    assert result == RemoteCategory.HYBRID_OR_ONSITE


def test_classifies_unknown_when_text_is_ambiguous():
    result = classify_remote("", "Flexible working policy available.")
    assert result == RemoteCategory.UNKNOWN
