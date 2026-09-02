# Decision Engine

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-09-01

---

# Purpose

The Decision Engine determines how ATREUS should respond to a classified
request or platform condition.

It converts explicit inputs into an immutable decision. It decides; it never
executes.

---

# Responsibilities

The Decision Engine is responsible for:

- Evaluating classified requests against current context and platform state.
- Evaluating platform conditions for desired operational-state changes.
- Determining the desired performance profile from approved inputs.
- Applying user-control, permission, confidence, and availability policy.
- Selecting one supported decision outcome.
- Identifying the intended target when an outcome requires one.
- Providing a stable reason code for transparency and diagnostics.
- Publishing the applicable Decision Engine-owned event after successful
  evaluation.

---

# Non-Responsibilities

The Decision Engine is not responsible for:

- Classifying requests.
- Executing capabilities.
- Invoking AI providers.
- Creating plans.
- Asking the user through an interface.
- Applying operational-state transitions or performance-profile changes.
- Reading operating-system state directly.
- Persisting decisions in Memory.
- Routing modules after the decision is returned.

The Core owns the next orchestration step.

---

# Request Decision Inputs

The engine accepts an immutable `DecisionInput` containing:

- `request`: Original normalized request reference and content.
- `classification`: `ClassifiedRequest` from the Request Classifier.
- `context`: Current `ContextSnapshot`.
- `memory`: Stable bounded `MemorySnapshot` captured for the request.
- `platform_state`: Current lifecycle, operational-state, and
  performance-profile snapshot.
- `user_policy`: Applicable user preferences, grants, and interruption policy.
- `candidate_capabilities`: Immutable metadata for relevant available
  capabilities, if any.
- `interpretation`: Optional locally validated `RequestInterpretation` supplied
  only for the second AI-assisted evaluation.

The Core assembles this input through module interfaces. The Decision Engine
does not query those modules directly. Version 0 decision policy receives but
does not interpret memory values.

Inputs must share the request correlation identifier and represent one coherent
point in the request lifecycle. Context and memory are the single snapshots
captured by Core for that request. Decision Engine does not query, refresh, or
persist either snapshot.

---

# Request Decision Outcomes

Version 1 supports:

- `EXECUTE`: Invoke one identified capability.
- `ASK_FOR_CONFIRMATION`: Obtain explicit user approval before continuing.
- `SUGGEST`: Offer an optional action without executing it.
- `IGNORE`: Take no action because policy or context makes intervention
  inappropriate.
- `DELEGATE`: Send the request to an identified non-capability service contract,
  such as `ai.request_interpreter`.
- `REQUEST_PLANNING`: Ask the Planner to transform a high-level goal into a
  plan.

An outcome describes the next orchestration step. It is not the step itself.

---

# Request Decision Outputs

The engine returns an immutable `Decision` containing:

- `request_id`: Correlated request identifier.
- `outcome`: One Version 1 decision outcome.
- `target`: Optional stable capability or service identifier required by the
  selected outcome.
- `reason_code`: Stable machine-readable explanation of the governing rule.

`EXECUTE` and `DELEGATE` require a target. `ASK_FOR_CONFIRMATION`, `SUGGEST`,
`IGNORE`, and `REQUEST_PLANNING` may omit a target when the Core can continue
using the original request.

Human-readable response text is not part of the Decision contract.

AI Provider V0 preserves two explicit evaluations. The first may return
`DELEGATE(ai.request_interpreter)` only when the deterministic path did not
resolve the request, the input is eligible for the bounded fallback, and no
suspicious or multi-action pattern is present. A validated interpretation is
provided explicitly in the second `DecisionInput`. The second evaluation never
delegates again and returns `ASK_FOR_CONFIRMATION` for a valid available and
permitted target. It never returns `EXECUTE` or `REQUEST_PLANNING` from the
interpretation.

---

# Platform Behavior Decisions

Operational state and performance profile are separate contracts.

The engine accepts an immutable `PlatformBehaviorDecisionInput` containing:

- `evaluation_id`: Unique identifier for the platform evaluation.
- `platform_state`: Current `PlatformStateSnapshot`, including operational state
  and active performance profile.
- `context`: Current `ContextSnapshot`.
- `system_signals`: Immutable approved System Layer observations.
- `configuration_policy`: Relevant validated configuration policy.
- `user_policy`: Applicable user preferences and restrictions.
- `trigger`: Stable reason code identifying why reevaluation was requested.

The engine returns an immutable `PlatformBehaviorDecision` containing:

- `evaluation_id`: Correlated platform evaluation identifier.
- `desired_operational_state`: One of `ACTIVE`, `PASSIVE`, or `STANDBY`.
- `operational_state_reason_code`: Stable explanation for the desired state.
- `desired_performance_profile`: One of `PERFORMANCE`, `BALANCED`, or `IDLE`.
- `performance_profile_reason_code`: Stable explanation for the desired profile.

Returning the current state or profile means no change is desired. Decision
Engine does not mutate platform state, pause modules, adjust module internals,
or publish Core-owned transition events.

Core compares the desired values with the current snapshot, validates permitted
transitions, applies approved changes, and publishes `OperationalStateChanged`
or `PerformanceProfileChanged` as appropriate.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class DecisionEngine(ABC):
    def decide(self, decision_input: DecisionInput) -> Decision: ...

    def decide_platform_behavior(
        self,
        decision_input: PlatformBehaviorDecisionInput,
    ) -> PlatformBehaviorDecision: ...
```

Implementations may compose small policy rules, but consumers depend only on
this interface.

---

# Request Decision Policy Order

Version 1 evaluates policy in deterministic precedence:

1. Validate input consistency.
2. Enforce explicit user restrictions and required permissions.
3. Evaluate safety and confirmation requirements.
4. Evaluate classification confidence.
5. Evaluate interruption policy from current context, operational state, and
   performance profile.
6. Evaluate candidate capability or service availability.
7. Determine whether the request requires planning.
8. Select the outcome and reason code.

For the V0 interpreter path, deterministic exact commands retain precedence.
Eligibility requires one approved application target, one bounded application
action, and no shell operators, command-injection markers, or additional
actions. After interpretation, Capability Catalog availability, user blocks,
permissions, and operational state remain authoritative before confirmation.

An earlier restrictive rule takes precedence over a later permissive rule.
Conflicting rules must not be resolved by arbitrary registration order.

---

# Platform Behavior Policy Order

Version 1 platform reevaluation follows deterministic precedence:

1. Validate input consistency and signal availability.
2. Enforce explicit user configuration and restrictions.
3. Evaluate lifecycle constraints for the desired operational state.
4. Evaluate context and system pressure for the desired performance profile.
5. Return both desired values and stable reason codes.

No individual context or System Layer signal applies a change directly. Numeric
thresholds remain injected configuration policy and are not defined here.

---

# Internal Flow

```text
DecisionInput
    │
    ▼
Input Consistency Validation
    │
    ▼
User Control and Permission Policy
    │
    ▼
Context, Confidence, and Availability Policy
    │
    ▼
Outcome Selection
    │
    ▼
Immutable Decision
```

Version 1 decision policy should be deterministic. AI is not required to make
platform control decisions.

Decision Engine does not invoke AI. It decides whether Core may delegate to the
Request Interpreter and later evaluates the validated result as untrusted,
non-executable input.

Platform behavior evaluation uses the same separation:

```text
PlatformBehaviorDecisionInput
    │
    ▼
Input and User-Policy Validation
    │
    ▼
Operational-State and Performance-Profile Policy
    │
    ▼
Immutable PlatformBehaviorDecision
    │
    ▼
Core validates and applies approved changes
```

---

# Dependencies

The Decision Engine depends on:

- Immutable request, classification, context, system-signal,
  memory-snapshot, configuration-policy, platform-state, user-policy, and
  capability metadata contracts.
- Optionally, the `EventBus` abstraction for domain event publication.

It does not depend directly on Core, Request Classifier, Context Engine,
Planner, `MemoryStore`, Capability Runtime, System Layer, or a concrete AI
provider. It consumes only the immutable `MemorySnapshot` data contract.

---

# Events

The Decision Engine owns:

## `DecisionMade`

Published after a successful decision.

Fields:

- Common event metadata.
- `request_id`.
- `outcome`.
- `target` when present.
- `reason_code`.

The event must not contain raw request content, user secrets, or capability
arguments.

## `PlatformBehaviorDecisionMade`

Published after successful platform behavior evaluation.

Fields:

- Common event metadata.
- `evaluation_id`.
- Desired operational state and its reason code.
- Desired performance profile and its reason code.

This event reports the Decision Engine result. It does not report that a change
was applied. Core-owned transition events remain authoritative for applied
state and profile changes.

---

# Error Handling

The module defines a `DecisionEngineException` base error with explicit errors
for inconsistent input, unsupported outcomes, and policy evaluation failure.

Invalid or incomplete input must not produce an optimistic `EXECUTE` decision.
When valid input is ambiguous, the engine should return
`ASK_FOR_CONFIRMATION` with an appropriate reason code instead of raising an
error.

---

# Testing Requirements

Tests must cover:

- Every Version 1 outcome.
- Policy precedence.
- Low classification confidence.
- Missing permissions.
- User restrictions.
- Context-sensitive interruption behavior.
- Performance and standby restrictions.
- Unavailable capabilities and services.
- Requests that do and do not require planning.
- Every operational state as a desired outcome.
- Every performance profile as a desired outcome.
- Independent state and profile decisions from the same input.
- Preservation of current values when no change is desired.
- Confirmation that Core-owned transitions are not applied or published.
- Invalid and inconsistent input.
- Decision and event immutability.
- Deterministic outcomes for identical inputs.
- Absence of execution side effects.

---

# Performance Considerations

The Decision Engine is on the critical path of requests and context-triggered
reevaluation. Policy evaluation must be local, bounded, and deterministic.

It must not perform network calls, operating-system queries, capability
execution, or unbounded searches. Candidate data is prepared by the Core before
the call.

---

# Security and Privacy Considerations

User restrictions and permission policy always take precedence over convenience
or proactivity.

Reason codes must explain decisions without exposing request content or private
context details. The engine must not persist its inputs. Proactive suggestions
must respect interruption policy and remain optional.

---

# Future Evolution

Future versions may add learned policy ranking, richer confidence handling, or
personalized decision strategies. Such changes must remain behind the stable
interface and must not bypass explicit user-control rules.

AI-assisted policy may be considered only after deterministic safety and
permission policy remains authoritative.

---

# Architectural Considerations

The Decision Engine owns decision logic, while the Core owns orchestration and
other modules own execution. Keeping `DecisionInput` complete prevents hidden
dependencies and circular calls.

A decision is explicit data that can be tested, logged safely through reason
codes, and reviewed before any side effect occurs.
