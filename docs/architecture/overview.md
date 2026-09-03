# Architecture Overview

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-09-02

---

# Overview

ATREUS is a modular, event-driven, context-aware personal intelligence
platform.

The platform coordinates specialized modules through explicit interfaces and
immutable data contracts. AI is one replaceable component and is not the center
of the architecture.

The Core owns the flow, never the work.

---

# High-Level Architecture

```text
User Request
    │
    ▼
Request Classifier ──classification──> Core
                                         │
                ┌────────────────────────┼─────────────────────────┐
                │                        │                         │
                ▼                        ▼                         ▼
         Context Engine           Decision Engine              Planner
                ▲                    │       ▲                      │
                │                    │       │ validated            ▼
          System Layer              │       │ interpretation  Capability Registry
                                    ▼       │                      ▲
                             Request Interpreter                  │
                                    │                             │
                                    ▼                             │
                                AI Provider              Capability Runtime
                                                                  │
                                                                  ▼
                                                           Capability Code
                                                                  │
                                                                  ▼
                                                             System Layer

Working Memory provides bounded process-local snapshots where explicitly
required.
Conversation Responder provides bounded text through AI Provider and owns access
to a separate process-local Conversation History. Neither boundary enters
Planner, Capability Runtime, or System Layer.
Configuration provides validated settings during bootstrap.
Domain modules publish immutable facts through the Event Bus.
```

Required workflow uses direct interface calls coordinated by the Core. The
Event Bus distributes facts to interested subscribers and does not replace
explicit control flow.

Version 1 is a local in-process modular monolith. It does not require
microservices, distributed messaging, or cloud infrastructure.

---

# Architectural Principles

The platform follows these principles:

- Modular architecture.
- SOLID and Separation of Concerns.
- Dependency Inversion through explicit interfaces.
- Low coupling and high cohesion.
- Composition over inheritance.
- Event-driven communication for domain facts.
- Context as a first-class concept.
- AI as a replaceable component, not the Core.
- Privacy by design.
- Local-first execution when appropriate.
- User control and predictable behavior.
- Simplicity, testability, and long-term maintainability.

These principles are expanded in `docs/design-principles.md`.

---

# Component Responsibilities

## Bootstrap and Configuration

Bootstrap creates the first functional runtime boundary. It loads validated,
immutable configuration through Configuration Manager and composes concrete
implementations behind their interfaces.

No other module reads environment variables or configuration files directly.

---

## Request Classifier

The Request Classifier identifies whether a request is a command, intention,
question, conversation, or task. It returns the request type and confidence.

It does not route or execute the request. The Core owns routing and flow.

---

## Core

The Core orchestrates startup, shutdown, requests, module lifecycle, platform
state, and performance-profile propagation.

It owns the operational state and applies approved state transitions. It never
performs classification, context detection, decision logic, planning, memory
storage, AI processing, or capability execution.

---

## Context Engine

The Context Engine consumes approved signals and maintains the current context,
such as `WORKING`, `STUDYING`, `GAMING`, `MEETING`, `ENTERTAINMENT`, `IDLE`, or
`UNKNOWN`.

It owns `ContextChanged` and provides situational awareness. It does not switch
operational states, change performance profiles, or execute actions.

---

## Decision Engine

The Decision Engine evaluates requests or platform conditions using current
context, configuration, system signals, user policy, operational state,
performance profile, and capability availability.

For requests, it returns outcomes such as execute, ask for confirmation,
suggest, ignore, delegate, or request planning. For lifecycle evaluation, it
determines the desired operational-state transition and performance profile.

It decides but does not apply or execute the result.

---

## Planner

The Planner transforms a high-level goal into an explicit immutable plan made
of ordered capability invocations.

Version 1 plans are finite and sequential. The Planner validates capability
metadata and permissions but does not execute plans or grant permissions.

---

## Working Memory

Version 0 Memory is bounded, volatile Working Memory for one composed process.
Its defaults are 64 entries with a fixed 1800-second lifetime, supplied through
validated Configuration. A new composition or process restart begins empty.

Core captures one immutable `MemorySnapshot` per request and reuses it in
Decision Engine and Planner inputs. Capability Runtime does not know about
Memory. Version 0 has no automatic producers, persistence, Long-Term Memory,
Knowledge Memory, Experience Memory, conversation history, or learning.

Short-Term Conversation History V1 is a separate bounded process-local store of
complete successful dialogue exchanges. It is available only to Conversation
Responder and is never projected into Working Memory or the operational
pipeline.

---

## Capability Registry

Capability Registry is the authoritative catalog of capability metadata.

It describes identifier, name, description, permissions, availability,
dependencies, and whether AI is required. It never loads or executes capability
implementations.

---

## Capability Runtime

Capability Runtime is the only component that loads and invokes capability
implementations.

It resolves capabilities through Registry metadata, validates user-configured
permission grants, enforces availability and deadlines, isolates failures, and
returns immutable execution results.

---

## Event Bus

Event Bus delivers immutable in-process events to subscribers.

Version 1 publication is synchronous and isolates subscriber failures. The
module that owns a state transition owns and publishes the corresponding event.
Event Bus owns delivery only.

---

## System Layer

System Layer provides controlled abstractions for processes, files, system
information, applications, and power state.

It normalizes operating-system behavior and enforces permissions at the system
boundary. It contains no user workflow or business logic.

---

## AI Provider

AI Provider is a provider-neutral abstraction for bounded language-model
processing when deterministic capabilities are insufficient.

Concrete providers are replaceable. ATREUS must continue operating in a reduced
but predictable mode when AI is unavailable.

V0 supports explicit selection of one OpenAI cloud adapter or one local Ollama
HTTP adapter per runtime composition. Ollama uses no API key, disables thinking
output, and is restricted to a configured local endpoint. There is no runtime
switching, automatic provider fallback, or AI Router.

AI Provider is used through `RequestInterpreter` for strict structured
interpretation of approved `OPEN_APPLICATION` and `APPLICATION_STATUS` intents,
and through `ConversationResponder` for bounded contextual text. Deterministic
application-open commands remain local and make no AI request. Provider output
is untrusted and returns to local validation before a typed `ApplicationAction`
reaches Decision Engine. Conversational output is non-executable and goes only
to the foreground interface. AI never authorizes, plans, or executes a
capability.

## Conversational AI

Conversational AI V1 answers eligible questions and conversation in Brazilian
Portuguese or English. Stable identity, capability, unsupported-capability, and
secret-refusal responses are deterministic. General responses use one bounded
AI request with complete prior conversational exchanges, no tools, Context,
Working Memory, web, filesystem, or execution access. Exact bilingual clear
requests remove only the current process-local Conversation History.

## Interactive Confirmation

Interactive Confirmation V0 owns one expiring, single-use, process-local
authorization slot per runtime composition. It supports only validated
AI-originated `OPEN_APPLICATION` actions. PT-BR is the default interaction
language, English is secondary, and ambiguous language resolves to PT-BR.

Core coordinates the confirmation flow through an injected coordinator. The
foreground interface renders a structured prompt from approved identifiers.
An exact acceptance returns to Decision Engine, then Planner receives a typed
approved action. Capability Runtime and System Layer remain independent and
retain their existing enforcement responsibilities. Working Memory does not
store confirmation state, and V0 publishes no confirmation-specific events.

Natural Language Actions V1 also supports read-only `APPLICATION_STATUS`
requests through `application.status`. Status actions do not require
confirmation. The local typed action matrix, not AI, selects capability
identifiers and rejects unsupported combinations such as Spotify status.

---

# Operational State

Operational state represents platform lifecycle behavior:

- `ACTIVE`: Full platform operation is enabled.
- `PASSIVE`: The platform remains available with lightweight monitoring.
- `STANDBY`: Only essential services remain active and resource use is
  minimized.

The Core owns the current operational state because it owns lifecycle and
orchestration.

Transition responsibility is separated:

1. System Layer provides current system signals.
2. Context Engine provides the current context.
3. Decision Engine may determine a desired transition.
4. Core validates and applies the transition.
5. Core publishes `OperationalStateChanged`.

Context Engine never applies a state transition by itself.

---

# Performance Profiles

Performance profile is separate from operational state:

- `PERFORMANCE`: Minimize non-essential work during demanding activity.
- `BALANCED`: Normal monitoring and responsiveness.
- `IDLE`: Allow eligible deferred and maintenance work when resources permit.

Decision Engine determines the desired profile from context, validated
configuration, user policy, and System Layer signals. Core records and
propagates the active profile. Every module must respect the active profile.

An `IDLE` performance profile is not the same concept as the Context Engine's
`IDLE` user context.

Version 1 does not introduce a separate presence or performance-management
module.

---

# Permissions

Version 1 permission grants come from validated user configuration.

Capability Registry declares required permission identifiers. Core includes the
configured grants in decision and invocation data. Capability Runtime verifies
those grants before execution, and System Layer enforces them again at the
operating-system boundary.

Version 1 does not include an interactive permission-grant system.

---

# AI Credentials

The OpenAI adapter reads `ATREUS_OPENAI_API_KEY` only from the process
environment during bootstrap. It is injected into that concrete provider
adapter. The local Ollama adapter requires no credential.

Credentials are never hardcoded, persisted by AI Provider, included in public
configuration snapshots, or written to logs, events, errors, requests, or
responses.

Core and consumers receive only the `AIProvider` abstraction.

---

# Request Flow

```text
User Request
    │
    ▼
Request Classifier
    │ classification
    ▼
Core
    │ assembles context, state, policy, and capability metadata
    ▼
Decision Engine
    │
    ├── EXECUTE ───────────────> Capability Runtime
    ├── REQUEST_PLANNING ──────> Planner ──> Core ──> Capability Runtime
    ├── DELEGATE ──────────────> Request Interpreter
    │                                │ one bounded structured AI request
    │                                ▼
    │                           AI Provider
    │                                │ validated interpretation
    │                                ▼
    │                    Core ──> Decision Engine
    │                                ├── ASK_FOR_CONFIRMATION for OPEN
    │                                └── REQUEST_PLANNING for STATUS
    ├── DELEGATE ──────────────> Conversation Responder
    │                                │ bounded Conversation History
    │                                │ local self-knowledge or one bounded
    │                                │ plain-text AI request
    │                                ▼
    │                         User-facing text only
    ├── ASK_FOR_CONFIRMATION ──> Confirmation Coordinator
    │                                │ structured prompt and later exact input
    │                                ▼
    │                    Core ──> Decision Engine
    │                                └── REQUEST_PLANNING after acceptance
    ├── SUGGEST ───────────────> User interaction boundary
    └── IGNORE ────────────────> No action

Core correlates results, captures one stable Working Memory snapshot, publishes
request lifecycle events, and returns the response.
```

One immutable `ApplicationAction` is preserved through interpretation,
Decision Engine, confirmation when required, and Planner. Capability Runtime
remains generic, while application launch and state observation stay behind
narrow System Layer interfaces.

Classification never selects or invokes the destination. Planner never invokes
capabilities. Capability Runtime never decides the next workflow step.

---

# Event Ownership

Event ownership follows the state owner:

- Core owns platform lifecycle, operational state, performance profile, and
  request lifecycle events.
- Context Engine owns context events, including `ContextChanged`.
- Request Classifier owns `RequestClassified`.
- Decision Engine owns `DecisionMade`.
- Planner owns `PlanCreated`.
- Working Memory V0 publishes no events.
- Conversation History V1 publishes no events.
- Capability Registry owns catalog and availability events.
- Capability Runtime owns capability execution events.
- AI Provider owns AI request and availability events.
- Interactive Confirmation V0 publishes no domain events.
- System Layer owns approved operating-system observation events.

Core reacts to domain events but does not republish them under the same meaning.

---

# Dependency Direction

Dependencies point toward abstractions and remain acyclic:

- Event Bus has no domain-module dependencies.
- Context Engine depends on System Layer abstractions and Event Bus.
- Planner depends on the read-only Capability Catalog and Event Bus.
- Capability Runtime depends on Capability Registry, AI availability, and Event
  Bus.
- Request Interpreter depends on AI Provider and the read-only Capability
  Catalog.
- Conversation Responder depends on AI Provider and the read-only Capability
  Catalog, plus its private Conversation History boundary.
- Capability implementations may depend on narrow System Layer or AI Provider
  interfaces.
- Domain modules do not depend on Core.
- Core depends on module interfaces, not concrete implementations.

---

# Numeric Policies

Working Memory V0 uses configurable defaults of 64 entries and 1800 seconds per
entry. Conversation History V1 uses configurable defaults of six complete
exchanges and 12,000 characters. Context stabilization, planning limits, and
execution timeouts continue to use validated configurable policies when
implemented.

Modules must not hardcode values that belong to validated configuration policy.

---

# Evolution Strategy

New behavior should be added through documented contracts and capability
implementations rather than by expanding Core responsibilities.

Future memory, provider, plugin, distributed, or multi-device behavior requires
separate architectural approval. Extensibility must not introduce speculative
complexity into Version 1.
