"""Contract tests for immutable provider-neutral AI models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from math import inf, nan
from uuid import uuid4

import pytest

from atreus.ai.exceptions import (
    InvalidAIRequestError,
    InvalidAIResponseError,
    InvalidRequestInterpretationError,
)
from atreus.ai.models import (
    AIRequest,
    AIRequestPurpose,
    AIResponse,
    RequestInterpretation,
)
from atreus.application.models import ApplicationAction, ApplicationIntent
from atreus.system.models import ApplicationIdentifier

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def make_ai_request() -> AIRequest:
    """Create one valid bounded AI request."""
    return AIRequest(
        ai_request_id=uuid4(),
        request_id=uuid4(),
        purpose=AIRequestPurpose.REQUEST_INTERPRETATION,
        instruction="Return structured interpretation only.",
        content="Please open calculator for me.",
        timeout_seconds=15,
    )


def test_ai_request_is_immutable_and_hides_private_content_from_repr() -> None:
    request = make_ai_request()

    with pytest.raises(FrozenInstanceError):
        request.timeout_seconds = 10  # type: ignore[misc]

    representation = repr(request)
    assert "Please open calculator" not in representation
    assert "Return structured interpretation" not in representation
    assert hasattr(request, "__slots__")


@pytest.mark.parametrize("timeout", [0, -1, nan, inf, True])
def test_ai_request_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(InvalidAIRequestError):
        AIRequest(
            uuid4(),
            uuid4(),
            AIRequestPurpose.REQUEST_INTERPRETATION,
            "instruction",
            "content",
            timeout,
        )


@pytest.mark.parametrize("max_output_tokens", [0, -1, 1.5, True])
def test_ai_request_rejects_invalid_output_limit(max_output_tokens: object) -> None:
    with pytest.raises(InvalidAIRequestError):
        AIRequest(
            uuid4(),
            uuid4(),
            AIRequestPurpose.CONVERSATIONAL_RESPONSE,
            "instruction",
            "content",
            10,
            max_output_tokens,  # type: ignore[arg-type]
        )


def test_ai_response_normalizes_time_and_hides_content_from_repr() -> None:
    request = make_ai_request()
    response = AIResponse(
        request.ai_request_id,
        request.request_id,
        '{"intent_id":"OPEN_APPLICATION"}',
        "provider",
        "model",
        NOW,
    )

    assert response.completed_at.tzinfo is UTC
    assert "OPEN_APPLICATION" not in repr(response)


def test_ai_response_rejects_naive_completion_time() -> None:
    request = make_ai_request()

    with pytest.raises(InvalidAIResponseError):
        AIResponse(
            request.ai_request_id,
            request.request_id,
            "content",
            "provider",
            "model",
            datetime(2026, 9, 1, 12, 0),
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1, nan, inf, True])
def test_request_interpretation_rejects_invalid_confidence(
    confidence: float,
) -> None:
    with pytest.raises(InvalidRequestInterpretationError):
        RequestInterpretation(
            uuid4(),
            ApplicationAction(
                ApplicationIntent.OPEN_APPLICATION,
                "application.open",
                ApplicationIdentifier.CALCULATOR,
            ),
            confidence,
        )
