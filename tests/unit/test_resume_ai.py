import asyncio

import pytest
from fastapi import HTTPException

from app.models.builder_schemas import ResumeAIRequest, StructuredResume
from app.services.resume_ai import _prompt, _validate_achievement_suggestion, generate_resume_content


def _request(operation: str, source_text: str) -> ResumeAIRequest:
    return ResumeAIRequest(
        operation=operation,
        resume=StructuredResume(),
        source_text=source_text,
        target_role="Software Engineer",
    )


def test_ai_achievement_operation_rejects_contact_information_before_provider_call():
    for operation in ("achievement", "bullet", "experience", "project"):
        request = _request(operation, "Email: jordan@example.com | Phone: +1 (415) 555-0134")

        with pytest.raises(HTTPException) as error:
            asyncio.run(generate_resume_content(request))

        assert error.value.status_code == 400
        assert "contact details" in error.value.detail


def test_ai_prompt_explicitly_preserves_contact_and_requires_placeholders():
    system_prompt, _ = _prompt(_request("bullet", "Built reporting tools with Python."))

    assert "never turn them into achievement statements" in system_prompt
    assert "[add verified ...]" in system_prompt


def test_ai_suggestion_validator_rejects_new_metrics_technologies_and_companies():
    source = "Built a reporting tool with Python."

    for suggestion in (
        "Built a reporting tool with Python, reducing costs by 40%.",
        "Built a reporting tool with Python and AWS.",
        "Built a reporting tool at ExampleCorp with Python.",
    ):
        with pytest.raises(HTTPException) as error:
            _validate_achievement_suggestion(suggestion, source)

        assert error.value.status_code == 502


def test_ai_suggestion_validator_rejects_unstated_outcomes():
        with pytest.raises(HTTPException) as error:
            _validate_achievement_suggestion(
                "Built a reporting tool, improving team productivity.",
                "Built a reporting tool.",
            )

        assert error.value.status_code == 502


def test_ai_suggestion_validator_allows_source_supported_claims():
    _validate_achievement_suggestion(
        "Built a reporting tool with Python for 12 teams.",
        "Built a reporting tool with Python for 12 teams.",
    )
