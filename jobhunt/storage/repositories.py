from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunt.jobs.models import CanonicalJob
from jobhunt.storage.database import JobRow


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, job: CanonicalJob) -> JobRow:
        existing = self.session.scalar(
            select(JobRow).where(
                JobRow.source_id == job.source_id,
                JobRow.source_job_id == job.source_job_id,
            )
        )
        if existing is None:
            existing = JobRow(source_id=job.source_id, source_job_id=job.source_job_id)
            self.session.add(existing)

        existing.source_url = job.source_url
        existing.title = job.title
        existing.company = job.company
        existing.location_text = job.location_text
        existing.remote_category = job.remote_category.value
        existing.description_text = job.description_text
        existing.employment_type = job.employment_type
        existing.salary_min = job.salary_min
        existing.salary_max = job.salary_max
        existing.salary_currency = job.salary_currency
        existing.tags = job.tags
        existing.published_at = job.published_at
        existing.fetched_at = job.fetched_at
        existing.attribution = job.attribution
        existing.raw_payload_hash = job.raw_payload_hash
        existing.fit_score = job.fit_score
        existing.fit_reasons = job.fit_reasons
        existing.concerns = job.concerns
        existing.status = job.status.value
        existing.raw = job.raw
        return existing

    def list_jobs(self, min_score: int | None = None) -> list[JobRow]:
        stmt = select(JobRow).order_by(
            JobRow.fit_score.desc().nullslast(),
            JobRow.fetched_at.desc(),
        )
        if min_score is not None:
            stmt = stmt.where(JobRow.fit_score >= min_score)
        return list(self.session.scalars(stmt))
