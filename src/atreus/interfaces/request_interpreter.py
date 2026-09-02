"""Boundary for bounded AI-assisted request interpretation."""

from abc import ABC, abstractmethod

from atreus.ai.models import RequestInterpretation
from atreus.shared.request import Request


class RequestInterpreter(ABC):
    """Interpret one request into a validated non-executable candidate."""

    @abstractmethod
    def interpret(self, request: Request) -> RequestInterpretation:
        """Return one locally validated interpretation for a request."""
