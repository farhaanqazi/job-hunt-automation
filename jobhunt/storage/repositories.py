from sqlalchemy import func, select
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

    def mark_missing_jobs_expired(self, source_id: str, company: str, live_job_ids: set[str]) -> int:
        from jobhunt.jobs.models import JobStatus
        stmt = select(JobRow).where(
            JobRow.source_id == source_id,
            JobRow.company == company,
            JobRow.status == JobStatus.FOUND.value
        )
        expired_count = 0
        for db_job in self.session.scalars(stmt):
            if str(db_job.source_job_id) not in live_job_ids:
                db_job.status = JobStatus.EXPIRED.value
                expired_count += 1
        return expired_count

    def list_jobs(self, min_score: int | None = None) -> list[JobRow]:
        return self.query(min_score=min_score)

    def get(self, job_id: int) -> JobRow | None:
        return self.session.get(JobRow, job_id)

    def query(
        self,
        *,
        min_score: int | None = None,
        remote_category: str | None = None,
        source_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        days_ago: int | None = None,
    ) -> list[JobRow]:
        """Filtered, ranked job query shared by the CLI and the web UI."""
        from datetime import datetime, timedelta, timezone
        
        stmt = select(JobRow)
        if min_score is not None:
            stmt = stmt.where(JobRow.fit_score >= min_score)
        if remote_category:
            stmt = stmt.where(JobRow.remote_category == remote_category)
        if source_id:
            stmt = stmt.where(JobRow.source_id == source_id)
        if status:
            stmt = stmt.where(JobRow.status == status)
        if search:
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                func.lower(JobRow.title).like(like) | func.lower(JobRow.company).like(like)
            )
            
        if days_ago is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            stmt = stmt.where(func.coalesce(JobRow.published_at, JobRow.fetched_at) >= cutoff)

        if sort_by == "date":
            stmt = stmt.order_by(
                JobRow.fetched_at.desc(),
                JobRow.published_at.desc().nullslast(),
            )
        else:
            stmt = stmt.order_by(
                JobRow.fit_score.desc().nullslast(),
                JobRow.fetched_at.desc(),
            )
        return list(self.session.scalars(stmt))

    def total(self) -> int:
        return self.session.scalar(select(func.count()).select_from(JobRow)) or 0

    def clear_all(self) -> int:
        from sqlalchemy import delete
        result = self.session.execute(delete(JobRow))
        return result.rowcount

    def remote_category_counts(self) -> dict[str, int]:
        stmt = select(JobRow.remote_category, func.count()).group_by(JobRow.remote_category)
        return {category: count for category, count in self.session.execute(stmt)}

    def source_counts(self) -> dict[str, int]:
        stmt = select(JobRow.source_id, func.count()).group_by(JobRow.source_id)
        return {source: count for source, count in self.session.execute(stmt)}
