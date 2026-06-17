# Remote-First Job Hunt Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a private, remote-first job discovery, scoring, and tracking assistant that gathers active job openings from public/free-access APIs and company ATS feeds without scraping hostile job portals.

**Architecture:** The system is a Python CLI application with strict source adapters, a canonical job model, SQLite persistence, deterministic scoring, and human-approved workflows. It treats job data as proprietary third-party content unless a source explicitly says otherwise, stores attribution and canonical source URLs, and does not republish listings.

**Tech Stack:** Python 3.11+, Typer, httpx, pydantic, pydantic-settings, SQLAlchemy, SQLite, PyYAML, Rich, pytest, pytest-httpx, freezegun, ruff.

---

## 1. Product Scope

### 1.1 Primary User

The primary user is a single job seeker using the tool locally for personal job discovery and application tracking.

### 1.2 Primary Job Focus

The system optimizes for remote roles.

Remote priority categories:

1. `global_remote`: available globally or explicitly "anywhere".
2. `india_remote`: available to candidates based in India.
3. `timezone_compatible`: remote but constrained to a timezone compatible with India.
4. `country_restricted_remote`: remote but restricted to a country or region.
5. `hybrid_or_onsite`: not a good match unless explicitly allowed.
6. `unknown_remote_status`: needs manual review.

### 1.3 Initial Source Strategy

The system uses public/free-access APIs and public ATS feeds. These are not open source data sources. The API code is closed, and most listing data is proprietary.

Initial v1 sources:

1. Remotive
   - Purpose: remote-first public feed.
   - Auth: none.
   - Compliance: keep source URL and attribution/linkback.
   - Endpoint: `https://remotive.com/api/remote-jobs`

2. Adzuna
   - Purpose: broad search, including India and remote keyword searches.
   - Auth: query params `app_id` and `app_key`.
   - Env vars: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.
   - Endpoint shape: `https://api.adzuna.com/v1/api/jobs/{country}/search/{page}`

3. Greenhouse
   - Purpose: target-company monitoring.
   - Auth: none.
   - Limitation: per-company board feed, not broad search.
   - Endpoint shape: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`

4. Lever
   - Purpose: target-company monitoring.
   - Auth: none.
   - Limitation: per-company handle feed, not broad search.
   - Endpoint shape: `https://api.lever.co/v0/postings/{company}?mode=json`

5. Arbeitnow
   - Purpose: supplemental EU/Germany and remote feed.
   - Auth: none.
   - Endpoint: `https://www.arbeitnow.com/api/job-board-api`

Optional later sources:

6. Reed
   - Purpose: UK remote roles.
   - Auth: HTTP Basic auth with API key as username and empty password.
   - Env var: `REED_API_KEY`.

7. USAJOBS
   - Purpose: US federal remote roles.
   - Auth headers:
     - `Host: data.usajobs.gov`
     - `User-Agent: <USAJOBS_EMAIL>`
     - `Authorization-Key: <USAJOBS_API_KEY>`
   - Env vars: `USAJOBS_EMAIL`, `USAJOBS_API_KEY`.

### 1.4 Explicit Non-Goals

- Do not scrape LinkedIn, Indeed, Naukri, Instahyre, Wellfound, Apna, or other hostile/closed portals in v1.
- Do not auto-submit job applications.
- Do not republish or resell listings.
- Do not build a public job board.
- Do not invent candidate experience when generating later application material.
- Do not call an API "open source" unless the source code is actually published under an open source license.

---

## 2. Legal And Compliance Model

Every source record must include these metadata fields:

```yaml
source_id: remotive
display_name: Remotive
data_access: public_api
source_code_license: closed
data_rights: proprietary
redistribution_allowed: false
requires_attribution: true
canonical_url_required: true
usage_notes: "Personal job-search use only. Preserve source URL and attribution."
```

Every stored job must preserve:

- `source_id`
- `source_job_id`
- `source_url`
- `company_url` when available
- `attribution`
- `fetched_at`
- `raw_payload_hash`

The application must present source URLs in list/detail views. Generated reports must be private local reports and must not be formatted as public syndicated feeds.

---

## 3. Final File Structure

```text
f:\job_hunt_automation\
  main.py
  plan.md
  pyproject.toml
  README.md
  .gitignore
  .env.example
  config\
    candidate_profile.example.yaml
    source_catalog.yaml
    target_companies.yaml
  jobhunt\
    __init__.py
    cli.py
    settings.py
    http_client.py
    logging_config.py
    sources\
      __init__.py
      base.py
      remotive.py
      adzuna.py
      greenhouse.py
      lever.py
      arbeitnow.py
      reed.py
      usajobs.py
      registry.py
    jobs\
      __init__.py
      models.py
      normalize.py
      dedupe.py
      remote_classifier.py
      scorer.py
    storage\
      __init__.py
      database.py
      repositories.py
      migrations.py
    applications\
      __init__.py
      tracker.py
    reports\
      __init__.py
      console.py
      export_csv.py
  tests\
    conftest.py
    fixtures\
      remotive_jobs.json
      adzuna_jobs_in.json
      greenhouse_jobs.json
      lever_jobs.json
      arbeitnow_jobs.json
    test_settings.py
    test_source_catalog.py
    test_remotive_source.py
    test_adzuna_source.py
    test_greenhouse_source.py
    test_lever_source.py
    test_arbeitnow_source.py
    test_normalize.py
    test_dedupe.py
    test_remote_classifier.py
    test_scorer.py
    test_database.py
    test_cli.py
```

---

## 4. Data Model

### 4.1 Canonical Job Model

Create a single canonical job representation independent of source schema.

```python
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RemoteCategory(str, Enum):
    GLOBAL_REMOTE = "global_remote"
    INDIA_REMOTE = "india_remote"
    TIMEZONE_COMPATIBLE = "timezone_compatible"
    COUNTRY_RESTRICTED_REMOTE = "country_restricted_remote"
    HYBRID_OR_ONSITE = "hybrid_or_onsite"
    UNKNOWN = "unknown_remote_status"


class JobStatus(str, Enum):
    FOUND = "found"
    SHORTLISTED = "shortlisted"
    ARCHIVED = "archived"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFER = "offer"


class CanonicalJob(BaseModel):
    source_id: str
    source_job_id: str
    source_url: str
    title: str
    company: str
    location_text: str | None = None
    remote_category: RemoteCategory = RemoteCategory.UNKNOWN
    description_text: str | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    tags: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime
    attribution: str | None = None
    raw_payload_hash: str
    fit_score: int | None = None
    fit_reasons: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.FOUND
    raw: dict[str, Any] = Field(default_factory=dict)
```

### 4.2 Source Metadata Model

```python
from pydantic import BaseModel


class SourceMetadata(BaseModel):
    source_id: str
    display_name: str
    enabled: bool
    source_type: str
    data_access: str
    source_code_license: str
    data_rights: str
    redistribution_allowed: bool
    requires_attribution: bool
    canonical_url_required: bool
    rate_limit_per_minute: int
    usage_notes: str
```

### 4.3 Candidate Profile Model

```python
from pydantic import BaseModel


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
```

---

## 5. Source Catalog

`config/source_catalog.yaml` must be the source of truth for which APIs are allowed.

```yaml
sources:
  remotive:
    display_name: Remotive
    enabled: true
    source_type: open_remote_feed
    data_access: public_api
    source_code_license: closed
    data_rights: proprietary
    redistribution_allowed: false
    requires_attribution: true
    canonical_url_required: true
    rate_limit_per_minute: 20
    usage_notes: "Private personal use only. Preserve Remotive links and attribution."

  adzuna:
    display_name: Adzuna
    enabled: true
    source_type: broad_search
    data_access: keyed_public_api
    source_code_license: closed
    data_rights: proprietary
    redistribution_allowed: false
    requires_attribution: true
    canonical_url_required: true
    rate_limit_per_minute: 20
    usage_notes: "Use API credentials. Store canonical redirect URL."

  greenhouse:
    display_name: Greenhouse
    enabled: true
    source_type: target_company_ats
    data_access: public_ats_feed
    source_code_license: closed
    data_rights: proprietary
    redistribution_allowed: false
    requires_attribution: false
    canonical_url_required: true
    rate_limit_per_minute: 30
    usage_notes: "Per-company board token feed, not broad search."

  lever:
    display_name: Lever
    enabled: true
    source_type: target_company_ats
    data_access: public_ats_feed
    source_code_license: closed
    data_rights: proprietary
    redistribution_allowed: false
    requires_attribution: false
    canonical_url_required: true
    rate_limit_per_minute: 30
    usage_notes: "Per-company handle feed, not broad search."

  arbeitnow:
    display_name: Arbeitnow
    enabled: true
    source_type: regional_open_feed
    data_access: public_api
    source_code_license: closed
    data_rights: proprietary
    redistribution_allowed: false
    requires_attribution: true
    canonical_url_required: true
    rate_limit_per_minute: 20
    usage_notes: "Supplemental EU/Germany-skewed source."
```

---

## 6. Environment Variables

Create `.env.example`.

```env
# Runtime
JOBHUNT_ENV=development
JOBHUNT_DATABASE_URL=sqlite:///./jobhunt.db
JOBHUNT_LOG_LEVEL=INFO

# Adzuna
ADZUNA_APP_ID=
ADZUNA_APP_KEY=

# USAJOBS, optional v2 source
USAJOBS_EMAIL=
USAJOBS_API_KEY=

# Reed, optional v2 source
REED_API_KEY=
```

Rules:

- `.env` must be ignored by git.
- `.env.example` must be committed.
- The application must start without keyed sources. It should disable keyed sources with a clear warning when credentials are missing.
- Never print API keys in logs or exceptions.

---

## 7. CLI Design

### 7.1 Commands

```text
python main.py sources list
python main.py sources check
python main.py scan --source remotive
python main.py scan --source adzuna --query "python remote" --country in
python main.py scan --all
python main.py jobs list --min-score 70
python main.py jobs show <job-id>
python main.py jobs archive <job-id>
python main.py jobs shortlist <job-id>
python main.py tracker status
python main.py export csv --output exports/jobs.csv
```

### 7.2 Console Output Requirements

`jobs list` should show:

```text
ID  Score  Remote              Company      Title                         Source
12  91     India remote        Example Co   Python Backend Engineer       Remotive
13  84     Global remote       Example AI   Automation Engineer           Adzuna
14  52     Country restricted  Example Ltd  Backend Developer             Greenhouse
```

`jobs show <job-id>` should show:

```text
Title: Python Backend Engineer
Company: Example Co
Score: 91
Remote: India remote
Source: Remotive
URL: https://...

Strong matches:
- Python
- APIs
- automation

Concerns:
- Salary not listed
- Timezone not explicit

Compliance:
- Attribution required: yes
- Redistribution allowed: no
```

---

## 8. Task Plan

### Task 1: Project Skeleton And Tooling

**Files:**
- Modify: `main.py`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `jobhunt/__init__.py`
- Create: `jobhunt/cli.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing CLI smoke test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from jobhunt.cli import app


def test_cli_help_exits_successfully():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Remote-first job hunt automation" in result.output
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_cli.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt'
```

- [ ] **Step 3: Create project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "job-hunt-automation"
version = "0.1.0"
description = "Private remote-first job discovery and tracking assistant"
requires-python = ">=3.11"
dependencies = [
  "typer>=0.12.0",
  "rich>=13.7.0",
  "httpx>=0.27.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.2.0",
  "SQLAlchemy>=2.0.0",
  "PyYAML>=6.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-httpx>=0.30.0",
  "freezegun>=1.5.0",
  "ruff>=0.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 4: Create ignore rules**

Create `.gitignore`:

```gitignore
.env
.env.local
*.db
*.sqlite
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
venv/
exports/
```

- [ ] **Step 5: Create CLI app**

Create `jobhunt/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `jobhunt/cli.py`:

```python
import typer

app = typer.Typer(help="Remote-first job hunt automation")


@app.callback()
def main() -> None:
    """Private remote-first job discovery and tracking assistant."""
```

Modify `main.py`:

```python
from jobhunt.cli import app


if __name__ == "__main__":
    app()
```

- [ ] **Step 6: Run the test and verify it passes**

Run:

```powershell
pytest tests/test_cli.py -v
```

Expected:

```text
1 passed
```

---

### Task 2: Settings And Secret Handling

**Files:**
- Create: `.env.example`
- Create: `jobhunt/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write settings tests**

Create `tests/test_settings.py`:

```python
from jobhunt.settings import Settings


def test_settings_defaults_to_sqlite_database():
    settings = Settings()
    assert settings.database_url == "sqlite:///./jobhunt.db"


def test_adzuna_is_disabled_when_credentials_are_missing():
    settings = Settings(adzuna_app_id="", adzuna_app_key="")
    assert settings.has_adzuna_credentials is False


def test_adzuna_is_enabled_when_credentials_are_present():
    settings = Settings(adzuna_app_id="app", adzuna_app_key="key")
    assert settings.has_adzuna_credentials is True
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_settings.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt.settings'
```

- [ ] **Step 3: Create env example**

Create `.env.example`:

```env
JOBHUNT_ENV=development
JOBHUNT_DATABASE_URL=sqlite:///./jobhunt.db
JOBHUNT_LOG_LEVEL=INFO

ADZUNA_APP_ID=
ADZUNA_APP_KEY=

USAJOBS_EMAIL=
USAJOBS_API_KEY=

REED_API_KEY=
```

- [ ] **Step 4: Implement settings**

Create `jobhunt/settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )

    env: str = Field(default="development", validation_alias="JOBHUNT_ENV")
    database_url: str = Field(
        default="sqlite:///./jobhunt.db",
        validation_alias="JOBHUNT_DATABASE_URL",
    )
    log_level: str = Field(default="INFO", validation_alias="JOBHUNT_LOG_LEVEL")

    adzuna_app_id: str = Field(default="", validation_alias="ADZUNA_APP_ID")
    adzuna_app_key: str = Field(default="", validation_alias="ADZUNA_APP_KEY")

    usajobs_email: str = Field(default="", validation_alias="USAJOBS_EMAIL")
    usajobs_api_key: str = Field(default="", validation_alias="USAJOBS_API_KEY")

    reed_api_key: str = Field(default="", validation_alias="REED_API_KEY")

    @property
    def has_adzuna_credentials(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @property
    def has_usajobs_credentials(self) -> bool:
        return bool(self.usajobs_email and self.usajobs_api_key)

    @property
    def has_reed_credentials(self) -> bool:
        return bool(self.reed_api_key)
```

- [ ] **Step 5: Run settings tests**

Run:

```powershell
pytest tests/test_settings.py -v
```

Expected:

```text
3 passed
```

---

### Task 3: Source Catalog

**Files:**
- Create: `config/source_catalog.yaml`
- Create: `jobhunt/sources/base.py`
- Create: `jobhunt/sources/__init__.py`
- Create: `tests/test_source_catalog.py`

- [ ] **Step 1: Write source catalog tests**

Create `tests/test_source_catalog.py`:

```python
from pathlib import Path

import yaml

from jobhunt.sources.base import SourceMetadata


def test_source_catalog_contains_required_v1_sources():
    data = yaml.safe_load(Path("config/source_catalog.yaml").read_text(encoding="utf-8"))
    sources = data["sources"]
    assert {"remotive", "adzuna", "greenhouse", "lever", "arbeitnow"}.issubset(sources)


def test_sources_do_not_claim_to_be_open_source():
    data = yaml.safe_load(Path("config/source_catalog.yaml").read_text(encoding="utf-8"))
    for source_id, source in data["sources"].items():
        metadata = SourceMetadata(source_id=source_id, **source)
        assert metadata.source_code_license == "closed"
        assert metadata.redistribution_allowed is False
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_source_catalog.py -v
```

Expected:

```text
FileNotFoundError: config/source_catalog.yaml
```

- [ ] **Step 3: Implement source metadata model**

Create `jobhunt/sources/__init__.py`:

```python
"""Job source adapters."""
```

Create `jobhunt/sources/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class SourceMetadata(BaseModel):
    source_id: str
    display_name: str
    enabled: bool
    source_type: str
    data_access: str
    source_code_license: str
    data_rights: str
    redistribution_allowed: bool
    requires_attribution: bool
    canonical_url_required: bool
    rate_limit_per_minute: int
    usage_notes: str


class JobSource(ABC):
    source_id: str

    @abstractmethod
    def fetch(self) -> list[Any]:
        raise NotImplementedError
```

- [ ] **Step 4: Create source catalog**

Create `config/source_catalog.yaml` with the source catalog from section 5.

- [ ] **Step 5: Run source catalog tests**

Run:

```powershell
pytest tests/test_source_catalog.py -v
```

Expected:

```text
2 passed
```

---

### Task 4: Canonical Job Model

**Files:**
- Create: `jobhunt/jobs/__init__.py`
- Create: `jobhunt/jobs/models.py`
- Create: `tests/test_normalize.py`

- [ ] **Step 1: Write model construction test**

Create `tests/test_normalize.py`:

```python
from datetime import UTC, datetime

from jobhunt.jobs.models import CanonicalJob, JobStatus, RemoteCategory


def test_canonical_job_model_accepts_required_fields():
    job = CanonicalJob(
        source_id="remotive",
        source_job_id="123",
        source_url="https://example.com/job/123",
        title="Python Backend Engineer",
        company="Example Co",
        location_text="Remote",
        remote_category=RemoteCategory.GLOBAL_REMOTE,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="abc123",
        attribution="Remotive",
    )

    assert job.status == JobStatus.FOUND
    assert job.remote_category == RemoteCategory.GLOBAL_REMOTE
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_normalize.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt.jobs'
```

- [ ] **Step 3: Implement canonical job model**

Create `jobhunt/jobs/__init__.py`:

```python
"""Canonical job models and job-domain services."""
```

Create `jobhunt/jobs/models.py` with the code in section 4.1.

- [ ] **Step 4: Run model tests**

Run:

```powershell
pytest tests/test_normalize.py -v
```

Expected:

```text
1 passed
```

---

### Task 5: Remote Eligibility Classifier

**Files:**
- Create: `jobhunt/jobs/remote_classifier.py`
- Create: `tests/test_remote_classifier.py`

- [ ] **Step 1: Write classifier tests**

Create `tests/test_remote_classifier.py`:

```python
from jobhunt.jobs.models import RemoteCategory
from jobhunt.jobs.remote_classifier import classify_remote


def test_classifies_global_remote():
    result = classify_remote("Remote - Worldwide", "Work from anywhere in the world")
    assert result == RemoteCategory.GLOBAL_REMOTE


def test_classifies_india_remote():
    result = classify_remote("Remote - India", "This role is open to candidates based in India.")
    assert result == RemoteCategory.INDIA_REMOTE


def test_classifies_country_restricted_remote():
    result = classify_remote("Remote - US only", "Applicants must be based in the United States.")
    assert result == RemoteCategory.COUNTRY_RESTRICTED_REMOTE


def test_classifies_hybrid_as_not_remote_first():
    result = classify_remote("Bangalore hybrid", "Three days per week in office.")
    assert result == RemoteCategory.HYBRID_OR_ONSITE


def test_classifies_unknown_when_text_is_ambiguous():
    result = classify_remote("", "Flexible working policy available.")
    assert result == RemoteCategory.UNKNOWN
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_remote_classifier.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt.jobs.remote_classifier'
```

- [ ] **Step 3: Implement deterministic classifier**

Create `jobhunt/jobs/remote_classifier.py`:

```python
from jobhunt.jobs.models import RemoteCategory


GLOBAL_REMOTE_TERMS = (
    "remote - worldwide",
    "remote worldwide",
    "work from anywhere",
    "anywhere in the world",
    "globally remote",
)

INDIA_REMOTE_TERMS = (
    "remote - india",
    "remote india",
    "based in india",
    "india remote",
)

COUNTRY_RESTRICTED_TERMS = (
    "us only",
    "united states only",
    "uk only",
    "must be based in",
    "only candidates based in",
)

HYBRID_ONSITE_TERMS = (
    "hybrid",
    "in office",
    "onsite",
    "on-site",
    "office-based",
)


def classify_remote(location_text: str | None, description_text: str | None) -> RemoteCategory:
    text = f"{location_text or ''} {description_text or ''}".lower()

    if any(term in text for term in HYBRID_ONSITE_TERMS):
        return RemoteCategory.HYBRID_OR_ONSITE

    if any(term in text for term in INDIA_REMOTE_TERMS):
        return RemoteCategory.INDIA_REMOTE

    if any(term in text for term in GLOBAL_REMOTE_TERMS):
        return RemoteCategory.GLOBAL_REMOTE

    if "remote" in text and any(term in text for term in COUNTRY_RESTRICTED_TERMS):
        return RemoteCategory.COUNTRY_RESTRICTED_REMOTE

    if "remote" in text:
        return RemoteCategory.UNKNOWN

    return RemoteCategory.UNKNOWN
```

- [ ] **Step 4: Run classifier tests**

Run:

```powershell
pytest tests/test_remote_classifier.py -v
```

Expected:

```text
5 passed
```

---

### Task 6: Remotive Source Adapter

**Files:**
- Create: `tests/fixtures/remotive_jobs.json`
- Create: `jobhunt/http_client.py`
- Create: `jobhunt/sources/remotive.py`
- Create: `tests/test_remotive_source.py`

- [ ] **Step 1: Create Remotive fixture**

Create `tests/fixtures/remotive_jobs.json`:

```json
{
  "jobs": [
    {
      "id": 101,
      "url": "https://remotive.com/remote-jobs/software-dev/python-backend-engineer-101",
      "title": "Python Backend Engineer",
      "company_name": "Example Remote Co",
      "category": "Software Development",
      "job_type": "full_time",
      "candidate_required_location": "Worldwide",
      "publication_date": "2026-06-16T12:00:00",
      "description": "Work from anywhere. Python, APIs, automation.",
      "salary": "$80000 - $120000"
    }
  ]
}
```

- [ ] **Step 2: Write source test**

Create `tests/test_remotive_source.py`:

```python
from pathlib import Path

import httpx
import pytest

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.remotive import RemotiveSource


def test_remotive_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/remotive_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://remotive.com/api/remote-jobs",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = RemotiveSource(client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_id == "remotive"
    assert job.source_job_id == "101"
    assert job.company == "Example Remote Co"
    assert job.remote_category == RemoteCategory.GLOBAL_REMOTE
    assert job.attribution == "Remotive"
    assert job.source_url.startswith("https://remotive.com/")
```

- [ ] **Step 3: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_remotive_source.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt.sources.remotive'
```

- [ ] **Step 4: Implement Remotive adapter**

Create `jobhunt/sources/remotive.py`:

```python
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class RemotiveSource:
    source_id = "remotive"
    endpoint = "https://remotive.com/api/remote-jobs"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        response = self.client.get(self.endpoint)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("jobs", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("candidate_required_location")
        description_text = item.get("description")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["url"],
            title=item["title"],
            company=item["company_name"],
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=item.get("job_type"),
            tags=[item.get("category", "")],
            published_at=_parse_datetime(item.get("publication_date")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Remotive",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=UTC)
```

- [ ] **Step 5: Run Remotive tests**

Run:

```powershell
pytest tests/test_remotive_source.py -v
```

Expected:

```text
1 passed
```

---

### Task 7: Adzuna Source Adapter

**Files:**
- Create: `tests/fixtures/adzuna_jobs_in.json`
- Create: `jobhunt/sources/adzuna.py`
- Create: `tests/test_adzuna_source.py`

- [ ] **Step 1: Create Adzuna fixture**

Create `tests/fixtures/adzuna_jobs_in.json`:

```json
{
  "results": [
    {
      "id": "adz-1",
      "title": "Remote Python Developer",
      "company": {"display_name": "Adzuna Example"},
      "location": {"display_name": "India"},
      "redirect_url": "https://www.adzuna.in/details/adz-1",
      "description": "Remote India role for Python API development.",
      "created": "2026-06-16T10:00:00Z",
      "category": {"label": "IT Jobs"},
      "salary_min": 1200000,
      "salary_max": 2200000
    }
  ]
}
```

- [ ] **Step 2: Write Adzuna tests**

Create `tests/test_adzuna_source.py`:

```python
from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.adzuna import AdzunaSource


def test_adzuna_source_uses_credentials_and_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/adzuna_jobs_in.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://api.adzuna.com/v1/api/jobs/in/search/1"
            "?app_id=app&app_key=key&what=python+remote&results_per_page=20"
        ),
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = AdzunaSource(app_id="app", app_key="key", client=httpx.Client())
    jobs = source.fetch(country="in", query="python remote")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_id == "adzuna"
    assert job.source_job_id == "adz-1"
    assert job.company == "Adzuna Example"
    assert job.remote_category == RemoteCategory.INDIA_REMOTE
    assert job.source_url == "https://www.adzuna.in/details/adz-1"
```

- [ ] **Step 3: Run the test and verify it fails**

Run:

```powershell
pytest tests/test_adzuna_source.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'jobhunt.sources.adzuna'
```

- [ ] **Step 4: Implement Adzuna adapter**

Create `jobhunt/sources/adzuna.py`:

```python
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class AdzunaSource:
    source_id = "adzuna"

    def __init__(
        self,
        app_id: str,
        app_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_key = app_key
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self, country: str, query: str, page: int = 1) -> list[CanonicalJob]:
        endpoint = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        response = self.client.get(
            endpoint,
            params={
                "app_id": self.app_id,
                "app_key": self.app_key,
                "what": query,
                "results_per_page": 20,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("results", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location", {}).get("display_name")
        description_text = item.get("description")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["redirect_url"],
            title=item["title"],
            company=item.get("company", {}).get("display_name", "Unknown company"),
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=None,
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            salary_currency=None,
            tags=[item.get("category", {}).get("label", "")],
            published_at=_parse_datetime(item.get("created")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Adzuna",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
```

- [ ] **Step 5: Run Adzuna tests**

Run:

```powershell
pytest tests/test_adzuna_source.py -v
```

Expected:

```text
1 passed
```

---

### Task 8: Greenhouse And Lever Target-Company Sources

**Files:**
- Create: `config/target_companies.yaml`
- Create: `tests/fixtures/greenhouse_jobs.json`
- Create: `tests/fixtures/lever_jobs.json`
- Create: `jobhunt/sources/greenhouse.py`
- Create: `jobhunt/sources/lever.py`
- Create: `tests/test_greenhouse_source.py`
- Create: `tests/test_lever_source.py`

- [ ] **Step 1: Create target company config**

Create `config/target_companies.yaml`:

```yaml
greenhouse:
  - company: Stripe
    board_token: stripe
    enabled: true

lever:
  - company: Example Lever Company
    handle: example
    enabled: false
```

- [ ] **Step 2: Create ATS fixtures**

Create `tests/fixtures/greenhouse_jobs.json`:

```json
{
  "jobs": [
    {
      "id": 7954688,
      "title": "Remote Backend Engineer",
      "absolute_url": "https://stripe.com/jobs/search?gh_jid=7954688",
      "location": {"name": "Remote"},
      "content": "Remote role. Python and distributed systems.",
      "updated_at": "2026-06-16T18:00:00-04:00"
    }
  ]
}
```

Create `tests/fixtures/lever_jobs.json`:

```json
[
  {
    "id": "lev-1",
    "text": "Remote Platform Engineer",
    "hostedUrl": "https://jobs.lever.co/example/lev-1",
    "categories": {
      "team": "Engineering",
      "location": "Remote",
      "commitment": "Full-time"
    },
    "descriptionPlain": "Work from anywhere on platform automation.",
    "createdAt": 1781604000000
  }
]
```

- [ ] **Step 3: Write ATS tests**

Create `tests/test_greenhouse_source.py`:

```python
from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.greenhouse import GreenhouseSource


def test_greenhouse_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/greenhouse_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = GreenhouseSource(board_token="stripe", company_name="Stripe", client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "greenhouse"
    assert jobs[0].company == "Stripe"
    assert jobs[0].remote_category == RemoteCategory.UNKNOWN
```

Create `tests/test_lever_source.py`:

```python
from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.lever import LeverSource


def test_lever_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/lever_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://api.lever.co/v0/postings/example?mode=json",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = LeverSource(handle="example", company_name="Example Lever Company", client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "lever"
    assert jobs[0].company == "Example Lever Company"
    assert jobs[0].remote_category == RemoteCategory.GLOBAL_REMOTE
```

- [ ] **Step 4: Implement Greenhouse adapter**

Create `jobhunt/sources/greenhouse.py`:

```python
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class GreenhouseSource:
    source_id = "greenhouse"

    def __init__(
        self,
        board_token: str,
        company_name: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.board_token = board_token
        self.company_name = company_name
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs"
        response = self.client.get(endpoint, params={"content": "true"})
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("jobs", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location", {}).get("name")
        description_text = item.get("content")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["absolute_url"],
            title=item["title"],
            company=self.company_name,
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            published_at=_parse_datetime(item.get("updated_at")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Greenhouse",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
```

- [ ] **Step 5: Implement Lever adapter**

Create `jobhunt/sources/lever.py`:

```python
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class LeverSource:
    source_id = "lever"

    def __init__(
        self,
        handle: str,
        company_name: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.handle = handle
        self.company_name = company_name
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        endpoint = f"https://api.lever.co/v0/postings/{self.handle}"
        response = self.client.get(endpoint, params={"mode": "json"})
        response.raise_for_status()
        return [self._normalize(item) for item in response.json()]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        categories = item.get("categories", {})
        location_text = categories.get("location")
        description_text = item.get("descriptionPlain")

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=str(item["id"]),
            source_url=item["hostedUrl"],
            title=item["text"],
            company=self.company_name,
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=categories.get("commitment"),
            tags=[categories.get("team", "")],
            published_at=_from_epoch_millis(item.get("createdAt")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Lever",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _from_epoch_millis(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)
```

- [ ] **Step 6: Run ATS tests**

Run:

```powershell
pytest tests/test_greenhouse_source.py tests/test_lever_source.py -v
```

Expected:

```text
2 passed
```

---

### Task 9: Arbeitnow Source Adapter

**Files:**
- Create: `tests/fixtures/arbeitnow_jobs.json`
- Create: `jobhunt/sources/arbeitnow.py`
- Create: `tests/test_arbeitnow_source.py`

- [ ] **Step 1: Create Arbeitnow fixture**

Create `tests/fixtures/arbeitnow_jobs.json`:

```json
{
  "data": [
    {
      "slug": "senior-python-developer-example",
      "company_name": "Berlin Example",
      "title": "Senior Python Developer",
      "description": "Remote possible. Python APIs.",
      "remote": true,
      "url": "https://www.arbeitnow.com/jobs/companies/berlin-example/senior-python-developer-example",
      "tags": ["Python", "Backend"],
      "job_types": ["full-time"],
      "location": "Berlin",
      "created_at": 1781604000
    }
  ]
}
```

- [ ] **Step 2: Write Arbeitnow test**

Create `tests/test_arbeitnow_source.py`:

```python
from pathlib import Path

import httpx

from jobhunt.jobs.models import RemoteCategory
from jobhunt.sources.arbeitnow import ArbeitnowSource


def test_arbeitnow_source_normalizes_jobs(httpx_mock):
    payload = Path("tests/fixtures/arbeitnow_jobs.json").read_text(encoding="utf-8")
    httpx_mock.add_response(
        method="GET",
        url="https://www.arbeitnow.com/api/job-board-api",
        content=payload,
        headers={"content-type": "application/json"},
    )

    source = ArbeitnowSource(client=httpx.Client())
    jobs = source.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_id == "arbeitnow"
    assert jobs[0].company == "Berlin Example"
    assert jobs[0].remote_category == RemoteCategory.UNKNOWN
```

- [ ] **Step 3: Implement Arbeitnow adapter**

Create `jobhunt/sources/arbeitnow.py`:

```python
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from jobhunt.jobs.models import CanonicalJob
from jobhunt.jobs.remote_classifier import classify_remote


class ArbeitnowSource:
    source_id = "arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self) -> list[CanonicalJob]:
        response = self.client.get(self.endpoint)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("data", [])]

    def _normalize(self, item: dict[str, Any]) -> CanonicalJob:
        raw_payload_hash = sha256(repr(sorted(item.items())).encode("utf-8")).hexdigest()
        location_text = item.get("location")
        description_text = item.get("description")
        if item.get("remote") is True:
            location_text = f"{location_text or ''} remote".strip()

        return CanonicalJob(
            source_id=self.source_id,
            source_job_id=item["slug"],
            source_url=item["url"],
            title=item["title"],
            company=item["company_name"],
            location_text=location_text,
            remote_category=classify_remote(location_text, description_text),
            description_text=description_text,
            employment_type=", ".join(item.get("job_types", [])) or None,
            tags=item.get("tags", []),
            published_at=_from_epoch_seconds(item.get("created_at")),
            fetched_at=datetime.now(tz=UTC),
            attribution="Arbeitnow",
            raw_payload_hash=raw_payload_hash,
            raw=item,
        )


def _from_epoch_seconds(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)
```

- [ ] **Step 4: Run Arbeitnow tests**

Run:

```powershell
pytest tests/test_arbeitnow_source.py -v
```

Expected:

```text
1 passed
```

---

### Task 10: Deduplication

**Files:**
- Create: `jobhunt/jobs/dedupe.py`
- Create: `tests/test_dedupe.py`

- [ ] **Step 1: Write dedupe tests**

Create `tests/test_dedupe.py`:

```python
from datetime import UTC, datetime

from jobhunt.jobs.dedupe import dedupe_key
from jobhunt.jobs.models import CanonicalJob


def make_job(title: str, company: str, url: str) -> CanonicalJob:
    return CanonicalJob(
        source_id="test",
        source_job_id=url,
        source_url=url,
        title=title,
        company=company,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
    )


def test_dedupe_key_normalizes_title_company_and_url():
    left = make_job("Senior Python Engineer", "Example, Inc.", "https://example.com/jobs/123?utm=abc")
    right = make_job("senior python engineer", "Example Inc", "https://example.com/jobs/123")

    assert dedupe_key(left) == dedupe_key(right)
```

- [ ] **Step 2: Implement dedupe key**

Create `jobhunt/jobs/dedupe.py`:

```python
import re
from urllib.parse import urlsplit, urlunsplit

from jobhunt.jobs.models import CanonicalJob


def dedupe_key(job: CanonicalJob) -> str:
    title = _normalize_text(job.title)
    company = _normalize_text(job.company)
    url = _normalize_url(job.source_url)
    return f"{company}|{title}|{url}"


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    lowered = re.sub(r"\b(inc|ltd|llc|plc|pvt)\b", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _normalize_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
```

- [ ] **Step 3: Run dedupe tests**

Run:

```powershell
pytest tests/test_dedupe.py -v
```

Expected:

```text
1 passed
```

---

### Task 11: Scoring Engine

**Files:**
- Create: `config/candidate_profile.example.yaml`
- Create: `jobhunt/jobs/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Create candidate profile example**

Create `config/candidate_profile.example.yaml`:

```yaml
target_titles:
  - python developer
  - backend engineer
  - automation engineer
preferred_skills:
  - python
  - fastapi
  - api
  - automation
  - sql
strong_skills:
  - python
  - backend
  - scripting
learning_skills:
  - aws
  - docker
excluded_keywords:
  - onsite
  - sales
  - unpaid
preferred_locations:
  - remote
  - india
timezone: Asia/Calcutta
remote_only: true
allow_contract: true
allow_internship: false
min_salary: null
salary_currency: null
```

- [ ] **Step 2: Write scoring tests**

Create `tests/test_scorer.py`:

```python
from datetime import UTC, datetime

from jobhunt.jobs.models import CanonicalJob, RemoteCategory
from jobhunt.jobs.scorer import CandidateProfile, score_job


def test_remote_python_job_scores_high():
    profile = CandidateProfile(
        target_titles=["python developer", "backend engineer"],
        preferred_skills=["python", "api", "automation"],
        strong_skills=["python"],
        learning_skills=["aws"],
        excluded_keywords=["onsite", "unpaid"],
        preferred_locations=["remote", "india"],
        timezone="Asia/Calcutta",
        remote_only=True,
        allow_contract=True,
        allow_internship=False,
        min_salary=None,
        salary_currency=None,
    )
    job = CanonicalJob(
        source_id="remotive",
        source_job_id="1",
        source_url="https://example.com",
        title="Python Backend Engineer",
        company="Example",
        location_text="Remote India",
        remote_category=RemoteCategory.INDIA_REMOTE,
        description_text="Python API automation role.",
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
    )

    scored = score_job(job, profile)

    assert scored.fit_score >= 80
    assert "remote match" in scored.fit_reasons
    assert "python" in scored.fit_reasons


def test_onsite_job_scores_low_for_remote_only_profile():
    profile = CandidateProfile(
        target_titles=["python developer"],
        preferred_skills=["python"],
        strong_skills=["python"],
        learning_skills=[],
        excluded_keywords=["onsite"],
        preferred_locations=["remote"],
        timezone="Asia/Calcutta",
        remote_only=True,
        allow_contract=True,
        allow_internship=False,
        min_salary=None,
        salary_currency=None,
    )
    job = CanonicalJob(
        source_id="test",
        source_job_id="2",
        source_url="https://example.com/2",
        title="Python Developer",
        company="Example",
        location_text="Bangalore onsite",
        remote_category=RemoteCategory.HYBRID_OR_ONSITE,
        description_text="Onsite Python role.",
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
    )

    scored = score_job(job, profile)

    assert scored.fit_score < 50
    assert "not remote-first" in scored.concerns
```

- [ ] **Step 3: Implement scoring**

Create `jobhunt/jobs/scorer.py`:

```python
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
```

- [ ] **Step 4: Run scoring tests**

Run:

```powershell
pytest tests/test_scorer.py -v
```

Expected:

```text
2 passed
```

---

### Task 12: SQLite Persistence

**Files:**
- Create: `jobhunt/storage/__init__.py`
- Create: `jobhunt/storage/database.py`
- Create: `jobhunt/storage/repositories.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write repository test**

Create `tests/test_database.py`:

```python
from datetime import UTC, datetime

from jobhunt.jobs.models import CanonicalJob, RemoteCategory
from jobhunt.storage.database import create_schema, get_engine, session_scope
from jobhunt.storage.repositories import JobRepository


def test_job_repository_upserts_by_source_and_source_job_id():
    engine = get_engine("sqlite:///:memory:")
    create_schema(engine)

    job = CanonicalJob(
        source_id="remotive",
        source_job_id="1",
        source_url="https://example.com/1",
        title="Python Backend Engineer",
        company="Example",
        remote_category=RemoteCategory.GLOBAL_REMOTE,
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
        fit_score=90,
    )

    with session_scope(engine) as session:
        repo = JobRepository(session)
        repo.upsert(job)
        repo.upsert(job)
        rows = repo.list_jobs()

    assert len(rows) == 1
    assert rows[0].title == "Python Backend Engineer"
```

- [ ] **Step 2: Implement database schema**

Create `jobhunt/storage/__init__.py`:

```python
"""Persistence layer."""
```

Create `jobhunt/storage/database.py`:

```python
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
```

- [ ] **Step 3: Implement repository**

Create `jobhunt/storage/repositories.py`:

```python
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
        stmt = select(JobRow).order_by(JobRow.fit_score.desc().nullslast(), JobRow.fetched_at.desc())
        if min_score is not None:
            stmt = stmt.where(JobRow.fit_score >= min_score)
        return list(self.session.scalars(stmt))
```

- [ ] **Step 4: Run database tests**

Run:

```powershell
pytest tests/test_database.py -v
```

Expected:

```text
1 passed
```

---

### Task 13: Source Registry And Scan Command

**Files:**
- Create: `jobhunt/sources/registry.py`
- Modify: `jobhunt/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Extend CLI tests**

Update `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from jobhunt.cli import app


def test_cli_help_exits_successfully():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Remote-first job hunt automation" in result.output


def test_sources_list_command_outputs_known_sources():
    runner = CliRunner()
    result = runner.invoke(app, ["sources", "list"])
    assert result.exit_code == 0
    assert "remotive" in result.output
    assert "adzuna" in result.output
```

- [ ] **Step 2: Implement source registry**

Create `jobhunt/sources/registry.py`:

```python
from pathlib import Path

import yaml

from jobhunt.sources.base import SourceMetadata


def load_source_catalog(path: str = "config/source_catalog.yaml") -> dict[str, SourceMetadata]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {
        source_id: SourceMetadata(source_id=source_id, **source)
        for source_id, source in data["sources"].items()
    }
```

- [ ] **Step 3: Add CLI source commands**

Modify `jobhunt/cli.py`:

```python
import typer
from rich.console import Console
from rich.table import Table

from jobhunt.sources.registry import load_source_catalog

app = typer.Typer(help="Remote-first job hunt automation")
sources_app = typer.Typer(help="Inspect configured job sources")
app.add_typer(sources_app, name="sources")

console = Console()


@app.callback()
def main() -> None:
    """Private remote-first job discovery and tracking assistant."""


@sources_app.command("list")
def list_sources() -> None:
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
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
pytest tests/test_cli.py -v
```

Expected:

```text
2 passed
```

---

### Task 14: Job Listing And Console Reports

**Files:**
- Create: `jobhunt/reports/__init__.py`
- Create: `jobhunt/reports/console.py`
- Modify: `jobhunt/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write report rendering unit test**

Create `tests/test_reports_console.py`:

```python
from jobhunt.reports.console import format_remote_label


def test_format_remote_label_humanizes_remote_category():
    assert format_remote_label("india_remote") == "India remote"
    assert format_remote_label("global_remote") == "Global remote"
```

- [ ] **Step 2: Implement report helper**

Create `jobhunt/reports/__init__.py`:

```python
"""Report and export helpers."""
```

Create `jobhunt/reports/console.py`:

```python
def format_remote_label(value: str) -> str:
    labels = {
        "global_remote": "Global remote",
        "india_remote": "India remote",
        "timezone_compatible": "Timezone compatible",
        "country_restricted_remote": "Country restricted",
        "hybrid_or_onsite": "Hybrid or onsite",
        "unknown_remote_status": "Unknown",
    }
    return labels.get(value, value)
```

- [ ] **Step 3: Add jobs command group**

Modify `jobhunt/cli.py` to add a `jobs` app with `list`.

```python
jobs_app = typer.Typer(help="Inspect stored jobs")
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs(min_score: int | None = typer.Option(None, "--min-score")) -> None:
    from jobhunt.settings import Settings
    from jobhunt.storage.database import create_schema, get_engine, session_scope
    from jobhunt.storage.repositories import JobRepository
    from jobhunt.reports.console import format_remote_label

    settings = Settings()
    engine = get_engine(settings.database_url)
    create_schema(engine)

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
```

- [ ] **Step 4: Run report tests**

Run:

```powershell
pytest tests/test_reports_console.py -v
```

Expected:

```text
1 passed
```

---

### Task 15: Scan Implementation

**Files:**
- Modify: `jobhunt/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Add scan command behavior**

The scan command must:

1. Load settings.
2. Create database schema.
3. Instantiate requested source.
4. Fetch jobs.
5. Score jobs.
6. Upsert jobs.
7. Print count and source attribution note.

Initial implemented source for scan should be `remotive` because it needs no key.

- [ ] **Step 2: Add command implementation**

Modify `jobhunt/cli.py`:

```python
@app.command("scan")
def scan(
    source: str = typer.Option("remotive", "--source"),
    query: str = typer.Option("python remote", "--query"),
    country: str = typer.Option("in", "--country"),
) -> None:
    from pathlib import Path

    import yaml

    from jobhunt.jobs.scorer import CandidateProfile, score_job
    from jobhunt.settings import Settings
    from jobhunt.sources.adzuna import AdzunaSource
    from jobhunt.sources.remotive import RemotiveSource
    from jobhunt.storage.database import create_schema, get_engine, session_scope
    from jobhunt.storage.repositories import JobRepository

    settings = Settings()
    engine = get_engine(settings.database_url)
    create_schema(engine)

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

    profile_data = yaml.safe_load(
        Path("config/candidate_profile.example.yaml").read_text(encoding="utf-8")
    )
    profile = CandidateProfile(**profile_data)
    scored_jobs = [score_job(job, profile) for job in jobs]

    with session_scope(engine) as session:
        repo = JobRepository(session)
        for job in scored_jobs:
            repo.upsert(job)

    console.print(f"Stored {len(scored_jobs)} jobs from {source}.")
    console.print("Private use only. Preserve source URLs and attribution.")
```

- [ ] **Step 3: Run full test suite**

Run:

```powershell
pytest -v
```

Expected:

```text
all tests passed
```

- [ ] **Step 4: Run a local smoke command without network**

Run:

```powershell
python main.py sources list
```

Expected:

```text
Configured job sources
remotive
adzuna
greenhouse
lever
arbeitnow
```

---

### Task 16: CSV Export

**Files:**
- Create: `jobhunt/reports/export_csv.py`
- Modify: `jobhunt/cli.py`
- Create: `tests/test_export_csv.py`

- [ ] **Step 1: Write CSV export test**

Create `tests/test_export_csv.py`:

```python
from types import SimpleNamespace

from jobhunt.reports.export_csv import rows_to_csv_text


def test_rows_to_csv_text_includes_source_url_and_attribution():
    rows = [
        SimpleNamespace(
            id=1,
            fit_score=90,
            remote_category="global_remote",
            company="Example",
            title="Python Engineer",
            source_id="remotive",
            source_url="https://example.com/job",
            attribution="Remotive",
            status="found",
        )
    ]

    text = rows_to_csv_text(rows)

    assert "source_url" in text
    assert "https://example.com/job" in text
    assert "Remotive" in text
```

- [ ] **Step 2: Implement CSV export helper**

Create `jobhunt/reports/export_csv.py`:

```python
import csv
from io import StringIO


def rows_to_csv_text(rows) -> str:
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "fit_score",
            "remote_category",
            "company",
            "title",
            "source_id",
            "source_url",
            "attribution",
            "status",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.id,
                "fit_score": row.fit_score,
                "remote_category": row.remote_category,
                "company": row.company,
                "title": row.title,
                "source_id": row.source_id,
                "source_url": row.source_url,
                "attribution": row.attribution,
                "status": row.status,
            }
        )
    return output.getvalue()
```

- [ ] **Step 3: Run CSV tests**

Run:

```powershell
pytest tests/test_export_csv.py -v
```

Expected:

```text
1 passed
```

---

## 9. Live Validation Plan

After unit tests pass, validate real sources manually.

### 9.1 Remotive

Run:

```powershell
python main.py scan --source remotive
python main.py jobs list --min-score 70
```

Expected:

- Command completes without credentials.
- Jobs are stored.
- Each job has `source_url`.
- CLI prints attribution warning.

### 9.2 Adzuna India Remote

Create `.env` locally:

```env
ADZUNA_APP_ID=actual_value
ADZUNA_APP_KEY=actual_value
```

Run:

```powershell
python main.py scan --source adzuna --country in --query "python remote"
python main.py jobs list --min-score 70
```

Expected:

- Command uses Adzuna credentials.
- Results include India/remote keyword matches.
- Missing credentials produce a clear error without stack trace.

### 9.3 Greenhouse

Add scan support after the base CLI works. Validate with known public board token:

```powershell
python main.py scan-company --ats greenhouse --company Stripe --token stripe
```

Expected:

- Remote roles, if present, are stored.
- Non-remote roles score lower.
- The user understands this is target-company monitoring, not broad search.

---

## 10. Quality Gates

Before calling v1 complete:

- [ ] `pytest -v` passes.
- [ ] `ruff check .` passes.
- [ ] `.env` is not committed.
- [ ] `.env.example` exists.
- [ ] Every job stores `source_url`.
- [ ] Every source in `source_catalog.yaml` has `redistribution_allowed: false`.
- [ ] Remotive jobs preserve attribution.
- [ ] Adzuna works only when credentials are present.
- [ ] Greenhouse and Lever are documented as company-targeted feeds.
- [ ] CLI can list, scan, store, score, and export jobs.
- [ ] The README says these are public/free-access APIs, not open source APIs.

---

## 11. README Content Requirements

The README must include:

```markdown
# Job Hunt Automation

Private remote-first job discovery and tracking assistant.

This project uses public/free-access job APIs and public ATS feeds. These are not open source data sources. Most job listings remain proprietary third-party content. Use this tool for private personal job search workflows only, preserve source URLs and attribution, respect rate limits, and do not republish listings.

## V1 Sources

- Remotive: remote feed, no key, attribution required.
- Adzuna: broad search, key required.
- Greenhouse: target-company ATS feed, no key, board token required.
- Lever: target-company ATS feed, no key, company handle required.
- Arbeitnow: supplemental EU/Germany feed, no key.

## Setup

1. Create a virtual environment.
2. Install the project with dev dependencies.
3. Copy `.env.example` to `.env`.
4. Add API keys only for sources you want to enable.
5. Run `python main.py sources list`.
```

---

## 12. Future Work

Add these only after v1 works reliably:

1. Reed source adapter for UK remote roles.
2. USAJOBS source adapter for US public-sector remote roles.
3. Better remote classifier using structured rules plus source-specific hints.
4. Application tracker commands: `shortlist`, `archive`, `applied`, `follow-up`.
5. Resume bullet and cover letter draft generation with strict no-invention rules.
6. Streamlit or FastAPI dashboard for review.
7. Target-company discovery list for remote-friendly companies.
8. Rate-limit persistence and backoff across runs.
9. HTML stripping and text cleanup for source descriptions.
10. Duplicate detection across sources using title/company/URL similarity.

---

## 13. Implementation Order Summary

1. Project skeleton.
2. Settings and `.env.example`.
3. Source catalog and compliance metadata.
4. Canonical job model.
5. Remote classifier.
6. Remotive adapter.
7. Adzuna adapter.
8. Greenhouse and Lever adapters.
9. Arbeitnow adapter.
10. Deduplication.
11. Scoring.
12. SQLite persistence.
13. Source registry and CLI commands.
14. Console reports.
15. Scan workflow.
16. CSV export.
17. Live source validation.
18. README and quality gates.

---

## 14. Notes For API Keys

The user should not paste secrets into chat.

Required for best v1:

```env
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

Optional later:

```env
USAJOBS_EMAIL=
USAJOBS_API_KEY=
REED_API_KEY=
```

Reed auth detail:

```text
HTTP Basic auth
username = REED_API_KEY
password = empty string
```

USAJOBS auth detail:

```text
Host: data.usajobs.gov
User-Agent: USAJOBS_EMAIL
Authorization-Key: USAJOBS_API_KEY
```

Adzuna auth detail:

```text
Query params:
app_id=ADZUNA_APP_ID
app_key=ADZUNA_APP_KEY
```

---

## 15. Self-Review

Spec coverage:

- Remote-first focus is covered by source selection, remote classifier, scoring, and CLI reports.
- Public/free-access API terminology is covered in compliance model, source catalog, README requirements, and quality gates.
- Personal-use boundary is covered in non-goals, source metadata, and CLI warnings.
- Source details are covered for Remotive, Adzuna, Greenhouse, Lever, Arbeitnow, Reed, and USAJOBS.
- API key handling is covered by `.env.example`, settings, and explicit auth notes.

Placeholder scan:

- No task uses unspecified implementation placeholders.
- Optional later work is intentionally isolated in Future Work and is not required for v1 completion.

Type consistency:

- `CanonicalJob`, `RemoteCategory`, `JobStatus`, and `CandidateProfile` are used consistently across adapters, scoring, persistence, and tests.
- Source ids are consistently lowercase: `remotive`, `adzuna`, `greenhouse`, `lever`, `arbeitnow`.
