"""Behavior tests for the minimal controlled System Layer boundary."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from atreus.shared.cancellation import StaticCancellationSignal
from atreus.system.exceptions import (
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
)
from atreus.system.models import (
    MetricAvailabilityStatus,
    PowerSource,
    SystemOperationContext,
)
from atreus.system.system_information import UnavailableSystemInformationProvider
from tests.support import NOW, FixedClock


def make_context(
    *,
    grants: tuple[str, ...] = ("system.metrics.read",),
    cancelled: bool = False,
) -> SystemOperationContext:
    """Create a controlled system operation context."""
    return SystemOperationContext(
        uuid4(),
        uuid4(),
        "system.snapshot",
        grants,
        StaticCancellationSignal(cancelled),
    )


def test_safe_provider_returns_normalized_unavailable_snapshot() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    snapshot = provider.snapshot(make_context())

    assert snapshot.metric_status is MetricAvailabilityStatus.UNAVAILABLE
    assert snapshot.power_source is PowerSource.UNKNOWN
    assert snapshot.cpu_utilization is None
    assert snapshot.observed_at == NOW
    with pytest.raises(FrozenInstanceError):
        snapshot.cpu_utilization = 1.0  # type: ignore[misc]


def test_system_layer_denies_missing_metrics_permission() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    with pytest.raises(SystemPermissionDeniedError):
        provider.snapshot(make_context(grants=()))


def test_system_layer_respects_pre_requested_cancellation() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    with pytest.raises(SystemOperationCancelledError):
        provider.snapshot(make_context(cancelled=True))


def test_system_information_boundary_has_no_arbitrary_execution() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    assert not hasattr(provider, "run")
    assert not hasattr(provider, "execute_command")
    assert not hasattr(provider, "shell")
    assert not hasattr(provider, "write_file")
