"""Clock contract used by time-sensitive ATREUS components."""

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Provide the current time through an injectable boundary."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current timezone-aware UTC timestamp."""
