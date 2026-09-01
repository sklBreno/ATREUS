"""Unavailable context provider for runtimes without a Context Engine."""

from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.interfaces.clock import Clock
from atreus.interfaces.context import ContextProvider


class UnavailableContextProvider(ContextProvider):
    """Provide a safe unknown context when no Context Engine is configured."""

    def __init__(self, clock: Clock) -> None:
        """Initialize the provider with its timestamp source.

        Args:
            clock: Time source for immutable context snapshots.
        """
        self._clock = clock
        self._started_at = clock.now()

    def current_context(self) -> ContextSnapshot:
        """Return an unavailable context snapshot without inferred behavior."""
        evaluated_at = self._clock.now()
        return ContextSnapshot(
            context_type=ContextType.UNKNOWN,
            confidence=0.0,
            started_at=self._started_at,
            evaluated_at=evaluated_at,
            signal_status=ContextSignalStatus.UNAVAILABLE,
        )
