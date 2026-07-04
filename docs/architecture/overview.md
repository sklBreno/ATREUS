# Architecture Overview

![ATREUS Architecture](diagrams/architecture-v1.0.png)

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-07-02

---

# Overview

ATREUS is built as a modular, event-driven, context-aware personal intelligence platform.

The platform is organized into independent architectural components, each responsible for a single domain.

Instead of relying on a central AI model to perform every task, ATREUS coordinates specialized modules that collaborate through clearly defined interfaces.

This approach improves maintainability, scalability, reliability, and long-term evolution.

---

# High-Level Architecture

```text
                            USER
                              │
                              ▼
                    Request Classifier
                              │
                              ▼
                        ATREUS Core
                              │
 ┌──────────────┬─────────────┼──────────────┬──────────────┐
 ▼              ▼             ▼              ▼              ▼
Context     Decision      Planner        Memory      Skill Manager
 Engine       Engine
 │              │             │              │              │
 └───────┬──────┴─────────────┴──────────────┴───────┬──────┘
         ▼                                           ▼
     Event Bus                               Capability Registry
         │                                           │
         └────────────────────┬──────────────────────┘
                              ▼
                       System Layer
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
     Windows             AI Providers          External Services
```

---

# Architectural Principles

The platform follows several fundamental principles.

- Modular architecture.
- Context-aware computing.
- Event-driven communication.
- AI as a component, not the core.
- Privacy by design.
- Local-first whenever possible.
- User remains in control.
- Long-term maintainability.

These principles guide every architectural decision made throughout the project.

---

# Component Responsibilities

## Request Classifier

Receives every user interaction and determines its nature before execution.

Possible request types include commands, intentions, questions, conversations, and tasks.

---

## Core

Coordinates the platform.

The Core never performs business logic directly.

Its responsibility is orchestration.

---

## Context Engine

Maintains awareness of the user's current computing context.

Examples include:

- Working
- Studying
- Gaming
- Meeting
- Idle

Context influences nearly every decision made by the platform.

---

## Decision Engine

Determines how ATREUS should respond based on:

- Current context
- Request type
- User preferences
- Platform state

---

## Planner

Transforms high-level intentions into executable action plans.

---

## Memory

Stores knowledge, experiences, preferences, and conversation context.

Memory evolves continuously while respecting user privacy.

---

## Skill Manager

Discovers and executes available platform capabilities.

Skills remain completely independent from the Core.

---

## Capability Registry

Maintains a catalog of everything ATREUS is capable of doing.

Capabilities can be added without modifying existing modules.

---

## Event Bus

Allows modules to communicate through events instead of direct dependencies.

This minimizes coupling across the platform.

---

## System Layer

Provides access to operating system functionality.

Examples include:

- Files
- Processes
- Hardware
- Windows APIs
- Power management
- Networking

---

## AI Providers

Provide language models and reasoning capabilities when necessary.

ATREUS remains independent of any specific AI provider.

---

# Architectural Flow

Every interaction follows the same general lifecycle.

```text
User Request

↓

Request Classification

↓

Context Evaluation

↓

Decision Making

↓

Planning (if required)

↓

Skill Execution or AI Processing

↓

Memory Update

↓

Event Publication

↓

Response
```

---

# Why This Architecture?

This architecture was designed to satisfy several long-term objectives.

- Easy maintenance.
- Independent module evolution.
- Low coupling.
- High scalability.
- Efficient resource utilization.
- Future multi-device expansion.

Rather than optimizing for the first release, the architecture prioritizes long-term sustainability.

---

# Evolution Strategy

The architecture is intentionally modular.

New capabilities should be added by extending existing modules instead of modifying the Core.

Future versions may introduce new components while preserving the same architectural philosophy.

The architecture should evolve continuously without losing its identity.