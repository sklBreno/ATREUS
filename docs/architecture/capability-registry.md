# Capability Registry

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-17

---

# Purpose

The Capability Registry is the authoritative catalog of what ATREUS can do.

It stores immutable capability metadata and exposes read-only discovery to the
Core, Decision Engine input assembly, Planner, and Capability Runtime. It
describes capabilities; it never executes them.

---

# Responsibilities

The Capability Registry is responsible for:

- Registering validated capability metadata during bootstrap.
- Rejecting duplicate capability identifiers.
- Validating capability dependency references and cycles.
- Maintaining current capability availability metadata.
- Providing lookup by stable identifier.
- Providing deterministic, filtered capability listings.
- Becoming read-only after bootstrap registration is sealed.
- Publishing catalog and availability events.

---

# Non-Responsibilities

The Capability Registry is not responsible for:

- Loading capability implementation objects.
- Invoking capabilities.
- Planning capability sequences.
- Granting permissions.
- Calling AI providers.
- Accessing the operating system.
- Persisting execution results.
- Discovering plugins from the filesystem or network.

---

# Capability Metadata

`CapabilityMetadata` is immutable and contains only:

- `identifier`: Stable unique technical identifier.
- `name`: Human-readable capability name.
- `description`: Concise description of the capability's effect.
- `permissions`: Immutable collection of required permission identifiers.
- `availability`: Current `CapabilityAvailability` value.
- `dependencies`: Immutable collection of required capability identifiers.
- `requires_ai`: Whether successful execution requires an available AI
  Provider.

The metadata does not contain implementation objects, callbacks, secrets,
provider clients, or mutable runtime state.

`identifier` is the public identity used by plans and invocations. It must
remain stable across compatible implementation changes.

---

# Availability Model

`CapabilityAvailability` contains:

- `state`: `AVAILABLE`, `DISABLED`, or `UNAVAILABLE`.
- `reason_code`: Optional stable reason when state is not `AVAILABLE`.

Meanings:

- `AVAILABLE`: Loaded and eligible for policy evaluation.
- `DISABLED`: Explicitly disabled by user or platform configuration.
- `UNAVAILABLE`: Cannot currently run because an implementation, dependency,
  permission prerequisite, platform feature, or required AI Provider is
  unavailable.

Availability does not authorize execution. The Decision Engine and Capability
Runtime still enforce user policy and permissions.

---

# Permission Identifiers

Permissions are stable opaque identifiers defined by the controlled boundary
that enforces them, normally the System Layer.

Examples of permission families include filesystem read, filesystem write,
process observation, application control, and power management. The Registry
stores identifiers but does not interpret or grant them.

An empty permission collection means the capability requires no privileged
platform operation. It does not bypass general user-control policy.

Natural Language Actions V1 registers two separate application capabilities:

- `application.open` requires `application.control`.
- `application.status` requires `application.read`.

The Registry stores these stable identifiers and metadata only. It does not
contain the intent-target action matrix, executable names, native process
names, paths, PIDs, or Windows-specific mappings.

---

# Dependency Rules

Capability dependencies express that one capability requires another
capability to be present and available.

Version 1 rules:

- A capability cannot depend on itself.
- Dependency identifiers must be unique within one metadata object.
- Dependency cycles are invalid.
- Missing dependencies make the dependent capability `UNAVAILABLE`.
- Disabled or unavailable dependencies make the dependent capability
  `UNAVAILABLE`.
- Dependencies do not imply automatic execution order.

The Planner explicitly includes required execution steps when dependencies must
be invoked. The Registry only reports dependency relationships.

---

# Public Interfaces

Consumers use a read-only catalog:

```python
class CapabilityCatalog(ABC):
    def get(self, identifier: str) -> CapabilityMetadata | None: ...

    def list_all(self) -> tuple[CapabilityMetadata, ...]: ...

    def list_available(self) -> tuple[CapabilityMetadata, ...]: ...
```

Bootstrap and Capability Runtime use a registration lifecycle contract:

```python
class CapabilityRegistry(CapabilityCatalog, ABC):
    def register(self, metadata: CapabilityMetadata) -> None: ...

    def update_availability(
        self,
        identifier: str,
        availability: CapabilityAvailability,
    ) -> None: ...

    def seal(self) -> None: ...
```

After `seal`, Version 1 rejects new registrations. Availability updates remain
allowed because local prerequisites can change during an Always-On session.

Listings are ordered by capability identifier to guarantee deterministic
behavior.

---

# Internal Flow

```text
Capability Runtime during Bootstrap
    │
    ▼
Metadata Validation
    │
    ▼
Identifier Registration
    │
    ▼
Dependency Validation
    │
    ▼
Registry Seal
    │
    ▼
Read-Only Capability Catalog
```

Availability updates validate downstream dependencies before publishing
events.

---

# Dependencies

The Capability Registry depends on:

- Immutable capability metadata contracts.
- Optionally, the `EventBus` abstraction for domain event publication.

It does not depend on Core, Planner, Capability Runtime implementations, System
Layer, Memory, or AI Provider.

Capability Runtime depends on the Registry contract; the Registry never calls
the Runtime.

---

# Events

The Capability Registry owns:

## `CapabilityRegistered`

- Common event metadata.
- `capability_id`.
- Initial availability state.

## `CapabilityAvailabilityChanged`

- Common event metadata.
- `capability_id`.
- Previous availability state.
- Current availability state.
- Current reason code when present.

Events must not contain implementation references or permission grants.

---

# Error Handling

The module defines a `CapabilityRegistryException` base error with explicit
errors for invalid metadata, duplicate identifiers, unknown identifiers,
registration after sealing, and dependency cycles.

`get` returns `None` for an unknown valid identifier. Mutation operations on an
unknown identifier raise an explicit error.

Catalog integrity errors during bootstrap prevent the catalog from being
sealed.

---

# Testing Requirements

Tests must cover:

- Valid registration and lookup.
- Duplicate identifiers.
- Metadata immutability.
- Deterministic listing order.
- Available-only filtering.
- Disabled and unavailable capabilities.
- Missing dependencies.
- Self-dependencies and dependency cycles.
- Availability propagation to dependents.
- Registration sealing.
- Event publication.
- Concurrent read behavior after sealing.
- Absence of execution behavior.

---

# Performance Considerations

Lookup by identifier should be constant time. Listings may use immutable
snapshots and must remain bounded by the number of registered local
capabilities.

The Registry performs no polling and no capability health checks. Availability
changes are supplied explicitly by lifecycle owners.

---

# Security and Privacy Considerations

Capability metadata is descriptive but may reveal privileged platform actions.
Only trusted local capability implementations may register metadata in Version
1.

Permission requirements must be complete and must never be reduced during an
availability update. Metadata and events must not include credentials, user
content, implementation paths, or executable objects.

---

# Future Evolution

Future versions may add versioned metadata, input schemas, signed plugins,
dynamic discovery, or remote catalogs after explicit architecture and trust
models are approved.

Version 1 remains a local in-process catalog populated during controlled
bootstrap.

---

# Architectural Considerations

The Capability Registry is the single source of truth for capability identity
and metadata. The Planner consumes descriptions, the Decision Engine receives
candidate metadata, and the Capability Runtime owns execution.

No second catalog or execution manager should duplicate these responsibilities.
