"""Allowlisted Windows application controller implementation."""

import subprocess
import sys
from collections.abc import Callable

from atreus.interfaces.application_controller import ApplicationController
from atreus.system.exceptions import (
    InvalidSystemOperationError,
    SystemNativeAdapterError,
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
    UnsupportedSystemOperationError,
)
from atreus.system.models import (
    APPLICATION_CONTROL_PERMISSION,
    ApplicationIdentifier,
    ApplicationInstance,
    ApplicationLaunchRequest,
    SystemOperationContext,
)

_APPLICATION_COMMANDS = {
    ApplicationIdentifier.CALCULATOR: ("calc.exe",),
}
type _ProcessStarter = Callable[[tuple[str, ...]], int]


def _start_windows_process(command: tuple[str, ...]) -> int:
    process = subprocess.Popen(command, shell=False)
    return process.pid


class WindowsApplicationController(ApplicationController):
    """Launch applications from a fixed Windows-specific allowlist."""

    def __init__(
        self,
        process_starter: _ProcessStarter | None = None,
        platform_name: str = sys.platform,
    ) -> None:
        """Initialize the controller with an injectable native process starter.

        Args:
            process_starter: Internal adapter used to launch a fixed command.
            platform_name: Host platform identifier used for availability checks.
        """
        self._process_starter = process_starter or _start_windows_process
        self._platform_name = platform_name

    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance:
        """Launch one allowlisted application without shell execution.

        Args:
            request: Approved application launch request.
            context: Correlation, grants, and cancellation for the operation.

        Returns:
            The immutable normalized application instance.

        Raises:
            InvalidSystemOperationError: If request or context is invalid.
            SystemPermissionDeniedError: If application control is not granted.
            SystemOperationCancelledError: If cancellation was requested.
            UnsupportedSystemOperationError: If the host is not Windows.
            SystemNativeAdapterError: If Windows cannot launch the application.
        """
        if not isinstance(request, ApplicationLaunchRequest) or not isinstance(
            request.application_id,
            ApplicationIdentifier,
        ):
            raise InvalidSystemOperationError(
                "Application launch requires an approved application identifier."
            )
        if not isinstance(context, SystemOperationContext):
            raise InvalidSystemOperationError(
                "Application launch requires a SystemOperationContext."
            )
        if APPLICATION_CONTROL_PERMISSION not in context.permission_grants:
            raise SystemPermissionDeniedError(
                "Application control permission is required."
            )
        if context.cancellation.is_cancelled():
            raise SystemOperationCancelledError(
                "Application launch operation was cancelled."
            )
        if self._platform_name != "win32":
            raise UnsupportedSystemOperationError(
                "Application launch is unavailable on this platform."
            )

        command = _APPLICATION_COMMANDS[request.application_id]
        try:
            process_id = self._process_starter(command)
        except OSError:
            raise SystemNativeAdapterError(
                f"Unable to launch approved application '{request.application_id}'."
            ) from None
        if process_id <= 0:
            raise SystemNativeAdapterError(
                f"Unable to launch approved application '{request.application_id}'."
            )
        return ApplicationInstance(request.application_id, process_id)
