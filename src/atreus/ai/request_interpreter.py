"""Bounded structured interpretation for approved operational requests."""

import json
from math import isfinite
from uuid import uuid4

from atreus.ai.exceptions import (
    InterpretationTargetUnavailableError,
    InvalidRequestInterpretationError,
)
from atreus.ai.models import (
    AIActionCandidate,
    AIIntent,
    AIProviderAvailabilityState,
    AIRequest,
    AIRequestPurpose,
    RequestInterpretation,
)
from atreus.capability.contracts import (
    OPEN_APPLICATION_CAPABILITY_ID,
    OPEN_APPLICATION_COMMAND_TARGETS,
)
from atreus.capability.models import CapabilityAvailabilityState
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.capability_registry import CapabilityCatalog
from atreus.interfaces.request_interpreter import RequestInterpreter
from atreus.shared.request import Request

_OPEN_APPLICATION_TARGET_IDS = tuple(
    target_id for _, target_id in OPEN_APPLICATION_COMMAND_TARGETS
)
_INTERPRETATION_INSTRUCTION = (
    "Interpret only an approved OPEN_APPLICATION request. Return exactly the "
    "required structured fields. Never return commands, paths, executable names, "
    "arguments, permissions, or additional actions."
)


class StructuredRequestInterpreter(RequestInterpreter):
    """Use an AI Provider only to identify one approved application target."""

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
        candidate = self._open_application_candidate()
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
        return self._parse_response(request, response.content, candidate)

    def _open_application_candidate(self) -> AIActionCandidate:
        metadata = self._capability_catalog.get(OPEN_APPLICATION_CAPABILITY_ID)
        if (
            metadata is None
            or metadata.availability.state
            is not CapabilityAvailabilityState.AVAILABLE
        ):
            raise InterpretationTargetUnavailableError(
                "Approved interpretation capability is unavailable."
            )
        return AIActionCandidate(
            intent_id=AIIntent.OPEN_APPLICATION,
            capability_id=metadata.identifier,
            target_ids=_OPEN_APPLICATION_TARGET_IDS,
        )

    @staticmethod
    def _parse_response(
        request: Request,
        content: str,
        candidate: AIActionCandidate,
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
        intent_id = decoded["intent_id"]
        target_id = decoded["target_id"]
        confidence = decoded["confidence"]
        if intent_id != candidate.intent_id.value:
            raise InvalidRequestInterpretationError(
                "AI structured output intent is unsupported."
            )
        if type(target_id) is not str or target_id not in candidate.target_ids:
            raise InvalidRequestInterpretationError(
                "AI structured output target is unsupported."
            )
        if (
            type(confidence) not in {int, float}
            or not isfinite(float(confidence))
            or not 0.0 <= confidence <= 1.0
        ):
            raise InvalidRequestInterpretationError(
                "AI structured output confidence is invalid."
            )
        return RequestInterpretation(
            request_id=request.request_id,
            intent_id=candidate.intent_id,
            capability_id=candidate.capability_id,
            target_id=target_id,
            confidence=float(confidence),
        )
