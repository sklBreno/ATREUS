"""Read-only context contract exposed to ATREUS consumers."""

from abc import ABC, abstractmethod

from atreus.context.models import ContextSnapshot


class ContextProvider(ABC):
    """Provide the latest normalized immutable context snapshot."""

    @abstractmethod
    def current_context(self) -> ContextSnapshot:
        """Return the current context snapshot."""
