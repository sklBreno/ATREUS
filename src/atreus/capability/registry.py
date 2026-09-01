"""In-memory Capability Registry implementation."""

from dataclasses import replace
from threading import RLock

from atreus.capability.exceptions import (
    CapabilityDependencyCycleError,
    DuplicateCapabilityError,
    InvalidCapabilityIdentifierError,
    InvalidCapabilityMetadataError,
    RegistrySealedError,
    UnknownCapabilityError,
)
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityChanged,
    CapabilityAvailabilityState,
    CapabilityMetadata,
    CapabilityRegistered,
)
from atreus.interfaces.capability_registry import CapabilityRegistry
from atreus.interfaces.event_bus import EventBus


class InMemoryCapabilityRegistry(CapabilityRegistry):
    """Maintain an authoritative in-process capability metadata catalog."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize an empty registry with optional event publication.

        Args:
            event_bus: Event Bus used to publish catalog changes.
        """
        self._event_bus = event_bus
        self._declared_metadata: dict[str, CapabilityMetadata] = {}
        self._effective_metadata: dict[str, CapabilityMetadata] = {}
        self._sealed = False
        self._lock = RLock()

    def register(self, metadata: CapabilityMetadata) -> None:
        """Register one capability and recompute dependent availability.

        Args:
            metadata: Immutable capability metadata to register.

        Raises:
            InvalidCapabilityMetadataError: If metadata is invalid.
            DuplicateCapabilityError: If the identifier is already registered.
            RegistrySealedError: If registration has been sealed.
            CapabilityDependencyCycleError: If registration creates a cycle.
        """
        self._validate_metadata(metadata)

        with self._lock:
            if self._sealed:
                raise RegistrySealedError("Capability registration is sealed.")
            if metadata.identifier in self._declared_metadata:
                raise DuplicateCapabilityError(
                    f"Capability '{metadata.identifier}' is already registered."
                )

            previous_effective = self._effective_metadata
            self._declared_metadata[metadata.identifier] = metadata
            try:
                self._validate_dependency_graph()
            except CapabilityDependencyCycleError:
                del self._declared_metadata[metadata.identifier]
                raise

            self._effective_metadata = self._build_effective_metadata()
            current = self._effective_metadata[metadata.identifier]
            availability_changes = self._availability_changes(
                previous_effective,
                self._effective_metadata,
                excluded_identifier=metadata.identifier,
            )

        self._publish_registered(current)
        self._publish_availability_changes(availability_changes)

    def update_availability(
        self,
        identifier: str,
        availability: CapabilityAvailability,
    ) -> None:
        """Update declared availability and propagate dependency effects.

        Args:
            identifier: Stable capability identifier.
            availability: New declared availability.

        Raises:
            InvalidCapabilityIdentifierError: If the identifier is invalid.
            InvalidCapabilityMetadataError: If availability is invalid.
            UnknownCapabilityError: If the capability is not registered.
        """
        self._validate_identifier(identifier)
        self._validate_availability(availability)

        with self._lock:
            metadata = self._declared_metadata.get(identifier)
            if metadata is None:
                raise UnknownCapabilityError(
                    f"Capability '{identifier}' is not registered."
                )

            previous_effective = self._effective_metadata
            self._declared_metadata[identifier] = replace(
                metadata,
                availability=availability,
            )
            self._effective_metadata = self._build_effective_metadata()
            availability_changes = self._availability_changes(
                previous_effective,
                self._effective_metadata,
            )

        self._publish_availability_changes(availability_changes)

    def seal(self) -> None:
        """Prevent further registrations while allowing availability updates."""
        with self._lock:
            self._sealed = True

    def get(self, identifier: str) -> CapabilityMetadata | None:
        """Return effective metadata for a valid registered identifier.

        Args:
            identifier: Stable capability identifier.

        Returns:
            Effective capability metadata, or ``None`` when absent.

        Raises:
            InvalidCapabilityIdentifierError: If the identifier is invalid.
        """
        self._validate_identifier(identifier)
        with self._lock:
            return self._effective_metadata.get(identifier)

    def list_all(self) -> tuple[CapabilityMetadata, ...]:
        """Return all effective metadata ordered by identifier."""
        with self._lock:
            return tuple(
                self._effective_metadata[identifier]
                for identifier in sorted(self._effective_metadata)
            )

    def list_available(self) -> tuple[CapabilityMetadata, ...]:
        """Return effectively available metadata ordered by identifier."""
        return tuple(
            metadata
            for metadata in self.list_all()
            if metadata.availability.state is CapabilityAvailabilityState.AVAILABLE
        )

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if not isinstance(identifier, str) or not identifier.strip():
            raise InvalidCapabilityIdentifierError(
                "Capability identifiers must be non-empty strings."
            )
        if identifier != identifier.strip():
            raise InvalidCapabilityIdentifierError(
                "Capability identifiers cannot contain surrounding whitespace."
            )

    @classmethod
    def _validate_metadata(cls, metadata: CapabilityMetadata) -> None:
        if not isinstance(metadata, CapabilityMetadata):
            raise InvalidCapabilityMetadataError(
                "Registration requires CapabilityMetadata."
            )

        try:
            cls._validate_identifier(metadata.identifier)
        except InvalidCapabilityIdentifierError as error:
            raise InvalidCapabilityMetadataError(
                "Capability metadata contains an invalid identifier."
            ) from error
        if (
            not isinstance(metadata.name, str)
            or not metadata.name.strip()
            or not isinstance(metadata.description, str)
            or not metadata.description.strip()
        ):
            raise InvalidCapabilityMetadataError(
                "Capability name and description must be non-empty."
            )
        if not isinstance(metadata.permissions, tuple) or not isinstance(
            metadata.dependencies,
            tuple,
        ):
            raise InvalidCapabilityMetadataError(
                "Permissions and dependencies must be immutable tuples."
            )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in metadata.permissions
        ):
            raise InvalidCapabilityMetadataError(
                "Capability permission identifiers must be non-empty strings."
            )
        if len(metadata.permissions) != len(set(metadata.permissions)):
            raise InvalidCapabilityMetadataError(
                "Capability permission identifiers must be unique."
            )
        try:
            for dependency in metadata.dependencies:
                cls._validate_identifier(dependency)
        except InvalidCapabilityIdentifierError as error:
            raise InvalidCapabilityMetadataError(
                "Capability dependencies must contain valid identifiers."
            ) from error
        if len(metadata.dependencies) != len(set(metadata.dependencies)):
            raise InvalidCapabilityMetadataError(
                "Capability dependency identifiers must be unique."
            )
        if metadata.identifier in metadata.dependencies:
            raise CapabilityDependencyCycleError(
                f"Capability '{metadata.identifier}' cannot depend on itself."
            )
        cls._validate_availability(metadata.availability)
        if not isinstance(metadata.requires_ai, bool):
            raise InvalidCapabilityMetadataError(
                "Capability requires_ai must be a boolean."
            )

    @staticmethod
    def _validate_availability(availability: CapabilityAvailability) -> None:
        if not isinstance(availability, CapabilityAvailability):
            raise InvalidCapabilityMetadataError(
                "Availability must be CapabilityAvailability."
            )
        if not isinstance(availability.state, CapabilityAvailabilityState):
            raise InvalidCapabilityMetadataError(
                "Availability state is invalid."
            )
        reason_code = availability.reason_code
        if reason_code is not None and (
            not isinstance(reason_code, str) or not reason_code.strip()
        ):
            raise InvalidCapabilityMetadataError(
                "Availability reason codes must be non-empty strings."
            )
        if (
            availability.state is CapabilityAvailabilityState.AVAILABLE
            and reason_code is not None
        ):
            raise InvalidCapabilityMetadataError(
                "Available capabilities cannot include a reason code."
            )

    def _validate_dependency_graph(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(identifier: str) -> None:
            if identifier in visiting:
                raise CapabilityDependencyCycleError(
                    f"Capability dependency cycle includes '{identifier}'."
                )
            if identifier in visited:
                return

            visiting.add(identifier)
            metadata = self._declared_metadata[identifier]
            for dependency in metadata.dependencies:
                if dependency in self._declared_metadata:
                    visit(dependency)
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in sorted(self._declared_metadata):
            visit(identifier)

    def _build_effective_metadata(self) -> dict[str, CapabilityMetadata]:
        effective: dict[str, CapabilityMetadata] = {}

        def resolve(identifier: str) -> CapabilityMetadata:
            existing = effective.get(identifier)
            if existing is not None:
                return existing

            declared = self._declared_metadata[identifier]
            availability = declared.availability
            if availability.state is CapabilityAvailabilityState.AVAILABLE:
                for dependency in declared.dependencies:
                    dependency_metadata = self._declared_metadata.get(dependency)
                    if dependency_metadata is None:
                        availability = CapabilityAvailability(
                            state=CapabilityAvailabilityState.UNAVAILABLE,
                            reason_code=f"missing_dependency:{dependency}",
                        )
                        break
                    dependency_effective = resolve(dependency)
                    if (
                        dependency_effective.availability.state
                        is not CapabilityAvailabilityState.AVAILABLE
                    ):
                        availability = CapabilityAvailability(
                            state=CapabilityAvailabilityState.UNAVAILABLE,
                            reason_code=f"dependency_unavailable:{dependency}",
                        )
                        break

            resolved = replace(declared, availability=availability)
            effective[identifier] = resolved
            return resolved

        for identifier in sorted(self._declared_metadata):
            resolve(identifier)
        return effective

    @staticmethod
    def _availability_changes(
        previous: dict[str, CapabilityMetadata],
        current: dict[str, CapabilityMetadata],
        excluded_identifier: str | None = None,
    ) -> tuple[tuple[str, CapabilityAvailability, CapabilityAvailability], ...]:
        changes: list[
            tuple[str, CapabilityAvailability, CapabilityAvailability]
        ] = []
        for identifier in sorted(previous.keys() & current.keys()):
            if identifier == excluded_identifier:
                continue
            old_availability = previous[identifier].availability
            new_availability = current[identifier].availability
            if old_availability != new_availability:
                changes.append((identifier, old_availability, new_availability))
        return tuple(changes)

    def _publish_registered(self, metadata: CapabilityMetadata) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            CapabilityRegistered(
                source="capability_registry",
                capability_id=metadata.identifier,
                availability_state=metadata.availability.state,
            )
        )

    def _publish_availability_changes(
        self,
        changes: tuple[
            tuple[str, CapabilityAvailability, CapabilityAvailability], ...
        ],
    ) -> None:
        if self._event_bus is None:
            return
        for identifier, previous, current in changes:
            self._event_bus.publish(
                CapabilityAvailabilityChanged(
                    source="capability_registry",
                    capability_id=identifier,
                    previous_state=previous.state,
                    current_state=current.state,
                    reason_code=current.reason_code,
                )
            )
