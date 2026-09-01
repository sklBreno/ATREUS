"""Simple immutable cancellation signal implementation."""

from dataclasses import dataclass

from atreus.interfaces.cancellation import CancellationSignal


@dataclass(frozen=True, slots=True)
class StaticCancellationSignal(CancellationSignal):
    """Represent cancellation state fixed for one synchronous invocation."""

    cancelled: bool = False

    def is_cancelled(self) -> bool:
        """Return the immutable cancellation state."""
        return self.cancelled
