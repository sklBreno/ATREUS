# ATREUS Design Principles

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-17

---

# Purpose

This document consolidates the design principles already adopted by ATREUS.

These principles guide architecture, implementation, testing, and review. They
do not replace module architecture documents or authorize undocumented
features.

---

# SOLID

ATREUS applies SOLID principles to preserve clear ownership and replaceable
components.

## Single Responsibility Principle

Every module, class, and function has one clear reason to change.

Classification, orchestration, context, decision, planning, memory, capability
metadata, capability execution, configuration, infrastructure, and external
integration remain separate responsibilities.

## Open/Closed Principle

New behavior should extend stable contracts and capability composition instead
of repeatedly modifying Core or unrelated modules.

Extension is justified only by current documented requirements.

## Liskov Substitution Principle

Implementations must preserve the behavior, errors, and invariants defined by
their interfaces. Replacing a provider, store, adapter, or strategy must not
surprise consumers.

## Interface Segregation Principle

Consumers depend on the smallest interface needed for their responsibility.

System Layer uses separate process, filesystem, system-information,
application, and power contracts instead of one unrestricted object.

## Dependency Inversion Principle

High-level policy and orchestration depend on abstractions. Concrete
implementations are composed and injected during bootstrap.

Core and domain modules must not locate global services or instantiate external
infrastructure internally.

---

# Separation of Concerns

Each concern remains in its documented boundary:

- Core orchestrates.
- Request Classifier classifies.
- Context Engine observes context.
- Decision Engine decides.
- Planner creates plan data.
- Capability Registry describes capabilities.
- Capability Runtime executes capabilities.
- Working Memory stores bounded temporary data.
- Event Bus delivers facts.
- System Layer translates operating-system operations.
- AI Provider isolates AI integration.
- Configuration supplies validated settings.

One module must not absorb another module's responsibility for convenience.

---

# Explicit Contracts

Interfaces define behavior. Immutable models define data exchanged between
modules. Explicit exceptions define failure boundaries.

Contracts must specify:

- Inputs and outputs.
- Ownership and mutability.
- Error behavior.
- Side effects.
- Security and privacy constraints.
- Version 1 limitations.

Required workflow remains visible through direct interface calls. Events must
not hide control flow.

---

# Low Coupling

Modules know as little as possible about one another.

They depend on stable interfaces, immutable contracts, or domain events rather
than implementation details. Domain modules never depend on Core, and Event Bus
never depends on domain modules.

---

# High Cohesion

Components grouped inside one module serve the same domain purpose.

Infrastructure, persistence, configuration, external providers, and business
behavior must not be mixed in one class merely because they are used together.

---

# Composition Over Inheritance

ATREUS builds behavior by composing focused components through dependency
injection.

Inheritance is appropriate for explicit interface contracts. Deep inheritance
hierarchies and shared base classes containing unrelated behavior should be
avoided.

---

# Event-Driven Communication

Events represent immutable facts owned by the module that produced the state
change.

Event Bus delivers those facts and isolates subscriber failures. It is not a
workflow engine, scheduler, or substitute for explicit module interfaces.

Version 1 favors local synchronous delivery and must not introduce distributed
messaging without an approved need.

---

# Local-First Where Appropriate

ATREUS prefers local deterministic processing when it satisfies the user's
need.

Local-first improves privacy, latency, availability, and user control. External
AI or services remain optional replaceable components and receive only the
minimum approved data.

Local-first does not prohibit future external integration. It requires that
external dependency be justified and explicit.

---

# User Control

The user remains authoritative over configuration, permissions, monitored
context sources, proactive behavior, startup behavior, and side effects.

Automation must remain transparent and predictable. Ambiguous or sensitive
operations prefer explicit confirmation over hidden action.

Version 1 permission grants come from validated user configuration. Capability
Runtime verifies them before execution, and System Layer enforces them at the
operating-system boundary.

---

# Privacy by Design

Privacy is an architectural constraint, not a later feature.

ATREUS applies:

- Data minimization.
- Explicit purpose and ownership.
- Bounded retention.
- Sensitive-data exclusion from events and logs.
- No hardcoded credentials.
- No hidden context collection.
- User-controlled deletion where memory exists.

AI credentials enter through approved environment or configuration loading,
are injected into the provider adapter, and are never persisted or logged by
AI Provider.

---

# Simplicity

Version 1 uses the smallest architecture that satisfies approved requirements.

Avoid:

- Speculative modules.
- Premature distributed systems.
- Unnecessary dependencies.
- Generic abstractions without a current consumer.
- Hidden framework behavior.
- Numeric policy values without validated configuration ownership.

Readable and explicit design is preferred over clever design.

---

# Testability

Every component should support isolated deterministic testing.

ATREUS favors:

- Dependency injection.
- Immutable inputs and outputs.
- Explicit clocks, policies, and providers where time or environment matters.
- Fake interfaces instead of real external systems in unit tests.
- Contract tests for replaceable implementations.
- Bounded operations and predictable failure behavior.

Tests must not depend on the developer's real environment, credentials, or
operating-system state unless an isolated integration test explicitly requires
it.

---

# Extensibility Without Speculative Complexity

ATREUS is designed to evolve, but future possibilities do not justify present
complexity.

Extensibility means:

- Stable public contracts.
- Replaceable implementations.
- Capability metadata and Runtime loading boundaries.
- Documented additions that preserve ownership.
- Migration paths when contracts genuinely need to change.

It does not mean implementing unused plugin systems, cloud infrastructure,
microservices, persistent memory, or provider fallback before they are required.

---

# Review Questions

Every architecture or implementation review should ask:

1. Does each component have one documented responsibility?
2. Do dependencies point toward abstractions?
3. Is required workflow explicit?
4. Is event ownership clear?
5. Can implementations be replaced and tested in isolation?
6. Does the design preserve user control and privacy?
7. Is the solution local and deterministic where appropriate?
8. Does the change add only complexity justified by the current requirement?
9. Are failures explicit, isolated, and safe to diagnose?
10. Does the design keep Core responsible for flow rather than work?

---

# Final Principle

ATREUS should remain understandable as it grows.

Maintainability, consistency, testability, privacy, and user control take
priority over short-term convenience.
