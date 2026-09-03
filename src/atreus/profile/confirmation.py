"""Process-local confirmation for destructive Personal Profile clear."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from atreus.interfaces.clock import Clock
from atreus.profile.exceptions import InvalidProfileClearConfirmationError
from atreus.profile.models import (
    PendingProfileClear,
    ProfileClearConfirmationCheck,
    ProfileClearConfirmationStatus,
)


class InMemoryProfileClearConfirmationCoordinator:
    """Own one expiring, process-local Personal Profile clear confirmation."""

    def __init__(self, clock: Clock, ttl: timedelta) -> None:
        """Initialize an empty coordinator with an explicit positive lifetime."""
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation TTL must be positive."
            )
        self._clock = clock
        self._ttl = ttl
        self._pending: PendingProfileClear | None = None

    def begin(self, original_request_id: UUID) -> PendingProfileClear:
        """Create or return the current valid pending clear confirmation."""
        if not isinstance(original_request_id, UUID):
            raise InvalidProfileClearConfirmationError(
                "Profile clear request identifier must be a UUID."
            )
        now = self._clock.now()
        self._discard_expired(now)
        if self._pending is None:
            self._pending = PendingProfileClear(
                confirmation_id=uuid4(),
                original_request_id=original_request_id,
                created_at=now,
                expires_at=now + self._ttl,
            )
        return self._pending

    def check(self) -> ProfileClearConfirmationCheck:
        """Inspect confirmation availability without consuming a valid slot."""
        now = self._clock.now()
        pending = self._pending
        if pending is None:
            return ProfileClearConfirmationCheck(
                ProfileClearConfirmationStatus.NO_PENDING,
                None,
            )
        if pending.expires_at <= now:
            self._pending = None
            return ProfileClearConfirmationCheck(
                ProfileClearConfirmationStatus.EXPIRED,
                None,
            )
        return ProfileClearConfirmationCheck(
            ProfileClearConfirmationStatus.AVAILABLE,
            pending,
        )

    def consume(self, confirmation_id: UUID) -> bool:
        """Consume the matching slot after a successful checked operation."""
        if not isinstance(confirmation_id, UUID):
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation identifier must be a UUID."
            )
        pending = self._pending
        if pending is None or pending.confirmation_id != confirmation_id:
            return False
        self._pending = None
        return True

    def _discard_expired(self, now: datetime) -> None:
        pending = self._pending
        if pending is not None and pending.expires_at <= now:
            self._pending = None
