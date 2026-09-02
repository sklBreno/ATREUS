"""Event Bus subscriber producing sanitized structured log records."""

from atreus.ai.models import AIRequestCompleted, AIRequestFailed, AIRequestStarted
from atreus.core.models import ErrorOccurred, RequestCompleted, RequestReceived
from atreus.decision.models import DecisionMade
from atreus.events.models import Subscription
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionFailed,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
)
from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.log_writer import LogWriter
from atreus.logging.models import StructuredLogRecord
from atreus.planner.models import PlanCreated
from atreus.request_classifier.models import RequestClassified
from atreus.runtime.models import (
    RuntimeFailed,
    RuntimeStarted,
    RuntimeStarting,
    RuntimeStopped,
    RuntimeStopping,
)

type ObservableEvent = (
    RequestReceived
    | RequestClassified
    | DecisionMade
    | PlanCreated
    | CapabilityExecutionStarted
    | CapabilityExecutionCompleted
    | CapabilityExecutionFailed
    | RequestCompleted
    | ErrorOccurred
    | RuntimeStarting
    | RuntimeStarted
    | RuntimeStopping
    | RuntimeStopped
    | RuntimeFailed
    | AIRequestStarted
    | AIRequestCompleted
    | AIRequestFailed
)


class EventLogObserver:
    """Observe runtime and request facts without influencing publishers."""

    def __init__(self, writer: LogWriter) -> None:
        """Initialize the observer with an injected structured writer.

        Args:
            writer: Persistence boundary for sanitized records.
        """
        self._writer = writer

    def subscribe(self, event_bus: EventBus) -> tuple[Subscription, ...]:
        """Subscribe to the observable runtime and request lifecycle.

        Args:
            event_bus: Synchronous Event Bus registration boundary.

        Returns:
            Handles for the exact event subscriptions created.
        """
        return (
            event_bus.subscribe(RequestReceived, self._observe),
            event_bus.subscribe(RequestClassified, self._observe),
            event_bus.subscribe(DecisionMade, self._observe),
            event_bus.subscribe(PlanCreated, self._observe),
            event_bus.subscribe(CapabilityExecutionStarted, self._observe),
            event_bus.subscribe(CapabilityExecutionCompleted, self._observe),
            event_bus.subscribe(CapabilityExecutionFailed, self._observe),
            event_bus.subscribe(RequestCompleted, self._observe),
            event_bus.subscribe(ErrorOccurred, self._observe),
            event_bus.subscribe(RuntimeStarting, self._observe),
            event_bus.subscribe(RuntimeStarted, self._observe),
            event_bus.subscribe(RuntimeStopping, self._observe),
            event_bus.subscribe(RuntimeStopped, self._observe),
            event_bus.subscribe(RuntimeFailed, self._observe),
            event_bus.subscribe(AIRequestStarted, self._observe),
            event_bus.subscribe(AIRequestCompleted, self._observe),
            event_bus.subscribe(AIRequestFailed, self._observe),
        )

    def _observe(self, event: ObservableEvent) -> None:
        self._writer.write(self._record(event))

    @staticmethod
    def _record(event: ObservableEvent) -> StructuredLogRecord:
        common = {
            "timestamp": event.occurred_at,
            "event_type": type(event).__name__,
            "correlation_id": event.correlation_id,
        }
        if isinstance(event, RuntimeFailed):
            return StructuredLogRecord(
                **common,
                level="ERROR",
                lifecycle_state=event.lifecycle_state.value,
                reason_code=f"{event.failure_stage}:{event.error_type}",
                message="Runtime lifecycle failed.",
            )
        if isinstance(
            event,
            (RuntimeStarting, RuntimeStarted, RuntimeStopping, RuntimeStopped),
        ):
            return StructuredLogRecord(
                **common,
                level="INFO",
                lifecycle_state=event.lifecycle_state.value,
                message="Runtime lifecycle state changed.",
            )
        request_common = {**common, "request_id": event.request_id}
        if isinstance(event, AIRequestStarted):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                provider_id=event.provider_id,
                message="AI Provider request started.",
            )
        if isinstance(event, AIRequestCompleted):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                provider_id=event.provider_id,
                model_id=event.model_id,
                message="AI Provider request completed.",
            )
        if isinstance(event, AIRequestFailed):
            return StructuredLogRecord(
                **request_common,
                level="ERROR",
                provider_id=event.provider_id,
                reason_code=event.error_code,
                message="AI Provider request failed.",
            )
        if isinstance(event, RequestReceived):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                message="Request accepted by Core.",
            )
        if isinstance(event, RequestClassified):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                message="Request classification completed.",
            )
        if isinstance(event, DecisionMade):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                decision_outcome=event.outcome.value,
                reason_code=event.reason_code,
                message="Request decision completed.",
            )
        if isinstance(event, PlanCreated):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                message="Request plan created.",
            )
        if isinstance(event, CapabilityExecutionStarted):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                capability_id=event.capability_id,
                message="Capability execution started.",
            )
        if isinstance(event, CapabilityExecutionCompleted):
            return StructuredLogRecord(
                **request_common,
                level="INFO",
                capability_id=event.capability_id,
                execution_status=CapabilityExecutionStatus.SUCCEEDED.value,
                message="Capability execution completed.",
            )
        if isinstance(event, CapabilityExecutionFailed):
            return StructuredLogRecord(
                **request_common,
                level="ERROR",
                capability_id=event.capability_id,
                execution_status=event.terminal_status.value,
                reason_code=event.error_code,
                message="Capability execution failed.",
            )
        if isinstance(event, RequestCompleted):
            failed = any(
                status is not CapabilityExecutionStatus.SUCCEEDED
                for status in event.execution_statuses
            )
            execution_status = (
                event.execution_statuses[0].value
                if len(event.execution_statuses) == 1
                else None
            )
            return StructuredLogRecord(
                **request_common,
                level="ERROR" if failed else "INFO",
                decision_outcome=event.decision_outcome.value,
                execution_status=execution_status,
                message="Request completed.",
            )
        if isinstance(event, ErrorOccurred):
            return StructuredLogRecord(
                **request_common,
                level="ERROR",
                reason_code=event.error_type,
                message="Request orchestration failed.",
            )
        raise TypeError(f"Unsupported observable event: {type(event).__name__}.")
