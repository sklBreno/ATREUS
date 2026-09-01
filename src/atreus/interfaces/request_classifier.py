"""Request Classifier contracts exposed to ATREUS consumers."""

from abc import ABC, abstractmethod

from atreus.request_classifier.models import ClassifiedRequest
from atreus.shared.request import Request


class RequestClassifier(ABC):
    """Define classification without routing or execution behavior."""

    @abstractmethod
    def classify(self, request: Request) -> ClassifiedRequest:
        """Classify one normalized request.

        Args:
            request: Immutable normalized user request.

        Returns:
            The immutable request type and confidence.
        """
