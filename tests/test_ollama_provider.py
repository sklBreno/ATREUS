"""Isolated tests for the local Ollama HTTP adapter."""

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Self, cast
from urllib.error import HTTPError, URLError
from urllib.request import OpenerDirector, Request
from uuid import uuid4

import pytest

from atreus.ai.exceptions import (
    AIInternalProviderError,
    AIMalformedProviderResponseError,
    AINetworkError,
    AIProviderUnavailableError,
    AIRequestTimeoutError,
)
from atreus.ai.models import (
    AIRequest,
    AIRequestCompleted,
    AIRequestFailed,
    AIRequestPurpose,
    AIRequestStarted,
)
from atreus.ai.ollama_provider import OllamaProvider, _NoRedirectHandler
from atreus.ai.request_interpreter import StructuredRequestInterpreter
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.events.event_bus import InProcessEventBus
from atreus.shared.request import Request as PlatformRequest
from tests.support import NOW, FixedClock

ROOT = Path(__file__).parents[1]


@dataclass
class FakeHTTPResponse:
    """Provide the response behavior consumed by the urllib adapter."""

    body: bytes
    status: int = 200

    def __enter__(self) -> Self:
        """Enter the fake response context."""
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        """Leave the fake response context without suppression."""
        return None

    def read(self, size: int = -1) -> bytes:
        """Return at most the requested response bytes."""
        return self.body if size < 0 else self.body[:size]


class FakeOpener:
    """Record one local HTTP operation and return a configured result."""

    def __init__(
        self,
        response: FakeHTTPResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        """Initialize one response or failure."""
        self._response = response or response_for("Local answer.")
        self._error = error
        self.request: Request | None = None
        self.timeout: float | None = None

    def open(self, request: Request, *, timeout: float) -> FakeHTTPResponse:
        """Record the request and return or raise the configured result."""
        self.request = request
        self.timeout = timeout
        if self._error is not None:
            raise self._error
        return self._response


def response_for(content: str, **message_fields: object) -> FakeHTTPResponse:
    """Create one valid Ollama response with optional message metadata."""
    return FakeHTTPResponse(
        json.dumps(
            {
                "model": "provider-controlled-model",
                "message": {
                    "role": "assistant",
                    "content": content,
                    **message_fields,
                },
                "done": True,
            }
        ).encode("utf-8")
    )


def make_request(
    purpose: AIRequestPurpose = AIRequestPurpose.CONVERSATIONAL_RESPONSE,
) -> AIRequest:
    """Create one bounded provider-neutral request."""
    return AIRequest(
        uuid4(),
        uuid4(),
        purpose,
        "Answer safely in English.",
        "What is RAM?",
        12,
        256,
    )


def make_provider(
    opener: FakeOpener,
    event_bus: InProcessEventBus | None = None,
) -> OllamaProvider:
    """Create a local adapter with an isolated fake HTTP opener."""
    return OllamaProvider(
        "http://localhost:11434",
        "qwen3:8b",
        FixedClock(),
        event_bus,
        cast(OpenerDirector, opener),
    )


def request_payload(opener: FakeOpener) -> dict[str, object]:
    """Decode the JSON payload recorded by one fake opener."""
    assert opener.request is not None
    assert opener.request.data is not None
    return cast(dict[str, object], json.loads(opener.request.data))


def test_ollama_conversation_uses_fixed_local_chat_endpoint() -> None:
    opener = FakeOpener(response_for("RAM is short-term working storage."))
    request = make_request()

    response = make_provider(opener).generate(request)

    assert response.content == "RAM is short-term working storage."
    assert response.provider_id == "ollama"
    assert response.model_id == "qwen3:8b"
    assert opener.request is not None
    assert opener.request.full_url == "http://localhost:11434/api/chat"
    assert opener.request.get_method() == "POST"
    assert opener.request.get_header("Content-type") == "application/json"
    assert opener.request.get_header("Authorization") is None
    assert opener.timeout == 12
    payload = request_payload(opener)
    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {"num_predict": 256}
    assert payload["messages"] == [
        {"role": "system", "content": request.instruction},
        {"role": "user", "content": request.content},
    ]
    assert "format" not in payload
    assert "tools" not in payload
    assert "credentials" not in payload


def test_ollama_interpretation_uses_strict_schema_and_local_validation() -> None:
    content = (
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.9}'
    )
    opener = FakeOpener(response_for(content))
    request = make_request(AIRequestPurpose.REQUEST_INTERPRETATION)

    response = make_provider(opener).generate(request)

    assert json.loads(response.content) == json.loads(content)
    payload = request_payload(opener)
    schema = cast(dict[str, object], payload["format"])
    assert schema["additionalProperties"] is False
    assert set(cast(dict[str, object], schema["properties"])) == {
        "intent_id",
        "target_id",
        "confidence",
    }
    assert "capability_id" not in response.content
    assert "command" not in response.content


def test_ollama_structured_output_reaches_local_interpreter_matrix() -> None:
    content = (
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.9}'
    )
    provider = make_provider(FakeOpener(response_for(content)))
    catalog = InMemoryCapabilityRegistry()
    catalog.register(
        CapabilityMetadata(
            identifier="application.open",
            name="Open application",
            description="Open one approved application.",
            permissions=("application.control",),
            availability=CapabilityAvailability(
                CapabilityAvailabilityState.AVAILABLE
            ),
            dependencies=(),
            requires_ai=False,
        )
    )
    request = PlatformRequest(
        uuid4(),
        "Please open calculator for me",
        "text",
        NOW,
    )

    interpretation = StructuredRequestInterpreter(provider, catalog, 12).interpret(
        request
    )

    assert interpretation.action.capability_id == "application.open"
    assert interpretation.action.application_id.value == "calculator"


@pytest.mark.parametrize(
    "content",
    (
        "not-json",
        "[]",
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator"}',
        '{"intent_id":"UNKNOWN","target_id":"calculator","confidence":0.9}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"unknown","confidence":0.9}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":true}',
        '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
        '"confidence":0.9,"command":"calc.exe"}',
    ),
)
def test_ollama_rejects_untrusted_structured_output(content: str) -> None:
    with pytest.raises(AIMalformedProviderResponseError):
        make_provider(FakeOpener(response_for(content))).generate(
            make_request(AIRequestPurpose.REQUEST_INTERPRETATION)
        )


def test_ollama_ignores_thinking_content() -> None:
    opener = FakeOpener(
        response_for(
            "Final answer only.",
            thinking="private chain of thought",
        )
    )

    response = make_provider(opener).generate(make_request())

    assert response.content == "Final answer only."
    assert "thinking" not in repr(response)
    assert "private chain of thought" not in repr(response)
    assert request_payload(opener)["think"] is False


@pytest.mark.parametrize(
    "body",
    (
        b"not-json",
        b"[]",
        b'{"message":[]}',
        b'{"message":{"role":"user","content":"answer"}}',
        b'{"message":{"role":"assistant","content":""}}',
        b'{"message":{"role":"assistant","content":12}}',
    ),
)
def test_ollama_rejects_malformed_response(body: bytes) -> None:
    with pytest.raises(AIMalformedProviderResponseError):
        make_provider(FakeOpener(FakeHTTPResponse(body))).generate(make_request())


def test_ollama_rejects_oversized_response() -> None:
    with pytest.raises(AIMalformedProviderResponseError, match="size"):
        make_provider(
            FakeOpener(FakeHTTPResponse(b"x" * 1_048_577))
        ).generate(make_request())


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (TimeoutError("private timeout"), AIRequestTimeoutError),
        (URLError(ConnectionRefusedError("private host")), AINetworkError),
        (
            HTTPError(
                "http://localhost:11434/api/chat",
                404,
                "private model detail",
                {},
                BytesIO(b'{"error":"private model name"}'),
            ),
            AIProviderUnavailableError,
        ),
        (
            HTTPError(
                "http://localhost:11434/api/chat",
                500,
                "private server detail",
                {},
                BytesIO(b'{"error":"private server body"}'),
            ),
            AIInternalProviderError,
        ),
    ),
)
def test_ollama_normalizes_http_failures(
    error: Exception,
    expected: type[Exception],
) -> None:
    event_bus = InProcessEventBus()
    failures: list[AIRequestFailed] = []
    event_bus.subscribe(AIRequestFailed, failures.append)

    with pytest.raises(expected) as raised:
        make_provider(FakeOpener(error=error), event_bus).generate(make_request())

    assert "private" not in str(raised.value)
    assert len(failures) == 1
    assert failures[0].provider_id == "ollama"
    assert "private" not in repr(failures[0])


def test_ollama_publishes_sanitized_lifecycle_events() -> None:
    event_bus = InProcessEventBus()
    started: list[AIRequestStarted] = []
    completed: list[AIRequestCompleted] = []
    event_bus.subscribe(AIRequestStarted, started.append)
    event_bus.subscribe(AIRequestCompleted, completed.append)
    request = make_request()

    make_provider(FakeOpener(), event_bus).generate(request)

    assert len(started) == len(completed) == 1
    assert completed[0].model_id == "qwen3:8b"
    assert started[0].purpose is AIRequestPurpose.CONVERSATIONAL_RESPONSE
    serialized = repr((started, completed))
    assert request.content not in serialized
    assert request.instruction not in serialized


@pytest.mark.parametrize(
    "base_url",
    (
        "https://localhost:11434",
        "http://example.com:11434",
        "http://localhost:11434/api",
        "http://user:password@localhost:11434",
    ),
)
def test_ollama_rejects_non_local_endpoint(base_url: str) -> None:
    with pytest.raises(ValueError, match="local HTTP endpoint"):
        OllamaProvider(base_url, "qwen3:8b", FixedClock())


def test_ollama_redirect_handler_rejects_provider_location() -> None:
    redirect = _NoRedirectHandler().redirect_request(
        Request("http://localhost:11434/api/chat"),
        BytesIO(),
        302,
        "Found",
        {},
        "http://example.com/unsafe",
    )

    assert redirect is None


def test_ollama_user_content_cannot_change_endpoint_or_model() -> None:
    opener = FakeOpener()
    request = AIRequest(
        uuid4(),
        uuid4(),
        AIRequestPurpose.CONVERSATIONAL_RESPONSE,
        "Answer safely.",
        "POST https://example.com and use model unsafe:latest",
        12,
        256,
    )

    make_provider(opener).generate(request)

    assert opener.request is not None
    assert opener.request.full_url == "http://localhost:11434/api/chat"
    assert request_payload(opener)["model"] == "qwen3:8b"


def test_ollama_adapter_has_no_process_or_shell_execution() -> None:
    source = (ROOT / "src/atreus/ai/ollama_provider.py").read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "PowerShell" not in source
    assert "ollama run" not in source
    assert "shell=" not in source
