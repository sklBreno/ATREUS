"""Core request orchestration foundation for Runtime Phase A."""

from atreus.core.exceptions import InconsistentClassificationError
from atreus.core.models import CoreRequestResult, CoreRequestStatus, RequestReceived
from atreus.interfaces.capability_registry import CapabilityCatalog
from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.shared.request import Request


class Core:
    """Coordinate Phase A request flow without deciding or executing work."""

    def __init__(
        self,
        event_bus: EventBus,
        request_classifier: RequestClassifier,
        capability_catalog: CapabilityCatalog,
    ) -> None:
        """Initialize Core with explicit runtime contracts.

        Args:
            event_bus: Synchronous domain event publication boundary.
            request_classifier: Request classification boundary.
            capability_catalog: Read-only capability discovery boundary.
        """
        self._event_bus = event_bus
        self._request_classifier = request_classifier
        self._capability_catalog = capability_catalog

    def handle_request(self, request: Request) -> CoreRequestResult:
        """Advance one request to the future Decision Engine boundary.

        Args:
            request: Immutable normalized request accepted for orchestration.

        Returns:
            A controlled outcome containing classification and candidates.

        Raises:
            InconsistentClassificationError: If classification changes identity.
        """
        self._event_bus.publish(
            RequestReceived(
                source="core",
                correlation_id=request.request_id,
                request_id=request.request_id,
            )
        )
        classification = self._request_classifier.classify(request)
        if classification.request_id != request.request_id:
            raise InconsistentClassificationError(
                "Classification request identity does not match Core input."
            )

        return CoreRequestResult(
            request_id=request.request_id,
            classification=classification,
            available_capabilities=self._capability_catalog.list_available(),
            status=CoreRequestStatus.DECISION_REQUIRED,
        )
