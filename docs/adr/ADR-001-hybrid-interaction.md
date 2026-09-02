# ADR-001 — Hybrid Interaction Model

**Status:** Accepted

**Date:** 2026-07-02

**Last Updated:** 2026-09-02

---

# Context

ATREUS must support efficient deterministic requests as well as natural,
high-level interaction.

Command-only systems are too restrictive. AI-only systems add unnecessary
latency, cost, privacy exposure, and provider dependency. A single interaction
category cannot represent direct commands, broad intentions, questions,
conversations, and constrained tasks accurately.

---

# Decision

ATREUS adopts a hybrid interaction model.

Every user request is classified before the Core determines the next
orchestration step.

Version 1 request types are:

- `COMMAND`.
- `INTENTION`.
- `QUESTION`.
- `TASK`.
- `CONVERSATION`.

The Request Classifier identifies request type and confidence. It does not
select a destination, route execution, create a plan, answer the request, or
invoke a capability.

The Core owns routing. It assembles current context, platform state, user
policy, configuration, and capability metadata for the Decision Engine. The
Decision Engine returns an explicit outcome, and the Core applies that outcome
through the appropriate interface.

Bounded AI request interpretation preserves this ownership. When an approved
application request is not resolved by the deterministic fast path, Decision
Engine may return `DELEGATE(ai.request_interpreter)`. Core invokes that bounded
service at most once and submits its locally validated, non-executable
interpretation to a second Decision Engine evaluation. A valid
`OPEN_APPLICATION` interpretation requires user confirmation. A valid
read-only `APPLICATION_STATUS` interpretation may request planning directly.
Neither interpretation directly invokes Planner, Capability Runtime, or System
Layer.

Interactive Confirmation V0 completes that user-control path with one
process-local, expiring, single-use pending action. ATREUS is PT-BR first and
supports English as the secondary interaction language; ambiguous interaction
language defaults to PT-BR. Language selection and exact yes/no parsing are
deterministic and do not use AI.

An accepted response is a new request and returns to Decision Engine. The
Decision Engine revalidates current policy and returns `REQUEST_PLANNING`, never
direct execution. Planner receives a typed approved action rather than raw AI
output or confirmation text. Capability Runtime and System Layer retain
authoritative enforcement, and confirmation never creates a permission grant.

---

# Interaction Examples

## Command

> "Open Visual Studio Code."

```text
Request Classifier: COMMAND
    ↓
Core
    ↓
Decision Engine: EXECUTE
    ↓
Capability Runtime
```

A direct command may use a deterministic capability without AI.

---

## Intention

> "Let's work on ATREUS."

```text
Request Classifier: INTENTION
    ↓
Core
    ↓
Decision Engine: REQUEST_PLANNING
    ↓
Planner
    ↓
Core coordinates approved PlanStep objects through Capability Runtime
```

The Planner creates data. It does not execute the plan.

---

## Question

> "What is Active Directory?"

```text
Request Classifier: QUESTION
    ↓
Core
    ↓
Decision Engine: DELEGATE or EXECUTE
    ↓
AI Provider or a deterministic information capability
```

AI is used only when it adds value and an approved provider is available.

V1 does not implement free-form answers or conversation. Its only AI purpose is
strict structured interpretation of `OPEN_APPLICATION` and
`APPLICATION_STATUS` with an already approved application target. Local policy
maps that output to a capability. Deterministic commands such as
`open calculator` and `open notepad` do not call AI.

---

## Task

> "Remind me tomorrow at 8 AM."

```text
Request Classifier: TASK
    ↓
Core
    ↓
Decision Engine: REQUEST_PLANNING or ASK_FOR_CONFIRMATION
    ↓
Planner when the task is supported by available capabilities
```

`TASK` is a classification category. It does not imply a dedicated scheduling
module in Version 1. Unsupported timing behavior must be reported explicitly.

---

## Conversation

> "Good morning."

```text
Request Classifier: CONVERSATION
    ↓
Core
    ↓
Decision Engine
    ↓
Deterministic response capability, AI Provider, or no action
```

`CONVERSATION` does not require a dedicated conversation module in Version 1.
AI Provider V0 does not implement this conversational route.

---

# Automatic Classification

The user does not specify the request type manually.

Request Classifier returns one supported type and confidence. Ambiguous input
remains explicit through low confidence so Decision Engine can choose
`ASK_FOR_CONFIRMATION` instead of allowing the classifier to guess a workflow.

---

# Rationale

The hybrid model provides:

- Fast deterministic execution for clear commands.
- Explicit planning for supported high-level goals.
- Optional AI use for requests that benefit from it.
- Mandatory confirmation before any AI-interpreted side effect.
- Direct planning for locally validated read-only AI interpretations.
- Single-use explicit user control with safe rejection, invalidation,
  expiration, and replay behavior.
- Separate handling for constrained tasks and conversations.
- Reduced dependency on language models.
- Clear ownership between classification, decision, orchestration, planning,
  and execution.

---

# Consequences

Positive consequences:

- Lower latency for deterministic operations.
- Reduced AI dependency and external data exposure.
- Better modularity and testability.
- Explicit handling of ambiguity through confidence.
- New request types can be introduced through documented contract changes.

Trade-offs:

- Classification becomes a critical request-path component.
- Incorrect classifications can influence later decisions.
- Core and Decision Engine must handle low-confidence results predictably.
- Adding a request type requires coordinated policy and test updates.

---

# Alternatives Considered

## Command-Only Architecture

Rejected because it cannot support natural intentions, questions, or responsible
proactivity.

## AI-Only Architecture

Rejected because it introduces unnecessary latency, cost, privacy exposure, and
provider dependency.

## Intent-Only Architecture

Rejected because direct commands, questions, tasks, and conversations have
different semantics and orchestration needs.

---

# Related Components

- Request Classifier.
- Core.
- Decision Engine.
- Planner.
- Capability Registry.
- Capability Runtime.
- AI Provider.
- Event Bus.

---

# Future Considerations

New request types require explicit architecture, Decision Engine policy, Core
orchestration behavior, and contract tests.

Possible future categories such as system events or automation triggers must not
be added to Version 1 implicitly.
