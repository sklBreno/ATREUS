"""Behavior tests for the synchronous in-process Event Bus."""

from dataclasses import FrozenInstanceError, dataclass

import pytest

from atreus.events.event_bus import InProcessEventBus
from atreus.events.exceptions import (
    InvalidEventError,
    InvalidEventHandlerError,
    UnknownSubscriptionError,
)
from atreus.events.models import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class ExampleEvent(Event):
    """Represent a test event with a typed payload."""

    value: str


@dataclass(frozen=True, slots=True, kw_only=True)
class OtherEvent(Event):
    """Represent a distinct test event type."""


def test_publish_without_subscribers_returns_empty_result() -> None:
    event_bus = InProcessEventBus()

    result = event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert result.delivered_count == 0
    assert result.failures == ()


def test_publish_delivers_to_one_subscriber() -> None:
    event_bus = InProcessEventBus()
    received: list[str] = []
    event_bus.subscribe(ExampleEvent, lambda event: received.append(event.value))

    result = event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert received == ["payload"]
    assert result.delivered_count == 1


def test_publish_preserves_multiple_subscriber_order() -> None:
    event_bus = InProcessEventBus()
    calls: list[str] = []
    event_bus.subscribe(ExampleEvent, lambda event: calls.append("first"))
    event_bus.subscribe(ExampleEvent, lambda event: calls.append("second"))

    result = event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert calls == ["first", "second"]
    assert result.delivered_count == 2


def test_unsubscribe_removes_exact_registration() -> None:
    event_bus = InProcessEventBus()
    calls: list[str] = []
    first = event_bus.subscribe(ExampleEvent, lambda event: calls.append("first"))
    event_bus.subscribe(ExampleEvent, lambda event: calls.append("second"))

    event_bus.unsubscribe(first)
    event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert calls == ["second"]
    with pytest.raises(UnknownSubscriptionError):
        event_bus.unsubscribe(first)


def test_unsubscribe_rejects_invalid_handle_explicitly() -> None:
    event_bus = InProcessEventBus()

    with pytest.raises(UnknownSubscriptionError):
        event_bus.unsubscribe(object())  # type: ignore[arg-type]


def test_subscriptions_match_exact_concrete_event_type() -> None:
    event_bus = InProcessEventBus()
    received: list[Event] = []
    event_bus.subscribe(Event, received.append)

    event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert received == []


def test_subscriber_failure_is_isolated_and_sanitized() -> None:
    event_bus = InProcessEventBus()
    calls: list[str] = []

    def fail(event: ExampleEvent) -> None:
        raise RuntimeError("sensitive failure detail")

    failed_subscription = event_bus.subscribe(ExampleEvent, fail)
    event_bus.subscribe(ExampleEvent, lambda event: calls.append("completed"))

    result = event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert calls == ["completed"]
    assert result.delivered_count == 1
    assert len(result.failures) == 1
    assert result.failures[0].subscription == failed_subscription
    assert result.failures[0].error_type == "RuntimeError"
    assert "sensitive" not in result.failures[0].description


def test_nested_publication_is_a_separate_synchronous_delivery() -> None:
    event_bus = InProcessEventBus()
    calls: list[str] = []

    def publish_nested(event: ExampleEvent) -> None:
        calls.append("outer-start")
        event_bus.publish(OtherEvent(source="test"))
        calls.append("outer-end")

    event_bus.subscribe(ExampleEvent, publish_nested)
    event_bus.subscribe(OtherEvent, lambda event: calls.append("nested"))

    event_bus.publish(ExampleEvent(source="test", value="payload"))

    assert calls == ["outer-start", "nested", "outer-end"]


def test_publication_uses_stable_subscription_snapshot() -> None:
    event_bus = InProcessEventBus()
    calls: list[str] = []

    def subscribe_during_delivery(event: ExampleEvent) -> None:
        calls.append("first")
        event_bus.subscribe(ExampleEvent, lambda nested: calls.append("late"))

    event_bus.subscribe(ExampleEvent, subscribe_during_delivery)

    event_bus.publish(ExampleEvent(source="test", value="one"))
    event_bus.publish(ExampleEvent(source="test", value="two"))

    assert calls == ["first", "first", "late"]


def test_event_and_publication_result_are_immutable() -> None:
    event_bus = InProcessEventBus()
    event = ExampleEvent(source="test", value="payload")
    result = event_bus.publish(event)

    with pytest.raises(FrozenInstanceError):
        event.value = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.delivered_count = 1  # type: ignore[misc]


def test_invalid_publication_and_subscription_raise_explicit_errors() -> None:
    event_bus = InProcessEventBus()

    with pytest.raises(InvalidEventError):
        event_bus.publish("not an event")  # type: ignore[arg-type]
    with pytest.raises(InvalidEventHandlerError):
        event_bus.subscribe(str, lambda event: None)  # type: ignore[type-var]
    with pytest.raises(InvalidEventHandlerError):
        event_bus.subscribe(ExampleEvent, "not callable")  # type: ignore[arg-type]
