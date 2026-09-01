"""Immutable contracts owned by the ATREUS Working Memory module."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from uuid import UUID

from atreus.memory.exceptions import (
    InvalidMemoryEntryError,
    InvalidMemorySnapshotError,
    InvalidMemoryValueError,
    InvalidWorkingMemoryPolicyError,
)

type MemoryScalar = str | int | float | bool


def _normalize_timestamp(
    timestamp: datetime,
    field_name: str,
    error_type: type[InvalidMemoryEntryError | InvalidMemorySnapshotError],
) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise error_type(f"Memory {field_name} must be timezone-aware.")
    return timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class MemoryValue:
    """Represent one named immutable scalar stored in Working Memory."""

    name: str
    value: MemoryScalar

    def __post_init__(self) -> None:
        """Validate the bounded scalar value contract.

        Raises:
            InvalidMemoryValueError: If the name or scalar is invalid.
        """
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidMemoryValueError(
                "Memory value name must be a non-empty string."
            )
        if type(self.value) not in {str, int, float, bool}:
            raise InvalidMemoryValueError(
                "Memory values must be strings, integers, floats, or booleans."
            )
        if isinstance(self.value, float) and not isfinite(self.value):
            raise InvalidMemoryValueError(
                "Memory float values must be finite."
            )


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """Represent one validated temporary Working Memory fact."""

    entry_id: UUID
    namespace: str
    values: tuple[MemoryValue, ...]
    source: str
    source_request_id: UUID | None
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        """Validate entry identity, ownership, values, and lifetime.

        Raises:
            InvalidMemoryEntryError: If the entry is inconsistent.
        """
        if not isinstance(self.entry_id, UUID):
            raise InvalidMemoryEntryError("Memory entry_id must be a UUID.")
        if not isinstance(self.namespace, str) or not self.namespace.strip():
            raise InvalidMemoryEntryError(
                "Memory namespace must be a non-empty string."
            )
        if not isinstance(self.source, str) or not self.source.strip():
            raise InvalidMemoryEntryError(
                "Memory source must be a non-empty string."
            )
        if self.source_request_id is not None and not isinstance(
            self.source_request_id,
            UUID,
        ):
            raise InvalidMemoryEntryError(
                "Memory source_request_id must be a UUID when provided."
            )
        if not isinstance(self.values, tuple) or not self.values or any(
            not isinstance(value, MemoryValue) for value in self.values
        ):
            raise InvalidMemoryEntryError(
                "Memory entry values must be a non-empty tuple of MemoryValue."
            )
        names = tuple(value.name for value in self.values)
        if len(names) != len(set(names)):
            raise InvalidMemoryEntryError(
                "Memory value names must be unique within an entry."
            )

        created_at = _normalize_timestamp(
            self.created_at,
            "created_at",
            InvalidMemoryEntryError,
        )
        expires_at = _normalize_timestamp(
            self.expires_at,
            "expires_at",
            InvalidMemoryEntryError,
        )
        if expires_at <= created_at:
            raise InvalidMemoryEntryError(
                "Memory expires_at must follow created_at."
            )
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    """Represent a stable immutable view of current Working Memory."""

    captured_at: datetime
    entries: tuple[MemoryEntry, ...]

    def __post_init__(self) -> None:
        """Validate snapshot timestamp and immutable entry collection.

        Raises:
            InvalidMemorySnapshotError: If the snapshot is invalid.
        """
        if not isinstance(self.entries, tuple) or any(
            not isinstance(entry, MemoryEntry) for entry in self.entries
        ):
            raise InvalidMemorySnapshotError(
                "Memory snapshot entries must be a tuple of MemoryEntry."
            )
        captured_at = _normalize_timestamp(
            self.captured_at,
            "captured_at",
            InvalidMemorySnapshotError,
        )
        object.__setattr__(self, "captured_at", captured_at)


@dataclass(frozen=True, slots=True)
class WorkingMemoryPolicy:
    """Provide immutable capacity and lifetime limits for Working Memory."""

    capacity: int
    entry_ttl: timedelta

    def __post_init__(self) -> None:
        """Validate bounded Working Memory policy values.

        Raises:
            InvalidWorkingMemoryPolicyError: If a policy value is invalid.
        """
        if type(self.capacity) is not int or self.capacity <= 0:
            raise InvalidWorkingMemoryPolicyError(
                "Working Memory capacity must be a positive integer."
            )
        if not isinstance(self.entry_ttl, timedelta) or self.entry_ttl <= timedelta(0):
            raise InvalidWorkingMemoryPolicyError(
                "Working Memory entry_ttl must be positive."
            )
