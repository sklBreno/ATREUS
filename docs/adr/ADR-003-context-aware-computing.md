# ADR-003 — Context-Aware Computing

**Status:** Accepted

**Date:** 2026-07-02

**Last Updated:** 2026-09-01

---

# Context

The same request or platform condition may require different behavior depending
on what the user is doing.

A purely reactive assistant ignores system load, current activity, interruption
risk, and opportunities for responsible assistance. ATREUS therefore treats
context as a first-class architectural concept rather than an optional feature.

---

# Decision

ATREUS adopts Context-Aware Computing.

Context Engine detects and maintains current user context from approved signals.
Other modules consume its immutable snapshot and must not independently classify
context.

Version 1 context types are:

- `WORKING`.
- `STUDYING`.
- `GAMING`.
- `MEETING`.
- `ENTERTAINMENT`.
- `IDLE`.
- `UNKNOWN`.

`UNKNOWN` represents insufficient reliable context. It is not equivalent to
`IDLE`.

Context is ephemeral situational state. Historical activity, learned
preferences, and retained experience belong to Memory. Runtime Host lifecycle,
operational state, and performance profile remain independent from context.

Explicit user-approved facts and preferences belong to the separate Personal
Profile boundary. They are not context signals, are never inferred by Context
Engine, and do not authorize context-informed actions.

Version 0 establishes only the immutable context snapshot and coherent request
propagation. Without approved evidence, production returns `UNKNOWN` with
confidence `0.0` and unavailable signal status. It does not guess or implement
signal aggregation, stabilization, or context events.

Core captures one snapshot per request and reuses the same instance for
decision, planning, capability invocation, and execution. Capability Runtime
does not query Context Engine or `ContextProvider`.

---

# Context Engine Responsibilities

Context Engine is responsible for:

- Receiving signals from approved System Layer providers.
- Evaluating signals through deterministic rules.
- Maintaining the current immutable `ContextSnapshot`.
- Stabilizing and committing context transitions.
- Publishing `ContextChanged` after a committed transition.
- Reporting signal availability.

Context Engine owns `ContextChanged`.

It does not execute capabilities, change operational state, select performance
profiles, suppress interactions, pause modules, or apply user-facing behavior.

---

# Context Sources

Version 1 may use approved local signals for:

- Running and active applications.
- User activity.
- CPU and GPU utilization when available.
- Available memory.
- Battery and power state.
- Time of day.

System Layer provides operating-system observations through narrow interfaces
and approved events. Context Engine never calls native APIs directly.

Calendar events, connected devices, external services, and personalized models
are future sources and require separate architecture.

---

# Context Transitions

Context transitions require deterministic confidence and stabilization policy.
This prevents rapid changes caused by temporary signals.

Numeric thresholds and time windows are not defined by this ADR. Future
implementations receive configurable defaults through validated configuration.

Only Context Engine commits a context transition. Core and other modules consume
the resulting snapshot or `ContextChanged` event.

---

# Operational State Relationship

Context and operational state are separate concepts.

- Context Engine provides current user context.
- System Layer provides current system signals.
- Decision Engine may determine a desired transition between `ACTIVE`,
  `PASSIVE`, and `STANDBY`.
- Core owns operational state and applies the approved transition.

A `GAMING` context may contribute to a `STANDBY` decision, but Context Engine
never activates Standby directly.

---

# Performance Profile Relationship

Context and performance profile are also separate concepts.

Decision Engine determines the desired `PERFORMANCE`, `BALANCED`, or `IDLE`
profile from context, validated configuration, user policy, and System Layer
signals. Core records and propagates the active profile. Modules adapt their own
permitted activity to that profile.

The `IDLE` user context and `IDLE` performance profile have different contracts
and must not be represented by one shared enum or state value.

---

# Context-Informed Behavior

Context may influence downstream decisions such as:

## Gaming

- Prefer reduced non-essential activity.
- Avoid proactive interruption.
- Delay eligible maintenance.

## Working

- Permit relevant productivity suggestions.
- Surface approved reminders.

## Meeting

- Prefer interruption suppression.
- Delay non-critical suggestions.

## Studying

- Prefer focus-preserving behavior.
- Permit relevant learning assistance.

## Idle

- Permit eligible deferred work when the active operational state and
  performance profile allow it.

These are Decision Engine inputs and policy outcomes. Context Engine does not
perform any listed behavior.

---

# Responsible Proactivity

Context awareness enables optional proactive assistance when confidence, user
policy, operational state, and performance profile permit it.

Proactive behavior must be transparent, predictable, non-intrusive, and always
subject to user control. Context alone never authorizes an action.

---

# Privacy Considerations

Users control which context sources are enabled and which contextual behaviors
are permitted.

Raw active-window titles, file names, process arguments, user input contents,
and detailed activity history must not appear in public snapshots, events, or
default logs.

Signals are retained only as long as required for current evaluation unless a
separate approved Memory policy exists. Context collection must never become
hidden surveillance.

---

# Rationale

Context awareness allows ATREUS to adapt without requiring constant manual mode
selection.

Deterministic local signals improve responsiveness, privacy, performance, and
predictability. Separating observation, decision, and application prevents
Context Engine from becoming an execution component.

---

# Consequences

Positive consequences:

- More relevant and less intrusive behavior.
- Better adaptive performance input.
- Foundation for responsible proactivity.
- Central source of truth for current context.
- Explicit privacy and event ownership.

Trade-offs:

- Context rules and stabilization require careful testing.
- Signal availability differs across systems.
- Incorrect context may influence downstream decisions.
- Privacy controls are mandatory.

---

# Alternatives Considered

## Reactive-Only Architecture

Rejected because it ignores valuable local context and prevents responsible
adaptation.

## AI-Only Context Detection

Rejected because deterministic system information is generally faster, more
private, predictable, and reliable for Version 1.

## Required Manual Context Selection

Rejected as the primary model because it creates unnecessary user friction.
Users still control enabled sources and may override supported platform
behavior through configuration.

---

# Related Components

- Context Engine.
- System Layer.
- Decision Engine.
- Core.
- Event Bus.
- Planner.
- Working Memory.
- Capability Runtime.

---

# Future Considerations

Future versions may add multi-context representation, calibrated confidence,
personalized models, or approved cross-device signals.

Future strategies must preserve Context Engine as an observer and single source
of context, with Core retaining lifecycle ownership and Decision Engine retaining
policy ownership.
