"""Bounded structured interpretation for approved operational requests."""

import json
from math import isfinite
from uuid import uuid4

from atreus.ai.exceptions import (
    InterpretationTargetUnavailableError,
    InvalidRequestInterpretationError,
)
from atreus.ai.models import (
    AIProviderAvailabilityState,
    AIRequest,
    AIRequestPurpose,
    RequestInterpretation,
)
from atreus.application.contracts import (
    APPLICATION_ACTION_DEFINITIONS,
    supported_application_action,
)
from atreus.application.models import ApplicationActionDefinition, ApplicationIntent
from atreus.capability.models import CapabilityAvailabilityState
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.capability_registry import CapabilityCatalog
from atreus.interfaces.request_interpreter import RequestInterpreter
from atreus.shared.request import Request
from atreus.system.models import ApplicationIdentifier

_INTERPRETATION_INSTRUCTION = (
    "Interpret only an approved OPEN_APPLICATION or APPLICATION_STATUS request. "
    "Return exactly the required structured fields. Never return commands, paths, "
    "executable names, arguments, permissions, or additional actions."
)


class StructuredRequestInterpreter(RequestInterpreter):
    """Use AI only to identify one locally approved application action."""

    def __init__(
        self,
        provider: AIProvider,
        capability_catalog: CapabilityCatalog,
        timeout_seconds: float,
    ) -> None:
        """Initialize the interpreter with provider and catalog boundaries."""
        self._provider = provider
        self._capability_catalog = capability_catalog
        self._timeout_seconds = timeout_seconds

    def interpret(self, request: Request) -> RequestInterpretation:
        """Return one locally validated non-executable interpretation."""
        candidates = self._available_action_definitions()
        availability = self._provider.availability()
        if availability.state is not AIProviderAvailabilityState.AVAILABLE:
            raise InterpretationTargetUnavailableError(
                "Request interpretation provider is unavailable."
            )
        ai_request = AIRequest(
            ai_request_id=uuid4(),
            request_id=request.request_id,
            purpose=AIRequestPurpose.REQUEST_INTERPRETATION,
            instruction=_INTERPRETATION_INSTRUCTION,
            content=request.content,
            timeout_seconds=self._timeout_seconds,
        )
        response = self._provider.generate(ai_request)
        if (
            response.ai_request_id != ai_request.ai_request_id
            or response.request_id != request.request_id
        ):
            raise InvalidRequestInterpretationError(
                "AI response request identity is inconsistent."
            )
        return self._parse_response(request, response.content, candidates)

    def _available_action_definitions(
        self,
    ) -> tuple[ApplicationActionDefinition, ...]:
        candidates = tuple(
            definition
            for definition in APPLICATION_ACTION_DEFINITIONS
            if definition.supported
            and (
                (metadata := self._capability_catalog.get(definition.capability_id))
                is not None
                and metadata.availability.state
                is CapabilityAvailabilityState.AVAILABLE
            )
        )
        if not candidates:
            raise InterpretationTargetUnavailableError(
                "Approved interpretation capabilities are unavailable."
            )
        return candidates

    @staticmethod
    def _parse_response(
        request: Request,
        content: str,
        candidates: tuple[ApplicationActionDefinition, ...],
    ) -> RequestInterpretation:
        try:
            decoded = json.loads(content)
        except (TypeError, json.JSONDecodeError) as error:
            raise InvalidRequestInterpretationError(
                "AI structured output is malformed."
            ) from error
        if not isinstance(decoded, dict) or set(decoded) != {
            "intent_id",
            "target_id",
            "confidence",
        }:
            raise InvalidRequestInterpretationError(
                "AI structured output fields are invalid."
            )
        try:
            intent_id = ApplicationIntent(decoded["intent_id"])
        except (TypeError, ValueError):
            raise InvalidRequestInterpretationError(
                "AI structured output intent is unsupported."
            ) from None
        try:
            application_id = ApplicationIdentifier(decoded["target_id"])
        except (TypeError, ValueError):
            raise InvalidRequestInterpretationError(
                "AI structured output target is unsupported."
            ) from None
        confidence = decoded["confidence"]
        if (
            type(confidence) not in {int, float}
            or not isfinite(float(confidence))
            or not 0.0 <= confidence <= 1.0
        ):
            raise InvalidRequestInterpretationError(
                "AI structured output confidence is invalid."
            )
        action = supported_application_action(intent_id, application_id)
        if action is None or not any(
            candidate.intent_id is action.intent_id
            and candidate.application_id is action.application_id
            and candidate.capability_id == action.capability_id
            for candidate in candidates
        ):
            raise InvalidRequestInterpretationError(
                "AI structured output action is unsupported."
            )
        return RequestInterpretation(
            request_id=request.request_id,
            action=action,
            confidence=float(confidence),
        )
