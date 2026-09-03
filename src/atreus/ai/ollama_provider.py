"""Ollama HTTP adapter for bounded local AI generation."""

import json
from datetime import datetime
from math import isfinite
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from atreus.ai.exceptions import (
    AIAuthenticationError,
    AIInternalProviderError,
    AIMalformedProviderResponseError,
    AINetworkError,
    AIProviderException,
    AIProviderUnavailableError,
    AIRateLimitError,
    AIRequestTimeoutError,
)
from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIRequestCompleted,
    AIRequestFailed,
    AIRequestPurpose,
    AIRequestStarted,
    AIResponse,
)
from atreus.application.models import ApplicationIntent
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.clock import Clock
from atreus.interfaces.event_bus import EventBus
from atreus.system.models import ApplicationIdentifier

_PROVIDER_ID = "ollama"
_LOCAL_HOSTS = {"localhost", "127.0.0.1"}
_MAX_RESPONSE_BYTES = 1_048_576
_APPROVED_TARGET_IDS = [application_id.value for application_id in ApplicationIdentifier]
_REQUEST_INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent_id": {
            "type": "string",
            "enum": [intent.value for intent in ApplicationIntent],
        },
        "target_id": {
            "type": "string",
            "enum": _APPROVED_TARGET_IDS,
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    },
    "required": ["intent_id", "target_id", "confidence"],
    "additionalProperties": False,
}


class _NoRedirectHandler(HTTPRedirectHandler):
    """Reject redirects so the local adapter cannot leave its configured host."""

    def redirect_request(
        self,
        request: Request,
        file_pointer: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> None:
        """Prevent urllib from following a provider-controlled location."""
        return None


class OllamaProvider(AIProvider):
    """Translate bounded ATREUS requests to the local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str,
        model_id: str,
        clock: Clock,
        event_bus: EventBus | None = None,
        opener: OpenerDirector | None = None,
    ) -> None:
        """Initialize one local-only adapter with injectable HTTP transport.

        Args:
            base_url: Explicit local Ollama HTTP endpoint.
            model_id: Configured local model identifier.
            clock: Time source for normalized responses and events.
            event_bus: Optional sanitized lifecycle publication boundary.
            opener: Optional urllib opener used by isolated tests.

        Raises:
            ValueError: If the endpoint or model identifier is invalid.
        """
        self._chat_endpoint = self._validated_chat_endpoint(base_url)
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("Ollama model_id must be non-empty.")
        self._model_id = model_id
        self._clock = clock
        self._event_bus = event_bus
        self._opener = opener or build_opener(
            ProxyHandler({}),
            _NoRedirectHandler(),
        )

    def availability(self) -> AIProviderAvailability:
        """Report configured availability without a hidden network probe."""
        return AIProviderAvailability(AIProviderAvailabilityState.AVAILABLE)

    def generate(self, request: AIRequest) -> AIResponse:
        """Generate one local response through the fixed Ollama chat endpoint."""
        started_at = self._clock.now()
        self._publish_started(request, started_at)
        try:
            content = self._request_content(request)
            completed_at = self._clock.now()
            response = AIResponse(
                ai_request_id=request.ai_request_id,
                request_id=request.request_id,
                content=content,
                provider_id=_PROVIDER_ID,
                model_id=self._model_id,
                completed_at=completed_at,
            )
        except Exception as error:
            normalized = self._normalize_error(error)
            self._publish_failed(request, normalized)
            if normalized is error:
                raise
            raise normalized from None
        self._publish_completed(request, response, started_at)
        return response

    def _request_content(self, request: AIRequest) -> str:
        payload: dict[str, object] = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": request.instruction},
                {"role": "user", "content": request.content},
            ],
            "stream": False,
            "think": False,
            "options": {"num_predict": request.max_output_tokens},
        }
        if request.purpose is AIRequestPurpose.REQUEST_INTERPRETATION:
            payload["format"] = _REQUEST_INTERPRETATION_SCHEMA
        elif request.purpose is not AIRequestPurpose.CONVERSATIONAL_RESPONSE:
            raise AIInternalProviderError("AI request purpose is unsupported.")

        encoded_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        http_request = Request(
            self._chat_endpoint,
            data=encoded_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self._opener.open(
            http_request,
            timeout=request.timeout_seconds,
        ) as http_response:
            if http_response.status != 200:
                raise AIInternalProviderError("AI Provider request failed.")
            response_bytes = http_response.read(_MAX_RESPONSE_BYTES + 1)
        if len(response_bytes) > _MAX_RESPONSE_BYTES:
            raise AIMalformedProviderResponseError(
                "AI Provider response exceeded the supported size."
            )
        return self._decode_content(response_bytes, request.purpose)

    @staticmethod
    def _decode_content(
        response_bytes: bytes,
        purpose: AIRequestPurpose,
    ) -> str:
        try:
            decoded = json.loads(response_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AIMalformedProviderResponseError(
                "AI Provider response is malformed."
            ) from error
        if not isinstance(decoded, dict):
            raise AIMalformedProviderResponseError(
                "AI Provider response object is invalid."
            )
        message = decoded.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise AIMalformedProviderResponseError(
                "AI Provider response message is invalid."
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise AIMalformedProviderResponseError(
                "AI Provider returned no content."
            )
        if purpose is AIRequestPurpose.REQUEST_INTERPRETATION:
            return OllamaProvider._validated_interpretation_content(content)
        return content

    @staticmethod
    def _validated_interpretation_content(content: str) -> str:
        try:
            structured = json.loads(content)
        except json.JSONDecodeError as error:
            raise AIMalformedProviderResponseError(
                "AI Provider structured output is malformed."
            ) from error
        if not isinstance(structured, dict) or set(structured) != {
            "intent_id",
            "target_id",
            "confidence",
        }:
            raise AIMalformedProviderResponseError(
                "AI Provider structured output fields are invalid."
            )
        try:
            ApplicationIntent(structured["intent_id"])
            ApplicationIdentifier(structured["target_id"])
        except (TypeError, ValueError):
            raise AIMalformedProviderResponseError(
                "AI Provider structured output values are invalid."
            ) from None
        confidence = structured["confidence"]
        if (
            type(confidence) not in {int, float}
            or not isfinite(float(confidence))
            or not 0.0 <= confidence <= 1.0
        ):
            raise AIMalformedProviderResponseError(
                "AI Provider structured confidence is invalid."
            )
        return json.dumps(structured, separators=(",", ":"))

    @staticmethod
    def _normalize_error(error: Exception) -> AIProviderException:
        if isinstance(error, AIProviderException):
            return error
        if isinstance(error, HTTPError):
            if error.code in {401, 403}:
                return AIAuthenticationError("AI Provider authentication failed.")
            if error.code == 404:
                return AIProviderUnavailableError(
                    "AI Provider model is unavailable."
                )
            if error.code == 429:
                return AIRateLimitError("AI Provider rate limit was reached.")
            if error.code in {408, 504}:
                return AIRequestTimeoutError("AI Provider request timed out.")
            return AIInternalProviderError("AI Provider request failed.")
        if isinstance(error, (TimeoutError, SocketTimeout)):
            return AIRequestTimeoutError("AI Provider request timed out.")
        if isinstance(error, URLError):
            if isinstance(error.reason, (TimeoutError, SocketTimeout)):
                return AIRequestTimeoutError("AI Provider request timed out.")
            return AINetworkError("AI Provider network request failed.")
        if isinstance(error, OSError):
            return AINetworkError("AI Provider network request failed.")
        return AIInternalProviderError("AI Provider failed internally.")

    @staticmethod
    def _validated_chat_endpoint(base_url: str) -> str:
        if not isinstance(base_url, str) or base_url != base_url.strip():
            raise ValueError("Ollama base_url must be a normalized local URL.")
        try:
            parsed = urlsplit(base_url)
            port = parsed.port
        except ValueError as error:
            raise ValueError("Ollama base_url is invalid.") from error
        if (
            parsed.scheme != "http"
            or parsed.hostname not in _LOCAL_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or port is None
        ):
            raise ValueError("Ollama base_url must identify a local HTTP endpoint.")
        return f"{base_url.rstrip('/')}/api/chat"

    def _publish_started(self, request: AIRequest, occurred_at: datetime) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(
                AIRequestStarted(
                    source="ai_provider",
                    occurred_at=occurred_at,
                    correlation_id=request.request_id,
                    ai_request_id=request.ai_request_id,
                    request_id=request.request_id,
                    provider_id=_PROVIDER_ID,
                    purpose=request.purpose,
                )
            )

    def _publish_completed(
        self,
        request: AIRequest,
        response: AIResponse,
        started_at: datetime,
    ) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(
                AIRequestCompleted(
                    source="ai_provider",
                    occurred_at=response.completed_at,
                    correlation_id=request.request_id,
                    ai_request_id=request.ai_request_id,
                    request_id=request.request_id,
                    provider_id=_PROVIDER_ID,
                    model_id=response.model_id,
                    duration_seconds=max(
                        0.0,
                        (response.completed_at - started_at).total_seconds(),
                    ),
                    purpose=request.purpose,
                )
            )

    def _publish_failed(
        self,
        request: AIRequest,
        error: AIProviderException,
    ) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(
                AIRequestFailed(
                    source="ai_provider",
                    occurred_at=self._clock.now(),
                    correlation_id=request.request_id,
                    ai_request_id=request.ai_request_id,
                    request_id=request.request_id,
                    provider_id=_PROVIDER_ID,
                    error_code=type(error).__name__,
                    purpose=request.purpose,
                )
            )
