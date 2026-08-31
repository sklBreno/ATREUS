# Configuration Manager

**Layer:** Infrastructure

**Status:** Approved

**Version:** 1.2

**Owner:** ATREUS Core Team

**Last Updated:** 2026-08-31

---

# Purpose

The Configuration Manager is responsible for providing a single, reliable source of configuration for the entire ATREUS platform.

Its primary purpose is to centralize configuration loading, validation, and access while keeping the rest of the system independent from configuration storage mechanisms.

The Configuration Manager is one of the first components initialized during the bootstrap process and is expected to be used by nearly every module in the platform.

The public Configuration object contains validated non-secret settings only.
Secrets use a separate bootstrap boundary and are injected directly into the
concrete component that requires them.

---

# Responsibilities

The Configuration Manager is responsible for:

- Loading configuration during platform bootstrap.
- Providing centralized access to configuration values.
- Applying default values when no user configuration exists.
- Loading configuration from supported sources.
- Validating configuration before exposing it to the platform.
- Maintaining configuration consistency throughout application execution.
- Supporting multiple configuration sources.
- Providing validated user permission grants.
- Providing validated policy objects for bounded runtime behavior.
- Allowing future expansion without affecting dependent modules.

---

# Non-Responsibilities

The Configuration Manager is **not** responsible for:

- Business logic.
- User memory.
- Decision making.
- Context detection.
- Capability execution.
- AI integration.
- Operating system interaction.
- Persisting user data.
- Storing, persisting, logging, or publicly exposing secrets.

Its sole responsibility is managing application configuration.

---

# Architecture

The Configuration Manager acts as the centralized configuration service shared across the entire platform.

```text
             Non-Secret Configuration Sources
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     Defaults         Environment      Future User Sources
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
               Configuration Manager
                          │
                    Configuration
                          │
     ┌──────────┬──────────┼──────────┬──────────┐
     │          │          │          │          │
    Core     Planner    Memory    Logger   Capability Runtime

Approved External Secret Source
                          │
                          ▼
                 Bootstrap Composition
                          │ dependency injection
                          ▼
              Concrete Provider or Adapter
```

No module should access configuration files directly.

All configuration requests must go through the Configuration Manager.

Secrets are not configuration requests. Bootstrap obtains them from approved
external sources and injects them directly into the selected concrete adapter.

---

# Internal Architecture

Version 1 is expected to follow the architecture below.

```text
                 Bootstrap
                     │
                     ▼
          ConfigurationLoader
                     │
                     ▼
       ConfigurationValidator
                     │
                     ▼
         ConfigurationManager
                     │
                     ▼
             Configuration
                     │
     ┌─────────┬─────────┬─────────┬─────────┐
     ▼         ▼         ▼         ▼
    Core    Planner   Memory   Logger
```

Each component has a single responsibility.

---

# Initialization Flow

During platform bootstrap, the following sequence occurs:

1. Bootstrap starts.
2. Configuration Loader loads default values.
3. Non-secret environment values are loaded.
4. Configuration Validator validates all non-secret values.
5. Configuration Manager creates a public Configuration object.
6. Bootstrap obtains required secrets from approved external sources without
   adding them to Configuration.
7. Bootstrap injects each secret directly into the concrete adapter that
   requires it.
8. The Configuration object becomes available.
9. Remaining platform components continue initialization.

---

# Configuration Sources

Version 1 supports:

- Built-in default values.
- Environment variables, optionally supplied through an approved local `.env`
  source.

Environment variables may also carry secrets, but secret values follow the
separate secret boundary and are never copied into the public Configuration
object.

Future versions may additionally support:

- JSON configuration files.
- YAML configuration files.
- User profiles.
- Database-backed configuration.
- Cloud synchronization.
- Graphical settings interface.

---

# Configuration Priority

When multiple non-secret sources define the same configuration value, the following priority applies:

1. User-defined configuration.
2. Environment variables (`.env`).
3. Default platform values.

This guarantees deterministic behavior across the platform.

Secret-source precedence is not part of the public Configuration contract and
must be defined by the concrete bootstrap integration that owns the secret.

---

# Configuration Object

The Configuration Manager provides a single immutable Configuration object.

The Configuration object contains only validated, non-secret configuration
values.

It does not contain loading logic, validation logic, or persistence logic.

Its sole responsibility is representing the current platform configuration.

Every module should consume this object rather than interacting directly with configuration sources.

Public snapshots, representations, diagnostics, events, and logs must never
contain secrets.

---

# Public Interface

Other modules must never read configuration files directly.

Instead, configuration is accessed through the Configuration Manager.

Conceptual examples:

```python
configuration.language
configuration.debug
configuration.log_level
configuration.start_with_windows
configuration.always_on
configuration.permission_grants
configuration.context_stabilization_policy
configuration.working_memory_policy
configuration.planning_policy
configuration.execution_policy
```

The public interface should remain stable regardless of how configuration is stored internally.

---

# Permission Grants

Version 1 permission grants are user-defined non-secret configuration.

The Configuration object exposes grants as an immutable collection of stable
permission identifiers. Validation rejects malformed or duplicate identifiers
and does not infer a broader grant from a narrower one.

Capability Registry declares permissions required by each capability.
Capability Runtime verifies configured grants before execution, and System
Layer enforces them again at the operating-system boundary.

Configuration Manager does not grant permissions interactively. Version 1 has
no interactive permission-grant system.

---

# Configurable Numeric Policies

The Configuration object supplies validated immutable policy objects for:

- Context transition stabilization.
- Working Memory capacity and expiration behavior.
- Planning bounds.
- Capability execution timeout defaults.

This architecture intentionally defines no concrete numeric values. Defaults
must be owned by future implementation configuration, validated before use, and
injected into the responsible module. Modules must not hardcode values that
belong to these policies.

---

# Secrets

Secrets include AI Provider credentials, API keys, tokens, and equivalent
authentication material.

Version 1 rules are:

- Secrets come only from approved external sources such as environment-backed
  bootstrap configuration.
- Bootstrap injects each secret directly into the selected concrete provider or
  adapter.
- Secrets never appear in the public Configuration object or its snapshots.
- Configuration Manager and AI Provider never persist secrets.
- Secrets never appear in logs, events, errors, requests, responses, or
  diagnostics.
- Secrets are never hardcoded.

The public Configuration object may contain a non-secret provider selector or
feature toggle, but never provider credentials.

---

# Mutability

Configuration values are immutable during normal platform execution.

Runtime configuration changes are not supported in Version 1.

Future versions may introduce controlled runtime updates through dedicated APIs.

---

# Planned Implementation

Version 1 is expected to be implemented using the following components:

- Configuration
- ConfigurationManager
- ConfigurationLoader
- ConfigurationValidator
- ConfigurationException

Each component should have one clearly defined responsibility.

---

# Thread Safety

Version 1 assumes a single-process application.

The Configuration Manager must support concurrent read operations.

Runtime write operations are not supported.

---

# Design Principles

The Configuration Manager follows these architectural principles:

- Single Source of Truth
- Single Responsibility Principle
- Separation of Concerns
- Low Coupling
- High Cohesion
- Simplicity
- Predictability
- Extensibility

---

# Dependencies

The Configuration Manager has no dependencies on other ATREUS modules.

It is initialized before nearly every other platform component.

This guarantees that configuration is always available when required.

---

# Testing Requirements

The module must be tested to ensure:

- Correct loading of default values.
- Correct loading of environment variables.
- Proper validation of invalid values.
- Correct priority resolution between configuration sources.
- Correct loading and validation of permission grants.
- Correct validation and exposure of numeric policy objects without hardcoded
  architecture values.
- Exclusion of secrets from Configuration objects, snapshots, representations,
  events, errors, and logs.
- Consistent configuration availability across the platform.
- Stable behavior during long-running execution.
- Immutable Configuration objects after initialization.

---

# Future Evolution

The Configuration Manager is designed to evolve without changing its public interface.

Future capabilities may include:

- Dynamic configuration reload.
- Multiple configuration profiles.
- User-specific settings.
- Integration with approved external secret providers.
- Runtime configuration updates.
- Cloud synchronization.

Future enhancements should not require changes to dependent modules.

---

# Architectural Considerations

The Configuration Manager is considered an infrastructure component.

Its purpose is to provide configuration information while remaining completely independent from business logic.

Configuration loading, validation, and representation are intentionally separated into independent components to maximize maintainability, scalability, and testability.

Future configuration sources should be introduced without requiring modifications to dependent modules.

The Configuration Manager is expected to remain one of the most stable components in the entire ATREUS architecture.
