"""Groq LLM client (contract-based) + a deterministic offline fallback.

The model is never asked to write prose. It is forced to call a single function whose
arguments match a fixed schema, with a system prompt that forbids invention. Whatever it
returns is still grounding-verified downstream, so this layer cannot leak hallucinations.
"""

from __future__ import annotations

import json
import re

import httpx

from jobhunt.profile.models import AnalysisResult, ProfileDraft, Question
from jobhunt.settings import Settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a strict CV information extractor for a private job-search tool. "
    "You DO NOT write prose, summaries, or cover letters. You ONLY call the "
    "submit_analysis function with structured data. Rules: "
    "(1) Use ONLY facts explicitly present in the CV text. "
    "(2) NEVER invent or infer skills, job titles, employers, locations, or preferences "
    "that are not written in the CV. "
    "(3) Copy skills and titles using the exact words from the CV. "
    "(4) If something is not in the CV, leave it out. "
    "(5) Do not guess preferences (remote, salary, contract) — instead add a short, "
    "specific question that references the CV so the user can tell you."
)

_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "draft": {
            "type": "object",
            "properties": {
                "target_titles": {"type": "array", "items": {"type": "string"}},
                "preferred_skills": {"type": "array", "items": {"type": "string"}},
                "strong_skills": {"type": "array", "items": {"type": "string"}},
                "learning_skills": {"type": "array", "items": {"type": "string"}},
                "preferred_locations": {"type": "array", "items": {"type": "string"}},
            },
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "prompt": {"type": "string"},
                    "field": {"type": "string"},
                    "kind": {"type": "string"},
                    "hint": {"type": "string"},
                },
                "required": ["id", "prompt", "field"],
            },
        },
    },
    "required": ["draft"],
}

_DRAFT_LIST_FIELDS = (
    "target_titles",
    "preferred_skills",
    "strong_skills",
    "learning_skills",
    "preferred_locations",
)


class LLMError(RuntimeError):
    pass


def groq_analyze(cv_text: str, settings: Settings) -> AnalysisResult:
    body = {
        "model": settings.groq_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CV text:\n\n{cv_text[:15000]}"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "submit_analysis",
                    "description": "Return the grounded profile draft and clarifying questions.",
                    "parameters": _ANALYSIS_SCHEMA,
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "submit_analysis"}},
    }
    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json=body,
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        arguments = payload["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
        data = json.loads(arguments)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"Groq request failed: {exc}") from exc

    draft_in = data.get("draft", {}) or {}
    draft = ProfileDraft(
        **{field: list(draft_in.get(field, []) or []) for field in _DRAFT_LIST_FIELDS}
    )
    questions = [Question(**q) for q in data.get("questions", []) if q.get("prompt")]
    return AnalysisResult(draft=draft, questions=questions, source="groq")


# --------------------------------------------------------------------------- #
# Offline deterministic fallback (no key / Groq unavailable)
# --------------------------------------------------------------------------- #

_SKILL_VOCAB = (
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#", "ruby",
    "php", "kotlin", "swift", "scala", "sql", "postgresql", "mysql", "mongodb", "redis",
    "fastapi", "django", "flask", "node", "express", "react", "vue", "angular", "svelte",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "linux", "git",
    "rest", "api", "graphql", "automation", "scripting", "etl", "spark", "kafka",
    "pandas", "numpy", "pytorch", "tensorflow", "machine learning", "data analysis",
    "backend", "frontend", "full stack", "devops", "ci/cd", "microservices",
)

_TITLE_HINTS = (
    "engineer", "developer", "programmer", "architect", "analyst", "scientist",
    "manager", "designer", "consultant", "administrator", "specialist", "lead",
)


def offline_analyze(cv_text: str) -> AnalysisResult:
    lowered = cv_text.lower()

    skills = [
        skill
        for skill in _SKILL_VOCAB
        if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", lowered)
    ]

    titles: list[str] = []
    for line in cv_text.splitlines():
        clean = line.strip()
        if 3 <= len(clean) <= 60 and any(h in clean.lower() for h in _TITLE_HINTS):
            titles.append(clean)
        if len(titles) >= 4:
            break

    draft = ProfileDraft(
        preferred_skills=skills[:12],
        strong_skills=skills[:4],
        target_titles=titles[:4],
    )
    return AnalysisResult(
        draft=draft,
        source="offline",
        notes=["Built offline from keyword matching. Review and refine via the questions below."],
    )
