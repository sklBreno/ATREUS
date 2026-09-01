"""Working Memory contracts exposed to ATREUS consumers."""

from abc import ABC, abstractmethod
from uuid import UUID

from atreus.memory.models import MemoryEntry, MemorySnapshot, MemoryValue


class MemorySnapshotProvider(ABC):
    """Provide stable immutable views of current Working Memory."""

    @abstractmethod
    def snapshot(self) -> MemorySnapshot:
        """Capture and return the current Working Memory view."""


class MemoryStore(MemorySnapshotProvider, ABC):
    """Store bounded temporary facts for the current process."""

    @abstractmethod
    def remember(
        self,
        namespace: str,
        values: tuple[MemoryValue, ...],
        source: str,
        source_request_id: UUID | None = None,
    ) -> MemoryEntry:
        """Store one explicit temporary fact and return its entry."""

    @abstractmethod
    def recall(self, entry_id: UUID) -> MemoryEntry | None:
        """Return one unexpired entry or ``None`` when it is absent."""

    @abstractmethod
    def forget(self, entry_id: UUID) -> bool:
        """Remove one unexpired entry and report whether it existed."""

    @abstractmethod
    def clear(self) -> int:
        """Remove all entries and return the number removed."""
