"""Orchestrates analyze -> ask -> finalize, enforcing grounding at every step."""

from __future__ import annotations

from jobhunt.profile.grounding import ground_filter
from jobhunt.profile.llm import LLMError, groq_analyze, offline_analyze
from jobhunt.profile.models import (
    FACT_LIST_FIELDS,
    REQUIRED_FACT_FIELDS,
    AnalysisResult,
    FinalizeResult,
    ProfileDraft,
    Question,
)
from jobhunt.settings import Settings

# Standard preference questions (facts come from the CV; preferences must be asked).
_STANDARD_QUESTIONS = [
    Question(id="q_titles", field="target_titles", kind="list",
             prompt="Which roles are you targeting? (comma-separated)"),
    Question(id="q_locations", field="preferred_locations", kind="list",
             prompt="Which locations or regions work for you? (e.g. remote, India)"),
    Question(id="q_timezone", field="timezone", kind="text",
             prompt="What is your timezone? (e.g. Asia/Calcutta)"),
    Question(id="q_remote", field="remote_only", kind="yesno",
             prompt="Do you want remote-only roles?"),
    Question(id="q_contract", field="allow_contract", kind="yesno",
             prompt="Are you open to contract roles?"),
    Question(id="q_intern", field="allow_internship", kind="yesno",
             prompt="Are you open to internships?"),
    Question(id="q_salary", field="min_salary", kind="number",
             prompt="Minimum annual salary? (leave blank to skip)"),
    Question(id="q_currency", field="salary_currency", kind="text",
             prompt="Salary currency? (e.g. USD, INR)"),
    Question(id="q_excluded", field="excluded_keywords", kind="list",
             prompt="Any keywords to avoid? (e.g. onsite, sales)"),
]

_TRUE = {"yes", "y", "true", "1", "open", "ok"}
_FALSE = {"no", "n", "false", "0"}


def analyze(cv_text: str, settings: Settings) -> AnalysisResult:
    if settings.has_groq_credentials:
        try:
            result = groq_analyze(cv_text, settings)
        except LLMError:
            result = offline_analyze(cv_text)
            result.notes.append("Groq was unavailable; used the offline builder instead.")
    else:
        result = offline_analyze(cv_text)

    result.draft = _ground_draft(result.draft, cv_text)
    result.questions = _merge_questions(result.questions)
    return result


def finalize(
    cv_text: str,
    draft: ProfileDraft,
    answers: dict[str, str],
    questions: list[Question],
    source: str = "offline",
) -> FinalizeResult:
    combined = cv_text + "\n" + "\n".join(v for v in answers.values() if v)
    draft = _apply_answers(draft, answers, questions)
    draft = _ground_draft(draft, combined)

    missing = [f for f in REQUIRED_FACT_FIELDS if not getattr(draft, f)]
    if missing:
        return FinalizeResult(
            draft=draft, complete=False, follow_up=_questions_for(missing), source=source
        )

    return FinalizeResult(
        draft=draft, complete=True, profile=_to_profile(draft), source=source
    )


# --------------------------------------------------------------------------- #


def _ground_draft(draft: ProfileDraft, source: str) -> ProfileDraft:
    data = draft.model_dump()
    for field in (*FACT_LIST_FIELDS, "preferred_locations", "excluded_keywords"):
        data[field] = ground_filter(data.get(field, []), source)
    return ProfileDraft(**data)


def _merge_questions(extra: list[Question]) -> list[Question]:
    """Standard preference questions first, then any non-duplicate LLM questions."""
    seen_fields = {q.field for q in _STANDARD_QUESTIONS}
    merged = list(_STANDARD_QUESTIONS)
    for q in extra:
        if q.field not in seen_fields:
            merged.append(q)
            seen_fields.add(q.field)
    return merged


def _questions_for(fields: list[str]) -> list[Question]:
    by_field = {q.field: q for q in _STANDARD_QUESTIONS}
    out: list[Question] = []
    for field in fields:
        if field in by_field:
            out.append(by_field[field])
        else:
            out.append(
                Question(id=f"q_{field}", field=field, kind="list",
                         prompt=f"Please provide your {field.replace('_', ' ')}.")
            )
    return out


def _apply_answers(
    draft: ProfileDraft, answers: dict[str, str], questions: list[Question]
) -> ProfileDraft:
    data = draft.model_dump()
    by_id = {q.id: q for q in questions}
    for qid, raw in answers.items():
        question = by_id.get(qid)
        if question is None or raw is None or raw.strip() == "":
            continue
        value = raw.strip()
        field, kind = question.field, question.kind

        if kind == "list":
            items = [part.strip() for part in value.split(",") if part.strip()]
            existing = data.get(field) or []
            data[field] = existing + [i for i in items if i not in existing]
        elif kind == "yesno":
            low = value.lower()
            if low in _TRUE:
                data[field] = True
            elif low in _FALSE:
                data[field] = False
        elif kind == "number":
            digits = "".join(ch for ch in value if ch.isdigit())
            data[field] = int(digits) if digits else None
        else:  # text
            data[field] = value
    return ProfileDraft(**data)


def _to_profile(draft: ProfileDraft) -> dict:
    """Fill preference defaults (choices, not invented facts) and return a profile dump."""
    strong = draft.strong_skills or draft.preferred_skills[:3]
    return {
        "target_titles": draft.target_titles,
        "preferred_skills": draft.preferred_skills,
        "strong_skills": strong,
        "learning_skills": draft.learning_skills,
        "excluded_keywords": draft.excluded_keywords,
        "preferred_locations": draft.preferred_locations or ["remote"],
        "timezone": draft.timezone or "Asia/Calcutta",
        "remote_only": True if draft.remote_only is None else draft.remote_only,
        "allow_contract": True if draft.allow_contract is None else draft.allow_contract,
        "allow_internship": False if draft.allow_internship is None else draft.allow_internship,
        "min_salary": draft.min_salary,
        "salary_currency": draft.salary_currency,
    }
