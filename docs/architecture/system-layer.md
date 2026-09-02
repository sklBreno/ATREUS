# System Layer

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-31

---

# Purpose

The System Layer is the controlled boundary between ATREUS and operating-system
functionality.

It translates platform-neutral contracts into operating-system operations and
normalizes results and failures. All modules and capabilities that require
system access depend on System Layer abstractions rather than calling native
APIs directly.

---

# Responsibilities

The System Layer is responsible for:

- Providing bounded process operations.
- Providing controlled filesystem operations.
- Providing system resource information.
- Providing application observation and control.
- Providing current power-state information.
- Enforcing operation-level permissions at the system boundary.
- Normalizing platform-specific data and errors.
- Publishing approved system-state events.

---

# Non-Responsibilities

The System Layer is not responsible for:

- Deciding why an operation should occur.
- Implementing user workflows or business logic.
- Classifying requests.
- Detecting the current user context.
- Planning capability sequences.
- Selecting or applying operational-state transitions or performance-profile
  changes.
- Granting permissions.
- Persisting user data unrelated to an explicit operation.
- Monitoring data sources that are not exposed by an approved contract.
- Providing unrestricted access to arbitrary native APIs.

---

# Architecture

The System Layer is a collection of cohesive interfaces, not one unrestricted
system object.

```text
Context Engine / Capability Implementations
    │
    ├── ProcessService
    ├── FileSystemService
    ├── SystemInformationProvider
    ├── ApplicationLauncher
    ├── ApplicationStateReader
    └── PowerStateProvider
             │
             ▼
    Operating-System Adapters
             │
             ▼
       Native OS APIs
```

Version 1 uses local in-process adapters. Platform-specific details remain below
the interfaces.

---

# Operation Context

Every operation that can observe private data or create a side effect accepts
an immutable `SystemOperationContext` containing:

- `operation_id`: Unique operation identifier.
- `request_id`: Optional correlated platform request identifier.
- `capability_id`: Identifier of the requesting capability when applicable.
- `permission_grants`: Immutable grants approved for the operation.
- `cancellation`: Cooperative cancellation signal.

The System Layer validates grants but does not create them.

---

# Public Interfaces

System Layer consumers depend on the narrow interface required for one domain.
No consumer receives an unrestricted aggregate system object.

## Process Service

`ProcessService` provides:

```python
class ProcessService(ABC):
    def list_processes(
        self,
        limit: int,
        context: SystemOperationContext,
    ) -> tuple[ProcessInfo, ...]: ...

    def start_process(
        self,
        request: ProcessStartRequest,
        context: SystemOperationContext,
    ) -> ProcessInfo: ...

    def terminate_process(
        self,
        process_id: int,
        context: SystemOperationContext,
    ) -> None: ...
```

`ProcessInfo` contains normalized process identifier, display name, executable
identity when disclosure is permitted, and running state. Command-line contents
are excluded by default.

Process start and termination require separate explicit permissions.

---

## File System Service

`FileSystemService` provides bounded operations:

```python
class FileSystemService(ABC):
    def stat(
        self,
        path: SystemPath,
        context: SystemOperationContext,
    ) -> FileMetadata: ...

    def list_directory(
        self,
        path: SystemPath,
        limit: int,
        context: SystemOperationContext,
    ) -> tuple[FileMetadata, ...]: ...

    def read_file(
        self,
        path: SystemPath,
        maximum_bytes: int,
        context: SystemOperationContext,
    ) -> bytes: ...

    def write_file(
        self,
        request: FileWriteRequest,
        context: SystemOperationContext,
    ) -> FileMetadata: ...
```

Paths are normalized platform-neutral values. Directory listing and file reads
require explicit positive bounds. Read and write permissions are separate.

Version 1 does not expose recursive deletion through the general contract.

---

## System Information Provider

`SystemInformationProvider` exposes:

```python
class SystemInformationProvider(ABC):
    def snapshot(
        self,
        context: SystemOperationContext,
    ) -> SystemSnapshot: ...
```

`SystemSnapshot` is immutable and contains only approved current metrics:

- CPU utilization.
- GPU utilization when available.
- Available and total memory.
- Battery level when available.
- Power source.
- Observation timestamp.
- Metric availability status.

It does not contain user content, application history, or hardware identifiers
that are unnecessary for adaptive performance.

---

## Application Boundaries

Natural Language Actions V1 uses two narrow interfaces:

```python
class ApplicationLauncher(ABC):
    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance: ...


class ApplicationStateReader(ABC):
    def read_status(
        self,
        request: ApplicationStatusRequest,
        context: SystemOperationContext,
    ) -> ApplicationStatusResult: ...
```

Both requests contain only an approved platform-neutral
`ApplicationIdentifier`. Neither interface accepts executable paths, process
names, PIDs, command lines, shell syntax, or arbitrary user input.

The Windows launcher uses fixed internal mappings for Calculator and Notepad
and invokes `subprocess.Popen` with `shell=False`. The Windows state reader uses
one fixed `tasklist.exe` command with `shell=False`, then compares the complete
observation only against internal approved process identities. Incomplete
evidence returns `UNKNOWN` rather than a false `NOT_RUNNING` result.

Spotify has no approved launch or status mapping in V1. Unsupported approved
identifiers fail through `UnsupportedSystemOperationError` before native work.
Close, focus, minimize, maximize, PID lookup, arbitrary process inspection, and
generic process execution are not exposed by these application interfaces.

Application observation requires `application.read`; launch requires
`application.control`. Capability Runtime checks grants first and the System
Layer enforces them again at this boundary.

---

## Power State Provider

`PowerStateProvider` exposes:

```python
class PowerStateProvider(ABC):
    def current_power_state(
        self,
        context: SystemOperationContext,
    ) -> PowerState: ...
```

`PowerState` contains normalized battery availability, battery level, charging
state, and power source.

Version 1 exposes power observation only. Sleep, shutdown, restart, and power
policy modification require separate future contracts and explicit user-control
architecture.

---

# Permission Identifiers

Version 1 defines separate permission identifiers for:

- `process.read`
- `process.start`
- `process.terminate`
- `filesystem.metadata.read`
- `filesystem.content.read`
- `filesystem.write`
- `application.read`
- `application.control`
- `system.metrics.read`
- `power.read`

Permissions follow least privilege. A broad permission must not be inferred from
a narrower grant.

---

# Internal Flow

```text
Platform-Neutral Request
    │
    ▼
Contract Validation
    │
    ▼
Permission Enforcement
    │
    ▼
Path / Identifier Normalization
    │
    ▼
Native OS Adapter
    │
    ▼
Normalized Result or Error
```

No native handle, exception, path object, or SDK type crosses the public
interface.

---

# Dependencies

System Layer interfaces depend on immutable platform-neutral system contracts
and, optionally, the `EventBus` abstraction for approved system-state events.

Concrete adapters depend on operating-system APIs and the standard logging
infrastructure. They do not depend on Core, Context Engine, Decision Engine,
Planner, Memory, Capability Registry, Capability Runtime, or AI Provider.

Context Engine and capability implementations depend on the narrow System Layer
interfaces they require.

---

# Events

System Layer owns events that originate from operating-system observations:

## `SystemResourcePressureChanged`

- Common event metadata.
- Previous pressure state.
- Current pressure state.
- Metric availability status.

## `PowerStateChanged`

- Common event metadata.
- Previous normalized power state.
- Current normalized power state.

## `ActiveApplicationChanged`

- Common event metadata.
- Previous application identifier when disclosure is permitted.
- Current application identifier when disclosure is permitted.

Routine file reads, writes, process listings, and direct application operations
do not automatically publish content-bearing events.

---

# Error Handling

The System Layer defines a `SystemLayerException` base error with normalized
errors for invalid operations, permission denial, resource not found, conflict,
unsupported platform operation, timeout, cancellation, and native adapter
failure.

Native error codes and exceptions remain internal. Public errors retain a
sanitized reason and safe resource identifier when appropriate.

Adapters must not silently retry destructive or side-effecting operations.

---

# Testing Requirements

Each adapter has contract tests covering:

- Successful normalized results.
- Input and bound validation.
- Permission enforcement.
- Resource-not-found behavior.
- Native error normalization.
- Cancellation and timeout where applicable.
- Platform feature unavailability.
- Result and event immutability.
- Sensitive data exclusion.
- Absence of business decisions.
- Fixed Calculator and Notepad launch and status identities.
- `UNKNOWN` when application-state evidence is incomplete.
- Spotify rejection without native invocation.
- `shell=False` and absence of user-derived native commands or process names.

Unit tests use fake native adapters and do not modify the developer's real
system. Operating-system integration tests run only in an isolated, explicitly
approved environment.

---

# Performance Considerations

System observation supports Always-On operation and must remain lightweight.
Adapters should prefer native notifications over aggressive polling.

Listings and reads are bounded. Resource snapshots contain current values and
do not accumulate history. Operational state and performance profile are
independent controls. When the `PERFORMANCE` performance profile is active or
the operational state is `STANDBY`, Core may reduce observation frequency
through explicit lifecycle controls. System Layer respects those controls and
continues to provide signals; it does not select or apply either value.

---

# Security and Privacy Considerations

The System Layer is a privileged boundary and follows least privilege, explicit
grants, data minimization, and defense in depth.

Paths must be normalized before authorization. Symlink, junction, and path
escape behavior must be tested. Arbitrary shell interpolation is prohibited.
Application and process data must exclude command lines and window contents by
default.

The user remains in control of enabled observations and side-effecting
capabilities. Sensitive operation inputs and results must not be logged.

---

# Future Evolution

Future versions may add network information, device access, power actions,
additional operating systems, or remote system adapters after explicit
contracts and permission models are approved.

Version 1 must not become cloud infrastructure, a remote administration layer,
or an unrestricted native API facade.

---

# Architectural Considerations

System Layer owns operating-system translation and enforcement, while
capabilities own user-facing behavior. Keeping interfaces narrow prevents
infrastructure from accumulating unrelated business logic.

All direct operating-system access should converge on this boundary so privacy,
permissions, testing, and platform replacement remain consistent.
