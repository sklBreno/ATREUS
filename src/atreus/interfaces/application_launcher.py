"""Controlled System Layer application-launch contract."""

from abc import ABC, abstractmethod

from atreus.system.models import (
    ApplicationInstance,
    ApplicationLaunchRequest,
    SystemOperationContext,
)


class ApplicationLauncher(ABC):
    """Launch explicitly identified applications through a narrow boundary."""

    @abstractmethod
    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance:
        """Launch one approved application and return its normalized instance."""
