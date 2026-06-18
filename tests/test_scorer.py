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


def test_skill_match_is_whole_word_not_substring():
    profile = CandidateProfile(
        target_titles=["writer"],
        preferred_skills=["api"],
        strong_skills=[],
        learning_skills=[],
        excluded_keywords=[],
        preferred_locations=["remote"],
        timezone="Asia/Calcutta",
        remote_only=False,
        allow_contract=True,
        allow_internship=False,
        min_salary=None,
        salary_currency=None,
    )
    job = CanonicalJob(
        source_id="test",
        source_job_id="3",
        source_url="https://example.com/3",
        title="Writer",
        company="Example",
        location_text="Worldwide",
        remote_category=RemoteCategory.GLOBAL_REMOTE,
        description_text="A capital role for a therapist-adjacent communicator.",
        fetched_at=datetime(2026, 6, 17, tzinfo=UTC),
        raw_payload_hash="hash",
    )

    scored = score_job(job, profile)

    # "api" must not match inside "capital" or "therapist".
    assert "api" not in scored.fit_reasons
