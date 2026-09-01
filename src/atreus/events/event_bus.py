"""Synchronous in-process Event Bus implementation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from atreus.events.exceptions import (
    InvalidEventError,
    InvalidEventHandlerError,
    UnknownSubscriptionError,
)
from atreus.events.models import (
    Event,
    PublicationResult,
    SubscriberFailure,
    Subscription,
)
from atreus.interfaces.event_bus import EventBus

type EventHandler = Callable[[Event], None]


@dataclass(slots=True)
class _RegisteredSubscription:
    """Store one mutable internal registration."""

    subscription: Subscription
    handler: EventHandler


class InProcessEventBus(EventBus):
    """Deliver events synchronously in stable subscription order."""

    def __init__(self) -> None:
        """Initialize an empty in-process subscription catalog."""
        self._subscriptions: dict[type[Event], list[_RegisteredSubscription]] = {}

    def subscribe[EventType: Event](
        self,
        event_type: type[EventType],
        handler: Callable[[EventType], None],
    ) -> Subscription:
        """Register a handler for one exact concrete event type.

        Args:
            event_type: Concrete event type handled by the subscriber.
            handler: Callable invoked synchronously for matching events.

        Returns:
            An opaque handle for removing the registration.

        Raises:
            InvalidEventHandlerError: If the event type or handler is invalid.
        """
        if not isinstance(event_type, type) or not issubclass(event_type, Event):
            raise InvalidEventHandlerError("Subscriptions require an Event type.")
        if not callable(handler):
            raise InvalidEventHandlerError("Subscriptions require a callable handler.")

        subscription = Subscription()
        registration = _RegisteredSubscription(
            subscription=subscription,
            handler=cast(EventHandler, handler),
        )
        self._subscriptions.setdefault(event_type, []).append(registration)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove exactly one event registration.

        Args:
            subscription: Opaque registration handle returned by ``subscribe``.

        Raises:
            UnknownSubscriptionError: If the handle is not currently registered.
        """
        if not isinstance(subscription, Subscription):
            raise UnknownSubscriptionError("Unknown subscription handle.")

        for event_type, registrations in tuple(self._subscriptions.items()):
            for index, registration in enumerate(registrations):
                if registration.subscription == subscription:
                    del registrations[index]
                    if not registrations:
                        del self._subscriptions[event_type]
                    return

        raise UnknownSubscriptionError(
            f"Unknown subscription: {subscription.identifier}."
        )

    def publish(self, event: Event) -> PublicationResult:
        """Publish one event to exact-type subscribers in registration order.

        Args:
            event: Immutable event to deliver.

        Returns:
            An immutable summary of successful and failed deliveries.

        Raises:
            InvalidEventError: If the published object is not an Event.
        """
        if not isinstance(event, Event):
            raise InvalidEventError("Only Event instances can be published.")

        registrations = tuple(self._subscriptions.get(type(event), ()))
        failures: list[SubscriberFailure] = []
        delivered_count = 0

        for registration in registrations:
            try:
                registration.handler(event)
            except Exception as error:
                error_type = type(error).__name__
                failures.append(
                    SubscriberFailure(
                        subscription=registration.subscription,
                        error_type=error_type,
                        description=f"Subscriber raised {error_type}.",
                    )
                )
            else:
                delivered_count += 1

        return PublicationResult(
            delivered_count=delivered_count,
            failures=tuple(failures),
        )
