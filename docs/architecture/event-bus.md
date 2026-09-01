# Event Bus

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-09-01

---

# Purpose

The Event Bus provides in-process event publication and subscription for the
ATREUS platform.

It allows modules to announce facts without depending on the concrete
implementations of interested consumers. It is a communication mechanism, not
a workflow engine. The Core continues to own orchestration and invokes required
operations through explicit interfaces.

---

# Responsibilities

The Event Bus is responsible for:

- Registering event subscriptions.
- Removing event subscriptions.
- Publishing immutable events to matching subscribers.
- Delivering events synchronously in Version 1.
- Isolating subscriber failures.
- Returning a deterministic publication result to the publisher.
- Preserving subscription order during delivery.

---

# Non-Responsibilities

The Event Bus is not responsible for:

- Deciding platform behavior.
- Routing user requests through the application lifecycle.
- Executing capabilities.
- Retrying failed business operations.
- Persisting or replaying events.
- Scheduling work.
- Distributed messaging.
- Inter-process or network communication.

Version 1 must not introduce a message broker, queue server, event store, or
distributed transport.

---

# Architecture

```text
Domain Module
    │
    │ publish(event)
    ▼
Event Bus
    │
    ├── Subscriber A
    ├── Subscriber B
    └── Subscriber C
```

Publishers and subscribers depend on the `EventBus` abstraction. The Event Bus
does not depend on domain modules and does not interpret event payloads.

---

# Events

Every event is an immutable data object with the following common metadata:

- `event_id`: Unique identifier for the event instance.
- `occurred_at`: UTC timestamp representing when the fact occurred.
- `source`: Stable identifier of the module that owns the event.
- `correlation_id`: Optional identifier connecting events from one platform
  operation.

Concrete event types define explicit, typed fields for their domain payload.
Events must not expose mutable dictionaries as their public contract.

An event describes something that has already happened. Event names therefore
use past-tense facts such as `ContextChanged`, `PlanCreated`, or
`CapabilityExecutionFailed`.

---

# Event Ownership

The module that owns the state transition owns the event type and publishes the
event.

Examples:

- The Core owns platform lifecycle and request lifecycle events.
- The Runtime Host owns foreground process lifecycle events:
  `RuntimeStarting`, `RuntimeStarted`, `RuntimeStopping`, `RuntimeStopped`, and
  `RuntimeFailed`.
- The Context Engine owns `ContextChanged`.
- The Planner owns `PlanCreated`.
- The Capability Runtime owns capability execution events.

The Core must not republish a domain event under the same meaning. Consumers
that need the event subscribe to its owner through the Event Bus abstraction.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class EventBus(ABC):
    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> Subscription: ...

    def unsubscribe(self, subscription: Subscription) -> None: ...

    def publish(self, event: Event) -> PublicationResult: ...
```

`EventHandler` accepts one event and returns `None`.

`Subscription` is an opaque immutable handle owned by the subscriber. It is
used to remove exactly one registration.

`PublicationResult` is immutable and contains:

- `delivered_count`: Number of handlers that completed successfully.
- `failures`: Ordered collection of `SubscriberFailure` records.

`SubscriberFailure` identifies the subscription and contains a sanitized error
description. It must not expose mutable exception state across module
boundaries.

---

# Internal Flow

## Synchronous Behavior

Version 1 uses synchronous, in-process publication.

When `publish` is called:

1. The Event Bus takes a stable snapshot of matching subscriptions.
2. Handlers are invoked in registration order.
3. The publisher waits until every matching handler has completed or failed.
4. Failures are collected without stopping later handlers.
5. A `PublicationResult` is returned.

Version 1 matches subscriptions by exact concrete event type. A subscription to
a base event class does not implicitly receive subtype instances.

Events published from inside a handler are separate publications. Modules must
avoid event cycles; the Event Bus does not detect business-level recursion.

Asynchronous publication may be introduced later behind a separate explicit
contract. Version 1 must not silently dispatch handlers in background threads.

---

# Failure Isolation

A subscriber exception must never prevent other subscribers from receiving the
event.

Subscriber failures are captured in `PublicationResult` and reported through
the logging infrastructure. The Event Bus must not publish another event while
handling its own subscriber failure because that can create recursive failure
loops.

Failures in the Event Bus itself, such as an invalid subscription or invalid
event object, raise an explicit `EventBusException` subtype.

---

# Interaction With Core

The Core initializes the Event Bus before modules that publish or subscribe to
events. It provides the `EventBus` abstraction through dependency injection.

The Core publishes only events for state it owns, including:

- `PlatformStarted`
- `PlatformStopped`
- `RequestReceived`
- `RequestCompleted`
- `ModuleInitialized`
- `ErrorOccurred`

The Event Bus does not choose the next request-processing step. Required flow
remains explicit:

```text
Core ──calls──> Module Interface
Module ──publishes fact──> Event Bus ──notifies──> Subscribers
```

---

# Dependencies

The Event Bus has no dependencies on other ATREUS modules.

Publishers and subscribers depend only on its interface and immutable event
contracts.

---

# Error Handling

Version 1 must define explicit errors for:

- Invalid event publication.
- Invalid handler registration.
- Unknown subscription removal.
- Internal bus failure.

Removing an already removed subscription should be deterministic and must not
silently remove another registration.

---

# Testing Requirements

Tests must cover:

- Publication to zero, one, and multiple subscribers.
- Delivery in registration order.
- Subscription removal.
- Exact event-type matching rules.
- Event immutability.
- Subscriber failure isolation.
- Publication result contents.
- Nested publication behavior.
- Concurrent reads of subscription state when applicable.
- Absence of hidden asynchronous execution.

---

# Performance Considerations

Event publication must remain lightweight because ATREUS is Always-On.

Handlers must perform short operations. Expensive work must be delegated by the
subscriber to the component responsible for that work. The Event Bus must not
poll, create a thread per publication, or retain completed events.

Subscription lookup should be organized by event type rather than scanning all
registered handlers.

---

# Security and Privacy Considerations

Events may cross module boundaries and must contain only the minimum data needed
by consumers.

Secrets, raw AI prompts, file contents, conversation contents, and detailed
context signals must not be included unless an approved contract explicitly
requires them. Logging must identify event type and correlation metadata without
serializing sensitive payloads by default.

Subscribers must not mutate shared state embedded in events.

---

# Future Evolution

Future versions may add explicit asynchronous subscriptions, prioritization,
bounded queues, or durable event history when justified by documented needs.

Distributed brokers, cloud transports, and cross-device delivery remain outside
Version 1.

---

# Architectural Considerations

The Event Bus reduces coupling only when events represent domain facts. It must
not hide required control flow or replace clear interfaces.

The architecture preserves a strict distinction:

- The Core owns flow.
- Domain modules own their state and events.
- The Event Bus owns delivery only.
