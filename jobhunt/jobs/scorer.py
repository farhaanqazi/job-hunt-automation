from pydantic import BaseModel

from jobhunt.jobs.models import CanonicalJob, RemoteCategory


class CandidateProfile(BaseModel):
    target_titles: list[str]
    preferred_skills: list[str]
    strong_skills: list[str]
    learning_skills: list[str]
    excluded_keywords: list[str]
    preferred_locations: list[str]
    timezone: str
    remote_only: bool
    allow_contract: bool
    allow_internship: bool
    min_salary: int | None
    salary_currency: str | None


def score_job(job: CanonicalJob, profile: CandidateProfile) -> CanonicalJob:
    text = f"{job.title} {job.location_text or ''} {job.description_text or ''}".lower()
    score = 0
    reasons: list[str] = []
    concerns: list[str] = []

    if any(title in job.title.lower() for title in profile.target_titles):
        score += 25
        reasons.append("title match")

    for skill in profile.preferred_skills:
        if skill.lower() in text:
            score += 8
            reasons.append(skill.lower())

    for skill in profile.strong_skills:
        if skill.lower() in text:
            score += 6
            reasons.append(f"strong: {skill.lower()}")

    for skill in profile.learning_skills:
        if skill.lower() in text:
            score += 3
            reasons.append(f"learning: {skill.lower()}")

    if job.remote_category in {
        RemoteCategory.GLOBAL_REMOTE,
        RemoteCategory.INDIA_REMOTE,
        RemoteCategory.TIMEZONE_COMPATIBLE,
    }:
        score += 30
        reasons.append("remote match")
    elif profile.remote_only:
        score -= 30
        concerns.append("not remote-first")

    for keyword in profile.excluded_keywords:
        if keyword.lower() in text:
            score -= 20
            concerns.append(f"excluded keyword: {keyword.lower()}")

    if job.salary_min and profile.min_salary and job.salary_min >= profile.min_salary:
        score += 10
        reasons.append("salary match")

    job.fit_score = max(0, min(100, score))
    job.fit_reasons = sorted(set(reasons))
    job.concerns = sorted(set(concerns))
    return job
