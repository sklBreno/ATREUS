# Capability Runtime

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-31

---

# Purpose

The Capability Runtime is the single platform component responsible for loading
and invoking capability implementations.

It provides a controlled execution boundary between plans or direct decisions
and capability code. The Core owns execution flow; the Runtime owns one
capability invocation lifecycle at a time.

---

# Responsibilities

The Capability Runtime is responsible for:

- Loading explicitly supplied local capability implementations during
  bootstrap.
- Registering implementation metadata with the Capability Registry.
- Resolving an implementation by capability identifier.
- Validating invocation structure.
- Checking current availability, dependencies, permissions, and AI
  prerequisites.
- Invoking capabilities through a stable contract.
- Enforcing an execution deadline when one is required.
- Isolating capability failures from the platform process.
- Returning immutable execution results.
- Publishing execution lifecycle events.

---

# Non-Responsibilities

The Capability Runtime is not responsible for:

- Deciding which capability should run.
- Creating or modifying plans.
- Cataloging metadata independently from Capability Registry.
- Granting user permissions.
- Selecting or applying operational-state transitions or performance-profile
  changes.
- Interpreting user requests.
- Persisting execution history.
- Implementing capability business logic.
- Discovering code from arbitrary filesystem or network locations.
- Automatically invoking dependency capabilities.

---

# Capability Contract

A Version 1 capability implementation exposes:

```python
class Capability(ABC):
    @property
    def metadata(self) -> CapabilityMetadata: ...

    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput: ...
```

Implementations own their domain behavior and validate their domain-specific
arguments. Dependencies such as System Layer or AI Provider abstractions are
injected when the capability is constructed during bootstrap.

A capability must not locate global services or read configuration sources
directly.

---

# Capability Loading

Version 1 loading is explicit and local:

1. Bootstrap constructs trusted capability implementations.
2. Bootstrap passes the immutable collection to Capability Runtime.
3. Runtime validates identifiers and implementation contracts.
4. Runtime registers each implementation's metadata with Capability Registry.
5. Runtime records the identifier-to-implementation mapping.
6. Registry dependency validation completes.
7. Registry is sealed after all required capabilities are loaded.

Version 1 does not scan plugin directories, import arbitrary module paths, or
download capability code.

One capability identifier maps to exactly one loaded implementation.

---

# Invocation Contract

`CapabilityInvocation` is immutable and contains:

- `invocation_id`: Unique execution identifier.
- `request_id`: Correlated request identifier.
- `plan_id`: Optional plan identifier.
- `step_id`: Optional plan step identifier.
- `capability_id`: Registry identifier to invoke.
- `arguments`: Immutable capability argument values.
- `timeout_seconds`: Optional positive execution deadline.
- `permission_grants`: Immutable grants approved for this invocation.
- `context`: The immutable snapshot captured once by Core for the request.

`ExecutionContext` contains only runtime information required by the capability,
including correlation identifiers, current context snapshot, cancellation
signal, and approved grants.

Capability Runtime copies the snapshot reference from `CapabilityInvocation`
into `ExecutionContext`. It does not depend on `ContextProvider`, capture a new
snapshot, merge context, or perform inference. This preserves one coherent
context view throughout a request.

Capabilities receive no direct reference to Core or Capability Registry.

---

# Execution Result

`CapabilityExecutionResult` is immutable and contains:

- `invocation_id`.
- `capability_id`.
- `status`: `SUCCEEDED`, `FAILED`, `TIMED_OUT`, or `CANCELLED`.
- `output`: Optional immutable capability output for successful execution.
- `error_code`: Optional stable sanitized code for unsuccessful execution.
- `started_at`.
- `completed_at`.

Raw exception objects and tracebacks do not cross the Runtime public boundary.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class CapabilityRuntime(ABC):
    def load(self, capabilities: tuple[Capability, ...]) -> None: ...

    def invoke(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityExecutionResult: ...
```

From the caller's perspective, `invoke` is synchronous and returns one terminal
result. Internal timeout enforcement must not change this contract.

---

# Internal Flow

```text
CapabilityInvocation
    │
    ▼
Invocation Validation
    │
    ▼
Registry and Implementation Resolution
    │
    ▼
Availability, Dependency, AI, and Permission Checks
    │
    ▼
CapabilityExecutionStarted
    │
    ▼
Bounded Capability Invocation
    │
    ├── success ─────> SUCCEEDED
    ├── exception ───> FAILED
    ├── deadline ────> TIMED_OUT
    └── cancellation > CANCELLED
    │
    ▼
Terminal Event + Immutable Result
```

Exactly one terminal result and one matching terminal event are produced for an
invocation that reaches the execution phase.

---

# Permissions and Preconditions

Before execution, Runtime verifies that:

- Capability metadata exists.
- A matching implementation is loaded.
- Capability availability is `AVAILABLE`.
- Metadata dependencies are currently available.
- Every required permission appears in the invocation grants.
- The injected AI Provider availability is `AVAILABLE` when capability metadata
  sets `requires_ai`.

Runtime checks grants but does not create them. System Layer adapters enforce
permissions again at the operating-system boundary.

---

# Timeouts and Cancellation

An explicit positive timeout is required for operations that may block on an
external service, long-running process, or unbounded operating-system response.

When a deadline expires:

- Runtime signals cooperative cancellation.
- The caller receives `TIMED_OUT`.
- Late output is discarded.
- The platform continues serving other requests.

Capabilities must observe the cancellation signal at safe boundaries. Version
1 does not forcibly terminate the ATREUS process to stop one capability.

---

# Interaction With Plans

The Core iterates an approved plan and creates one invocation per eligible
step. Runtime does not accept a complete plan and does not choose the next step.

After each result, the Core determines whether to continue, stop, ask for user
input, or report failure according to the plan and decision policy.

---

# Dependencies

The Capability Runtime depends on:

- The `CapabilityRegistry` and read-only `CapabilityCatalog` abstractions.
- The `AIProvider` availability contract for AI-required preconditions.
- Capability, invocation, execution-context, and result contracts.
- A bounded execution and clock abstraction for timeout handling.
- Optionally, the `EventBus` abstraction for lifecycle events.

Capability implementations may depend on System Layer or the full AI Provider
abstraction through constructor injection. Runtime uses AI availability only and
does not perform operating-system or AI work.

Runtime does not depend on Core, Planner, Decision Engine, or Memory.
It also does not depend on Context Engine or `ContextProvider`; context arrives
as immutable invocation data.

---

# Events

Capability Runtime owns:

## `CapabilityExecutionStarted`

- Common event metadata.
- `invocation_id`.
- `request_id`.
- `capability_id`.
- Optional `plan_id` and `step_id`.

## `CapabilityExecutionCompleted`

- Common event metadata.
- Correlation identifiers.
- `capability_id`.
- Duration metadata.

## `CapabilityExecutionFailed`

- Common event metadata.
- Correlation identifiers.
- `capability_id`.
- Terminal status.
- Sanitized `error_code`.

Events must not contain arguments, outputs, permission grants, secrets, or raw
exceptions.

---

# Error Handling

The module defines a `CapabilityRuntimeException` base error with explicit
errors for invalid loading, duplicate implementations, invalid invocation,
unknown capability, unavailable capability, and missing permissions.

Errors detected before execution raise explicit exceptions because no execution
lifecycle started. Exceptions raised by capability code after execution starts
are isolated and converted into a `FAILED` result.

One capability failure must not stop the Runtime or Event Bus.

---

# Testing Requirements

Tests must cover:

- Loading valid implementations.
- Duplicate and mismatched identifiers.
- Registry registration and sealing interaction.
- Successful invocation.
- Invalid and unknown invocations.
- Unavailable and disabled capabilities.
- Missing dependencies and permissions.
- AI-required capability preconditions.
- Capability exception isolation.
- Timeout and cooperative cancellation.
- Exactly one terminal result and event.
- Result and event immutability.
- Absence of plan orchestration.

---

# Performance Considerations

Runtime resolution by identifier should be constant time. The executor must use
bounded resources and must not create an unbounded thread or task for every
invocation.

Operational state and performance profile independently constrain whether Core
invokes a capability. When the `PERFORMANCE` performance profile is active or
the operational state is `STANDBY`, Core may delay non-essential invocations
before calling Runtime. Runtime respects the invocation boundary, does not
select or apply either value, and still enforces invocation-level deadlines and
cancellation.

---

# Security and Privacy Considerations

Only trusted implementations supplied during controlled bootstrap may be
loaded. Every invocation follows least privilege and carries only the grants
approved for that operation.

Arguments and outputs may be sensitive and must not be logged or included in
events by default. Error messages are sanitized at the Runtime boundary.

System Layer and AI Provider dependencies remain behind their own security and
privacy contracts.

---

# Future Evolution

Future versions may add signed plugins, dynamic loading, sandboxed execution,
streaming results, or out-of-process isolation after explicit architecture is
approved.

Version 1 remains local, in-process, explicitly loaded, and synchronous from the
caller's perspective.

---

# Architectural Considerations

Capability Runtime supersedes earlier execution terminology in legacy
documents. It is the only component that loads and invokes capabilities.

The separation is strict:

- Capability Registry describes.
- Planner proposes.
- Core orchestrates.
- Capability Runtime executes.
