"""Structured logging contract exposed to observability components."""

from abc import ABC, abstractmethod

from atreus.logging.models import StructuredLogRecord


class LogWriter(ABC):
    """Define persistence for sanitized structured log records."""

    @abstractmethod
    def write(self, record: StructuredLogRecord) -> None:
        """Persist one structured record.

        Args:
            record: Sanitized record produced by an observability adapter.
        """
