"""Data shapes for the profile builder."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Profile fields that must be grounded in the CV/answers (facts, not preferences).
FACT_LIST_FIELDS = ("target_titles", "preferred_skills", "strong_skills", "learning_skills")
# Required before a profile can be saved.
REQUIRED_FACT_FIELDS = ("target_titles", "preferred_skills")


class Question(BaseModel):
    id: str
    prompt: str
    field: str
    kind: str = "text"  # text | yesno | number | list
    hint: str | None = None


class ProfileDraft(BaseModel):
    target_titles: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    strong_skills: list[str] = Field(default_factory=list)
    learning_skills: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    timezone: str | None = None
    remote_only: bool | None = None
    allow_contract: bool | None = None
    allow_internship: bool | None = None
    min_salary: int | None = None
    salary_currency: str | None = None


class AnalysisResult(BaseModel):
    draft: ProfileDraft
    questions: list[Question] = Field(default_factory=list)
    source: str = "offline"  # "groq" | "offline"
    notes: list[str] = Field(default_factory=list)


class FinalizeResult(BaseModel):
    draft: ProfileDraft
    complete: bool
    follow_up: list[Question] = Field(default_factory=list)
    profile: dict | None = None  # CandidateProfile dump when complete
    source: str = "offline"
