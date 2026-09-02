"""Tests for bounded structured request interpretation."""

from uuid import uuid4

import pytest

from atreus.ai.exceptions import (
    InterpretationTargetUnavailableError,
    InvalidRequestInterpretationError,
)
from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIResponse,
)
from atreus.ai.request_interpreter import StructuredRequestInterpreter
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.interfaces.ai_provider import AIProvider
from atreus.shared.request import Request
from tests.support import NOW


class RecordingAIProvider(AIProvider):
    """Return one configured structured response without network access."""

    def __init__(
        self,
        content: str,
        state: AIProviderAvailabilityState = AIProviderAvailabilityState.AVAILABLE,
    ) -> None:
        """Initialize deterministic provider output and availability."""
        self._content = content
        self._state = state
        self.requests: list[AIRequest] = []

    def availability(self) -> AIProviderAvailability:
        """Return configured provider availability."""
        return AIProviderAvailability(self._state)

    def generate(self, request: AIRequest) -> AIResponse:
        """Record a request and return configured response content."""
        self.requests.append(request)
        return AIResponse(
            request.ai_request_id,
            request.request_id,
            self._content,
            "test",
            "test-model",
            NOW,
        )


class InconsistentAIProvider(RecordingAIProvider):
    """Return a response with a mismatched AI operation identity."""

    def generate(self, request: AIRequest) -> AIResponse:
        """Return a response that cannot be correlated safely."""
        self.requests.append(request)
        return AIResponse(
            uuid4(),
            request.request_id,
            self._content,
            "test",
            "test-model",
            NOW,
        )


def make_catalog(
    state: CapabilityAvailabilityState = CapabilityAvailabilityState.AVAILABLE,
) -> InMemoryCapabilityRegistry:
    """Create a registry containing the approved application capabilities."""
    catalog = InMemoryCapabilityRegistry()
    for identifier, permission in (
        ("application.open", "application.control"),
        ("application.status", "application.read"),
    ):
        catalog.register(
            CapabilityMetadata(
                identifier=identifier,
                name=identifier,
                description=f"Provide {identifier}.",
                permissions=(permission,),
                availability=CapabilityAvailability(state),
                dependencies=(),
                requires_ai=False,
            )
        )
    return catalog


def make_request() -> Request:
    """Create one eligible natural-language request."""
    return Request(uuid4(), "Please open calculator for me", "text", NOW)


def test_interpreter_maps_valid_output_to_local_capability_once() -> None:
    provider = RecordingAIProvider(
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.92}'
    )
    interpreter = StructuredRequestInterpreter(provider, make_catalog(), 15)
    request = make_request()

    interpretation = interpreter.interpret(request)

    assert len(provider.requests) == 1
    assert interpretation.request_id == request.request_id
    assert interpretation.action.capability_id == "application.open"
    assert interpretation.action.application_id.value == "calculator"
    assert not hasattr(provider.requests[0], "context")
    assert not hasattr(provider.requests[0], "memory")


def test_interpreter_maps_status_to_local_capability_without_ai_capability_id() -> None:
    provider = RecordingAIProvider(
        '{"intent_id":"APPLICATION_STATUS","target_id":"notepad",'
        '"confidence":0.91}'
    )
    interpreter = StructuredRequestInterpreter(provider, make_catalog(), 15)
    request = make_request()

    interpretation = interpreter.interpret(request)

    assert interpretation.action.intent_id.value == "APPLICATION_STATUS"
    assert interpretation.action.capability_id == "application.status"
    assert interpretation.action.application_id.value == "notepad"
    assert "capability_id" not in provider.requests[0].instruction


@pytest.mark.parametrize(
    "content",
    (
        "not-json",
        "[]",
        '{"intent_id":"UNKNOWN","target_id":"calculator","confidence":0.9}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"unknown","confidence":0.9}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator","confidence":2}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator","confidence":NaN}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator","confidence":true}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator","confidence":"high"}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.9,"command":"calc.exe"}',
        '{"intent_id":"APPLICATION_STATUS","target_id":"spotify",'
        '"confidence":0.9}',
    ),
)
def test_interpreter_rejects_untrusted_structured_output(content: str) -> None:
    interpreter = StructuredRequestInterpreter(
        RecordingAIProvider(content),
        make_catalog(),
        15,
    )

    with pytest.raises(InvalidRequestInterpretationError):
        interpreter.interpret(make_request())


def test_interpreter_rejects_unavailable_capability_before_provider_call() -> None:
    provider = RecordingAIProvider("{}")
    interpreter = StructuredRequestInterpreter(
        provider,
        make_catalog(CapabilityAvailabilityState.UNAVAILABLE),
        15,
    )

    with pytest.raises(InterpretationTargetUnavailableError):
        interpreter.interpret(make_request())

    assert provider.requests == []


def test_interpreter_rejects_unavailable_provider_without_generation() -> None:
    provider = RecordingAIProvider(
        "{}",
        AIProviderAvailabilityState.UNAVAILABLE,
    )
    interpreter = StructuredRequestInterpreter(provider, make_catalog(), 15)

    with pytest.raises(InterpretationTargetUnavailableError):
        interpreter.interpret(make_request())

    assert provider.requests == []


def test_interpreter_rejects_inconsistent_ai_response_identity() -> None:
    provider = InconsistentAIProvider(
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.9}'
    )
    interpreter = StructuredRequestInterpreter(provider, make_catalog(), 15)

    with pytest.raises(InvalidRequestInterpretationError, match="identity"):
        interpreter.interpret(make_request())
