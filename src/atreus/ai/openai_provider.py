"""OpenAI adapter for bounded provider-neutral generation purposes."""

from datetime import datetime

from openai import (
    APIConnectionError,
    APIError,
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
    AIProviderException,
    AIRateLimitError,
    AIRequestTimeoutError,
)
from atreus.ai.models import (
    AIMessage,
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

_PROVIDER_ID = "openai"
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


class OpenAIProvider(AIProvider):
    """Translate bounded ATREUS requests to the official OpenAI SDK."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        clock: Clock,
        event_bus: EventBus | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """Initialize the isolated adapter without retaining the credential."""
        self._model_id = model_id
        self._clock = clock
        self._event_bus = event_bus
        self._client = (
            client
            if client is not None
            else OpenAI(api_key=api_key, max_retries=0)
        )

    def availability(self) -> AIProviderAvailability:
        """Report that the configured adapter is available for requests."""
        return AIProviderAvailability(AIProviderAvailabilityState.AVAILABLE)

    def generate(self, request: AIRequest) -> AIResponse:
        """Generate one purpose-specific response without exposing SDK data."""
        started_at = self._clock.now()
        self._publish_started(request, started_at)
        try:
            creation_arguments = self._creation_arguments(request)
            sdk_response = self._client.with_options(
                timeout=request.timeout_seconds
            ).responses.create(**creation_arguments)
            content = sdk_response.output_text
            if not isinstance(content, str) or not content.strip():
                raise AIMalformedProviderResponseError(
                    "AI Provider returned no content."
                )
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

    def _creation_arguments(self, request: AIRequest) -> dict[str, object]:
        arguments: dict[str, object] = {
            "model": self._model_id,
            "instructions": request.instruction,
            "max_output_tokens": request.max_output_tokens,
        }
        if request.purpose is AIRequestPurpose.REQUEST_INTERPRETATION:
            arguments["input"] = request.content
            arguments["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "atreus_request_interpretation",
                    "strict": True,
                    "schema": _REQUEST_INTERPRETATION_SCHEMA,
                }
            }
            return arguments
        if request.purpose is AIRequestPurpose.CONVERSATIONAL_RESPONSE:
            arguments["input"] = [
                *(self._message_input(message) for message in request.history),
                {"role": "user", "content": request.content},
            ]
            return arguments
        raise AIInternalProviderError("AI request purpose is unsupported.")

    @staticmethod
    def _message_input(message: AIMessage) -> dict[str, str]:
        return {
            "role": message.role.value.casefold(),
            "content": message.content,
        }

    @staticmethod
    def _normalize_error(error: Exception) -> AIProviderException:
        if isinstance(error, AIProviderException):
            return error
        if isinstance(error, AuthenticationError):
            return AIAuthenticationError("AI Provider authentication failed.")
        if isinstance(error, RateLimitError):
            return AIRateLimitError("AI Provider rate limit was reached.")
        if isinstance(error, APITimeoutError):
            return AIRequestTimeoutError("AI Provider request timed out.")
        if isinstance(error, APIConnectionError):
            return AINetworkError("AI Provider network request failed.")
        if isinstance(error, APIError):
            return AIInternalProviderError("AI Provider request failed.")
        return AIInternalProviderError("AI Provider failed internally.")

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
