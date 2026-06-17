from __future__ import annotations

import logging
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from jobhunt.jobs.models import JobStatus
from jobhunt.jobs.scorer import CandidateProfile, score_job
from jobhunt.logging_config import configure_logging
from jobhunt.reports.console import format_remote_label
from jobhunt.reports.export_csv import rows_to_csv_text
from jobhunt.settings import Settings
from jobhunt.sources.registry import load_source_catalog
from jobhunt.storage.database import create_schema, get_engine, session_scope
from jobhunt.storage.repositories import JobRepository

app = typer.Typer(help="Remote-first job hunt automation")
sources_app = typer.Typer(help="Inspect configured job sources")
jobs_app = typer.Typer(help="Inspect stored jobs")
tracker_app = typer.Typer(help="Application tracking")
export_app = typer.Typer(help="Export stored jobs")
app.add_typer(sources_app, name="sources")
app.add_typer(jobs_app, name="jobs")
app.add_typer(tracker_app, name="tracker")
app.add_typer(export_app, name="export")

console = Console()
logger = logging.getLogger("jobhunt")

PROFILE_PATH = "config/candidate_profile.example.yaml"
ATTRIBUTION_NOTE = "Private use only. Preserve source URLs and attribution."


@app.callback()
def main() -> None:
    """Private remote-first job discovery and tracking assistant."""
    configure_logging(Settings().log_level)


def _load_profile(path: str = PROFILE_PATH) -> CandidateProfile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return CandidateProfile(**data)


def _bootstrap_engine() -> object:
    settings = Settings()
    engine = get_engine(settings.database_url)
    create_schema(engine)
    return engine


# --- sources -----------------------------------------------------------------


@sources_app.command("list")
def list_sources() -> None:
    """List the configured (allowed) job sources and their compliance posture."""
    catalog = load_source_catalog()
    table = Table(title="Configured job sources")
    table.add_column("Source")
    table.add_column("Type")
    table.add_column("Enabled")
    table.add_column("Data rights")
    table.add_column("Redistribution")

    for source in catalog.values():
        table.add_row(
            source.source_id,
            source.source_type,
            str(source.enabled),
            source.data_rights,
            str(source.redistribution_allowed),
        )

    console.print(table)


@sources_app.command("check")
def check_sources() -> None:
    """Report which sources are usable given currently available credentials."""
    settings = Settings()
    catalog = load_source_catalog()
    table = Table(title="Source readiness")
    table.add_column("Source")
    table.add_column("Status")

    for source in catalog.values():
        if source.source_id == "adzuna" and not settings.has_adzuna_credentials:
            status = "disabled (missing ADZUNA_APP_ID/ADZUNA_APP_KEY)"
        elif not source.enabled:
            status = "disabled (catalog)"
        else:
            status = "ready"
        table.add_row(source.source_id, status)

    console.print(table)


# --- scan --------------------------------------------------------------------


@app.command("scan")
def scan(
    source: str = typer.Option("remotive", "--source"),
    query: str = typer.Option("python remote", "--query"),
    country: str = typer.Option("in", "--country"),
) -> None:
    """Fetch, score, and store jobs from a single source."""
    from jobhunt.sources.adzuna import AdzunaSource
    from jobhunt.sources.remotive import RemotiveSource

    settings = Settings()
    engine = _bootstrap_engine()

    if source == "remotive":
        jobs = RemotiveSource().fetch()
    elif source == "adzuna":
        if not settings.has_adzuna_credentials:
            raise typer.BadParameter("Adzuna requires ADZUNA_APP_ID and ADZUNA_APP_KEY")
        jobs = AdzunaSource(settings.adzuna_app_id, settings.adzuna_app_key).fetch(
            country=country,
            query=query,
        )
    else:
        raise typer.BadParameter(f"Unsupported scan source: {source}")

    profile = _load_profile()
    scored_jobs = [score_job(job, profile) for job in jobs]

    with session_scope(engine) as session:
        repo = JobRepository(session)
        for job in scored_jobs:
            repo.upsert(job)

    logger.info("Stored %d jobs from %s", len(scored_jobs), source)
    console.print(f"Stored {len(scored_jobs)} jobs from {source}.")
    console.print(ATTRIBUTION_NOTE)


# --- jobs --------------------------------------------------------------------


@jobs_app.command("list")
def list_jobs(min_score: int | None = typer.Option(None, "--min-score")) -> None:
    """List stored jobs, highest fit first."""
    engine = _bootstrap_engine()
    with session_scope(engine) as session:
        rows = JobRepository(session).list_jobs(min_score=min_score)

        table = Table(title="Jobs")
        table.add_column("ID")
        table.add_column("Score")
        table.add_column("Remote")
        table.add_column("Company")
        table.add_column("Title")
        table.add_column("Source")

        for row in rows:
            table.add_row(
                str(row.id),
                str(row.fit_score or ""),
                format_remote_label(row.remote_category),
                row.company,
                row.title,
                row.source_id,
            )

    console.print(table)


@jobs_app.command("show")
def show_job(job_id: int = typer.Argument(...)) -> None:
    """Show full detail and compliance posture for a single job."""
    from jobhunt.storage.database import JobRow

    engine = _bootstrap_engine()
    catalog = load_source_catalog()
    with session_scope(engine) as session:
        row = session.get(JobRow, job_id)
        if row is None:
            raise typer.BadParameter(f"No job with id {job_id}")

        meta = catalog.get(row.source_id)
        console.print(f"Title: {row.title}")
        console.print(f"Company: {row.company}")
        console.print(f"Score: {row.fit_score if row.fit_score is not None else 'n/a'}")
        console.print(f"Remote: {format_remote_label(row.remote_category)}")
        console.print(f"Source: {row.attribution or row.source_id}")
        console.print(f"URL: {row.source_url}")
        if row.fit_reasons:
            console.print("\nStrong matches:")
            for reason in row.fit_reasons:
                console.print(f"- {reason}")
        if row.concerns:
            console.print("\nConcerns:")
            for concern in row.concerns:
                console.print(f"- {concern}")
        console.print("\nCompliance:")
        if meta is not None:
            console.print(f"- Attribution required: {'yes' if meta.requires_attribution else 'no'}")
            console.print(
                f"- Redistribution allowed: {'yes' if meta.redistribution_allowed else 'no'}"
            )


def _set_status(job_id: int, status: JobStatus) -> None:
    from jobhunt.applications.tracker import ApplicationTracker, JobNotFoundError

    engine = _bootstrap_engine()
    with session_scope(engine) as session:
        try:
            ApplicationTracker(session).set_status(job_id, status)
        except JobNotFoundError as exc:
            raise typer.BadParameter(str(exc)) from exc
    console.print(f"Job {job_id} -> {status.value}")


@jobs_app.command("archive")
def archive_job(job_id: int = typer.Argument(...)) -> None:
    """Archive a job."""
    _set_status(job_id, JobStatus.ARCHIVED)


@jobs_app.command("shortlist")
def shortlist_job(job_id: int = typer.Argument(...)) -> None:
    """Shortlist a job."""
    _set_status(job_id, JobStatus.SHORTLISTED)


# --- tracker -----------------------------------------------------------------


@tracker_app.command("status")
def tracker_status() -> None:
    """Show a count of stored jobs grouped by status."""
    from jobhunt.applications.tracker import ApplicationTracker

    engine = _bootstrap_engine()
    with session_scope(engine) as session:
        counts = ApplicationTracker(session).status_counts()

    table = Table(title="Application status")
    table.add_column("Status")
    table.add_column("Count")
    for status, count in sorted(counts.items()):
        table.add_row(status, str(count))
    console.print(table)


# --- export ------------------------------------------------------------------


@export_app.command("csv")
def export_csv(
    output: str = typer.Option("exports/jobs.csv", "--output"),
    min_score: int | None = typer.Option(None, "--min-score"),
) -> None:
    """Export stored jobs to a private local CSV file."""
    engine = _bootstrap_engine()
    with session_scope(engine) as session:
        rows = JobRepository(session).list_jobs(min_score=min_score)
        text = rows_to_csv_text(rows)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="")
    console.print(f"Wrote {len(rows)} jobs to {out_path}.")
    console.print(ATTRIBUTION_NOTE)
