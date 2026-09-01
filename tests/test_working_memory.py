"""Behavior tests for bounded process-local Working Memory."""

import ast
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from atreus.interfaces.clock import Clock
from atreus.memory.exceptions import (
    InvalidMemoryEntryError,
    InvalidMemorySnapshotError,
    InvalidMemoryValueError,
    InvalidWorkingMemoryPolicyError,
)
from atreus.memory.models import (
    MemoryEntry,
    MemorySnapshot,
    MemoryValue,
    WorkingMemoryPolicy,
)
from atreus.memory.working_memory import InMemoryWorkingMemory

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class MutableClock(Clock):
    """Expose deterministic controllable UTC time to memory tests."""

    def __init__(self, now: datetime = NOW) -> None:
        """Initialize the current timestamp."""
        self.current = now

    def now(self) -> datetime:
        """Return the current test timestamp."""
        return self.current

    def advance(self, delta: timedelta) -> None:
        """Advance the current timestamp by one deterministic duration."""
        self.current += delta


def make_store(
    clock: MutableClock | None = None,
    *,
    capacity: int = 3,
    ttl: timedelta = timedelta(minutes=30),
) -> tuple[InMemoryWorkingMemory, MutableClock]:
    """Create an empty store with deterministic policy and time."""
    selected_clock = clock or MutableClock()
    return (
        InMemoryWorkingMemory(
            selected_clock,
            WorkingMemoryPolicy(capacity, ttl),
        ),
        selected_clock,
    )


def remember(
    store: InMemoryWorkingMemory,
    value: str,
) -> MemoryEntry:
    """Store one deterministic test fact."""
    return store.remember(
        "tests.recent_action",
        (MemoryValue("application_id", value),),
        "tests",
    )


def test_memory_models_are_immutable_and_use_slots() -> None:
    store, _ = make_store()
    entry = remember(store, "calculator")
    snapshot = store.snapshot()

    with pytest.raises(FrozenInstanceError):
        entry.namespace = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.entries = ()  # type: ignore[misc]

    assert not hasattr(MemoryValue("status", True), "__dict__")
    assert not hasattr(entry, "__dict__")
    assert not hasattr(snapshot, "__dict__")


def test_memory_timestamps_are_normalized_to_utc() -> None:
    offset = timezone(timedelta(hours=-4))
    created_at = datetime(2026, 9, 1, 8, 0, tzinfo=offset)
    entry = MemoryEntry(
        uuid4(),
        "tests",
        (MemoryValue("status", "ok"),),
        "tests",
        None,
        created_at,
        created_at + timedelta(minutes=1),
    )
    snapshot = MemorySnapshot(created_at, (entry,))

    assert entry.created_at == NOW
    assert entry.created_at.tzinfo is UTC
    assert snapshot.captured_at == NOW
    assert snapshot.captured_at.tzinfo is UTC


@pytest.mark.parametrize("field_name", ("created_at", "expires_at"))
def test_memory_entry_rejects_naive_timestamps(field_name: str) -> None:
    values: dict[str, object] = {
        "entry_id": uuid4(),
        "namespace": "tests",
        "values": (MemoryValue("status", "ok"),),
        "source": "tests",
        "source_request_id": None,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=1),
    }
    values[field_name] = datetime(2026, 9, 1, 12, 0)

    with pytest.raises(InvalidMemoryEntryError, match="timezone-aware"):
        MemoryEntry(**values)  # type: ignore[arg-type]


def test_memory_snapshot_rejects_naive_timestamp() -> None:
    with pytest.raises(InvalidMemorySnapshotError, match="timezone-aware"):
        MemorySnapshot(datetime(2026, 9, 1, 12, 0), ())


@pytest.mark.parametrize("field_name", ("namespace", "source"))
def test_memory_entry_rejects_empty_owner_fields(field_name: str) -> None:
    values: dict[str, object] = {
        "entry_id": uuid4(),
        "namespace": "tests",
        "values": (MemoryValue("status", "ok"),),
        "source": "tests",
        "source_request_id": None,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=1),
    }
    values[field_name] = "   "

    with pytest.raises(InvalidMemoryEntryError):
        MemoryEntry(**values)  # type: ignore[arg-type]


def test_memory_value_rejects_empty_name() -> None:
    with pytest.raises(InvalidMemoryValueError, match="name"):
        MemoryValue(" ", "value")


@pytest.mark.parametrize("value", (None, (), [], {}, object()))
def test_memory_value_rejects_arbitrary_payloads(value: object) -> None:
    with pytest.raises(InvalidMemoryValueError, match="strings"):
        MemoryValue("value", value)  # type: ignore[arg-type]


def test_memory_value_accepts_bool_and_int_as_distinct_supported_types() -> None:
    assert type(MemoryValue("enabled", True).value) is bool
    assert type(MemoryValue("count", 1).value) is int


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_memory_value_rejects_non_finite_float(value: float) -> None:
    with pytest.raises(InvalidMemoryValueError, match="finite"):
        MemoryValue("measurement", value)


@pytest.mark.parametrize(
    "expires_at",
    (NOW, NOW - timedelta(seconds=1)),
)
def test_memory_entry_requires_expiration_after_creation(
    expires_at: datetime,
) -> None:
    with pytest.raises(InvalidMemoryEntryError, match="follow"):
        MemoryEntry(
            uuid4(),
            "tests",
            (MemoryValue("status", "ok"),),
            "tests",
            None,
            NOW,
            expires_at,
        )


@pytest.mark.parametrize("capacity", (0, -1, True))
def test_working_memory_policy_rejects_invalid_capacity(capacity: object) -> None:
    with pytest.raises(InvalidWorkingMemoryPolicyError, match="capacity"):
        WorkingMemoryPolicy(  # type: ignore[arg-type]
            capacity,
            timedelta(minutes=30),
        )


@pytest.mark.parametrize("ttl", (timedelta(0), timedelta(seconds=-1)))
def test_working_memory_policy_rejects_invalid_ttl(ttl: timedelta) -> None:
    with pytest.raises(InvalidWorkingMemoryPolicyError, match="entry_ttl"):
        WorkingMemoryPolicy(64, ttl)


def test_store_starts_empty_and_remembers_entry() -> None:
    store, _ = make_store()

    assert store.snapshot().entries == ()

    entry = remember(store, "calculator")

    assert store.recall(entry.entry_id) is entry
    assert entry.expires_at - entry.created_at == timedelta(minutes=30)


def test_forget_and_clear_report_removed_entries() -> None:
    store, _ = make_store()
    first = remember(store, "calculator")
    remember(store, "notepad")

    assert store.forget(first.entry_id) is True
    assert store.forget(first.entry_id) is False
    assert store.clear() == 1
    assert store.snapshot().entries == ()


def test_recall_does_not_renew_ttl() -> None:
    store, clock = make_store(ttl=timedelta(minutes=30))
    entry = remember(store, "calculator")
    clock.advance(timedelta(minutes=29))

    assert store.recall(entry.entry_id) is entry

    clock.advance(timedelta(minutes=2))
    assert store.recall(entry.entry_id) is None


def test_expired_entries_are_removed_before_capacity_eviction() -> None:
    store, clock = make_store(capacity=1, ttl=timedelta(minutes=1))
    expired = remember(store, "calculator")
    clock.advance(timedelta(minutes=2))

    current = remember(store, "notepad")

    assert store.recall(expired.entry_id) is None
    assert store.recall(current.entry_id) is current


def test_capacity_evicts_oldest_entry_with_fifo_policy() -> None:
    store, clock = make_store(capacity=2)
    first = remember(store, "calculator")
    clock.advance(timedelta(seconds=1))
    second = remember(store, "notepad")
    assert store.recall(first.entry_id) is first
    clock.advance(timedelta(seconds=1))

    third = remember(store, "spotify")

    assert store.recall(first.entry_id) is None
    assert store.recall(second.entry_id) is second
    assert store.recall(third.entry_id) is third
    assert len(store.snapshot().entries) == 2


def test_invalid_write_does_not_evict_valid_entry() -> None:
    store, _ = make_store(capacity=1)
    current = remember(store, "calculator")

    with pytest.raises(InvalidMemoryEntryError):
        store.remember(
            " ",
            (MemoryValue("application_id", "notepad"),),
            "tests",
        )

    assert store.snapshot().entries == (current,)


def test_snapshot_orders_entries_newest_first() -> None:
    store, clock = make_store()
    first = remember(store, "calculator")
    clock.advance(timedelta(seconds=1))
    second = remember(store, "notepad")

    snapshot = store.snapshot()

    assert snapshot.entries == (second, first)


def test_previous_snapshot_does_not_change_after_new_write() -> None:
    store, _ = make_store()
    first = remember(store, "calculator")
    previous = store.snapshot()

    second = remember(store, "notepad")

    assert previous.entries == (first,)
    assert store.snapshot().entries == (second, first)


def test_memory_module_has_no_external_or_persistent_dependencies() -> None:
    forbidden_roots = {
        "asyncio",
        "sqlite3",
        "threading",
        "pathlib",
        "os",
        "ai",
    }
    source_files = tuple(Path("src/atreus/memory").glob("*.py"))

    assert source_files
    for source_file in source_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.partition(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert forbidden_roots.isdisjoint(imported_roots)


def test_capability_runtime_has_no_working_memory_dependency() -> None:
    runtime_source = Path("src/atreus/execution/runtime.py").read_text(
        encoding="utf-8"
    )

    assert "MemoryStore" not in runtime_source
    assert "MemorySnapshotProvider" not in runtime_source
    assert "atreus.memory" not in runtime_source
