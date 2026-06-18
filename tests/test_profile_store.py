from jobhunt.profile.store import (
    load_active_profile,
    load_profile,
    profile_exists,
    resolve_profile_path,
    save_profile,
)
from jobhunt.settings import Settings

PROFILE = {
    "target_titles": ["Backend Engineer"],
    "preferred_skills": ["python", "fastapi"],
    "strong_skills": ["python"],
    "learning_skills": ["aws"],
    "excluded_keywords": ["onsite"],
    "preferred_locations": ["remote", "india"],
    "timezone": "Asia/Calcutta",
    "remote_only": True,
    "allow_contract": True,
    "allow_internship": False,
    "min_salary": 1200000,
    "salary_currency": "INR",
}


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "candidate_profile.yaml"
    save_profile(PROFILE, str(path))
    loaded = load_profile(str(path))
    assert loaded.target_titles == ["Backend Engineer"]
    assert loaded.remote_only is True


def test_resolve_prefers_saved_then_falls_back_to_example(tmp_path):
    path = tmp_path / "candidate_profile.yaml"
    settings = Settings(_env_file=None, profile_path=str(path))

    # Before saving: falls back to the bundled example.
    assert profile_exists(settings) is False
    assert resolve_profile_path(settings).endswith("candidate_profile.example.yaml")
    assert load_active_profile(settings).target_titles  # example loads fine

    # After saving: uses the personal profile.
    save_profile(PROFILE, str(path))
    assert profile_exists(settings) is True
    assert resolve_profile_path(settings) == str(path)
    assert load_active_profile(settings).salary_currency == "INR"
