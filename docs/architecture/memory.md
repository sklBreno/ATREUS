# Memory

**Status:** Draft

**Version:** 1.1

**Last Updated:** 2026-09-01

---

# Purpose

Memory provides bounded temporary platform information needed during the
current ATREUS process.

Working Memory is distinct from current Context, Configuration, conversation
history, Long-Term Memory, Knowledge Memory, and Experience Memory. It stores
only explicit temporary facts and does not decide, learn, infer, or act.

---

# Version 0 Scope

Working Memory V0 is:

- Local to one composed process runtime.
- Volatile and empty after a new composition or process restart.
- Bounded by validated Configuration policy.
- Deterministic and synchronous.
- Explicitly written through a narrow interface.
- Exposed to request consumers through immutable snapshots.

Version 0 has no persistence, database, filesystem access, AI, embeddings,
vector index, background cleanup, or external integration.

Production does not contain an automatic memory producer in Version 0. No
request content, conversation text, plan, capability arguments, complete
capability results, exceptions, credentials, context snapshots, or log records
are stored automatically.

Conversational AI V0 is stateless and receives no `MemorySnapshot`. Neither its
requests nor its responses are written to Working Memory. Conversation history
and continuity remain separate future architecture.

---

# Responsibilities

Working Memory is responsible for:

- Storing immutable temporary entries supplied explicitly by a caller.
- Returning entries by identifier.
- Capturing immutable snapshots.
- Removing entries explicitly.
- Expiring entries lazily through a fixed lifetime policy.
- Enforcing capacity through deterministic FIFO eviction.
- Clearing all entries on an explicit request.

Callers remain responsible for selecting approved minimized facts and their
namespace. Working Memory does not decide what should be remembered.

---

# Non-Responsibilities

Working Memory is not responsible for:

- Long-term retention or persistence.
- User preferences, learned knowledge, or historical experience.
- Conversation behavior or complete conversation history.
- Context detection or signal retention.
- Configuration loading.
- Request decisions, planning, or capability execution.
- Operating-system access.
- Memory promotion or retention policy based on AI.

---

# Data Contracts

All Version 0 contracts are immutable and use timezone-aware UTC timestamps.

## `MemoryValue`

- `name`: Non-empty stable field name.
- `value`: One `str`, `int`, `float`, or `bool` scalar.

Arbitrary objects, dictionaries, mutable collections, non-finite floats, and
executable values are invalid.

## `MemoryEntry`

- `entry_id`: Unique entry identifier.
- `namespace`: Stable owner-defined namespace.
- `values`: Non-empty immutable collection of uniquely named `MemoryValue`.
- `source`: Stable identifier of the producing component.
- `source_request_id`: Optional request identifier that produced the fact.
- `created_at`: UTC creation timestamp.
- `expires_at`: UTC expiration timestamp after creation.

## `MemorySnapshot`

- `captured_at`: UTC snapshot timestamp.
- `entries`: Immutable entries ordered from newest to oldest.

A snapshot is a stable point-in-time view. Later writes, expiration, or
eviction do not mutate earlier snapshots.

## `WorkingMemoryPolicy`

- `capacity`: Positive maximum entry count.
- `entry_ttl`: Positive fixed lifetime applied to every Version 0 entry.

Validated Configuration defaults are 64 entries and 1800 seconds. Both values
may be overridden through the existing `.env` and process-environment loading
priority before bootstrap composition.

---

# Public Interfaces

`MemorySnapshotProvider` exposes only:

```python
def snapshot(self) -> MemorySnapshot: ...
```

`MemoryStore` extends that read boundary with:

```python
def remember(
    self,
    namespace: str,
    values: tuple[MemoryValue, ...],
    source: str,
    source_request_id: UUID | None = None,
) -> MemoryEntry: ...

def recall(self, entry_id: UUID) -> MemoryEntry | None: ...

def forget(self, entry_id: UUID) -> bool: ...

def clear(self) -> int: ...
```

Core depends only on `MemorySnapshotProvider`. Version 0 does not introduce
separate reader, writer, manager, repository, or policy-engine abstractions.

---

# Capacity and Expiration

`InMemoryWorkingMemory` applies this deterministic policy:

1. Capture the current time from the injected `Clock`.
2. Remove expired entries before `remember`, `recall`, `snapshot`, and
   `forget`.
3. Before a write, evict the oldest inserted entry while capacity is full.
4. Insert the new entry with the configured fixed TTL.

Reads do not renew TTL or change insertion priority. Entries at their exact
expiration timestamp are expired. `clear` removes all entries directly.

No timer, polling loop, scheduler, thread, async task, or background worker is
used for cleanup.

---

# Request Integration

For every request, Core captures exactly one `MemorySnapshot` after current
context capture and before Decision Engine evaluation. Core reuses that same
instance in `DecisionInput` and `PlanningRequest` when planning occurs.

Decision Engine and Planner may observe the immutable snapshot but do not query
or write `MemoryStore`. Their current deterministic behavior does not depend on
memory values.

Capability Runtime, `CapabilityInvocation`, and `ExecutionContext` do not
receive, capture, or write Working Memory. Core does not store entries or
decide what should be remembered.

---

# Lifecycle

Bootstrap creates one `InMemoryWorkingMemory` for each composed runtime and
injects its snapshot boundary into Core. Every request handled by that runtime
observes the same underlying store through a new stable snapshot.

A new composition creates a new empty store. Runtime shutdown performs no
persistence, and process restart begins empty.

---

# Error Handling

Invalid values, entries, snapshots, identifiers, and policies raise explicit
Memory exceptions.

Unknown or expired identifiers return `None` from `recall` and `False` from
`forget`. Capacity pressure is handled through FIFO eviction and is not an
error.

A snapshot-provider exception fails request orchestration before Decision
Engine, Planner, or execution. Core reports only the exception type and
orchestration stage through its existing sanitized error event.

---

# Events and Observability

Version 0 publishes no memory events. It does not define `MemoryRead`,
`MemoryWritten`, `MemoryExpired`, or `MemoryCleared`.

Memory values must not appear in events, structured logs, exceptions, or
default diagnostics.

---

# Security and Privacy

Working Memory follows data minimization even though it is volatile. Callers
must supply only the smallest approved scalar facts required by a current
operation.

Version 0 does not introduce a sensitivity or scope classification because no
access-control or disclosure enforcement exists for those labels yet.

---

# Testing Requirements

Tests must cover contract immutability, UTC normalization, invalid values,
policy validation, remember/recall/forget/clear behavior, fixed TTL, lazy
expiration, FIFO eviction, capacity, newest-first snapshots, snapshot
stability, request-level snapshot identity, bootstrap lifetime, sanitized
provider failure, and absence of persistence, AI, operating-system, or
concurrent infrastructure dependencies.

---

# Future Evolution

Version 1 may add approved namespace-specific producers, richer typed values,
bounded queries, explicit conversation continuity, and deterministic memory
selection policy.

Long-Term Memory, Knowledge Memory, Experience Memory, persistence, semantic
retrieval, embeddings, cross-device synchronization, and promotion policy are
separate future architecture. AI may suggest memory candidates in the future,
but it must never write directly to the store or promote data without approved
policy and authorization.
