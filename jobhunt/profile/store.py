"""Load/save the active candidate profile (YAML)."""

from __future__ import annotations

from pathlib import Path

import yaml

from jobhunt.jobs.scorer import CandidateProfile
from jobhunt.settings import Settings

EXAMPLE_PROFILE_PATH = "config/candidate_profile.example.yaml"


def save_profile(profile: dict | CandidateProfile, path: str) -> None:
    data = profile.model_dump() if isinstance(profile, CandidateProfile) else dict(profile)
    # Validate before writing so we never persist an invalid profile.
    CandidateProfile(**data)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_profile(path: str) -> CandidateProfile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return CandidateProfile(**data)


def profile_exists(settings: Settings) -> bool:
    return Path(settings.profile_path).exists()


def resolve_profile_path(settings: Settings) -> str:
    """The saved personal profile if present, otherwise the bundled example."""
    return settings.profile_path if profile_exists(settings) else EXAMPLE_PROFILE_PATH


def load_active_profile(settings: Settings) -> CandidateProfile:
    return load_profile(resolve_profile_path(settings))
