"""Behavior tests for the in-memory Capability Registry."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from atreus.capability.exceptions import (
    CapabilityDependencyCycleError,
    DuplicateCapabilityError,
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
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.events.event_bus import InProcessEventBus

AVAILABLE = CapabilityAvailability(CapabilityAvailabilityState.AVAILABLE)
DISABLED = CapabilityAvailability(
    CapabilityAvailabilityState.DISABLED,
    "disabled_by_configuration",
)


def make_metadata(
    identifier: str,
    *,
    availability: CapabilityAvailability = AVAILABLE,
    permissions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    requires_ai: bool = False,
) -> CapabilityMetadata:
    """Create capability metadata for Registry tests."""
    return CapabilityMetadata(
        identifier=identifier,
        name=identifier.replace(".", " ").title(),
        description=f"Provide {identifier} behavior.",
        permissions=permissions,
        availability=availability,
        dependencies=dependencies,
        requires_ai=requires_ai,
    )


def test_register_get_and_list_metadata_deterministically() -> None:
    registry = InMemoryCapabilityRegistry()
    second = make_metadata("system.status")
    first = make_metadata("application.open")

    registry.register(second)
    registry.register(first)

    assert registry.get(first.identifier) == first
    assert registry.get("missing.capability") is None
    assert registry.list_all() == (first, second)
    assert registry.list_available() == (first, second)


def test_registry_preserves_permissions_dependencies_and_ai_metadata() -> None:
    registry = InMemoryCapabilityRegistry()
    dependency = make_metadata("system.status")
    metadata = make_metadata(
        "application.open",
        permissions=("application.control",),
        dependencies=(dependency.identifier,),
        requires_ai=True,
    )

    registry.register(dependency)
    registry.register(metadata)

    registered = registry.get(metadata.identifier)
    assert registered is not None
    assert registered.permissions == ("application.control",)
    assert registered.dependencies == ("system.status",)
    assert registered.requires_ai is True
    assert not hasattr(registered, "execute")
    assert not hasattr(registered, "callable")


def test_metadata_is_immutable_and_uses_immutable_collections() -> None:
    metadata = make_metadata("application.open")

    with pytest.raises(FrozenInstanceError):
        metadata.name = "Changed"  # type: ignore[misc]

    assert isinstance(metadata.permissions, tuple)
    assert isinstance(metadata.dependencies, tuple)


def test_duplicate_registration_raises_explicit_error() -> None:
    registry = InMemoryCapabilityRegistry()
    metadata = make_metadata("application.open")
    registry.register(metadata)

    with pytest.raises(DuplicateCapabilityError):
        registry.register(metadata)


def test_invalid_metadata_raises_domain_error() -> None:
    registry = InMemoryCapabilityRegistry()
    metadata = make_metadata("application.open")
    invalid = CapabilityMetadata(
        identifier=metadata.identifier,
        name=1,  # type: ignore[arg-type]
        description=metadata.description,
        permissions=metadata.permissions,
        availability=metadata.availability,
        dependencies=metadata.dependencies,
        requires_ai=metadata.requires_ai,
    )

    with pytest.raises(InvalidCapabilityMetadataError):
        registry.register(invalid)


def test_disabled_capability_is_excluded_from_available_listing() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("application.open", availability=DISABLED))

    assert len(registry.list_all()) == 1
    assert registry.list_available() == ()


def test_missing_dependency_makes_capability_effectively_unavailable() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(
        make_metadata("application.open", dependencies=("system.status",))
    )

    metadata = registry.get("application.open")
    assert metadata is not None
    assert metadata.availability.state is CapabilityAvailabilityState.UNAVAILABLE
    assert metadata.availability.reason_code == "missing_dependency:system.status"


def test_registering_missing_dependency_restores_dependent_availability() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(
        make_metadata("application.open", dependencies=("system.status",))
    )

    registry.register(make_metadata("system.status"))

    metadata = registry.get("application.open")
    assert metadata is not None
    assert metadata.availability == AVAILABLE


def test_availability_updates_propagate_to_dependents_after_sealing() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.status"))
    registry.register(
        make_metadata("application.open", dependencies=("system.status",))
    )
    registry.seal()

    registry.update_availability("system.status", DISABLED)

    dependent = registry.get("application.open")
    assert dependent is not None
    assert dependent.availability.state is CapabilityAvailabilityState.UNAVAILABLE
    assert (
        dependent.availability.reason_code
        == "dependency_unavailable:system.status"
    )


def test_unknown_availability_update_raises_explicit_error() -> None:
    registry = InMemoryCapabilityRegistry()

    with pytest.raises(UnknownCapabilityError):
        registry.update_availability("missing.capability", DISABLED)


def test_self_dependency_and_dependency_cycles_are_rejected() -> None:
    registry = InMemoryCapabilityRegistry()
    with pytest.raises(CapabilityDependencyCycleError):
        registry.register(
            make_metadata("application.open", dependencies=("application.open",))
        )

    registry.register(make_metadata("capability.a", dependencies=("capability.b",)))
    with pytest.raises(CapabilityDependencyCycleError):
        registry.register(
            make_metadata("capability.b", dependencies=("capability.a",))
        )
    assert registry.get("capability.b") is None


def test_seal_rejects_registration_but_remains_idempotent() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.seal()
    registry.seal()

    with pytest.raises(RegistrySealedError):
        registry.register(make_metadata("application.open"))


def test_registry_publishes_registration_and_availability_events() -> None:
    event_bus = InProcessEventBus()
    registered: list[CapabilityRegistered] = []
    changed: list[CapabilityAvailabilityChanged] = []
    event_bus.subscribe(CapabilityRegistered, registered.append)
    event_bus.subscribe(CapabilityAvailabilityChanged, changed.append)
    registry = InMemoryCapabilityRegistry(event_bus)

    registry.register(make_metadata("application.open"))
    registry.update_availability("application.open", DISABLED)

    assert len(registered) == 1
    assert registered[0].capability_id == "application.open"
    assert registered[0].availability_state is CapabilityAvailabilityState.AVAILABLE
    assert len(changed) == 1
    assert changed[0].previous_state is CapabilityAvailabilityState.AVAILABLE
    assert changed[0].current_state is CapabilityAvailabilityState.DISABLED
    assert changed[0].reason_code == "disabled_by_configuration"


def test_sealed_registry_supports_concurrent_read_snapshots() -> None:
    registry = InMemoryCapabilityRegistry()
    expected = tuple(
        make_metadata(identifier)
        for identifier in ("application.open", "system.status")
    )
    for metadata in reversed(expected):
        registry.register(metadata)
    registry.seal()

    with ThreadPoolExecutor(max_workers=4) as executor:
        snapshots = tuple(executor.map(lambda _: registry.list_all(), range(20)))

    assert all(snapshot == expected for snapshot in snapshots)
