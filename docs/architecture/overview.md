# Architecture Overview

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-08-17

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
                ▲                        │                         │
                │                        │                         ▼
          System Layer                   │              Capability Registry
                                         │                         ▲
                                         ▼                         │
                                  Capability Runtime ──────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                 Capability Code                  AI Provider
                         │
                         ▼
                    System Layer

Working Memory provides bounded process-local data where explicitly required.
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

Version 1 Memory is bounded, volatile Working Memory for the current process.

It may hold short-lived request, decision, plan, and execution context. It does
not implement Long-Term Memory, Knowledge, Experience Memory, persistent
conversation context, or learning in Version 1.

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

AI Provider credentials enter through approved environment or configuration
loading during bootstrap. They are injected into the selected concrete provider
adapter.

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
    ├── DELEGATE ──────────────> AI Provider or another explicit service
    ├── ASK_FOR_CONFIRMATION ──> User interaction boundary
    ├── SUGGEST ───────────────> User interaction boundary
    └── IGNORE ────────────────> No action

Core correlates results, uses Working Memory only when required, publishes
request lifecycle events, and returns the response.
```

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
- Working Memory owns memory-entry lifecycle events.
- Capability Registry owns catalog and availability events.
- Capability Runtime owns capability execution events.
- AI Provider owns AI request and availability events.
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
- Capability implementations may depend on narrow System Layer or AI Provider
  interfaces.
- Domain modules do not depend on Core.
- Core depends on module interfaces, not concrete implementations.

---

# Numeric Policies

Context stabilization, Working Memory capacity, planning limits, and execution
timeouts use configurable defaults supplied during future implementation.

This architecture intentionally does not define numeric values. Implementations
must not hardcode policy values that should come from validated configuration.

---

# Evolution Strategy

New behavior should be added through documented contracts and capability
implementations rather than by expanding Core responsibilities.

Future memory, provider, plugin, distributed, or multi-device behavior requires
separate architectural approval. Extensibility must not introduce speculative
complexity into Version 1.
