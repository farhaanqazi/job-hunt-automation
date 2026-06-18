import json

from jobhunt.profile.llm import groq_analyze, offline_analyze
from jobhunt.settings import Settings


def test_groq_analyze_parses_forced_tool_call(httpx_mock):
    tool_args = {
        "draft": {
            "preferred_skills": ["Python", "FastAPI"],
            "target_titles": ["Backend Engineer"],
        },
        "questions": [
            {"id": "q1", "prompt": "Remote only?", "field": "remote_only", "kind": "yesno"}
        ],
    }
    httpx_mock.add_response(
        method="POST",
        url="https://api.groq.com/openai/v1/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "submit_analysis",
                                    "arguments": json.dumps(tool_args),
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )

    settings = Settings(_env_file=None, groq_api_key="k")
    result = groq_analyze("Python FastAPI Backend Engineer", settings)
    assert result.source == "groq"
    assert "Python" in result.draft.preferred_skills
    assert result.questions[0].field == "remote_only"


def test_offline_analyze_needs_no_network():
    result = offline_analyze("Senior Python Developer. Skills: Python, Django, AWS.")
    assert result.source == "offline"
    assert "python" in [s.lower() for s in result.draft.preferred_skills]
