# Planner

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-09-02

---

# Purpose

The Planner transforms a high-level goal into an explicit, validated sequence
of capability invocations.

A plan describes intended work. The Planner does not perform that work.

---

# Responsibilities

The Planner is responsible for:

- Accepting a planning request with one clear goal.
- Discovering relevant capability metadata through the Capability Registry
  abstraction.
- Decomposing the goal into ordered steps.
- Representing every step as immutable data.
- Verifying that referenced capabilities exist and are available.
- Surfacing required permissions and confirmations.
- Validating structural consistency before returning a plan.
- Publishing `PlanCreated` after successful planning.

---

# Non-Responsibilities

The Planner is not responsible for:

- Executing capabilities.
- Loading capability implementations.
- Granting permissions.
- Asking the user for confirmation.
- Selecting the current context.
- Changing platform state.
- Persisting plans or execution history.
- Calling operating-system APIs.

The Core decides when planning is required. The Capability Runtime executes an
approved plan one invocation at a time.

---

# Inputs

The Planner accepts an immutable `PlanningRequest` containing:

- `planning_id`: Unique planning operation identifier.
- `request_id`: Correlated user request identifier.
- `goal`: Normalized high-level goal.
- `constraints`: Explicit immutable planning constraints.
- `context`: Current context snapshot relevant to planning.
- `memory`: Stable bounded memory snapshot captured for the request.
- `action`: Optional approved `ApplicationAction` supplied by Core after local
  interpretation validation or a single-use confirmation resolution.

The context is the same immutable snapshot captured by Core for the request.
Planner consumes it as planning input and must not select, refresh, merge, or
persist context.

The memory snapshot is also the same immutable instance captured by Core.
Planner does not query or write `MemoryStore`, and Version 0 planning behavior
does not interpret memory values.

Constraints may limit available capabilities, require confirmation, or express
a deadline. They must not contain executable callbacks or implementation
objects.

`PlanningConstraints` contains only:

- `allowed_capability_ids`: Optional immutable allowlist.
- `blocked_capability_ids`: Immutable denylist.
- `maximum_steps`: Positive upper bound for generated steps.
- `deadline`: Optional UTC completion constraint.
- `require_confirmation`: Whether the complete plan requires approval.

An empty goal is invalid.

---

# Plan Contract

The Planner returns an immutable `Plan` containing:

- `plan_id`: Unique plan identifier.
- `request_id`: Correlated request identifier.
- `goal`: Goal represented by the plan.
- `steps`: Ordered immutable collection of `PlanStep` objects.
- `required_permissions`: Deduplicated permissions required by all steps.
- `requires_confirmation`: Whether the complete plan needs user approval before
  execution.

A `PlanStep` contains:

- `step_id`: Identifier unique within the plan.
- `capability_id`: Stable Capability Registry identifier.
- `arguments`: Immutable capability input values.
- `depends_on`: Identifiers of earlier steps that must complete successfully.
- `requires_confirmation`: Whether this step requires explicit approval.

Plan objects contain no executable functions, capability implementations, or
provider clients.

---

# Version 1 Plan Semantics

Version 1 plans are finite and sequential.

- Steps are considered in collection order.
- `depends_on` may reference only earlier steps.
- Parallel branches are not supported.
- Conditional branches are not supported.
- Loops are not supported.
- Automatic retries are not part of the plan.
- Dynamic generation of new steps during execution is not supported.
- Arguments are resolved when the plan is created.

Goals that require unsupported dynamic behavior fail planning explicitly rather
than producing a partially executable plan.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class Planner(ABC):
    def create_plan(self, request: PlanningRequest) -> Plan: ...
```

The Planner depends on a read-only `CapabilityCatalog` contract exposed by the
Capability Registry:

```python
class CapabilityCatalog(ABC):
    def get(self, capability_id: str) -> CapabilityMetadata | None: ...

    def list_available(self) -> tuple[CapabilityMetadata, ...]: ...
```

---

# Internal Flow

```text
PlanningRequest
    │
    ▼
Goal and Constraint Validation
    │
    ▼
Capability Catalog Query
    │
    ▼
Goal Decomposition
    │
    ▼
Step Construction
    │
    ▼
Plan Validation
    │
    ▼
Immutable Plan
```

Version 1 should use deterministic planning strategies for supported goals. AI
is not required for plan creation.

---

# Plan Validation

Before a plan is returned, the Planner verifies:

- The plan contains at least one step.
- Every step identifier is unique.
- Every capability identifier exists.
- Every selected capability is available.
- Capability dependencies are present and available.
- Step dependencies reference only earlier steps.
- Required permissions match Capability Registry metadata.
- Confirmation requirements are preserved.
- The plan respects request constraints.

Validation does not grant permissions or reserve resources.

---

# Dependencies

The Planner depends on:

- The read-only `CapabilityCatalog` abstraction.
- Immutable request, context, memory-snapshot, capability metadata, and plan
  contracts.
- Optionally, the `EventBus` abstraction for domain event publication.

It does not depend on Core, Capability Runtime, System Layer, `MemoryStore`, or
a concrete AI provider. It consumes only the immutable `MemorySnapshot` data
contract.

AI Provider does not place `RequestInterpretation` in `PlanningRequest`. A
valid interpretation first returns to Decision Engine. Open actions are
planned only after a later exact confirmation response is accepted and
reevaluated; read-only status actions may be planned immediately. Core supplies
only the approved `ApplicationAction`, never raw AI output or yes/no content.

Planner maps the typed action to exactly one specific capability invocation:

- `OPEN_APPLICATION` becomes
  `application.open(application_id=<approved ApplicationIdentifier>)`.
- `APPLICATION_STATUS` becomes
  `application.status(application_id=<approved ApplicationIdentifier>)`.

It does not reconstruct the target from request text or know Windows
executables and process names. Capability Catalog validation and normal
planning constraints remain active.

---

# Events

The Planner owns:

## `PlanCreated`

Published after a plan passes validation.

Fields:

- Common event metadata.
- `plan_id`.
- `request_id`.
- Ordered capability identifiers.
- `step_count`.
- `requires_confirmation`.

The event must not contain capability arguments or private goal content.

Planning failures are returned as explicit exceptions. The Core may publish
`ErrorOccurred` for the request lifecycle.

---

# Error Handling

The module defines a `PlanningException` base error with specific errors for:

- Invalid planning requests.
- Goals that cannot be planned with available capabilities.
- Invalid capability references.
- Invalid plan structure.
- Unsupported Version 1 plan semantics.

The Planner must never return an incomplete or structurally invalid plan as a
successful result.

---

# Testing Requirements

Tests must cover:

- Single-step and multi-step plans.
- Capability lookup and availability.
- Capability dependencies.
- Permission aggregation.
- Confirmation propagation.
- Duplicate and invalid step identifiers.
- Forward and unknown step dependencies.
- Empty and unsupported goals.
- Deterministic planning for identical inputs.
- Identity preservation for the request memory snapshot.
- Plan and step immutability.
- Event publication without sensitive arguments.
- Absence of capability execution.
- Confirmed action planning from typed identifiers without response-text or AI
  output reconstruction.

---

# Performance Considerations

Planning must operate over a bounded snapshot of Capability Registry metadata.
Version 1 must not perform unbounded graph search, network calls, or speculative
execution.

The number of generated steps must be limited by planning policy. If the limit
is exceeded, planning fails explicitly.

---

# Security and Privacy Considerations

Plans may contain sensitive arguments. Full plans and step arguments must not be
logged or included in events by default.

The Planner must preserve permission and confirmation requirements from
capability metadata. It cannot downgrade requirements to make a plan executable.

Plans are proposals until the Core applies user-control policy and authorizes
execution.

---

# Future Evolution

Future versions may add conditional steps, parallel execution, output bindings,
partial replanning, or AI-assisted decomposition after explicit architectural
approval.

Future AI-assisted planners must depend on `AIProvider`, preserve deterministic plan
validation, and remain optional.

---

# Architectural Considerations

The Planner owns goal decomposition and plan structure. The Capability Registry
owns capability descriptions, the Core owns workflow, and the Capability
Runtime owns execution.

This separation makes plans inspectable, testable, and subject to confirmation
before side effects occur.
