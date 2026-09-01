"""Deterministic Version 1 request classification."""

import re

from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.request_classifier.exceptions import InvalidRequestError
from atreus.request_classifier.models import (
    ClassifiedRequest,
    RequestClassified,
    RequestType,
)
from atreus.shared.request import Request

_CONVERSATION_PHRASES = frozenset(
    {
        "good afternoon",
        "good evening",
        "good morning",
        "hello",
        "hey",
        "hi",
        "how are you",
        "thank you",
        "thanks",
    }
)
_QUESTION_PREFIXES = (
    "can you explain",
    "could you explain",
    "how ",
    "what ",
    "when ",
    "where ",
    "which ",
    "who ",
    "why ",
)
_INTENTION_PREFIXES = (
    "help me ",
    "i need ",
    "i want ",
    "i would like ",
    "i'd like ",
    "let's ",
    "my goal is ",
)
_COMMAND_PREFIXES = (
    "close ",
    "create ",
    "launch ",
    "list ",
    "open ",
    "run ",
    "show ",
    "start ",
    "stop ",
    "turn ",
)
_TASK_PATTERN = re.compile(
    r"\b(?:at \d{1,2}(?::\d{2})?|by \d{1,2}(?::\d{2})?|deadline|"
    r"every day|next week|remind|schedule|tomorrow)\b"
)


class DeterministicRequestClassifier(RequestClassifier):
    """Classify requests through bounded deterministic rules."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the classifier with optional event publication.

        Args:
            event_bus: Event Bus used to publish successful classifications.
        """
        self._event_bus = event_bus

    def classify(self, request: Request) -> ClassifiedRequest:
        """Classify one request without routing or execution.

        Args:
            request: Immutable normalized user request.

        Returns:
            The immutable request type and confidence.

        Raises:
            InvalidRequestError: If request content is empty or invalid.
        """
        if not isinstance(request, Request):
            raise InvalidRequestError("Classification requires a Request instance.")

        content = request.content.strip()
        if not content:
            raise InvalidRequestError(
                f"Request {request.request_id} contains no classifiable content."
            )

        request_type, confidence = self._classify_content(content)
        classified_request = ClassifiedRequest(
            request_id=request.request_id,
            request_type=request_type,
            confidence=confidence,
        )
        self._publish_classification(classified_request)
        return classified_request

    @staticmethod
    def _classify_content(content: str) -> tuple[RequestType, float]:
        normalized_content = " ".join(content.casefold().split())
        phrase = normalized_content.strip(" .!?")

        if phrase in _CONVERSATION_PHRASES:
            return RequestType.CONVERSATION, 0.95
        if _TASK_PATTERN.search(normalized_content):
            return RequestType.TASK, 0.90
        if normalized_content.endswith("?") or normalized_content.startswith(
            _QUESTION_PREFIXES
        ):
            return RequestType.QUESTION, 0.95
        if normalized_content.startswith(_INTENTION_PREFIXES):
            return RequestType.INTENTION, 0.85
        if normalized_content.startswith(_COMMAND_PREFIXES):
            return RequestType.COMMAND, 0.90

        return RequestType.INTENTION, 0.25

    def _publish_classification(
        self,
        classified_request: ClassifiedRequest,
    ) -> None:
        if self._event_bus is None:
            return

        self._event_bus.publish(
            RequestClassified(
                source="request_classifier",
                correlation_id=classified_request.request_id,
                request_id=classified_request.request_id,
                request_type=classified_request.request_type,
                confidence=classified_request.confidence,
            )
        )
