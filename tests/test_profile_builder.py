from jobhunt.profile.builder import analyze, finalize
from jobhunt.profile.grounding import ground_filter, is_grounded
from jobhunt.profile.models import ProfileDraft, Question
from jobhunt.settings import Settings

CV = """
Arjun Shankar — Backend Engineer
Skills: Python, FastAPI, PostgreSQL, Docker, AWS
Experience: Built REST APIs and automation pipelines in Python.
"""


def test_grounding_keeps_only_present_terms():
    kept = ground_filter(["Python", "FastAPI", "Rust", "Haskell"], CV)
    assert kept == ["Python", "FastAPI"]


def test_is_grounded_is_whole_word():
    assert is_grounded("api", "we build REST APIs") is False  # 'api' not a standalone word
    assert is_grounded("python", CV) is True


def test_offline_analyze_extracts_only_grounded_skills():
    result = analyze(CV, Settings(_env_file=None))  # no Groq key -> offline
    assert result.source == "offline"
    assert "python" in [s.lower() for s in result.draft.preferred_skills]
    # Standard preference questions are always offered.
    fields = {q.field for q in result.questions}
    assert {"target_titles", "remote_only", "preferred_locations"}.issubset(fields)


def test_finalize_blocks_until_required_facts_present():
    draft = ProfileDraft(preferred_skills=["Python"])  # no target_titles yet
    questions = [Question(id="q_titles", field="target_titles", kind="list", prompt="?")]

    incomplete = finalize(CV, draft, answers={"q_titles": ""}, questions=questions)
    assert incomplete.complete is False
    assert any(q.field == "target_titles" for q in incomplete.follow_up)

    complete = finalize(
        CV, draft, answers={"q_titles": "Backend Engineer, Python Developer"}, questions=questions
    )
    assert complete.complete is True
    assert "Backend Engineer" in complete.profile["target_titles"]


def test_finalize_drops_ungrounded_answer_items():
    # An answer that references something not in the CV or the answer text is dropped.
    draft = ProfileDraft(preferred_skills=["Python"])
    questions = [Question(id="q_titles", field="target_titles", kind="list", prompt="?")]
    result = finalize(
        CV, draft, answers={"q_titles": "Backend Engineer"}, questions=questions
    )
    # "Backend Engineer" is grounded because the answer text itself is part of the source.
    assert result.complete is True
    assert result.profile["target_titles"] == ["Backend Engineer"]


def test_finalize_applies_preference_answers():
    draft = ProfileDraft(target_titles=["Backend Engineer"], preferred_skills=["Python"])
    questions = [
        Question(id="q_remote", field="remote_only", kind="yesno", prompt="?"),
        Question(id="q_salary", field="min_salary", kind="number", prompt="?"),
    ]
    result = finalize(
        CV, draft, answers={"q_remote": "yes", "q_salary": "120000"}, questions=questions
    )
    assert result.complete is True
    assert result.profile["remote_only"] is True
    assert result.profile["min_salary"] == 120000
