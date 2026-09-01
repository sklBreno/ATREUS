"""Controlled application-opening capability."""

from uuid import uuid4

from atreus.capability.contracts import (
    APPLICATION_ID_ARGUMENT,
    OPEN_APPLICATION_CAPABILITY_ID,
    CapabilityArguments,
    CapabilityOutput,
    CapabilityOutputItem,
)
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.execution.models import ExecutionContext
from atreus.interfaces.application_controller import ApplicationController
from atreus.interfaces.capability import Capability
from atreus.system.models import (
    APPLICATION_CONTROL_PERMISSION,
    ApplicationIdentifier,
    ApplicationLaunchRequest,
    SystemOperationContext,
)


class OpenApplicationCapability(Capability):
    """Open one explicitly allowlisted application through the System Layer."""

    def __init__(self, application_controller: ApplicationController) -> None:
        """Initialize the capability with the application-control boundary.

        Args:
            application_controller: Controlled System Layer application service.
        """
        self._application_controller = application_controller
        self._metadata = CapabilityMetadata(
            identifier=OPEN_APPLICATION_CAPABILITY_ID,
            name="Open Application",
            description="Open one explicitly approved desktop application.",
            permissions=(APPLICATION_CONTROL_PERMISSION,),
            availability=CapabilityAvailability(
                CapabilityAvailabilityState.AVAILABLE
            ),
            dependencies=(),
            requires_ai=False,
        )

    @property
    def metadata(self) -> CapabilityMetadata:
        """Return immutable application-opening metadata."""
        return self._metadata

    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput:
        """Open one approved application from a validated identifier.

        Args:
            arguments: Exactly one ``application_id`` string argument.
            context: Correlation, grants, context, and cancellation metadata.

        Returns:
            Immutable normalized launch result values.

        Raises:
            ValueError: If arguments do not identify an approved application.
        """
        application_id = self._application_id(arguments)
        instance = self._application_controller.launch(
            ApplicationLaunchRequest(application_id),
            SystemOperationContext(
                operation_id=uuid4(),
                request_id=context.request_id,
                capability_id=self.metadata.identifier,
                permission_grants=context.permission_grants,
                cancellation=context.cancellation,
            ),
        )
        return (
            CapabilityOutputItem("application_id", instance.application_id.value),
            CapabilityOutputItem("process_id", instance.process_id),
            CapabilityOutputItem("status", "launched"),
        )

    @staticmethod
    def _application_id(
        arguments: CapabilityArguments,
    ) -> ApplicationIdentifier:
        if len(arguments) != 1 or arguments[0].name != APPLICATION_ID_ARGUMENT:
            raise ValueError(
                "Open application requires one application_id argument."
            )
        value = arguments[0].value
        if not isinstance(value, str):
            raise ValueError("Application identifier must be a string.")
        try:
            return ApplicationIdentifier(value)
        except ValueError:
            raise ValueError("Application identifier is not approved.") from None
