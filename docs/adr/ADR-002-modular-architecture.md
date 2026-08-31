# ADR-002 — Modular Architecture

**Status:** Accepted

**Date:** 2026-07-02

**Last Updated:** 2026-08-17

---

# Context

ATREUS is a long-term personal intelligence platform expected to evolve across
many capabilities, providers, and operating environments.

A tightly coupled architecture would make new behavior increasingly difficult
to implement, test, replace, and understand. An AI-centered architecture would
also make the platform dependent on one technology instead of its own stable
contracts.

---

# Decision

ATREUS adopts a modular monolith for Version 1.

Each module owns one domain and communicates through explicit interfaces,
immutable data contracts, or domain events. Modules depend on abstractions and
never on another module's internal implementation.

The Core coordinates lifecycle and workflow but does not execute domain work.

Major platform modules are:

- Configuration.
- Event Bus.
- Request Classifier.
- Core.
- Context Engine.
- Decision Engine.
- Planner.
- Working Memory.
- Capability Registry.
- Capability Runtime.
- AI Provider.
- System Layer.

Capability Registry describes what ATREUS can do. Capability Runtime is the
single component that loads and invokes capability implementations.

---

# Module Boundaries

## Core

Owns flow, lifecycle, operational state, and orchestration. It never owns
business execution.

## Domain Modules

Own classification, context, decisions, plans, working-memory data, capability
metadata, capability execution, AI integration, or system translation according
to their architecture documents.

## Event Bus

Owns event delivery only. Events communicate facts and do not hide required
workflow.

## Interfaces

Define stable behavior and types. Concrete implementations remain inside their
own modules and are supplied through dependency injection.

---

# Design Principles

## Single Responsibility

Every module has one clear purpose. Responsibilities must not overlap.

## Separation of Concerns

Decision, orchestration, planning, execution, storage, infrastructure, and
external integration remain distinct.

## Dependency Inversion

High-level modules depend on interfaces rather than concrete implementations.

## Low Coupling

Modules know only the contracts required for their work.

## High Cohesion

Components inside one module serve the same domain responsibility.

## Composition

Platform behavior is assembled through small components rather than deep
inheritance hierarchies.

## Replaceability

AI providers, capability implementations, memory stores, classification
strategies, system adapters, and other implementations can be replaced behind
stable interfaces.

## Extensibility

New capabilities extend Registry and Runtime without adding business logic to
Core. Extension must follow an approved need and must not introduce speculative
Version 1 complexity.

---

# Dependency Direction

Dependencies remain acyclic:

- Event Bus has no domain-module dependencies.
- Context Engine depends on System Layer abstractions.
- Planner depends on the read-only Capability Catalog.
- Capability Runtime depends on Capability Registry and AI availability.
- Capability implementations may depend on narrow System Layer or AI Provider
  interfaces.
- Domain modules never depend on Core.
- Core depends on module interfaces supplied during composition.

Events may cross these boundaries, but event publication does not reverse
interface ownership.

---

# Rationale

A modular monolith provides:

- Independent module evolution.
- Focused testing.
- Replaceable infrastructure and providers.
- Lower coupling and clearer ownership.
- Efficient local in-process operation for an Always-On platform.
- A path for future evolution without premature distribution.

---

# Consequences

Positive consequences:

- Better maintainability and onboarding.
- Easier isolated testing and dependency injection.
- Explicit ownership and failure boundaries.
- Reduced provider and operating-system coupling.
- Controlled extensibility.

Trade-offs:

- Interfaces and data contracts require deliberate design.
- Initial development includes more boundary definitions.
- Cross-module changes require coordinated contract review.
- Event use requires clear ownership to avoid hidden workflows.

---

# Alternatives Considered

## Tightly Coupled Monolith

Rejected because module internals would become difficult to replace and test.

## AI-Centered Architecture

Rejected because ATREUS must remain functional and provider-agnostic when AI is
unavailable.

## Distributed Service Architecture

Deferred. Version 1 is a local in-process modular monolith. Distribution may be
considered only when justified by approved multi-device requirements.

---

# Related Components

- All platform modules.
- Interface standards.
- Module development standards.
- Design principles.

---

# Future Considerations

Individual boundaries may evolve toward isolated processes or services only
after operational need, security, failure, and deployment architecture are
documented.

The current modular design must not be treated as permission to introduce
microservices, remote catalogs, cloud infrastructure, or dynamic plugins in
Version 1.
