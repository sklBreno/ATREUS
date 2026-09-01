"""Behavior and integration tests for the Core Phase A foundation."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.core.core import Core
from atreus.core.exceptions import InconsistentClassificationError
from atreus.core.models import CoreRequestStatus, RequestReceived
from atreus.events.event_bus import InProcessEventBus
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.request_classifier.classifier import DeterministicRequestClassifier
from atreus.request_classifier.models import (
    ClassifiedRequest,
    RequestClassified,
    RequestType,
)
from atreus.shared.request import Request


def make_request(content: str = "Open the settings") -> Request:
    """Create a normalized request for Core tests."""
    return Request(
        request_id=uuid4(),
        content=content,
        source="text",
        received_at=datetime.now(UTC),
    )


def make_capability(identifier: str) -> CapabilityMetadata:
    """Create available capability metadata for Core discovery tests."""
    return CapabilityMetadata(
        identifier=identifier,
        name="Open Application",
        description="Open one local application.",
        permissions=("application.control",),
        availability=CapabilityAvailability(
            CapabilityAvailabilityState.AVAILABLE
        ),
        dependencies=(),
        requires_ai=False,
    )


def test_core_advances_request_to_controlled_decision_boundary() -> None:
    event_bus = InProcessEventBus()
    registry = InMemoryCapabilityRegistry()
    capability = make_capability("application.open")
    registry.register(capability)
    core = Core(
        event_bus=event_bus,
        request_classifier=DeterministicRequestClassifier(event_bus),
        capability_catalog=registry,
    )
    request = make_request()

    result = core.handle_request(request)

    assert result.request_id == request.request_id
    assert result.classification.request_type is RequestType.COMMAND
    assert result.available_capabilities == (capability,)
    assert result.status is CoreRequestStatus.DECISION_REQUIRED
    assert not hasattr(result, "execution_result")
    assert not hasattr(result, "plan")


def test_core_and_classifier_publish_owned_events_in_flow_order() -> None:
    event_bus = InProcessEventBus()
    event_order: list[str] = []
    event_bus.subscribe(
        RequestReceived,
        lambda event: event_order.append(type(event).__name__),
    )
    event_bus.subscribe(
        RequestClassified,
        lambda event: event_order.append(type(event).__name__),
    )
    core = Core(
        event_bus,
        DeterministicRequestClassifier(event_bus),
        InMemoryCapabilityRegistry(),
    )
    request = make_request("Why is the sky blue?")

    core.handle_request(request)

    assert event_order == ["RequestReceived", "RequestClassified"]


def test_core_object_processes_multiple_requests_without_reconstruction() -> None:
    event_bus = InProcessEventBus()
    core = Core(
        event_bus,
        DeterministicRequestClassifier(event_bus),
        InMemoryCapabilityRegistry(),
    )

    first = core.handle_request(make_request("Hello"))
    second = core.handle_request(make_request("What time is it?"))

    assert first.classification.request_type is RequestType.CONVERSATION
    assert second.classification.request_type is RequestType.QUESTION
    assert first.request_id != second.request_id


class MismatchedRequestClassifier(RequestClassifier):
    """Return an invalid classification identity for boundary testing."""

    def classify(self, request: Request) -> ClassifiedRequest:
        """Return a classification for a different request identifier."""
        return ClassifiedRequest(
            request_id=uuid4(),
            request_type=RequestType.COMMAND,
            confidence=1.0,
        )


def test_core_rejects_classification_for_different_request() -> None:
    core = Core(
        InProcessEventBus(),
        MismatchedRequestClassifier(),
        InMemoryCapabilityRegistry(),
    )

    with pytest.raises(InconsistentClassificationError):
        core.handle_request(make_request())
