"""Event Bus contracts exposed to ATREUS modules."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from atreus.events.models import Event, PublicationResult, Subscription


class EventBus(ABC):
    """Define synchronous publication and subscription behavior."""

    @abstractmethod
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
        """

    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove exactly one event registration.

        Args:
            subscription: Opaque registration handle returned by ``subscribe``.
        """

    @abstractmethod
    def publish(self, event: Event) -> PublicationResult:
        """Publish one event synchronously.

        Args:
            event: Immutable event to deliver.

        Returns:
            An immutable summary of successful and failed deliveries.
        """
