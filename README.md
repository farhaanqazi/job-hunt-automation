# Job Hunt Automation

> A private, remote-first job discovery, scoring, and tracking assistant — built as a local Python CLI.

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-31%20passing-brightgreen.svg)](#testing)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Built with Typer](https://img.shields.io/badge/CLI-Typer-009688.svg)](https://typer.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLite](https://img.shields.io/badge/storage-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

Job Hunt Automation gathers active job openings from **public / free-access APIs and company ATS feeds**, normalizes them into one canonical model, classifies how remote-friendly each role is, scores it against your candidate profile, and tracks it through your application pipeline — all stored locally in SQLite. It does **not** scrape hostile job portals, does **not** auto-apply, and does **not** republish listings.

> [!IMPORTANT]
> The sources used here expose **public/free-access APIs** — they are *not* open-source data. Most listing data stays proprietary third-party content. Use this tool for **private, personal job search only**: preserve source URLs and attribution, respect rate limits, and never redistribute listings. See [Compliance model](#compliance-model).

---

## Table of Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Sources](#sources)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Remote classification & scoring](#remote-classification--scoring)
- [Compliance model](#compliance-model)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- **Multi-source aggregation** from 5 public job APIs / ATS feeds via pluggable adapters.
- **Canonical job model** — every source is normalized into one consistent shape (`CanonicalJob`).
- **Remote eligibility classifier** — buckets each role as global / India / timezone-compatible / country-restricted / hybrid-onsite / unknown.
- **Deterministic fit scoring** against a YAML candidate profile (titles, skills, exclusions, remote-only, salary).
- **Local SQLite persistence** with idempotent upserts (no duplicate rows on re-scan).
- **Application tracking** — shortlist, archive, and status roll-ups.
- **Cross-source de-duplication** key (normalizes title, company, and URL).
- **Private CSV export** for offline review in a spreadsheet.
- **Compliance-first** — attribution, canonical source URL, and a raw-payload hash are stored for every job.
- **Secret-safe** — keyed sources auto-disable with a clear warning when credentials are missing; keys are never logged.

## How it works

```
 fetch            normalize            classify           score            store              review
┌────────┐      ┌────────────┐      ┌────────────┐    ┌──────────┐     ┌──────────┐     ┌──────────────┐
│ Source │─────▶│ Canonical  │─────▶│   Remote   │───▶│   Fit    │────▶│  SQLite  │────▶│ list / show  │
│adapter │ raw  │    Job     │      │ classifier │    │  scorer  │     │  (upsert)│     │ export / track│
└────────┘      └────────────┘      └────────────┘    └──────────┘     └──────────┘     └──────────────┘
```

## Sources

| Source | Type | Auth | Notes |
|---|---|---|---|
| **Remotive** | Remote-first feed | None | Broad remote listings; attribution required. |
| **Adzuna** | Broad search | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | Country + keyword search (incl. India & remote). |
| **Greenhouse** | Target-company ATS | None | Per-company board token; monitoring, not broad search. |
| **Lever** | Target-company ATS | None | Per-company handle; monitoring, not broad search. |
| **Arbeitnow** | Regional feed | None | Supplemental EU/Germany-skewed remote roles. |

> Adapters for **Reed** (UK) and **USAJOBS** (US public sector) are stubbed for future work — see [Roadmap](#roadmap).

The catalog of allowed sources and their compliance metadata lives in [`config/source_catalog.yaml`](config/source_catalog.yaml) and is the single source of truth for what the tool may query.

## Quick start

> Windows / PowerShell shown below. For tiny, copy-paste, one-line-at-a-time instructions, see **[run.md](run.md)**.

```powershell
# 1. Clone and enter the project
git clone <your-repo-url> job_hunt_automation
cd job_hunt_automation

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install (with dev tools)
pip install -e ".[dev]"

# 4. (Optional) create your env file for keyed sources
copy .env.example .env

# 5. Verify it runs
python main.py sources list
```

Requires **Python 3.11+**. The app starts and runs fully without any API keys — keyed sources (Adzuna) simply stay disabled until credentials are present.

## Usage

```powershell
# Inspect configured sources and readiness
python main.py sources list
python main.py sources check

# Discover jobs (Remotive needs no key)
python main.py scan --source remotive
python main.py scan --source adzuna --country in --query "python remote"

# Review what was found
python main.py jobs list --min-score 70
python main.py jobs show <job-id>

# Track applications
python main.py jobs shortlist <job-id>
python main.py jobs archive <job-id>
python main.py tracker status

# Export a private local CSV
python main.py export csv --output exports/jobs.csv --min-score 70
```

Add `--help` to any command (e.g. `python main.py jobs --help`) for its full options.

### Example output

```text
                                     Jobs
+-----------------------------------------------------------------------------+
| ID | Score | Remote        | Company           | Title                  | Source   |
|----+-------+---------------+-------------------+------------------------+----------|
| 1  | 91    | India remote  | Example Remote Co | Python Backend Engineer| remotive |
+-----------------------------------------------------------------------------+
```

## Configuration

| File | Purpose |
|---|---|
| [`.env`](.env.example) | Runtime settings + API credentials (git-ignored; copy from `.env.example`). |
| [`config/source_catalog.yaml`](config/source_catalog.yaml) | Allowed sources and their compliance metadata. |
| [`config/candidate_profile.example.yaml`](config/candidate_profile.example.yaml) | Your target titles, skills, exclusions, remote/salary preferences. |
| [`config/target_companies.yaml`](config/target_companies.yaml) | Greenhouse board tokens / Lever handles to monitor. |

Environment variables (all optional except where you enable a keyed source):

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

> Never paste API keys into a chat or commit them. `.env` is git-ignored; keys are never printed in logs or errors.

## Remote classification & scoring

**Remote categories:** `global_remote`, `india_remote`, `timezone_compatible`, `country_restricted_remote`, `hybrid_or_onsite`, `unknown_remote_status`. The classifier is deterministic and keyword-driven over the role's location + description text.

**Fit score (0–100)** is computed from your candidate profile:

| Signal | Effect |
|---|---|
| Title matches a target title | +25 |
| Each matched preferred skill | +8 |
| Each matched strong skill | +6 |
| Each matched learning skill | +3 |
| Remote-friendly category (global / India / timezone) | +30 |
| Not remote-first while `remote_only: true` | −30 (+ concern) |
| Each excluded keyword present | −20 (+ concern) |
| Salary meets your minimum | +10 |

Scores are clamped to `[0, 100]`, and each job records human-readable `fit_reasons` and `concerns`.

## Compliance model

Every stored job preserves: `source_id`, `source_job_id`, `source_url`, `attribution`, `fetched_at`, and `raw_payload_hash`. Every source in the catalog is marked `redistribution_allowed: false` and `source_code_license: closed`. Reports are **private local files** and must not be formatted as public syndicated feeds.

**Non-goals (by design):** no scraping of LinkedIn/Indeed/Naukri/etc., no auto-applying, no republishing or reselling listings, no public job board, and never calling a source "open source" unless its code actually is.

## Project structure

```text
jobhunt/
  cli.py                 # Typer CLI: sources / scan / jobs / tracker / export
  settings.py            # pydantic-settings; credential gating
  http_client.py         # shared httpx client
  logging_config.py      # Rich logging setup
  sources/               # one adapter per source + base + registry
  jobs/                  # models, remote_classifier, scorer, dedupe
  storage/               # SQLAlchemy engine, schema, repositories
  applications/          # status tracker
  reports/               # console formatting + CSV export
tests/                   # 31 tests (offline; HTTP mocked via pytest-httpx)
config/                  # source catalog, candidate profile, target companies
main.py                  # entry point -> jobhunt.cli:app
```

## Testing

The suite is fully offline — all HTTP is mocked with `pytest-httpx`, so no network or credentials are needed.

```powershell
pytest -q          # 31 tests
ruff check .       # lint (vendored research/ is excluded)
```

**Tech stack:** Python 3.11+ · [Typer](https://typer.tiangolo.com/) · [httpx](https://www.python-httpx.org/) · [Pydantic v2](https://docs.pydantic.dev/) + pydantic-settings · [SQLAlchemy 2](https://www.sqlalchemy.org/) / SQLite · [Rich](https://rich.readthedocs.io/) · PyYAML · pytest / pytest-httpx / freezegun · [ruff](https://github.com/astral-sh/ruff).

## Roadmap

- Reed (UK) and USAJOBS (US public-sector) adapters.
- Richer remote classifier with source-specific hints.
- Extended tracker workflow (applied / follow-up scheduling).
- HTML stripping & text cleanup for descriptions.
- Cross-source duplicate detection via title/company/URL similarity.
- Optional local dashboard (FastAPI/Streamlit) for review.

## License

Released under the [MIT License](LICENSE). **The license covers this project's source code only** — it grants no rights to job-listing data retrieved through third-party APIs, which remains the proprietary content of its respective sources. Use responsibly and for personal job search.
