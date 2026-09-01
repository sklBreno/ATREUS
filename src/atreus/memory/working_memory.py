"""Bounded process-local Working Memory implementation."""

from datetime import datetime
from uuid import UUID, uuid4

from atreus.interfaces.clock import Clock
from atreus.interfaces.memory import MemoryStore
from atreus.memory.exceptions import InvalidMemoryIdentifierError
from atreus.memory.models import (
    MemoryEntry,
    MemorySnapshot,
    MemoryValue,
    WorkingMemoryPolicy,
)


class InMemoryWorkingMemory(MemoryStore):
    """Retain bounded temporary facts for one composed process runtime."""

    def __init__(self, clock: Clock, policy: WorkingMemoryPolicy) -> None:
        """Initialize an empty store with explicit time and policy boundaries.

        Args:
            clock: Time source used for creation, expiration, and snapshots.
            policy: Immutable capacity and entry lifetime limits.
        """
        self._clock = clock
        self._policy = policy
        self._entries: dict[UUID, MemoryEntry] = {}

    def remember(
        self,
        namespace: str,
        values: tuple[MemoryValue, ...],
        source: str,
        source_request_id: UUID | None = None,
    ) -> MemoryEntry:
        """Store one explicit fact after lazy expiration and FIFO eviction.

        Args:
            namespace: Stable owner-defined namespace.
            values: Immutable scalar fields selected by the caller.
            source: Stable identifier of the producing component.
            source_request_id: Optional request that produced the fact.

        Returns:
            The immutable stored entry.
        """
        now = self._clock.now()
        self._remove_expired(now)
        entry = MemoryEntry(
            entry_id=uuid4(),
            namespace=namespace,
            values=values,
            source=source,
            source_request_id=source_request_id,
            created_at=now,
            expires_at=now + self._policy.entry_ttl,
        )
        while len(self._entries) >= self._policy.capacity:
            oldest_entry_id = next(iter(self._entries))
            del self._entries[oldest_entry_id]
        self._entries[entry.entry_id] = entry
        return entry

    def recall(self, entry_id: UUID) -> MemoryEntry | None:
        """Return one unexpired entry without changing its lifetime or order."""
        self._validate_entry_id(entry_id)
        self._remove_expired(self._clock.now())
        return self._entries.get(entry_id)

    def snapshot(self) -> MemorySnapshot:
        """Capture entries newest-first in one immutable stable view."""
        now = self._clock.now()
        self._remove_expired(now)
        return MemorySnapshot(
            captured_at=now,
            entries=tuple(reversed(tuple(self._entries.values()))),
        )

    def forget(self, entry_id: UUID) -> bool:
        """Remove one unexpired entry without changing unrelated entries."""
        self._validate_entry_id(entry_id)
        self._remove_expired(self._clock.now())
        return self._entries.pop(entry_id, None) is not None

    def clear(self) -> int:
        """Remove every current entry without performing expiration work."""
        removed_count = len(self._entries)
        self._entries.clear()
        return removed_count

    def _remove_expired(self, now: datetime) -> None:
        expired_entry_ids = tuple(
            entry_id
            for entry_id, entry in self._entries.items()
            if entry.expires_at <= now
        )
        for entry_id in expired_entry_ids:
            del self._entries[entry_id]

    @staticmethod
    def _validate_entry_id(entry_id: UUID) -> None:
        if not isinstance(entry_id, UUID):
            raise InvalidMemoryIdentifierError(
                "Working Memory entry identifier must be a UUID."
            )
