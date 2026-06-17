"""Application status tracking.

Provides status transitions over stored jobs (shortlist, archive, applied, follow-up).
Full follow-up scheduling is future work (see plan section 12); the transitions below
are the v1 surface used by the CLI.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunt.jobs.models import JobStatus
from jobhunt.storage.database import JobRow


class JobNotFoundError(LookupError):
    """Raised when a job id does not exist."""


class ApplicationTracker:
    def __init__(self, session: Session) -> None:
        self.session = session

    def set_status(self, job_id: int, status: JobStatus) -> JobRow:
        row = self.session.get(JobRow, job_id)
        if row is None:
            raise JobNotFoundError(f"No job with id {job_id}")
        row.status = status.value
        return row

    def shortlist(self, job_id: int) -> JobRow:
        return self.set_status(job_id, JobStatus.SHORTLISTED)

    def archive(self, job_id: int) -> JobRow:
        return self.set_status(job_id, JobStatus.ARCHIVED)

    def mark_applied(self, job_id: int) -> JobRow:
        return self.set_status(job_id, JobStatus.APPLIED)

    def status_counts(self) -> dict[str, int]:
        stmt = select(JobRow.status, func.count()).group_by(JobRow.status)
        return {status: count for status, count in self.session.execute(stmt)}
