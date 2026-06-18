"""FastAPI application factory for the Job Hunt web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import sessionmaker

from jobhunt.settings import Settings
from jobhunt.storage.database import create_schema, get_engine
from jobhunt.web.presentation import TEMPLATE_GLOBALS
from jobhunt.web.routes import router

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="Job Hunt Automation", docs_url=None, redoc_url=None)

    engine = get_engine(settings.database_url)
    create_schema(engine)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals.update(TEMPLATE_GLOBALS)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, future=True)
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(router)
    return app
