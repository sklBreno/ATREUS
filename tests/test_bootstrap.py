"""Integration tests for the ATREUS foundation Bootstrap."""

from datetime import timedelta

import pytest

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
from atreus.interfaces.clock import Clock
from atreus.memory.models import MemorySnapshot, MemoryValue, WorkingMemoryPolicy
from atreus.memory.working_memory import InMemoryWorkingMemory
from tests.support import (
    FixedClock,
    RecordingApplicationController,
    RecordingLogWriter,
)


def test_bootstrap_runs_configuration_foundation_flow() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "false"},
    )
    manager = ConfigurationManager(loader=loader)

    configuration = Bootstrap(configuration_provider=manager).run()

    assert isinstance(configuration, Configuration)
    assert configuration.debug is False


def test_bootstrap_composes_complete_production_runtime() -> None:
    controller = RecordingApplicationController(process_id=2468)
    runtime = Bootstrap(
        application_controller=controller,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("open calculator")

    assert result.request_id == result.classification.request_id
    assert result.request_id == result.decision.request_id
    assert result.decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert result.plan is not None
    assert result.plan.request_id == result.request_id
    assert len(result.execution_results) == 1
    assert (
        result.execution_results[0].status
        is CapabilityExecutionStatus.SUCCEEDED
    )
    assert len(controller.calls) == 1


def test_bootstrap_does_not_bypass_runtime_permission_enforcement() -> None:
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        application_controller=controller,
        clock=FixedClock(),
        permission_grants=(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("open calculator")

    assert result.decision.outcome is DecisionOutcome.IGNORE
    assert result.decision.reason_code == "required_permission_missing"
    assert result.execution_results == ()
    assert controller.calls == []


def test_bootstrap_keeps_one_memory_store_per_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecordingWorkingMemory(InMemoryWorkingMemory):
        """Record snapshots captured by one composed runtime."""

        def __init__(self, clock: Clock, policy: WorkingMemoryPolicy) -> None:
            """Initialize the recording store."""
            super().__init__(clock, policy)
            self.snapshots: list[MemorySnapshot] = []

        def snapshot(self) -> MemorySnapshot:
            """Record and return one stable memory snapshot."""
            snapshot = super().snapshot()
            self.snapshots.append(snapshot)
            return snapshot

    stores: list[RecordingWorkingMemory] = []
    policies: list[WorkingMemoryPolicy] = []

    def create_store(
        clock: Clock,
        policy: WorkingMemoryPolicy,
    ) -> RecordingWorkingMemory:
        store = RecordingWorkingMemory(clock, policy)
        stores.append(store)
        policies.append(policy)
        return store

    monkeypatch.setattr(
        "atreus.bootstrap.bootstrap.InMemoryWorkingMemory",
        create_store,
    )
    bootstrap = Bootstrap(
        application_controller=RecordingApplicationController(),
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    )
    first_runtime = bootstrap.compose()
    first_store = stores[0]
    remembered = first_store.remember(
        "tests.recent_action",
        (MemoryValue("application_id", "calculator"),),
        "tests",
    )

    first_runtime.submit("arbitrary text")
    first_runtime.submit("arbitrary text")

    assert policies[0] == WorkingMemoryPolicy(
        64,
        timedelta(seconds=1800),
    )
    assert len(first_store.snapshots) == 2
    assert all(
        snapshot.entries == (remembered,)
        for snapshot in first_store.snapshots
    )

    second_runtime = bootstrap.compose()
    second_runtime.submit("arbitrary text")

    assert len(stores) == 2
    assert stores[1] is not first_store
    assert stores[1].snapshots[0].entries == ()
