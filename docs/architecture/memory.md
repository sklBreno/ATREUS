# Memory

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-17

---

# Purpose

Memory provides bounded, temporary platform information needed during the
current ATREUS process.

Version 1 implements Working Memory only. It establishes a small and testable
contract without prematurely designing long-term learning, knowledge, or
experience storage.

---

# Version 1 Scope

Working Memory is:

- Local to the current process.
- Volatile and cleared when the process ends.
- Bounded by a configured platform policy.
- Explicitly written and queried through an interface.
- Suitable for short-lived request, decision, plan, and execution context.

Version 1 does not persist memory to files, databases, or cloud services.

---

# Responsibilities

Memory is responsible for:

- Storing immutable working-memory entries.
- Retrieving entries by identifier.
- Querying entries through bounded criteria.
- Removing entries explicitly.
- Expiring entries with a defined lifetime.
- Enforcing capacity limits deterministically.
- Clearing entries within an explicit scope.
- Publishing metadata-only lifecycle events.

---

# Non-Responsibilities

Memory is not responsible for:

- Deciding what the platform should remember long term.
- Learning user behavior.
- Building a knowledge graph.
- Storing configuration.
- Storing credentials or secrets.
- Managing conversation behavior.
- Planning or executing capabilities.
- Collecting context signals directly.
- Synchronizing data between devices.

Callers own the decision to store approved temporary information.

---

# Memory Entry Contract

A `MemoryEntry` is immutable and contains:

- `entry_id`: Unique entry identifier.
- `namespace`: Stable owner-defined namespace.
- `value`: Immutable typed payload defined by the namespace contract.
- `created_at`: UTC creation timestamp.
- `expires_at`: Optional UTC expiration timestamp.
- `source`: Stable identifier of the module that created the entry.
- `sensitivity`: `NORMAL` or `SENSITIVE` handling classification.

Namespaces prevent unrelated modules from interpreting each other's values.
Each namespace owner documents its payload contract.

Mutable service clients, open files, callbacks, and executable objects must not
be stored as values.

---

# Query Contract

A `MemoryQuery` is immutable and may specify:

- `namespace`.
- `source`.
- `created_after`.
- `created_before`.
- `limit`.

Every query requires a positive bounded `limit`. Version 1 does not provide
full-text search, semantic search, or arbitrary query expressions.

Results are ordered from newest to oldest and returned as an immutable
collection.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class MemoryStore(ABC):
    def put(self, entry: MemoryEntry) -> None: ...

    def get(self, entry_id: str) -> MemoryEntry | None: ...

    def query(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]: ...

    def remove(self, entry_id: str) -> bool: ...

    def clear(self, namespace: str | None = None) -> int: ...
```

`clear(None)` removes all working-memory entries and is used during controlled
shutdown or an explicit user privacy action.

---

# Internal Flow

```text
Caller
    │
    ▼
Contract and Policy Validation
    │
    ▼
Expiration Cleanup
    │
    ▼
Bounded In-Process Store
    │
    ├── Read / Query
    ├── Insert / Replace
    └── Remove / Clear
```

An entry with an existing identifier may be replaced only by the same namespace
owner. Replacement is a new write and must preserve deterministic event
behavior.

---

# Capacity and Expiration

Version 1 applies this capacity policy:

1. Remove expired entries before each write and bounded query.
2. If capacity remains unavailable, evict the oldest entry.
3. Publish `MemoryEntryRemoved` with reason `EXPIRED` or `CAPACITY`.
4. Insert the new entry.

Capacity and default lifetime are immutable policy values supplied at startup.
They may become user-configurable only after Configuration architecture defines
the settings.

Entries without `expires_at` remain only until explicit removal, capacity
eviction, or process shutdown.

---

# Dependencies

Memory depends on:

- Immutable memory contracts and policy.
- A clock abstraction for deterministic expiration tests.
- Optionally, the `EventBus` abstraction for metadata-only events.

It does not depend on Core, Planner, Context Engine, Capability Runtime, System
Layer, AI Provider, or persistent infrastructure.

---

# Events

Memory owns:

## `MemoryEntryStored`

- Common event metadata.
- `entry_id`.
- `namespace`.
- `source`.
- `sensitivity`.

## `MemoryEntryRemoved`

- Common event metadata.
- `entry_id`.
- `namespace`.
- Removal reason: `EXPLICIT`, `EXPIRED`, `CAPACITY`, or `CLEAR`.

Events must never contain the entry value.

---

# Error Handling

The module defines a `MemoryException` base error with explicit errors for
invalid entries, invalid queries, namespace ownership violations, and internal
store failures.

`get` returns `None` for an unknown or expired identifier. `remove` returns
`False` for an unknown or expired identifier. Invalid identifiers and malformed
queries raise explicit errors.

---

# Testing Requirements

Tests must cover:

- Store and retrieve operations.
- Bounded queries and deterministic ordering.
- Namespace filtering.
- Explicit removal and clear operations.
- Expiration using an injected clock.
- Capacity eviction order.
- Replacement ownership.
- Entry and result immutability.
- Metadata-only events.
- Sensitive entry handling.
- Concurrent read behavior when applicable.
- Complete volatility across store instances.

---

# Performance Considerations

Working Memory is used by an Always-On process and must remain bounded.

Reads by identifier should be constant time. Queries must enforce their limit
before returning results. Expiration cleanup must avoid unbounded background
polling; cleanup occurs during operations and controlled maintenance.

Large binary values and unbounded collections are not supported.

---

# Security and Privacy Considerations

Memory follows data minimization. A module stores only information needed for a
current operation and assigns the shortest practical lifetime.

Sensitive values must not appear in events or default logs. User-triggered
clear operations must take effect immediately for the selected scope. Because
Version 1 is volatile, no memory data should remain in project files or
persistent stores after process termination.

---

# Future Memory Concepts

The following concepts are explicitly future architecture:

## Long-Term Memory

Durable user-approved information across process restarts.

## Knowledge

Structured facts and relationships with provenance and update rules.

## Experience Memory

Historical outcomes used to improve future behavior.

## Persistent Conversation Context

User-approved conversation continuity across sessions.

None of these concepts is part of Version 1 Working Memory. They require
separate retention, consent, persistence, deletion, and migration architecture.

---

# Future Evolution

Future implementations may add approved persistent stores, semantic retrieval,
encryption, or cross-session memory behind separate interfaces.

The `MemoryStore` contract may be extended only after persistence and privacy
requirements are documented. Version 1 must not create dormant database or
cloud abstractions.

---

# Architectural Considerations

Memory stores data; it does not decide, learn, or act. This boundary prevents a
minimal Working Memory implementation from becoming an undefined intelligence
subsystem.

Modules remain responsible for their namespace contracts and for deciding when
temporary data is no longer needed.
