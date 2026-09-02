"""Tests for production event-driven observability."""

import json
from pathlib import Path
from typing import cast
from uuid import uuid4

from atreus.ai.models import AIRequestCompleted, AIRequestFailed, AIRequestStarted
from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.core.models import ErrorOccurred, RequestCompleted, RequestReceived
from atreus.decision.models import DecisionMade, DecisionOutcome
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionFailed,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
)
from atreus.interfaces.log_writer import LogWriter
from atreus.logging.event_observer import EventLogObserver
from atreus.logging.jsonl_writer import JsonLinesLogWriter
from atreus.logging.models import StructuredLogRecord
from atreus.planner.models import PlanCreated
from atreus.request_classifier.models import RequestClassified, RequestType
from atreus.runtime.models import (
    RuntimeFailed,
    RuntimeLifecycleState,
    RuntimeStarted,
    RuntimeStarting,
    RuntimeStopped,
    RuntimeStopping,
)
from atreus.system.windows_application_controller import (
    WindowsApplicationController,
)
from tests.support import (
    NOW,
    FixedClock,
    RecordingApplicationController,
    RecordingLogWriter,
)

type JsonRecord = dict[str, object]


def make_configuration_manager(log_level: str = "INFO") -> ConfigurationManager:
    """Create deterministic configuration with one explicit logging level."""
    return ConfigurationManager(
        loader=ConfigurationLoader(
            env_file_path=None,
            environment={"ATREUS_LOG_LEVEL": log_level},
        )
    )


def read_json_lines(path: Path) -> list[JsonRecord]:
    """Read one test JSON object per line from a temporary log file."""
    return [
        cast(JsonRecord, json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def make_record(*, level: str, event_type: str) -> StructuredLogRecord:
    """Create one deterministic structured record for writer tests."""
    request_id = uuid4()
    return StructuredLogRecord(
        timestamp=NOW,
        level=level,
        event_type=event_type,
        message="Lifecycle event observed.",
        correlation_id=request_id,
        request_id=request_id,
    )


def test_json_lines_writer_appends_valid_structured_records(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "atreus.log"
    writer = JsonLinesLogWriter(log_path, "INFO")

    writer.write(make_record(level="INFO", event_type="RequestReceived"))
    writer.write(make_record(level="ERROR", event_type="ErrorOccurred"))

    records = read_json_lines(log_path)
    assert [record["event_type"] for record in records] == [
        "RequestReceived",
        "ErrorOccurred",
    ]
    assert all(record["timestamp"] == "2026-08-31T12:00:00Z" for record in records)
    assert log_path.read_bytes().count(b"\n") == 2


def test_json_lines_writer_respects_minimum_level(tmp_path: Path) -> None:
    log_path = tmp_path / "atreus.log"
    writer = JsonLinesLogWriter(log_path, "ERROR")

    writer.write(make_record(level="INFO", event_type="RequestReceived"))
    writer.write(make_record(level="ERROR", event_type="ErrorOccurred"))

    records = read_json_lines(log_path)
    assert [record["event_type"] for record in records] == ["ErrorOccurred"]


def test_observer_subscribes_to_runtime_and_request_lifecycle() -> None:
    request_id = uuid4()
    invocation_id = uuid4()
    writer = RecordingLogWriter()
    event_bus = InProcessEventBus()
    subscriptions = EventLogObserver(writer).subscribe(event_bus)
    common = {
        "source": "test",
        "occurred_at": NOW,
        "correlation_id": request_id,
    }
    events = (
        RequestReceived(**common, request_id=request_id),
        RequestClassified(
            **common,
            request_id=request_id,
            request_type=RequestType.COMMAND,
            confidence=1.0,
        ),
        DecisionMade(
            **common,
            request_id=request_id,
            outcome=DecisionOutcome.REQUEST_PLANNING,
            target="application.open",
            reason_code="command_requires_explicit_plan",
        ),
        PlanCreated(
            **common,
            plan_id=uuid4(),
            request_id=request_id,
            capability_ids=("application.open",),
            step_count=1,
            requires_confirmation=False,
        ),
        CapabilityExecutionStarted(
            **common,
            invocation_id=invocation_id,
            request_id=request_id,
            capability_id="application.open",
            plan_id=uuid4(),
            step_id="step-1",
        ),
        CapabilityExecutionCompleted(
            **common,
            invocation_id=invocation_id,
            request_id=request_id,
            capability_id="application.open",
            plan_id=uuid4(),
            step_id="step-1",
            duration_seconds=0.0,
        ),
        CapabilityExecutionFailed(
            **common,
            invocation_id=invocation_id,
            request_id=request_id,
            capability_id="application.open",
            plan_id=uuid4(),
            step_id="step-1",
            terminal_status=CapabilityExecutionStatus.FAILED,
            error_code="capability_execution_failed",
        ),
        RequestCompleted(
            **common,
            request_id=request_id,
            decision_outcome=DecisionOutcome.REQUEST_PLANNING,
            execution_statuses=(CapabilityExecutionStatus.FAILED,),
        ),
        ErrorOccurred(
            **common,
            request_id=request_id,
            orchestration_step="planning",
            error_type="InconsistentPlanError",
        ),
        RuntimeStarting(
            source="runtime_host",
            occurred_at=NOW,
            lifecycle_state=RuntimeLifecycleState.STARTING,
        ),
        RuntimeStarted(
            source="runtime_host",
            occurred_at=NOW,
            lifecycle_state=RuntimeLifecycleState.RUNNING,
        ),
        RuntimeStopping(
            source="runtime_host",
            occurred_at=NOW,
            lifecycle_state=RuntimeLifecycleState.STOPPING,
        ),
        RuntimeStopped(
            source="runtime_host",
            occurred_at=NOW,
            lifecycle_state=RuntimeLifecycleState.STOPPED,
        ),
        RuntimeFailed(
            source="runtime_host",
            occurred_at=NOW,
            lifecycle_state=RuntimeLifecycleState.FAILED,
            failure_stage="startup",
            error_type="OSError",
        ),
        AIRequestStarted(
            **common,
            ai_request_id=uuid4(),
            request_id=request_id,
            provider_id="openai",
        ),
        AIRequestCompleted(
            **common,
            ai_request_id=uuid4(),
            request_id=request_id,
            provider_id="openai",
            model_id="test-model",
            duration_seconds=0.1,
        ),
        AIRequestFailed(
            **common,
            ai_request_id=uuid4(),
            request_id=request_id,
            provider_id="openai",
            error_code="AIRequestTimeoutError",
        ),
    )

    for event in events:
        event_bus.publish(event)

    assert len(subscriptions) == 17
    assert [record.event_type for record in writer.records] == [
        "RequestReceived",
        "RequestClassified",
        "DecisionMade",
        "PlanCreated",
        "CapabilityExecutionStarted",
        "CapabilityExecutionCompleted",
        "CapabilityExecutionFailed",
        "RequestCompleted",
        "ErrorOccurred",
        "RuntimeStarting",
        "RuntimeStarted",
        "RuntimeStopping",
        "RuntimeStopped",
        "RuntimeFailed",
        "AIRequestStarted",
        "AIRequestCompleted",
        "AIRequestFailed",
    ]

    assert all(record.provider_id in {None, "openai"} for record in writer.records)
    assert not hasattr(events[-3], "content")
    assert not hasattr(events[-2], "response")
    assert not hasattr(events[-1], "error_message")


def test_runtime_failure_log_is_structured_and_sanitized(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "atreus.log"

    def fail_input(prompt: str) -> str:
        raise RuntimeError("private terminal and environment detail")

    host = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=RecordingApplicationController(),
        clock=FixedClock(),
        log_path=log_path,
    ).compose_host(fail_input, lambda output: None)

    assert host.run() == 1

    records = read_json_lines(log_path)
    assert [record["event_type"] for record in records] == [
        "RuntimeStarting",
        "RuntimeStarted",
        "RuntimeFailed",
    ]
    assert [record["lifecycle_state"] for record in records] == [
        "STARTING",
        "RUNNING",
        "FAILED",
    ]
    assert records[-1]["reason_code"] == "foreground_interface:RuntimeError"
    serialized = log_path.read_text(encoding="utf-8")
    assert "private terminal" not in serialized
    assert "environment detail" not in serialized


def test_bootstrap_logs_correlated_success_without_sensitive_data(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "logs" / "atreus.log"
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=controller,
        clock=FixedClock(),
        log_path=log_path,
    ).compose()

    result = runtime.submit("open calculator")

    records = read_json_lines(log_path)
    assert [record["event_type"] for record in records] == [
        "RequestReceived",
        "RequestClassified",
        "DecisionMade",
        "PlanCreated",
        "CapabilityExecutionStarted",
        "CapabilityExecutionCompleted",
        "RequestCompleted",
    ]
    assert {record["correlation_id"] for record in records} == {
        str(result.request_id)
    }
    assert {record["request_id"] for record in records} == {
        str(result.request_id)
    }
    serialized = log_path.read_text(encoding="utf-8")
    assert "open calculator" not in serialized
    assert "application_id" not in serialized
    assert "application.control" not in serialized
    assert "calc.exe" not in serialized


def test_failed_execution_is_sanitized_and_uses_configured_level(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "atreus.log"
    commands: list[tuple[str, ...]] = []
    controller = WindowsApplicationController(
        lambda command: commands.append(command) or 1234,
        "win32",
    )
    runtime = Bootstrap(
        configuration_provider=make_configuration_manager("ERROR"),
        application_controller=controller,
        clock=FixedClock(),
        log_path=log_path,
    ).compose()

    result = runtime.submit("open spotify")

    assert result.execution_results[0].status is CapabilityExecutionStatus.FAILED
    assert commands == []
    records = read_json_lines(log_path)
    assert [record["event_type"] for record in records] == [
        "CapabilityExecutionFailed",
        "RequestCompleted",
    ]
    assert records[0]["execution_status"] == "FAILED"
    assert records[0]["reason_code"] == "capability_execution_failed"
    assert all(record["level"] == "ERROR" for record in records)
    assert "spotify" not in log_path.read_text(encoding="utf-8")


def test_non_executing_decision_logs_no_capability_lifecycle() -> None:
    controller = RecordingApplicationController()
    writer = RecordingLogWriter()
    runtime = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=controller,
        clock=FixedClock(),
        log_writer=writer,
    ).compose()

    result = runtime.submit("open calculator && shutdown")

    assert result.execution_results == ()
    assert controller.calls == []
    assert [record.event_type for record in writer.records] == [
        "RequestReceived",
        "RequestClassified",
        "DecisionMade",
        "RequestCompleted",
    ]
    assert writer.records[2].decision_outcome == "ASK_FOR_CONFIRMATION"


def test_logging_write_failure_does_not_break_request_pipeline() -> None:
    class FailingLogWriter(LogWriter):
        """Raise one isolated persistence failure for every record."""

        def write(self, record: StructuredLogRecord) -> None:
            """Fail without exposing record contents."""
            raise OSError("private logging failure")

    controller = RecordingApplicationController()
    runtime = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=controller,
        clock=FixedClock(),
        log_writer=FailingLogWriter(),
    ).compose()

    result = runtime.submit("open calculator")

    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED
    assert len(controller.calls) == 1
