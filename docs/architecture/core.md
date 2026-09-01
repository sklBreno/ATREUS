# Core

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-08-17

---

# Purpose

The Core is the central orchestration component of ATREUS.

It coordinates platform lifecycle, routes classified requests, applies platform
state transitions, and invokes specialized modules through explicit interfaces.

The Core owns the flow, never the work.

---

# Philosophy

The Core should remain small and stable.

It understands module contracts and lifecycle order but never absorbs domain
logic. Classification, context detection, decision policy, planning, memory,
capability execution, AI processing, and operating-system access remain in
their specialized components.

Every feature added directly to the Core increases coupling. New behavior
should normally enter through an interface, capability, or domain event.

---

# Responsibilities

The Core is responsible for:

- Coordinating deterministic startup and graceful shutdown.
- Managing the platform lifecycle.
- Owning the current operational state.
- Recording and propagating the active performance profile.
- Routing classified requests according to Decision Engine results.
- Assembling immutable inputs from module contracts.
- Coordinating approved plans one step at a time.
- Publishing Core-owned lifecycle and request events.
- Reacting to domain events without taking ownership of them.
- Isolating module failures where recovery is possible.
- Maintaining correlation across one platform operation.

---

# Non-Responsibilities

The Core is not responsible for:

- Classifying requests.
- Detecting or determining user context.
- Making domain or request decisions.
- Creating plans.
- Loading or executing capability implementations.
- Cataloging capability metadata.
- Storing memory entries directly.
- Calling native operating-system APIs.
- Performing AI processing.
- Reading environment variables or configuration files.
- Granting permissions interactively.

---

# Platform State

Core exposes an immutable `PlatformStateSnapshot` containing at least:

- Current lifecycle phase.
- Current operational state.
- Active performance profile.
- Startup timestamp.
- Latest state-change timestamp.

Consumers receive snapshots and must not mutate Core state directly.

---

# Operational State

Version 1 defines:

- `ACTIVE`.
- `PASSIVE`.
- `STANDBY`.

Core owns and applies operational-state transitions because they affect
platform lifecycle and module orchestration.

Core does not determine a transition alone. The transition flow is:

```text
System Layer Signals + ContextSnapshot + Configuration + Current Platform State
                                  │
                                  ▼
                           Decision Engine
                                  │ desired state
                                  ▼
                                Core
                                  │
                 validate transition and apply lifecycle behavior
                                  │
                                  ▼
                    OperationalStateChanged
```

Context Engine supplies context but never changes operational state. System
Layer supplies observations but never chooses lifecycle behavior.

Core rejects invalid transitions explicitly and preserves the previous valid
state.

---

# Performance Profiles

Version 1 defines performance profiles separately from operational state:

- `PERFORMANCE`.
- `BALANCED`.
- `IDLE`.

Decision Engine determines the desired profile from current context, validated
configuration, user policy, and System Layer signals.

Core records and propagates the selected profile through the platform-state
contract and `PerformanceProfileChanged`. Modules remain responsible for
adapting their own permitted activity to the active profile.

Core does not implement module-specific performance tuning.

---

# Startup Sequence

Bootstrap loads and validates configuration before constructing Core. Concrete
components are supplied behind their interfaces through dependency injection.

Core then coordinates this deterministic Version 1 sequence:

1. Receive validated Configuration and composed module interfaces.
2. Initialize Event Bus.
3. Initialize bounded Working Memory.
4. Initialize System Layer adapters.
5. Initialize the configured AI Provider abstraction, if available.
6. Initialize Capability Registry.
7. Initialize Capability Runtime and load trusted local capabilities.
8. Seal Capability Registry after dependency validation.
9. Initialize Context Engine.
10. Initialize Request Classifier.
11. Initialize Decision Engine.
12. Initialize Planner.
13. Register event subscriptions.
14. Establish the configured initial operational state and performance profile.
15. Start approved background observation.
16. Begin accepting user requests.

No module reads raw configuration sources during this sequence.

---

# Request Lifecycle

Every request follows explicit orchestration:

```text
User Request
    │
    ▼
Core publishes RequestReceived
    │
    ▼
Request Classifier returns ClassifiedRequest
    │
    ▼
Core assembles DecisionInput
    │
    ▼
Decision Engine returns Decision
    │
    ├── EXECUTE ───────────────> Capability Runtime
    ├── REQUEST_PLANNING ──────> Planner
    │                                │
    │                                ▼
    │                           approved Plan
    │                                │
    │                                ▼
    │                    Core invokes each eligible step
    │                                │
    │                                ▼
    │                         Capability Runtime
    ├── DELEGATE ──────────────> Explicit service interface
    ├── ASK_FOR_CONFIRMATION ──> User interaction boundary
    ├── SUGGEST ───────────────> User interaction boundary
    └── IGNORE ────────────────> No action
    │
    ▼
Core correlates result and publishes RequestCompleted or ErrorOccurred
```

The Core never asks the Request Classifier to select a destination. It never
passes an entire plan to Capability Runtime because Core owns step progression.

Working Memory is used only when a request requires bounded temporary state.

---

# Plan Coordination

For an approved plan, Core:

1. Verifies that user confirmation requirements are satisfied.
2. Creates one immutable `CapabilityInvocation` for the next eligible step.
3. Includes configured permission grants and current context.
4. Calls Capability Runtime.
5. Evaluates the immutable execution result.
6. Continues, stops, or requests user input according to plan dependencies and
   decision policy.

Core does not modify the plan or execute capability code.

---

# Permissions

Version 1 permission grants are defined by validated user configuration.

Core receives an immutable configured grant set during bootstrap. It supplies
the relevant grants to `DecisionInput`, `CapabilityInvocation`, and system
operation context without expanding them.

Capability Registry declares required permissions. Capability Runtime verifies
grants before execution. System Layer enforces permissions again at the native
boundary.

Core does not grant permissions interactively and cannot infer a broad grant
from a narrower configured permission.

---

# AI Provider Initialization

AI credentials enter through approved environment or configuration loading.
Bootstrap injects them into the selected concrete provider adapter and supplies
Core only with the `AIProvider` abstraction.

Core must never store, inspect, log, publish, or forward raw credentials.
AI Provider must not persist them. Credentials are never hardcoded.

The absence of an available provider is a supported platform state. Core keeps
deterministic capabilities operational and respects `requires_ai` availability
from capability metadata.

---

# Module Coordination

Core communicates through interfaces with:

- Configuration Provider.
- Event Bus.
- Working Memory Store.
- System Layer services.
- AI Provider.
- Capability Registry and Capability Catalog.
- Capability Runtime.
- Context Provider and Context Engine lifecycle contract.
- Request Classifier.
- Decision Engine.
- Planner.

Domain modules do not depend on Core. Core receives implementations through
composition and depends only on contracts.

---

# Event Coordination

Core owns and publishes:

- `PlatformStarted`.
- `PlatformStopped`.
- `ModuleInitialized`.
- `RequestReceived`.
- `RequestCompleted`.
- `OperationalStateChanged`.
- `PerformanceProfileChanged`.
- `ErrorOccurred` for orchestration failures.

Context Engine owns `ContextChanged`. Core subscribes and reacts to that event
but must not republish it under the same meaning.

Other domain modules own their events as defined in their architecture
documents. Event Bus delivers those facts and never chooses the next lifecycle
or request step.

---

# Error Handling

One recoverable module failure should not crash the platform.

Core must:

- Preserve correlation and identify the failed orchestration step.
- Isolate failures when the module contract allows recovery.
- Publish a sanitized `ErrorOccurred`.
- Keep unaffected modules available.
- Avoid retrying side-effecting operations without explicit policy.
- Shut down gracefully when a required foundation component is unavailable.

Module-specific exceptions remain owned by their modules. Core translates them
only into orchestration outcomes and safe user-facing results.

---

# Performance

Core remains lightweight and performs no heavy computation.

It coordinates profile changes but does not implement module-specific throttling.
Modules consume the active profile and apply their documented behavior.

Numeric thresholds for state transitions, performance adaptation, context
stabilization, planning, Working Memory, and execution deadlines are not defined
here. Future implementations receive configurable defaults through validated
configuration.

---

# Testing Requirements

Core tests must cover:

- Deterministic startup and reverse-order shutdown.
- Request routing for every Decision outcome.
- Plan-step coordination without direct execution.
- Operational-state ownership and valid transitions.
- Performance-profile propagation.
- `ContextChanged` consumption without duplicate publication.
- Permission-grant propagation without expansion.
- AI Provider unavailable behavior.
- Module failure isolation.
- Core-owned event publication.
- Dependency injection through interfaces.
- Absence of business logic and native system access.

---

# Scalability

New modules should integrate through documented interfaces and events without
absorbing their behavior into Core.

Changes to required workflow remain explicit and documented. Event-driven
communication must not hide control flow merely to avoid updating orchestration.

---

# Guiding Principles

- Orchestrate, never execute.
- Own flow and lifecycle state.
- Delegate decisions and work.
- Depend on abstractions.
- Preserve explicit event ownership.
- Minimize coupling.
- Remain predictable and testable.
- Fail gracefully.
- Keep user control authoritative.

---

# Future Evolution

Future versions may introduce approved plugin loading, multi-device
orchestration, richer health monitoring, or self-diagnostics.

These changes require documented contracts and must preserve Core as the
platform orchestrator rather than a business-logic container.
