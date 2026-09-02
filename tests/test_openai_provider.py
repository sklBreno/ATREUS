"""Isolated tests for the OpenAI structured-output adapter."""

from dataclasses import dataclass
from typing import Self, cast
from uuid import uuid4

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from atreus.ai.exceptions import (
    AIAuthenticationError,
    AIInternalProviderError,
    AIMalformedProviderResponseError,
    AINetworkError,
    AIRateLimitError,
    AIRequestTimeoutError,
)
from atreus.ai.models import (
    AIRequest,
    AIRequestCompleted,
    AIRequestFailed,
    AIRequestPurpose,
    AIRequestStarted,
)
from atreus.ai.openai_provider import OpenAIProvider
from atreus.application.models import ApplicationIntent
from atreus.events.event_bus import InProcessEventBus
from atreus.system.models import ApplicationIdentifier
from tests.support import FixedClock


@dataclass
class FakeSDKResponse:
    """Provide only the SDK response field consumed by the adapter."""

    output_text: str


class FakeOpenAIClient:
    """Record SDK options and response creation without network access."""

    def __init__(
        self,
        output_text: str = (
            '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
            '"confidence":0.9}'
        ),
        error: Exception | None = None,
    ) -> None:
        """Initialize one result or failure."""
        self.output_text = output_text
        self.error = error
        self.timeout: float | None = None
        self.create_arguments: dict[str, object] | None = None
        self.responses = self

    def with_options(self, *, timeout: float) -> Self:
        """Record the per-request timeout and return this fake client."""
        self.timeout = timeout
        return self

    def create(self, **arguments: object) -> FakeSDKResponse:
        """Record structured request arguments and return or raise."""
        self.create_arguments = arguments
        if self.error is not None:
            raise self.error
        return FakeSDKResponse(self.output_text)


def make_request() -> AIRequest:
    """Create one bounded request for adapter tests."""
    return AIRequest(
        uuid4(),
        uuid4(),
        AIRequestPurpose.REQUEST_INTERPRETATION,
        "Return approved structured output.",
        "Please open calculator",
        12,
        128,
    )


def make_conversation_request() -> AIRequest:
    """Create one bounded free-text request for adapter tests."""
    return AIRequest(
        uuid4(),
        uuid4(),
        AIRequestPurpose.CONVERSATIONAL_RESPONSE,
        "Answer safely in English.",
        "What is RAM?",
        12,
        512,
    )


def make_provider(
    client: FakeOpenAIClient,
    event_bus: InProcessEventBus | None = None,
) -> OpenAIProvider:
    """Create an adapter with a fake SDK client and no usable credential."""
    return OpenAIProvider(
        api_key="not-retained",
        model_id="test-model",
        clock=FixedClock(),
        event_bus=event_bus,
        client=cast(OpenAI, client),
    )


def test_openai_adapter_uses_strict_schema_without_tools() -> None:
    client = FakeOpenAIClient()
    request = make_request()

    response = make_provider(client).generate(request)

    assert response.request_id == request.request_id
    assert response.provider_id == "openai"
    assert client.timeout == 12
    assert client.create_arguments is not None
    assert client.create_arguments["model"] == "test-model"
    assert client.create_arguments["max_output_tokens"] == 128
    assert "tools" not in client.create_arguments
    text = cast(dict[str, object], client.create_arguments["text"])
    output_format = cast(dict[str, object], text["format"])
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    schema = cast(dict[str, object], output_format["schema"])
    assert schema["additionalProperties"] is False
    properties = cast(dict[str, object], schema["properties"])
    assert set(properties) == {"intent_id", "target_id", "confidence"}
    intent_schema = cast(dict[str, object], properties["intent_id"])
    target_schema = cast(dict[str, object], properties["target_id"])
    assert intent_schema["enum"] == [
        intent.value for intent in ApplicationIntent
    ]
    assert target_schema["enum"] == [
        application_id.value for application_id in ApplicationIdentifier
    ]
    assert "capability_id" not in properties
    assert "executable" not in properties
    assert "process" not in properties
    assert "pid" not in properties
    assert "path" not in properties
    assert "command" not in properties


def test_openai_adapter_uses_plain_text_without_tools_for_conversation() -> None:
    client = FakeOpenAIClient("RAM is short-term working storage.")
    request = make_conversation_request()

    response = make_provider(client).generate(request)

    assert response.content == "RAM is short-term working storage."
    assert client.create_arguments is not None
    assert client.create_arguments["max_output_tokens"] == 512
    assert "text" not in client.create_arguments
    assert "tools" not in client.create_arguments
    assert "tool_choice" not in client.create_arguments


def test_openai_adapter_publishes_sanitized_lifecycle_events() -> None:
    event_bus = InProcessEventBus()
    started: list[AIRequestStarted] = []
    completed: list[AIRequestCompleted] = []
    event_bus.subscribe(AIRequestStarted, started.append)
    event_bus.subscribe(AIRequestCompleted, completed.append)
    request = make_request()

    make_provider(FakeOpenAIClient(), event_bus).generate(request)

    assert len(started) == len(completed) == 1
    assert started[0].request_id == request.request_id
    assert completed[0].model_id == "test-model"
    assert started[0].purpose is AIRequestPurpose.REQUEST_INTERPRETATION
    assert completed[0].purpose is AIRequestPurpose.REQUEST_INTERPRETATION
    serialized = repr((started[0], completed[0]))
    assert request.content not in serialized
    assert request.instruction not in serialized
    assert "not-retained" not in serialized


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (
            AuthenticationError(
                "private auth detail",
                response=httpx.Response(
                    401,
                    request=httpx.Request("POST", "https://example.invalid"),
                ),
                body=None,
            ),
            AIAuthenticationError,
        ),
        (
            RateLimitError(
                "private rate detail",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://example.invalid"),
                ),
                body=None,
            ),
            AIRateLimitError,
        ),
        (
            APITimeoutError(
                httpx.Request("POST", "https://example.invalid")
            ),
            AIRequestTimeoutError,
        ),
        (
            APIConnectionError(
                request=httpx.Request("POST", "https://example.invalid")
            ),
            AINetworkError,
        ),
        (RuntimeError("private internal detail"), AIInternalProviderError),
    ),
)
def test_openai_adapter_normalizes_provider_failures(
    error: Exception,
    expected: type[Exception],
) -> None:
    event_bus = InProcessEventBus()
    failures: list[AIRequestFailed] = []
    event_bus.subscribe(AIRequestFailed, failures.append)

    with pytest.raises(expected) as raised:
        make_provider(FakeOpenAIClient(error=error), event_bus).generate(
            make_request()
        )

    assert "private" not in str(raised.value)
    assert len(failures) == 1
    assert "private" not in repr(failures[0])


def test_openai_adapter_rejects_empty_provider_output() -> None:
    with pytest.raises(AIMalformedProviderResponseError):
        make_provider(FakeOpenAIClient(output_text=" ")).generate(make_request())


def test_openai_adapter_repr_does_not_reveal_credential() -> None:
    provider = make_provider(FakeOpenAIClient())

    assert "not-retained" not in repr(provider)
    assert not hasattr(provider, "_api_key")


def test_openai_adapter_disables_sdk_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def create_client(**arguments: object) -> OpenAI:
        captured.update(arguments)
        return cast(OpenAI, FakeOpenAIClient())

    monkeypatch.setattr("atreus.ai.openai_provider.OpenAI", create_client)

    provider = OpenAIProvider(
        api_key="private-key",
        model_id="test-model",
        clock=FixedClock(),
    )

    assert captured == {"api_key": "private-key", "max_retries": 0}
    assert "private-key" not in repr(provider)
