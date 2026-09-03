# Core

**Status:** Draft

**Version:** 1.2

**Last Updated:** 2026-09-02

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

- Coordinating deterministic platform-module startup and graceful shutdown.
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
- Owning the foreground process or Runtime Host lifecycle.

---

# Runtime Host Lifecycle

The local Runtime Host owns the outer foreground process lifecycle. Its states
are `CREATED`, `STARTING`, `RUNNING`, `STOPPING`, `STOPPED`, and `FAILED`. The
Host starts the composed runtime, governs the foreground interface, and stops
the process deterministically. It does not classify, decide, plan, or execute
capabilities.

Core lifecycle responsibilities refer to platform and module orchestration,
including operational-state and performance-profile changes. They do not make
Core the owner of the Runtime Host process state. The `lifecycle_phase` in a
`PlatformStateSnapshot` describes the composed platform phase observed by Core;
it is not the mutable state of the Runtime Host.

Runtime lifecycle state, operational state, and performance profile are
independent contracts. Stopping the Runtime Host does not create a new
`OperationalState` or `PerformanceProfile`.

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
4. Initialize the process-local Interactive Confirmation coordinator.
5. Initialize System Layer adapters.
6. Initialize the configured AI Provider, bounded Request Interpreter when
   available, and stateless Conversation Responder.
7. Initialize Capability Registry.
8. Initialize Capability Runtime and load trusted local capabilities.
9. Seal Capability Registry after dependency validation.
10. Initialize Context Engine.
11. Initialize Request Classifier.
12. Initialize Decision Engine.
13. Initialize Planner.
14. Register event subscriptions.
15. Establish the configured initial operational state and performance profile.
16. Start approved background observation.
17. Begin accepting user requests.

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
    │                                │
    │                ┌───────────────┴────────────────┐
    │                ▼                                ▼
    │       Request Interpreter             Conversation Responder
    │                │                                │
    │                ▼                                ▼
    │       second Decision evaluation      user-facing text only
    ├── ASK_FOR_CONFIRMATION ──> User interaction boundary
    ├── SUGGEST ───────────────> User interaction boundary
    └── IGNORE ────────────────> No action
    │
    ▼
Core correlates result and publishes RequestCompleted or ErrorOccurred
```

The Core never asks the Request Classifier to select a destination. It never
passes an entire plan to Capability Runtime because Core owns step progression.

After classification, Core captures exactly one immutable `ContextSnapshot`
for the request. It reuses that same instance in `DecisionInput`,
`PlanningRequest`, and every `CapabilityInvocation` created for the request.
Core does not retain the snapshot after request orchestration completes, and no
downstream module refreshes it during that request.

Core also captures exactly one immutable `MemorySnapshot` for every request.
It reuses that same instance in `DecisionInput` and `PlanningRequest` when
planning occurs. Capability invocations and Capability Runtime do not receive
memory. Core reads only the snapshot boundary and does not store entries,
select memory facts, or retain the snapshot after request orchestration.

For bounded request interpretation, the first Decision Engine evaluation may
return `DELEGATE(ai.request_interpreter)` only after the deterministic path has
not resolved the request. Core calls the injected `RequestInterpreter` at most
once and supplies only the original `Request`; it does not supply Context or
Working Memory. A valid `RequestInterpretation` is added explicitly to a second
`DecisionInput` that reuses the same Context and Memory snapshots and the same
Capability Catalog view. The second decision never directly executes a
capability. A validated open action requires confirmation; a validated
read-only status action may proceed to planning. Core does not loop, interpret
provider output, or forward `RequestInterpretation` to Planner or Capability
Runtime.

For eligible questions and conversation, Decision Engine may instead return
`DELEGATE(ai.conversation_responder)`. Core calls the injected
`ConversationResponder` at most once with the original request and resolved
interaction language. It validates response correlation and language, then
returns the immutable response to the foreground boundary. This path does not
invoke Planner, Capability Runtime, or System Layer, and it cannot execute an
action. Core supplies neither Context nor Working Memory to the responder.

Operational actions and confirmation resolution retain precedence over
conversation. Core does not generate conversational text, define assistant
self-knowledge, or maintain conversation history.

When the second evaluation returns `ASK_FOR_CONFIRMATION`, Core passes the exact
validated `ApplicationAction` to the injected `ConfirmationCoordinator`. The
returned `ConfirmationPrompt` contains only approved structured identifiers,
expiration, and interaction language. The foreground interface renders the
prompt; Core does not produce translated sentences.

A later response is a new request with its own single Context and Memory
snapshots. Core resolves it through the coordinator before any AI delegation.
An accepted single-use resolution returns to Decision Engine and may produce
`REQUEST_PLANNING`; it never authorizes direct `EXECUTE`. Core passes the same
approved `ApplicationAction` instance to Planner. Rejected, invalidated,
expired, or unmatched confirmation tokens complete safely without planning or
execution.

For `APPLICATION_STATUS`, Core passes the exact locally validated action from
the second Decision Engine result directly to Planner. It does not create
confirmation state, reconstruct the action from text, inspect processes, or
render the status result.

---

# Plan Coordination

For an approved plan, Core:

1. Verifies that user confirmation requirements are satisfied.
2. Creates one immutable `CapabilityInvocation` for the next eligible step.
3. Includes configured permission grants and the context snapshot already
   captured for the request.
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

Bootstrap constructs exactly one provider selected by validated Configuration.
`openai` uses the existing OpenAI adapter and reads its credential only from
`ATREUS_OPENAI_API_KEY` in the process environment. `ollama` uses the local HTTP
adapter with its validated local endpoint and model and requires no credential.
Selection is fixed for one composition; V0 has no automatic fallback or AI
Router. Bootstrap supplies Core only with provider-neutral `RequestInterpreter`
and `ConversationResponder` abstractions.

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
- Working Memory Snapshot Provider.
- System Layer services.
- AI Provider.
- Request Interpreter.
- Conversation Responder.
- Confirmation Coordinator.
- Interaction Language Resolver.
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
stabilization, planning, and execution deadlines are not defined here. Working
Memory V0 receives validated defaults of 64 entries and 1800 seconds per entry
through Configuration; both values remain overridable before bootstrap.

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
- Exactly one Working Memory snapshot per request and identity preservation
  through decision and planning.
- Working Memory snapshot failure before downstream decision or execution.
- AI Provider unavailable behavior.
- One bounded interpretation call, second-decision identity preservation, and
  mandatory confirmation.
- Single-use confirmation resolution, replay prevention, and planning only
  after accepted Decision Engine reevaluation.
- One Context and Memory snapshot for each initial or response request.
- AI interpretation failure without planning or capability execution.
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
