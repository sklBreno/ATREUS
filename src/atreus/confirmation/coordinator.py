"""In-memory single-slot Interactive Confirmation coordinator."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from atreus.application.models import ApplicationAction
from atreus.confirmation.exceptions import (
    InvalidConfirmationError,
    PendingConfirmationExistsError,
)
from atreus.confirmation.models import (
    ConfirmationResolution,
    ConfirmationResolutionStatus,
    PendingConfirmation,
)
from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.clock import Clock
from atreus.interfaces.confirmation import ConfirmationCoordinator

_AFFIRMATIVE_RESPONSES = frozenset(
    {"sim", "s", "confirmar", "yes", "y", "confirm"}
)
_NEGATIVE_RESPONSES = frozenset(
    {"não", "nao", "n", "cancelar", "no", "cancel"}
)


class InMemoryConfirmationCoordinator(ConfirmationCoordinator):
    """Own exactly one expiring process-local confirmation slot."""

    def __init__(self, clock: Clock, ttl: timedelta) -> None:
        """Initialize an empty coordinator with explicit time policy.

        Args:
            clock: Time source for creation, expiration, and resolution.
            ttl: Positive fixed lifetime for each pending confirmation.
        """
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
            raise InvalidConfirmationError(
                "Confirmation TTL must be a positive timedelta."
            )
        self._clock = clock
        self._ttl = ttl
        self._pending: PendingConfirmation | None = None

    def begin(
        self,
        original_request_id: UUID,
        action: ApplicationAction,
        language: InteractionLanguage,
    ) -> PendingConfirmation:
        """Create one pending action without replacing a valid slot."""
        now = self._clock.now()
        self._discard_expired(now)
        if self._pending is not None:
            raise PendingConfirmationExistsError(
                "A valid pending confirmation already exists."
            )
        pending = PendingConfirmation(
            confirmation_id=uuid4(),
            original_request_id=original_request_id,
            action=action,
            language=language,
            created_at=now,
            expires_at=now + self._ttl,
        )
        self._pending = pending
        return pending

    def resolve(
        self,
        response_request_id: UUID,
        content: str,
    ) -> ConfirmationResolution:
        """Resolve exact yes/no input and consume every terminal pending state."""
        if not isinstance(response_request_id, UUID):
            raise InvalidConfirmationError(
                "Confirmation response identifier must be a UUID."
            )
        if not isinstance(content, str):
            raise InvalidConfirmationError(
                "Confirmation response content must be a string."
            )
        now = self._clock.now()
        normalized = content.strip().casefold()
        recognized = normalized in _AFFIRMATIVE_RESPONSES | _NEGATIVE_RESPONSES
        pending = self._pending
        if pending is None:
            status = (
                ConfirmationResolutionStatus.NO_PENDING
                if recognized
                else ConfirmationResolutionStatus.NOT_APPLICABLE
            )
            return ConfirmationResolution(response_request_id, status, None, now)
        if pending.expires_at <= now:
            self._pending = None
            return ConfirmationResolution(
                response_request_id,
                ConfirmationResolutionStatus.EXPIRED,
                pending,
                now,
            )

        self._pending = None
        if normalized in _AFFIRMATIVE_RESPONSES:
            status = ConfirmationResolutionStatus.ACCEPTED
        elif normalized in _NEGATIVE_RESPONSES:
            status = ConfirmationResolutionStatus.REJECTED
        else:
            status = ConfirmationResolutionStatus.INVALIDATED
        return ConfirmationResolution(response_request_id, status, pending, now)

    def clear(self) -> bool:
        """Remove the current slot without persistence or secondary effects."""
        existed = self._pending is not None
        self._pending = None
        return existed

    def _discard_expired(self, now: datetime) -> None:
        pending = self._pending
        if pending is not None and pending.expires_at <= now:
            self._pending = None
