"""All HTTP routes for the web UI (full-page views + HTMX fragments)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from jobhunt.applications.tracker import ApplicationTracker, JobNotFoundError
from jobhunt.jobs.models import JobStatus, RemoteCategory
from jobhunt.profile import builder, cv_extract, store
from jobhunt.profile.models import ProfileDraft, Question
from jobhunt.reports.export_csv import rows_to_csv_text
from jobhunt.scanning import (
    SCANNABLE_SOURCES,
    ScanError,
    perform_scan,
    scan_target_companies,
    scan_all_sources,
)
from jobhunt.profile.store import load_active_profile
from jobhunt.settings import Settings
from jobhunt.sources.registry import load_source_catalog
from jobhunt.storage.repositories import JobRepository
from jobhunt.web.deps import get_session, get_settings
from jobhunt import targets

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
    if source_id == "usajobs":
        return settings.has_usajobs_credentials
    return True


# --- dashboard ---------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
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
        has_profile=store.profile_exists(settings),
    )


# --- jobs --------------------------------------------------------------------


def _parse_min_score(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _filtered(session: Session, *, min_score, remote, source, status, q, sort_by=None, days_ago=None):
    return JobRepository(session).query(
        min_score=_parse_min_score(min_score),
        remote_category=remote or None,
        source_id=source or None,
        status=status or None,
        search=q or None,
        sort_by=sort_by or None,
        days_ago=int(days_ago) if days_ago else None,
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    min_score: str | None = None,
    remote: str | None = None,
    source: str | None = None,
    status: str | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    days_ago: str | None = None,
    session: Session = Depends(get_session),
):
    jobs = _filtered(
        session, min_score=min_score, remote=remote, source=source, status=status, q=q, sort_by=sort_by, days_ago=days_ago
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
            "sort_by": sort_by or "score",
            "days_ago": days_ago or "",
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
    sort_by: str | None = None,
    days_ago: str | None = None,
    session: Session = Depends(get_session),
):
    jobs = _filtered(
        session, min_score=min_score, remote=remote, source=source, status=status, q=q, sort_by=sort_by, days_ago=days_ago
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
    try:
        profile = load_active_profile(settings)
        default_query = " OR ".join(profile.target_titles) if profile.target_titles else "python remote"
    except Exception:
        default_query = "python remote"
        
    return _render(
        request,
        "scan.html",
        active="scan",
        scannable=SCANNABLE_SOURCES,
        has_adzuna=settings.has_adzuna_credentials,
        has_usajobs=settings.has_usajobs_credentials,
        default_query=default_query,
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


@router.post("/system/reset")
def wipe_database(session: Session = Depends(get_session)):
    repo = JobRepository(session)
    repo.clear_all()
    session.commit()
    return RedirectResponse(url="/jobs", status_code=303)


@router.post("/scan/all", response_class=HTMLResponse)
def run_global_scan(
    request: Request,
    query: str = Form("python remote"),
    country: str = Form("in"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    try:
        results = scan_all_sources(session, settings=settings, query=query, country=country)
    except Exception as exc:
        return _render(request, "partials/scan_result.html", error=f"Global scan failed: {exc}")
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


# --- profile / onboarding ----------------------------------------------------


def _questions_payload(questions: list[Question]) -> str:
    return json.dumps([q.model_dump() for q in questions])


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    saved: str | None = None,
    settings: Settings = Depends(get_settings),
):
    return _render(
        request,
        "profile.html",
        active="profile",
        exists=store.profile_exists(settings),
        profile=store.load_active_profile(settings),
        path=settings.profile_path,
        saved=bool(saved),
        has_groq=settings.has_groq_credentials,
    )


@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request, settings: Settings = Depends(get_settings)):
    return _render(
        request, "onboarding.html", active="profile", has_groq=settings.has_groq_credentials
    )


@router.post("/onboarding/analyze", response_class=HTMLResponse)
async def onboarding_analyze(
    request: Request,
    cv_text: str = Form(""),
    cv_file: UploadFile | None = File(None),
    settings: Settings = Depends(get_settings),
):
    text = cv_text or ""
    if cv_file is not None and cv_file.filename:
        data = await cv_file.read()
        try:
            text = (text + "\n" + cv_extract.extract_text(cv_file.filename, data)).strip()
        except cv_extract.CvExtractionError as exc:
            return _render(
                request, "onboarding.html", active="profile",
                error=str(exc), has_groq=settings.has_groq_credentials,
            )

    text = text.strip()
    if not text:
        return _render(
            request, "onboarding.html", active="profile",
            error="Please paste your CV text or upload a file.",
            has_groq=settings.has_groq_credentials,
        )

    result = builder.analyze(text, settings)
    return _render(
        request,
        "onboarding_questions.html",
        active="profile",
        cv_text=text,
        draft=result.draft.model_dump(),
        draft_json=result.draft.model_dump_json(),
        questions=result.questions,
        questions_json=_questions_payload(result.questions),
        source=result.source,
        notes=result.notes,
    )


@router.post("/onboarding/finalize", response_class=HTMLResponse)
async def onboarding_finalize(request: Request, settings: Settings = Depends(get_settings)):
    form = await request.form()
    cv_text = str(form.get("cv_text", ""))
    draft = ProfileDraft.model_validate_json(str(form.get("draft_json", "{}")))
    questions = [Question(**q) for q in json.loads(str(form.get("questions_json", "[]")))]
    answers = {q.id: str(form.get(f"ans_{q.id}", "")) for q in questions}

    result = builder.finalize(cv_text, draft, answers, questions)

    if not result.complete:
        known = {q.id for q in questions}
        merged = questions + [q for q in result.follow_up if q.id not in known]
        return _render(
            request,
            "onboarding_questions.html",
            active="profile",
            cv_text=cv_text,
            draft=result.draft.model_dump(),
            draft_json=result.draft.model_dump_json(),
            questions=merged,
            questions_json=_questions_payload(merged),
            source=result.source,
            error="A couple of required fields still need grounding — please fill them in.",
        )

    return _render(
        request,
        "onboarding_review.html",
        active="profile",
        profile=result.profile,
        profile_json=json.dumps(result.profile),
    )


@router.post("/onboarding/save")
async def onboarding_save(request: Request, settings: Settings = Depends(get_settings)):
    form = await request.form()
    profile = json.loads(str(form.get("profile_json", "{}")))
    store.save_profile(profile, settings.profile_path)
    return RedirectResponse(url="/profile?saved=1", status_code=303)


# --- targets -----------------------------------------------------------------


@router.get("/targets", response_class=HTMLResponse)
def targets_page(request: Request):
    t = targets.load_targets()
    ats_dir = targets.load_ats_directory()
    
    return _render(
        request,
        "targets.html",
        active="targets",
        targets=t,
        directory=ats_dir
    )


@router.post("/targets/add", response_class=HTMLResponse)
async def add_target(request: Request):
    form = await request.form()
    ats_type = str(form.get("ats_type", ""))
    
    # Handle the dropdown selection (which is a pipe-separated string "Company Name|token")
    selected_val = str(form.get("selected_company", ""))
    if selected_val and "|" in selected_val:
        company, token = selected_val.split("|", 1)
    else:
        # Handle custom addition
        company = str(form.get("company", "")).strip()
        token = str(form.get("token", "")).strip()
        
    if ats_type and token and company:
        targets.add_target(ats_type, company, token)
        
    return RedirectResponse(url="/targets", status_code=303)


@router.post("/targets/toggle", response_class=HTMLResponse)
async def toggle_target(request: Request):
    form = await request.form()
    ats_type = str(form.get("ats_type", ""))
    token = str(form.get("token", ""))
    enabled = str(form.get("enabled", "")) == "true"
    
    if ats_type and token:
        targets.toggle_target(ats_type, token, enabled)
        
    return RedirectResponse(url="/targets", status_code=303)


@router.post("/targets/delete", response_class=HTMLResponse)
async def delete_target(request: Request):
    form = await request.form()
    ats_type = str(form.get("ats_type", ""))
    token = str(form.get("token", ""))
    
    if ats_type and token:
        targets.delete_target(ats_type, token)
        
    return RedirectResponse(url="/targets", status_code=303)
