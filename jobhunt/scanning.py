"""Shared scan workflow used by both the CLI and the web UI.

Keeps fetch -> score -> upsert in one place so the two front ends never drift.
Callers own the SQLAlchemy session (CLI via ``session_scope``, web via a request
session), and these functions just operate within it.
"""

from __future__ import annotations

import pathlib
import logging

import httpx
import yaml
from sqlalchemy.orm import Session

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.scorer import CandidateProfile, score_job
from jobhunt.settings import Settings
from jobhunt.sources.adzuna import AdzunaSource
from jobhunt.sources.arbeitnow import ArbeitnowSource
from jobhunt.sources.greenhouse import GreenhouseSource
from jobhunt.sources.lever import LeverSource
from jobhunt.sources.remotive import RemotiveSource
from jobhunt.sources.usajobs import USAJobsSource
from jobhunt.storage.repositories import JobRepository

DEFAULT_PROFILE_PATH = "config/candidate_profile.example.yaml"
TARGET_COMPANIES_PATH = "config/target_companies.yaml"

#: Sources that can be scanned directly from the UI without per-company config.
SCANNABLE_SOURCES: tuple[str, ...] = ("remotive", "arbeitnow", "adzuna", "usajobs")


class ScanError(RuntimeError):
    """Raised for an unsupported source or missing credentials."""


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> CandidateProfile:
    data = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
    return CandidateProfile(**data)


def fetch_jobs(
    source: str,
    settings: Settings,
    *,
    query: str = "python remote",
    country: str = "in",
) -> list[CanonicalJob]:
    if source == "remotive":
        return RemotiveSource().fetch()
    if source == "arbeitnow":
        return ArbeitnowSource().fetch()
    if source == "adzuna":
        if not settings.has_adzuna_credentials:
            raise ScanError("Adzuna requires ADZUNA_APP_ID and ADZUNA_APP_KEY")
        return AdzunaSource(settings.adzuna_app_id, settings.adzuna_app_key).fetch(
            country=country, query=query
        )
    if source == "usajobs":
        if not settings.has_usajobs_credentials:
            raise ScanError("USAJOBS requires USAJOBS_EMAIL and USAJOBS_API_KEY")
        return USAJobsSource(settings.usajobs_email, settings.usajobs_api_key).fetch(query=query)
    raise ScanError(f"Unsupported scan source: {source}")


def perform_scan(
    session: Session,
    source: str,
    *,
    settings: Settings,
    query: str = "python remote",
    country: str = "in",
    profile: CandidateProfile | None = None,
) -> int:
    """Fetch, score, and upsert jobs from one source. Returns the count stored."""
    from jobhunt.profile.store import load_active_profile

    profile = profile or load_active_profile(settings)
    jobs = fetch_jobs(source, settings, query=query, country=country)
    repo = JobRepository(session)
    for job in jobs:
        repo.upsert(score_job(job, profile))
    return len(jobs)


def scan_target_companies(
    session: Session,
    *,
    profile: CandidateProfile | None = None,
    path: str = TARGET_COMPANIES_PATH,
) -> dict[str, int]:
    """Scan every enabled Greenhouse/Lever target company. Returns counts per company."""
    profile = profile or load_profile()
    config = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8")) or {}
    repo = JobRepository(session)
    logger = logging.getLogger(__name__)
    results: dict[str, int] = {}

    for entry in config.get("greenhouse", []):
        if not entry.get("enabled"):
            continue
        try:
            jobs = GreenhouseSource(
                board_token=entry["board_token"], company_name=entry["company"]
            ).fetch()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch greenhouse jobs for {entry['company']}: {e}")
            continue
        live_job_ids = set()
        for job in jobs:
            repo.upsert(score_job(job, profile))
            live_job_ids.add(str(job.source_job_id))
        repo.mark_missing_jobs_expired("greenhouse", entry["company"], live_job_ids)
        results[entry["company"]] = len(jobs)

    for entry in config.get("lever", []):
        if not entry.get("enabled"):
            continue
        try:
            jobs = LeverSource(handle=entry["handle"], company_name=entry["company"]).fetch()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch lever jobs for {entry['company']}: {e}")
            continue
        live_job_ids = set()
        for job in jobs:
            repo.upsert(score_job(job, profile))
            live_job_ids.add(str(job.source_job_id))
        repo.mark_missing_jobs_expired("lever", entry["company"], live_job_ids)
        results[entry["company"]] = len(jobs)

    return results

def scan_all_sources(
    session: Session,
    *,
    settings: Settings,
    query: str = "python remote",
    country: str = "in",
    profile: CandidateProfile | None = None,
) -> dict[str, int]:
    """Scan all standard sources and all target companies."""
    from jobhunt.profile.store import load_active_profile
    profile = profile or load_active_profile(settings)
    
    results: dict[str, int] = {}
    logger = logging.getLogger(__name__)

    for source in SCANNABLE_SOURCES:
        try:
            count = perform_scan(
                session, source, settings=settings, query=query, country=country, profile=profile
            )
            results[source] = count
        except ScanError as exc:
            logger.warning(f"Skipping source {source}: {exc}")
        except Exception as exc:
            logger.error(f"Failed to fetch jobs for {source}: {exc}")

    try:
        target_results = scan_target_companies(session, profile=profile)
        results.update(target_results)
    except Exception as exc:
        logger.error(f"Target company scan failed during global scan: {exc}")

    return results
