"""Allowlisted Windows application-state reader implementation."""

import csv
import subprocess
import sys
from collections.abc import Callable
from io import StringIO

from atreus.interfaces.application_state_reader import ApplicationStateReader
from atreus.system.exceptions import (
    InvalidSystemOperationError,
    SystemNativeAdapterError,
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
    UnsupportedSystemOperationError,
)
from atreus.system.models import (
    APPLICATION_READ_PERMISSION,
    ApplicationIdentifier,
    ApplicationState,
    ApplicationStatusRequest,
    ApplicationStatusResult,
    SystemOperationContext,
)

_APPLICATION_PROCESS_NAMES = {
    ApplicationIdentifier.CALCULATOR: frozenset(
        {"calculatorapp.exe", "calc.exe"}
    ),
    ApplicationIdentifier.NOTEPAD: frozenset({"notepad.exe"}),
}
type _ProcessNameReader = Callable[[], tuple[str, ...] | None]


def _read_windows_process_names() -> tuple[str, ...] | None:
    result = subprocess.run(
        ("tasklist.exe", "/FO", "CSV", "/NH"),
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    rows = tuple(csv.reader(StringIO(result.stdout)))
    process_names = tuple(row[0] for row in rows if row and row[0].strip())
    return process_names or None


class WindowsApplicationStateReader(ApplicationStateReader):
    """Observe approved application state through fixed native identities."""

    def __init__(
        self,
        process_name_reader: _ProcessNameReader | None = None,
        platform_name: str = sys.platform,
    ) -> None:
        """Initialize the reader with an injectable process observation boundary."""
        self._process_name_reader = (
            process_name_reader or _read_windows_process_names
        )
        self._platform_name = platform_name

    def read_status(
        self,
        request: ApplicationStatusRequest,
        context: SystemOperationContext,
    ) -> ApplicationStatusResult:
        """Read state for one allowlisted application without user native input."""
        if not isinstance(request, ApplicationStatusRequest) or not isinstance(
            request.application_id,
            ApplicationIdentifier,
        ):
            raise InvalidSystemOperationError(
                "Application status requires an approved application identifier."
            )
        if not isinstance(context, SystemOperationContext):
            raise InvalidSystemOperationError(
                "Application status requires a SystemOperationContext."
            )
        if APPLICATION_READ_PERMISSION not in context.permission_grants:
            raise SystemPermissionDeniedError(
                "Application read permission is required."
            )
        if context.cancellation.is_cancelled():
            raise SystemOperationCancelledError(
                "Application status operation was cancelled."
            )
        if self._platform_name != "win32":
            raise UnsupportedSystemOperationError(
                "Application status is unavailable on this platform."
            )
        approved_names = _APPLICATION_PROCESS_NAMES.get(request.application_id)
        if approved_names is None:
            raise UnsupportedSystemOperationError(
                f"Application '{request.application_id}' has no approved "
                "Windows status mapping."
            )
        try:
            process_names = self._process_name_reader()
        except (OSError, subprocess.SubprocessError):
            raise SystemNativeAdapterError(
                f"Unable to read approved application '{request.application_id}'."
            ) from None
        if process_names is None:
            state = ApplicationState.UNKNOWN
        elif approved_names.intersection(name.casefold() for name in process_names):
            state = ApplicationState.RUNNING
        else:
            state = ApplicationState.NOT_RUNNING
        return ApplicationStatusResult(request.application_id, state)
