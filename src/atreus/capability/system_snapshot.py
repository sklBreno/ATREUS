"""Safe read-only system snapshot capability."""

from uuid import uuid4

from atreus.capability.contracts import (
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
from atreus.interfaces.capability import Capability
from atreus.interfaces.system_information import SystemInformationProvider
from atreus.system.models import SystemOperationContext


class SystemSnapshotCapability(Capability):
    """Expose approved system metrics through the controlled System Layer."""

    def __init__(self, system_information: SystemInformationProvider) -> None:
        """Initialize the capability with a narrow System Layer dependency.

        Args:
            system_information: Approved read-only metrics provider.
        """
        self._system_information = system_information
        self._metadata = CapabilityMetadata(
            identifier="system.snapshot",
            name="System Snapshot",
            description="Return approved current system metric availability.",
            permissions=("system.metrics.read",),
            availability=CapabilityAvailability(
                CapabilityAvailabilityState.AVAILABLE
            ),
            dependencies=(),
            requires_ai=False,
        )

    @property
    def metadata(self) -> CapabilityMetadata:
        """Return immutable metadata for the system snapshot capability."""
        return self._metadata

    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput:
        """Read one safe system snapshot without mutating the host.

        Args:
            arguments: Must be empty because this capability accepts no input.
            context: Correlation, grants, context, and cancellation metadata.

        Returns:
            Approved immutable metric values and availability metadata.

        Raises:
            ValueError: If unsupported arguments are supplied.
        """
        if arguments:
            raise ValueError("System snapshot capability accepts no arguments.")
        snapshot = self._system_information.snapshot(
            SystemOperationContext(
                operation_id=uuid4(),
                request_id=context.request_id,
                capability_id=self.metadata.identifier,
                permission_grants=context.permission_grants,
                cancellation=context.cancellation,
            )
        )
        return (
            CapabilityOutputItem("cpu_utilization", snapshot.cpu_utilization),
            CapabilityOutputItem("gpu_utilization", snapshot.gpu_utilization),
            CapabilityOutputItem(
                "available_memory_bytes",
                snapshot.available_memory_bytes,
            ),
            CapabilityOutputItem(
                "total_memory_bytes",
                snapshot.total_memory_bytes,
            ),
            CapabilityOutputItem("battery_level", snapshot.battery_level),
            CapabilityOutputItem("power_source", snapshot.power_source.value),
            CapabilityOutputItem("observed_at", snapshot.observed_at.isoformat()),
            CapabilityOutputItem("metric_status", snapshot.metric_status.value),
        )
