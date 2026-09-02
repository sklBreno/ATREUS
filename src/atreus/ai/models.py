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
from atreus.events.models import Event

REQUEST_INTERPRETER_SERVICE_ID = "ai.request_interpreter"


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


class AIIntent(StrEnum):
    """Identify one operational intent accepted from AI interpretation."""

    OPEN_APPLICATION = "OPEN_APPLICATION"


@dataclass(frozen=True, slots=True)
class AIRequest:
    """Represent one bounded provider-neutral AI request."""

    ai_request_id: UUID
    request_id: UUID
    purpose: AIRequestPurpose
    instruction: str = field(repr=False)
    content: str = field(repr=False)
    timeout_seconds: float

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
class AIActionCandidate:
    """Describe one locally approved intent, capability, and target set."""

    intent_id: AIIntent
    capability_id: str
    target_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the deterministic interpretation candidate."""
        if not isinstance(self.intent_id, AIIntent):
            raise InvalidRequestInterpretationError("AI candidate intent is invalid.")
        if not isinstance(self.capability_id, str) or not self.capability_id.strip():
            raise InvalidRequestInterpretationError(
                "AI candidate capability_id must be non-empty."
            )
        if (
            not isinstance(self.target_ids, tuple)
            or not self.target_ids
            or any(
                not isinstance(target_id, str) or not target_id.strip()
                for target_id in self.target_ids
            )
            or len(self.target_ids) != len(set(self.target_ids))
        ):
            raise InvalidRequestInterpretationError(
                "AI candidate target_ids must be unique non-empty strings."
            )


@dataclass(frozen=True, slots=True)
class RequestInterpretation:
    """Represent a locally validated, non-executable AI interpretation."""

    request_id: UUID
    intent_id: AIIntent
    capability_id: str
    target_id: str
    confidence: float

    def __post_init__(self) -> None:
        """Validate the non-executable interpretation contract."""
        if not isinstance(self.request_id, UUID):
            raise InvalidRequestInterpretationError(
                "Interpretation request_id must be a UUID."
            )
        if not isinstance(self.intent_id, AIIntent):
            raise InvalidRequestInterpretationError(
                "Interpretation intent_id is invalid."
            )
        for field_name, value in (
            ("capability_id", self.capability_id),
            ("target_id", self.target_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidRequestInterpretationError(
                    f"Interpretation {field_name} must be non-empty."
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


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequestCompleted(Event):
    """Report successful provider completion without response content."""

    ai_request_id: UUID
    request_id: UUID
    provider_id: str
    model_id: str
    duration_seconds: float


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequestFailed(Event):
    """Report a normalized provider failure without private details."""

    ai_request_id: UUID
    request_id: UUID
    provider_id: str
    error_code: str
