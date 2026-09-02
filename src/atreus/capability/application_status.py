"""Controlled read-only application-status capability."""

from uuid import uuid4

from atreus.application.contracts import supported_application_action
from atreus.application.models import ApplicationIntent
from atreus.capability.contracts import (
    APPLICATION_ID_ARGUMENT,
    APPLICATION_STATUS_CAPABILITY_ID,
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
from atreus.interfaces.application_state_reader import ApplicationStateReader
from atreus.interfaces.capability import Capability
from atreus.system.models import (
    APPLICATION_READ_PERMISSION,
    ApplicationIdentifier,
    ApplicationState,
    ApplicationStatusRequest,
    ApplicationStatusResult,
    SystemOperationContext,
)


class ApplicationStatusCapability(Capability):
    """Read state for one approved application through the System Layer."""

    def __init__(self, application_state_reader: ApplicationStateReader) -> None:
        """Initialize the capability with the read-only application boundary."""
        self._application_state_reader = application_state_reader
        self._metadata = CapabilityMetadata(
            identifier=APPLICATION_STATUS_CAPABILITY_ID,
            name="Application Status",
            description="Read state for one explicitly approved application.",
            permissions=(APPLICATION_READ_PERMISSION,),
            availability=CapabilityAvailability(
                CapabilityAvailabilityState.AVAILABLE
            ),
            dependencies=(),
            requires_ai=False,
        )

    @property
    def metadata(self) -> CapabilityMetadata:
        """Return immutable application-status metadata."""
        return self._metadata

    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput:
        """Read one approved application's normalized state."""
        application_id = self._application_id(arguments)
        if (
            supported_application_action(
                ApplicationIntent.APPLICATION_STATUS,
                application_id,
            )
            is None
        ):
            raise ValueError("Application status is not supported.")
        status = self._application_state_reader.read_status(
            ApplicationStatusRequest(application_id),
            SystemOperationContext(
                operation_id=uuid4(),
                request_id=context.request_id,
                capability_id=self.metadata.identifier,
                permission_grants=context.permission_grants,
                cancellation=context.cancellation,
            ),
        )
        if (
            not isinstance(status, ApplicationStatusResult)
            or status.application_id is not application_id
            or not isinstance(status.state, ApplicationState)
        ):
            raise ValueError("Application status result is inconsistent.")
        return (
            CapabilityOutputItem("application_id", status.application_id.value),
            CapabilityOutputItem("state", status.state.value),
        )

    @staticmethod
    def _application_id(
        arguments: CapabilityArguments,
    ) -> ApplicationIdentifier:
        if len(arguments) != 1 or arguments[0].name != APPLICATION_ID_ARGUMENT:
            raise ValueError(
                "Application status requires one application_id argument."
            )
        value = arguments[0].value
        if not isinstance(value, str):
            raise ValueError("Application identifier must be a string.")
        try:
            return ApplicationIdentifier(value)
        except ValueError:
            raise ValueError("Application identifier is not approved.") from None
