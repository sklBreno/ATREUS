"""Safe fallback implementation of the System Information boundary."""

from atreus.interfaces.clock import Clock
from atreus.interfaces.system_information import SystemInformationProvider
from atreus.system.exceptions import (
    InvalidSystemOperationError,
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
)
from atreus.system.models import (
    SYSTEM_METRICS_READ_PERMISSION,
    MetricAvailabilityStatus,
    PowerSource,
    SystemOperationContext,
    SystemSnapshot,
)


class UnavailableSystemInformationProvider(SystemInformationProvider):
    """Report unavailable metrics without calling native operating-system APIs."""

    def __init__(self, clock: Clock) -> None:
        """Initialize the provider with an injectable clock.

        Args:
            clock: Time source used for snapshot observation metadata.
        """
        self._clock = clock

    def snapshot(self, context: SystemOperationContext) -> SystemSnapshot:
        """Return a normalized unavailable snapshot after policy checks.

        Args:
            context: Correlation, grants, and cancellation for the operation.

        Returns:
            A snapshot indicating that no native metrics adapter is configured.

        Raises:
            InvalidSystemOperationError: If the context is invalid.
            SystemPermissionDeniedError: If metrics permission is absent.
            SystemOperationCancelledError: If cancellation was requested.
        """
        if not isinstance(context, SystemOperationContext):
            raise InvalidSystemOperationError(
                "System snapshot requires a SystemOperationContext."
            )
        if SYSTEM_METRICS_READ_PERMISSION not in context.permission_grants:
            raise SystemPermissionDeniedError(
                "System metrics permission is required."
            )
        if context.cancellation.is_cancelled():
            raise SystemOperationCancelledError(
                "System snapshot operation was cancelled."
            )

        return SystemSnapshot(
            cpu_utilization=None,
            gpu_utilization=None,
            available_memory_bytes=None,
            total_memory_bytes=None,
            battery_level=None,
            power_source=PowerSource.UNKNOWN,
            observed_at=self._clock.now(),
            metric_status=MetricAvailabilityStatus.UNAVAILABLE,
        )
