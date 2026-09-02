"""Controlled System Layer application-state observation contract."""

from abc import ABC, abstractmethod

from atreus.system.models import (
    ApplicationStatusRequest,
    ApplicationStatusResult,
    SystemOperationContext,
)


class ApplicationStateReader(ABC):
    """Read state only for explicitly identified approved applications."""

    @abstractmethod
    def read_status(
        self,
        request: ApplicationStatusRequest,
        context: SystemOperationContext,
    ) -> ApplicationStatusResult:
        """Return the normalized current state of one approved application."""
