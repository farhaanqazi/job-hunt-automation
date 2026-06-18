"""All HTTP routes for the web UI (full-page views + HTMX fragments)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from jobhunt.applications.tracker import ApplicationTracker, JobNotFoundError
from jobhunt.jobs.models import JobStatus, RemoteCategory
from jobhunt.reports.export_csv import rows_to_csv_text
from jobhunt.scanning import (
    SCANNABLE_SOURCES,
    ScanError,
    perform_scan,
    scan_target_companies,
)
from jobhunt.settings import Settings
from jobhunt.sources.registry import load_source_catalog
from jobhunt.storage.repositories import JobRepository
from jobhunt.web.deps import get_session, get_settings

router = APIRouter()

REMOTE_CATEGORIES = [c.value for c in RemoteCategory]
STATUSES = [s.value for s in JobStatus]


def _render(request: Request, template: str, **context):
    return request.app.state.templates.TemplateResponse(
        request, template, {"settings": request.app.state.settings, **context}
    )


def _source_ready(source_id: str, enabled: bool, settings: Settings) -> bool:
    if not enabled:
        return False
    if source_id == "adzuna":
        return settings.has_adzuna_credentials
    return True


# --- dashboard ---------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    repo = JobRepository(session)
    tracker = ApplicationTracker(session)
    return _render(
        request,
        "dashboard.html",
        active="dashboard",
        total=repo.total(),
        status_counts=tracker.status_counts(),
        remote_counts=repo.remote_category_counts(),
        source_counts=repo.source_counts(),
        top_jobs=repo.query()[:8],
    )


# --- jobs --------------------------------------------------------------------


def _parse_min_score(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _filtered(session: Session, *, min_score, remote, source, status, q):
    return JobRepository(session).query(
        min_score=_parse_min_score(min_score),
        remote_category=remote or None,
        source_id=source or None,
        status=status or None,
        search=q or None,
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    min_score: str | None = None,
    remote: str | None = None,
    source: str | None = None,
    status: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
):
    jobs = _filtered(
        session, min_score=min_score, remote=remote, source=source, status=status, q=q
    )
    return _render(
        request,
        "jobs.html",
        active="jobs",
        jobs=jobs,
        remote_categories=REMOTE_CATEGORIES,
        statuses=STATUSES,
        sources=sorted(JobRepository(session).source_counts()),
        filters={
            "min_score": min_score or "",
            "remote": remote or "",
            "source": source or "",
            "status": status or "",
            "q": q or "",
        },
    )


@router.get("/jobs/fragment", response_class=HTMLResponse)
def jobs_fragment(
    request: Request,
    min_score: str | None = None,
    remote: str | None = None,
    source: str | None = None,
    status: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
):
    jobs = _filtered(
        session, min_score=min_score, remote=remote, source=source, status=status, q=q
    )
    return _render(request, "partials/job_table.html", jobs=jobs)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int, session: Session = Depends(get_session)):
    repo = JobRepository(session)
    job = repo.get(job_id)
    if job is None:
        return _render(request, "not_found.html", active="jobs", job_id=job_id)
    catalog = load_source_catalog()
    return _render(
        request,
        "job_detail.html",
        active="jobs",
        job=job,
        meta=catalog.get(job.source_id),
        statuses=STATUSES,
    )


@router.post("/jobs/{job_id}/status", response_class=HTMLResponse)
def change_status(
    request: Request,
    job_id: int,
    value: str = Form(...),
    fragment: str = Form("row"),
    session: Session = Depends(get_session),
):
    try:
        tracker = ApplicationTracker(session)
        tracker.set_status(job_id, JobStatus(value))
    except (JobNotFoundError, ValueError):
        return Response(status_code=404)
    session.flush()
    job = JobRepository(session).get(job_id)
    template = "partials/status_panel.html" if fragment == "panel" else "partials/job_row.html"
    return _render(request, template, job=job, statuses=STATUSES)


# --- scan --------------------------------------------------------------------


@router.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request, settings: Settings = Depends(get_settings)):
    return _render(
        request,
        "scan.html",
        active="scan",
        scannable=SCANNABLE_SOURCES,
        has_adzuna=settings.has_adzuna_credentials,
    )


@router.post("/scan", response_class=HTMLResponse)
def run_scan(
    request: Request,
    source: str = Form(...),
    query: str = Form("python remote"),
    country: str = Form("in"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    try:
        count = perform_scan(
            session, source, settings=settings, query=query, country=country
        )
    except ScanError as exc:
        return _render(request, "partials/scan_result.html", error=str(exc))
    except Exception as exc:  # network / source errors surfaced to the user
        return _render(request, "partials/scan_result.html", error=f"Scan failed: {exc}")
    return _render(request, "partials/scan_result.html", count=count, source=source)


@router.post("/scan/targets", response_class=HTMLResponse)
def run_target_scan(request: Request, session: Session = Depends(get_session)):
    try:
        results = scan_target_companies(session)
    except Exception as exc:
        return _render(request, "partials/scan_result.html", error=f"Scan failed: {exc}")
    return _render(request, "partials/scan_result.html", results=results)


# --- sources -----------------------------------------------------------------


@router.get("/sources", response_class=HTMLResponse)
def sources_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
):
    catalog = load_source_catalog()
    counts = JobRepository(session).source_counts()
    rows = [
        {
            "meta": meta,
            "ready": _source_ready(sid, meta.enabled, settings),
            "count": counts.get(sid, 0),
        }
        for sid, meta in catalog.items()
    ]
    return _render(request, "sources.html", active="sources", rows=rows)


# --- export ------------------------------------------------------------------


@router.get("/export", response_class=HTMLResponse)
def export_page(request: Request, session: Session = Depends(get_session)):
    return _render(request, "export.html", active="export", total=JobRepository(session).total())


@router.get("/export/download")
def export_download(
    min_score: str | None = None,
    session: Session = Depends(get_session),
):
    rows = JobRepository(session).query(min_score=_parse_min_score(min_score))
    csv_text = rows_to_csv_text(rows)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jobs.csv"'},
    )
