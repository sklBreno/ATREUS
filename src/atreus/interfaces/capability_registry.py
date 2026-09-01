"""Capability Registry contracts exposed to ATREUS modules."""

from abc import ABC, abstractmethod

from atreus.capability.models import CapabilityAvailability, CapabilityMetadata


class CapabilityCatalog(ABC):
    """Define read-only capability metadata discovery."""

    @abstractmethod
    def get(self, identifier: str) -> CapabilityMetadata | None:
        """Return metadata for a valid identifier when registered.

        Args:
            identifier: Stable capability identifier.

        Returns:
            Capability metadata, or ``None`` when it is not registered.
        """

    @abstractmethod
    def list_all(self) -> tuple[CapabilityMetadata, ...]:
        """Return all metadata ordered by capability identifier."""

    @abstractmethod
    def list_available(self) -> tuple[CapabilityMetadata, ...]:
        """Return effectively available metadata ordered by identifier."""


class CapabilityRegistry(CapabilityCatalog, ABC):
    """Define the controlled capability registration lifecycle."""

    @abstractmethod
    def register(self, metadata: CapabilityMetadata) -> None:
        """Register one immutable capability description.

        Args:
            metadata: Validated capability metadata.
        """

    @abstractmethod
    def update_availability(
        self,
        identifier: str,
        availability: CapabilityAvailability,
    ) -> None:
        """Update declared availability for a registered capability.

        Args:
            identifier: Stable capability identifier.
            availability: New declared availability.
        """

    @abstractmethod
    def seal(self) -> None:
        """Prevent further capability registrations."""
