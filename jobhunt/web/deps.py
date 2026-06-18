"""Request-scoped dependencies for the web app."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from jobhunt.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped session that commits on success, rolls back on error."""
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
