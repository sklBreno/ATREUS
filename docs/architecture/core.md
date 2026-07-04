# Core

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-07-02

---

# Purpose

The Core is the central orchestration component of ATREUS.

Its responsibility is to coordinate the platform, route requests, initialize modules, and maintain the application's execution lifecycle.

The Core is not responsible for implementing business logic.

It delegates responsibilities to specialized components.

---

# Philosophy

The Core should remain small.

It should understand the platform.

It should never become the platform.

Every feature added directly to the Core increases coupling and reduces maintainability.

The Core exists to coordinate.

Nothing more.

---

# Responsibilities

The Core is responsible for:

- Initializing platform components.
- Managing the application lifecycle.
- Coordinating module communication.
- Routing requests.
- Maintaining platform state.
- Publishing system events.
- Handling graceful startup and shutdown.
- Monitoring module health.

The Core should never perform AI processing, memory management, context detection, or skill execution directly.

---

# Startup Sequence

During startup the Core performs the following steps.

1. Load configuration.

2. Initialize Event Bus.

3. Initialize Memory.

4. Initialize Context Engine.

5. Initialize Capability Registry.

6. Initialize Skill Manager.

7. Initialize Planner.

8. Initialize AI Providers.

9. Register platform services.

10. Start background monitoring.

11. Begin accepting user requests.

The initialization order should remain deterministic.

---

# Request Lifecycle

Every request follows the same lifecycle.

```text
User

↓

Request Classifier

↓

Core

↓

Decision Engine

↓

Planner (optional)

↓

Skill Manager / AI Provider

↓

Memory Update

↓

Event Bus

↓

Response
```

The Core coordinates this flow.

It does not execute the work itself.

---

# Module Coordination

The Core communicates with:

- Request Classifier
- Decision Engine
- Context Engine
- Planner
- Memory
- Skill Manager
- Capability Registry
- Event Bus
- AI Providers
- System Layer
- Configuration Manager

Every dependency should be abstracted through interfaces whenever possible.

---

# Event Coordination

The Core publishes important platform events.

Examples include:

- PlatformStarted
- PlatformStopped
- RequestReceived
- RequestCompleted
- ModuleInitialized
- ContextChanged
- ErrorOccurred

Modules should react to events rather than depending directly on one another.

---

# Error Handling

The Core should never crash because a module fails.

Whenever possible:

- isolate failures;
- restart recoverable modules;
- report errors through the Event Bus;
- preserve platform availability.

Platform resilience is considered a primary responsibility of the Core.

---

# Performance

The Core should remain lightweight.

Heavy computation must always be delegated.

The Core should spend most of its execution time coordinating rather than processing.

---

# Scalability

Future platform growth should not require modifications to the Core.

Adding a new module should require:

- registering the module;
- defining its interfaces;
- subscribing to the necessary events.

No additional orchestration logic should be necessary.

---

# Guiding Principles

The Core follows these principles.

- Orchestrate, never execute.
- Delegate responsibilities.
- Minimize coupling.
- Maximize stability.
- Keep business logic outside the Core.
- Remain predictable.
- Fail gracefully.
- Remain easy to understand.

---

# Future Evolution

Future versions of the Core may introduce:

- Distributed execution.
- Multi-device orchestration.
- Plugin loading.
- Dynamic module discovery.
- Health monitoring.
- Self-diagnostics.

These improvements should preserve the Core's primary responsibility as the platform orchestrator.
