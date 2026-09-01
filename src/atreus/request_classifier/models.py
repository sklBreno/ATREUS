"""Immutable contracts owned by the Request Classifier."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from atreus.events.models import Event


class RequestType(StrEnum):
    """Identify one supported Version 1 request category."""

    COMMAND = "COMMAND"
    INTENTION = "INTENTION"
    QUESTION = "QUESTION"
    CONVERSATION = "CONVERSATION"
    TASK = "TASK"


@dataclass(frozen=True, slots=True)
class ClassifiedRequest:
    """Represent the immutable result of request classification."""

    request_id: UUID
    request_type: RequestType
    confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestClassified(Event):
    """Report that a request was classified successfully."""

    request_id: UUID
    request_type: RequestType
    confidence: float
