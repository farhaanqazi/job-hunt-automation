from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class JobRow(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source_id", "source_job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    location_text: Mapped[str | None] = mapped_column(Text)
    remote_category: Mapped[str] = mapped_column(String(64), nullable=False)
    description_text: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str | None] = mapped_column(String(128))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(16))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    attribution: Mapped[str | None] = mapped_column(String(255))
    raw_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    fit_score: Mapped[int | None] = mapped_column(Integer)
    fit_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    concerns: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


def get_engine(database_url: str):
    return create_engine(database_url, future=True)


def create_schema(engine) -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(engine) -> Iterator[Session]:
    session_factory = sessionmaker(bind=engine, future=True)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
