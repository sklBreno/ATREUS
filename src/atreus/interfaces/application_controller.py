"""Controlled System Layer application-launch contract."""

from abc import ABC, abstractmethod

from atreus.system.models import (
    ApplicationInstance,
    ApplicationLaunchRequest,
    SystemOperationContext,
)


class ApplicationController(ABC):
    """Launch explicitly identified applications through a controlled boundary."""

    @abstractmethod
    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance:
        """Launch one approved application.

        Args:
            request: Platform-neutral approved application identifier.
            context: Correlation, grants, and cancellation for the operation.

        Returns:
            The immutable normalized launched application instance.
        """
