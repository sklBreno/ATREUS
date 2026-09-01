"""Cooperative cancellation contract for bounded operations."""

from abc import ABC, abstractmethod


class CancellationSignal(ABC):
    """Expose whether cooperative cancellation has been requested."""

    @abstractmethod
    def is_cancelled(self) -> bool:
        """Return whether the current operation should stop cooperatively."""
