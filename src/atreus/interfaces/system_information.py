"""Narrow read-only System Layer information contract."""

from abc import ABC, abstractmethod

from atreus.system.models import SystemOperationContext, SystemSnapshot


class SystemInformationProvider(ABC):
    """Provide an approved current system metrics snapshot."""

    @abstractmethod
    def snapshot(self, context: SystemOperationContext) -> SystemSnapshot:
        """Return a bounded platform-neutral system snapshot.

        Args:
            context: Correlation, grants, and cancellation for the operation.

        Returns:
            The immutable normalized system metrics snapshot.
        """
