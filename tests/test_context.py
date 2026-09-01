"""Tests for immutable Context V0 contracts and fallback behavior."""

import ast
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from atreus.context.exceptions import InvalidContextSnapshotError
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.context.unavailable_context import UnavailableContextProvider
from atreus.interfaces.clock import Clock
from tests.support import NOW


def make_snapshot(
    *,
    context_type: ContextType = ContextType.WORKING,
    confidence: float = 0.9,
    started_at: datetime = NOW,
    evaluated_at: datetime = NOW,
    signal_status: ContextSignalStatus = ContextSignalStatus.AVAILABLE,
) -> ContextSnapshot:
    """Create a valid context snapshot with overridable fields."""
    return ContextSnapshot(
        context_type,
        confidence,
        started_at,
        evaluated_at,
        signal_status,
    )


def test_context_snapshot_is_immutable() -> None:
    snapshot = make_snapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.confidence = 0.5  # type: ignore[misc]


@pytest.mark.parametrize("confidence", (-0.1, 1.1, float("nan")))
def test_context_snapshot_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(InvalidContextSnapshotError):
        make_snapshot(confidence=confidence)


@pytest.mark.parametrize("field_name", ("started_at", "evaluated_at"))
def test_context_snapshot_rejects_naive_timestamps(field_name: str) -> None:
    values = {field_name: datetime(2026, 9, 1, 12, 0)}

    with pytest.raises(InvalidContextSnapshotError):
        make_snapshot(**values)  # type: ignore[arg-type]


def test_context_snapshot_normalizes_aware_timestamps_to_utc() -> None:
    local_time = datetime(
        2026,
        9,
        1,
        8,
        0,
        tzinfo=timezone(-timedelta(hours=4)),
    )

    snapshot = make_snapshot(started_at=local_time, evaluated_at=local_time)

    assert snapshot.started_at == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    assert snapshot.evaluated_at == snapshot.started_at
    assert snapshot.started_at.tzinfo is UTC


def test_context_snapshot_rejects_start_after_evaluation() -> None:
    with pytest.raises(InvalidContextSnapshotError):
        make_snapshot(
            started_at=NOW + timedelta(seconds=1),
            evaluated_at=NOW,
        )


@pytest.mark.parametrize(
    ("context_type", "confidence"),
    (
        (ContextType.WORKING, 0.0),
        (ContextType.UNKNOWN, 0.1),
    ),
)
def test_unavailable_context_requires_unknown_with_zero_confidence(
    context_type: ContextType,
    confidence: float,
) -> None:
    with pytest.raises(InvalidContextSnapshotError):
        make_snapshot(
            context_type=context_type,
            confidence=confidence,
            signal_status=ContextSignalStatus.UNAVAILABLE,
        )


class SequenceClock(Clock):
    """Return a bounded sequence of deterministic timestamps."""

    def __init__(self, timestamps: tuple[datetime, ...]) -> None:
        """Initialize the sequence used by consecutive reads."""
        self._timestamps = iter(timestamps)

    def now(self) -> datetime:
        """Return the next configured timestamp."""
        return next(self._timestamps)


def test_unavailable_provider_keeps_start_and_updates_evaluation_time() -> None:
    started_at = NOW
    first_evaluation = NOW + timedelta(seconds=1)
    second_evaluation = NOW + timedelta(seconds=2)
    provider = UnavailableContextProvider(
        SequenceClock((started_at, first_evaluation, second_evaluation))
    )

    first = provider.current_context()
    second = provider.current_context()

    assert first.context_type is ContextType.UNKNOWN
    assert first.confidence == 0.0
    assert first.signal_status is ContextSignalStatus.UNAVAILABLE
    assert first.started_at == started_at
    assert second.started_at == started_at
    assert first.evaluated_at == first_evaluation
    assert second.evaluated_at == second_evaluation


def test_context_domain_has_no_windows_or_native_process_imports() -> None:
    forbidden_imports = {
        "subprocess",
        "atreus.system.windows_application_controller",
    }

    for path in Path("src/atreus/context").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)
        assert imported_modules.isdisjoint(forbidden_imports)
