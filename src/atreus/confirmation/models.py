"""Immutable contracts for bounded interactive confirmation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from atreus.application.contracts import is_supported_application_action
from atreus.application.models import ApplicationAction, ApplicationIntent
from atreus.confirmation.exceptions import InvalidConfirmationError
from atreus.interaction.models import InteractionLanguage
from atreus.system.models import ApplicationIdentifier


class ConfirmationResolutionStatus(StrEnum):
    """Identify one terminal interpretation of foreground confirmation input."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_PENDING = "NO_PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class PendingConfirmation:
    """Represent one process-local action awaiting a single response."""

    confirmation_id: UUID
    original_request_id: UUID
    action: ApplicationAction
    language: InteractionLanguage
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        """Validate identities, action, language, and UTC lifetime."""
        if not isinstance(self.confirmation_id, UUID) or not isinstance(
            self.original_request_id,
            UUID,
        ):
            raise InvalidConfirmationError(
                "Pending confirmation identifiers must be UUIDs."
            )
        if (
            not isinstance(self.action, ApplicationAction)
            or self.action.intent_id is not ApplicationIntent.OPEN_APPLICATION
            or not is_supported_application_action(self.action)
        ):
            raise InvalidConfirmationError(
                "Pending confirmation action is invalid."
            )
        if not isinstance(self.language, InteractionLanguage):
            raise InvalidConfirmationError(
                "Pending confirmation language is invalid."
            )
        created_at = _normalize_utc(self.created_at, "created_at")
        expires_at = _normalize_utc(self.expires_at, "expires_at")
        if expires_at <= created_at:
            raise InvalidConfirmationError(
                "Pending confirmation must expire after creation."
            )
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ConfirmationResolution:
    """Represent one safe result from resolving confirmation input."""

    response_request_id: UUID
    status: ConfirmationResolutionStatus
    pending: PendingConfirmation | None
    resolved_at: datetime

    def __post_init__(self) -> None:
        """Validate response identity, status payload, and UTC time."""
        if not isinstance(self.response_request_id, UUID):
            raise InvalidConfirmationError(
                "Confirmation response identifier must be a UUID."
            )
        if not isinstance(self.status, ConfirmationResolutionStatus):
            raise InvalidConfirmationError(
                "Confirmation resolution status is invalid."
            )
        requires_pending = self.status in {
            ConfirmationResolutionStatus.ACCEPTED,
            ConfirmationResolutionStatus.REJECTED,
            ConfirmationResolutionStatus.INVALIDATED,
            ConfirmationResolutionStatus.EXPIRED,
        }
        if requires_pending != isinstance(self.pending, PendingConfirmation):
            raise InvalidConfirmationError(
                "Confirmation resolution payload is inconsistent."
            )
        object.__setattr__(
            self,
            "resolved_at",
            _normalize_utc(self.resolved_at, "resolved_at"),
        )


@dataclass(frozen=True, slots=True)
class ConfirmationPrompt:
    """Provide structured safe data for interface-owned prompt rendering."""

    confirmation_id: UUID
    intent_id: ApplicationIntent
    target_id: ApplicationIdentifier
    expires_at: datetime
    language: InteractionLanguage

    def __post_init__(self) -> None:
        """Validate prompt fields without storing translated text."""
        if not isinstance(self.confirmation_id, UUID):
            raise InvalidConfirmationError(
                "Confirmation prompt identifier must be a UUID."
            )
        if self.intent_id is not ApplicationIntent.OPEN_APPLICATION:
            raise InvalidConfirmationError(
                "Confirmation prompt intent must be OPEN_APPLICATION."
            )
        if not isinstance(self.target_id, ApplicationIdentifier):
            raise InvalidConfirmationError(
                "Confirmation prompt target is invalid."
            )
        if not isinstance(self.language, InteractionLanguage):
            raise InvalidConfirmationError(
                "Confirmation prompt language is invalid."
            )
        object.__setattr__(
            self,
            "expires_at",
            _normalize_utc(self.expires_at, "expires_at"),
        )


def _normalize_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or (
        value.tzinfo is None or value.utcoffset() is None
    ):
        raise InvalidConfirmationError(
            f"Confirmation {field_name} must be timezone-aware."
        )
    return value.astimezone(UTC)
