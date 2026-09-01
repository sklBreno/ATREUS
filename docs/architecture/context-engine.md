# Context Engine

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-09-01

---

# Purpose

The Context Engine detects and maintains the user's current computing context.

Context is a first-class platform concept established by ADR-003. The engine
turns approved system signals into a stable, immutable context snapshot that
other modules can use when making decisions.

Context is ephemeral situational state. It does not contain historical
activity, learned preferences, or retained experience; those concerns belong
to Memory. Runtime Host lifecycle, operational state, and performance profile
are independent contracts and must not be represented as user context.

---

# Version 0 Scope

Version 0 establishes the immutable context contract and coherent request
propagation without implementing context inference.

Production uses an unavailable provider that returns `UNKNOWN`, confidence
`0.0`, and `UNAVAILABLE`. It does not infer a context when no approved evidence
exists. Signal providers, aggregation, transition stabilization, and context
events remain Version 1 work.

For each request, Core captures exactly one `ContextSnapshot`. The same
instance is supplied to Decision Engine, Planner, `CapabilityInvocation`, and
Capability Runtime's `ExecutionContext`. Capability Runtime never queries a
`ContextProvider` or refreshes context during an invocation.

---

# Responsibilities

The Context Engine is responsible for:

- Receiving context signals from approved providers.
- Evaluating signals using deterministic Version 1 rules.
- Maintaining the current context snapshot.
- Detecting transitions between contexts.
- Stabilizing transitions to avoid rapid context changes.
- Providing the current context through an interface.
- Publishing context change and signal availability events.

---

# Non-Responsibilities

The Context Engine is not responsible for:

- Executing capabilities or operating-system actions.
- Deciding or applying operational-state transitions or performance-profile
  changes.
- Suppressing notifications.
- Creating plans.
- Making request decisions.
- Persisting user activity history.
- Inferring context from unapproved data sources.

It provides situational awareness. The Core and Decision Engine coordinate any
behavior influenced by context.

---

# Context Types

Version 1 supports these contexts:

- `WORKING`
- `STUDYING`
- `GAMING`
- `MEETING`
- `ENTERTAINMENT`
- `IDLE`
- `UNKNOWN`

`UNKNOWN` is used during startup or when available signals do not support a
reliable classification. It must not be treated as `IDLE`.

---

# Context Signals

A `ContextSignal` is an immutable observation with:

- `signal_type`: Stable signal identifier.
- `value`: Typed value defined by the signal provider contract.
- `observed_at`: UTC observation timestamp.
- `source`: Stable provider identifier.

Version 1 may use approved signals for:

- Active application.
- Running applications.
- User input activity.
- CPU utilization.
- GPU utilization when available.
- Available memory.
- Battery and power state.
- Time of day.

Calendar events, connected devices, personalized models, and external services
are future sources and are not required for Version 1.

The System Layer supplies operating-system observations through abstractions.
The Context Engine must not call operating-system APIs directly.

---

# Current Context

The engine exposes an immutable `ContextSnapshot` containing:

- `context_type`: Current Version 1 context.
- `confidence`: Numeric value from `0.0` to `1.0`.
- `started_at`: UTC timestamp of the current context transition.
- `evaluated_at`: UTC timestamp of the latest evaluation.
- `signal_status`: Whether required signal coverage is `AVAILABLE`, `DEGRADED`,
  or `UNAVAILABLE`.

Raw signal values are not included in the public snapshot.

Version 0 snapshots enforce confidence boundaries, timezone-aware timestamps,
chronological ordering, and the invariant that `UNAVAILABLE` requires
`UNKNOWN` with confidence `0.0`.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class ContextProvider(ABC):
    def current_context(self) -> ContextSnapshot: ...


class ContextEngine(ContextProvider, ABC):
    def evaluate(
        self,
        signals: tuple[ContextSignal, ...],
    ) -> ContextSnapshot: ...
```

Consumers that only need current context depend on `ContextProvider`. Bootstrap
and orchestration code may depend on the broader `ContextEngine` lifecycle
contract.

Version 0 composes only `ContextProvider`. A broader `ContextEngine` contract
must not be implemented until approved signal providers and deterministic
evaluation rules exist.

---

# Transition Model

A transition occurs only when a candidate context is stable enough to replace
the current context.

Version 1 follows this deterministic flow:

1. Validate and discard stale signals while reporting invalid observations.
2. Evaluate the remaining signals against context rules.
3. Produce a candidate context and confidence.
4. Compare the candidate with the current snapshot.
5. Require the candidate to meet the minimum confidence and stability policy.
6. Keep the existing context while the candidate is unstable.
7. Commit one transition and publish `ContextChanged` after stabilization.

The stabilization policy is an injected immutable policy object. Its thresholds
must have platform defaults and may become user-configurable only after the
Configuration architecture defines those values.

This policy prevents context flapping caused by short application switches or
temporary resource spikes.

---

# Internal Flow

```text
System Layer Signal Providers
    │
    ▼
Signal Validation
    │
    ▼
Context Evaluation Rules
    │
    ▼
Transition Stabilization
    │
    ├── no transition ──> Existing ContextSnapshot
    │
    └── transition ─────> New ContextSnapshot + ContextChanged
```

Version 1 should prefer deterministic signal rules. AI-based context detection
is not required and must not be the primary mechanism.

---

# Relationship With Performance Profiles and Operational States

Context is an input to Decision Engine operational-state and
performance-profile decisions, not a command.

Operational state and performance profile are independent. For example,
`GAMING` may contribute to a Decision Engine outcome that requests the
`PERFORMANCE` performance profile, the `STANDBY` operational state, both, or
neither. Context Engine provides context but does not decide or apply either
value. Core supplies the current context and system signals to Decision Engine,
then validates and applies approved changes and publishes the corresponding
Core-owned events.

Context transitions should trigger reevaluation of platform operating behavior.
They must not directly pause modules, change polling rates, or suppress user
interactions.

---

# Dependencies

The Context Engine depends on:

- System Layer signal-provider abstractions.
- The `EventBus` abstraction for domain event publication.
- Immutable context policy and data contracts.

It does not depend on Core, Decision Engine, Planner, Capability Runtime, Memory,
or concrete operating-system APIs.

---

# Events

The Context Engine owns:

## `ContextChanged`

Published after a stabilized transition.

Fields:

- Common event metadata.
- `previous_context`.
- `current_context`.
- `confidence`.
- `started_at`.

## `ContextSignalAvailabilityChanged`

Published when required signal coverage changes between `AVAILABLE`, `DEGRADED`,
and `UNAVAILABLE`.

Fields:

- Common event metadata.
- `previous_status`.
- `current_status`.
- Provider identifiers affected.

Neither event contains raw user activity or application history.

Version 0 publishes neither event because it performs no signal evaluation or
semantic context transition. Structural provider failures use the existing
sanitized Core orchestration error path.

The Context Engine subscribes to these System Layer events when their providers
are enabled:

- `SystemResourcePressureChanged`.
- `PowerStateChanged`.
- `ActiveApplicationChanged`.

Subscription handlers translate approved event fields into `ContextSignal`
objects and trigger evaluation. They do not execute actions or publish a
context transition until the stabilization policy is satisfied.

---

# Error Handling

The module defines a `ContextEngineException` base error with explicit errors
for invalid signals, evaluation failure, and invalid transition policy.

A single unavailable optional signal must not stop context evaluation. The
engine marks the snapshot as degraded and reports the provider failure. If no
reliable evaluation is possible, it returns `UNKNOWN` with `UNAVAILABLE` signal
status rather than guessing.

---

# Testing Requirements

Tests must cover:

- Version 0 snapshot invariants and immutability.
- Stable unavailable-context start time and clock-based evaluation time.
- Exactly one context capture per request.
- Identity preservation through decision, planning, invocation, and execution.
- Provider failure before decision or execution without private-detail events.
- Absence of operating-system dependencies from the context domain.

Version 1 tests must additionally cover:

- Every Version 1 context type.
- Startup with no signals.
- Available, degraded, and unavailable signal coverage.
- Confidence boundaries.
- Transition stabilization.
- Prevention of context flapping.
- Stale and invalid signals.
- Exactly one event per committed transition.
- Snapshot and event immutability.
- Context reads during repeated evaluations.
- Absence of action execution.

---

# Performance Considerations

The Context Engine is an Always-On component and must remain lightweight.

It should react to System Layer notifications and bounded sampling rather than
perform aggressive polling. Evaluation must be incremental where practical and
must not retain unbounded signal history.

During high system load, signal frequency may be reduced by orchestration policy
without changing the context contract.

---

# Security and Privacy Considerations

Only explicitly approved signal providers may be enabled. Users must be able to
disable context sources through supported platform settings.

Raw active-window titles, file names, user input contents, and process arguments
must not be included in public snapshots, events, or default logs. Signals are
kept only as long as needed for current evaluation unless a separate approved
Memory policy exists.

Context availability and confidence must remain transparent to the user.

---

# Future Evolution

Future versions may add multi-context representation, personalized context
models, calendar signals, confidence calibration, or cross-device context after
their architectures are approved.

Future detection strategies must preserve the `ContextProvider` contract and
the rule that the Context Engine observes but does not act.

---

# Architectural Considerations

The Context Engine is the single source of truth for current context. Other
modules consume its snapshot and must not independently classify user context.

The Context Engine owns `ContextChanged`. The Core may react to this event but
must not publish a duplicate context event.
