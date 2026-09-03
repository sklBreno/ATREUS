"""Immutable provider-neutral contracts for bounded AI processing."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from atreus.ai.exceptions import (
    InvalidAIRequestError,
    InvalidAIResponseError,
    InvalidRequestInterpretationError,
)
from atreus.application.models import ApplicationAction
from atreus.events.models import Event

REQUEST_INTERPRETER_SERVICE_ID = "ai.request_interpreter"
CONVERSATION_RESPONDER_SERVICE_ID = "ai.conversation_responder"


class AIProviderAvailabilityState(StrEnum):
    """Identify the current availability of an AI Provider."""

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class AIProviderAvailability:
    """Describe provider availability without exposing provider internals."""

    state: AIProviderAvailabilityState
    reason_code: str | None = None


class AIRequestPurpose(StrEnum):
    """Identify one approved bounded use of an AI Provider."""

    REQUEST_INTERPRETATION = "REQUEST_INTERPRETATION"
    CONVERSATIONAL_RESPONSE = "CONVERSATIONAL_RESPONSE"


class AIMessageRole(StrEnum):
    """Identify one provider-neutral conversational message role."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"


@dataclass(frozen=True, slots=True)
class AIMessage:
    """Represent one validated provider-neutral conversation message."""

    role: AIMessageRole
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        """Validate role and private textual content."""
        if not isinstance(self.role, AIMessageRole):
            raise InvalidAIRequestError("AI message role is invalid.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidAIRequestError("AI message content must be non-empty.")
        if any(
            ord(character) < 32 and character not in "\n\t"
            for character in self.content
        ):
            raise InvalidAIRequestError(
                "AI message content contains invalid control characters."
            )


@dataclass(frozen=True, slots=True)
class AIRequest:
    """Represent one bounded provider-neutral AI request."""

    ai_request_id: UUID
    request_id: UUID
    purpose: AIRequestPurpose
    instruction: str = field(repr=False)
    content: str = field(repr=False)
    timeout_seconds: float
    max_output_tokens: int = 128
    history: tuple[AIMessage, ...] = ()

    def __post_init__(self) -> None:
        """Validate the bounded provider request contract."""
        if not isinstance(self.ai_request_id, UUID) or not isinstance(
            self.request_id,
            UUID,
        ):
            raise InvalidAIRequestError("AI request identifiers must be UUIDs.")
        if not isinstance(self.purpose, AIRequestPurpose):
            raise InvalidAIRequestError("AI request purpose is invalid.")
        if not isinstance(self.instruction, str) or not self.instruction.strip():
            raise InvalidAIRequestError("AI request instruction must be non-empty.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidAIRequestError("AI request content must be non-empty.")
        if (
            type(self.timeout_seconds) not in {int, float}
            or not isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise InvalidAIRequestError(
                "AI request timeout_seconds must be positive and finite."
            )
        if type(self.max_output_tokens) is not int or self.max_output_tokens <= 0:
            raise InvalidAIRequestError(
                "AI request max_output_tokens must be a positive integer."
            )
        if not isinstance(self.history, tuple) or any(
            not isinstance(message, AIMessage) for message in self.history
        ):
            raise InvalidAIRequestError(
                "AI request history must be an immutable tuple of AIMessage."
            )
        if (
            self.purpose is AIRequestPurpose.REQUEST_INTERPRETATION
            and self.history
        ):
            raise InvalidAIRequestError(
                "Request interpretation cannot receive conversation history."
            )
        if self.purpose is AIRequestPurpose.CONVERSATIONAL_RESPONSE:
            self._validate_conversation_history()

    def _validate_conversation_history(self) -> None:
        if len(self.history) % 2 != 0:
            raise InvalidAIRequestError(
                "Conversation history must contain complete message pairs."
            )
        for index, message in enumerate(self.history):
            expected_role = (
                AIMessageRole.USER if index % 2 == 0 else AIMessageRole.ASSISTANT
            )
            if message.role is not expected_role:
                raise InvalidAIRequestError(
                    "Conversation history must alternate user and assistant messages."
                )


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Represent one normalized provider response without raw SDK objects."""

    ai_request_id: UUID
    request_id: UUID
    content: str = field(repr=False)
    provider_id: str
    model_id: str
    completed_at: datetime

    def __post_init__(self) -> None:
        """Validate identities, metadata, content, and completion time."""
        if not isinstance(self.ai_request_id, UUID) or not isinstance(
            self.request_id,
            UUID,
        ):
            raise InvalidAIResponseError("AI response identifiers must be UUIDs.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidAIResponseError("AI response content must be non-empty.")
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise InvalidAIResponseError("AI response provider_id must be non-empty.")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise InvalidAIResponseError("AI response model_id must be non-empty.")
        if not isinstance(self.completed_at, datetime) or (
            self.completed_at.tzinfo is None
            or self.completed_at.utcoffset() is None
        ):
            raise InvalidAIResponseError(
                "AI response completed_at must be timezone-aware."
            )
        object.__setattr__(self, "completed_at", self.completed_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class RequestInterpretation:
    """Represent a locally validated, non-executable AI interpretation."""

    request_id: UUID
    action: ApplicationAction
    confidence: float

    def __post_init__(self) -> None:
        """Validate the non-executable interpretation contract."""
        if not isinstance(self.request_id, UUID):
            raise InvalidRequestInterpretationError(
                "Interpretation request_id must be a UUID."
            )
        if not isinstance(self.action, ApplicationAction):
            raise InvalidRequestInterpretationError(
                "Interpretation action is invalid."
            )
        if (
            type(self.confidence) not in {int, float}
            or not isfinite(float(self.confidence))
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise InvalidRequestInterpretationError(
                "Interpretation confidence must be between 0.0 and 1.0."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequestStarted(Event):
    """Report that one bounded provider request started."""

    ai_request_id: UUID
    request_id: UUID
    provider_id: str
    purpose: AIRequestPurpose


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequestCompleted(Event):
    """Report successful provider completion without response content."""

    ai_request_id: UUID
    request_id: UUID
    provider_id: str
    model_id: str
    duration_seconds: float
    purpose: AIRequestPurpose


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequestFailed(Event):
    """Report a normalized provider failure without private details."""

    ai_request_id: UUID
    request_id: UUID
    provider_id: str
    error_code: str
    purpose: AIRequestPurpose
