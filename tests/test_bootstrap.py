"""Integration tests for the ATREUS foundation Bootstrap."""

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
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
