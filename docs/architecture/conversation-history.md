# Conversation History

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-09-02

---

# Purpose

Conversation History provides bounded short-term dialogue continuity for the
current ATREUS process composition. It retains only complete successful
conversational exchanges and exposes them through immutable snapshots.

Conversation History is separate from Working Memory and Long-Term Memory. It
does not decide, plan, authorize, execute, infer context, or persist data.
It is also separate from the explicit persisted Personal Profile.

---

# Version 1 Scope

Version 1 is:

- Process-local and volatile.
- Bounded by exchange count and total character count.
- Synchronous and deterministic.
- Ordered from oldest to newest.
- Shared only with the composed `ConversationResponder`.
- Cleared by process restart, new composition, or an explicit clear request.

Version 1 has no persistence, filesystem storage, database, embeddings, vector
index, semantic retrieval, AI Router, background work, or multi-session
identity.

---

# Data Contracts

All contracts are immutable and use timezone-aware UTC timestamps.

`ConversationRole` contains only `USER` and `ASSISTANT`. History cannot contain
a `SYSTEM` role.

`ConversationTurn` contains a UUID turn identifier, correlated request UUID,
role, private content, interaction language, and creation timestamp. Content is
excluded from representations.

`ConversationExchange` contains exactly one user turn followed by one assistant
turn. Both turns have the same request identity and interaction language, and
the user timestamp does not follow the assistant timestamp.

`ConversationHistorySnapshot` contains a capture timestamp and an immutable
tuple of complete exchanges ordered from oldest to newest.

`ConversationHistoryPolicy` contains positive `max_exchanges` and
`max_characters` limits. Validated Configuration defaults are six exchanges and
12,000 characters.

---

# Public Interfaces

`ConversationHistoryProvider` exposes only `snapshot()`.

`ConversationHistoryStore` extends that boundary with:

```python
def try_append(self, exchange: ConversationExchange) -> bool: ...

def clear(self) -> int: ...
```

`try_append` returns `False` when one otherwise valid exchange exceeds the
complete history character budget. This is a policy result, not a provider
failure. Invalid inputs and structural failures remain explicit exceptions.

---

# Retention Policy

`InMemoryConversationHistory` validates the complete exchange before changing
state. If it fits individually, the store considers the new exchange and evicts
oldest complete exchanges until both configured limits are satisfied. It then
replaces its retained state in one operation.

Individual turns are never truncated or pruned separately. Reads do not alter
order. An oversized append leaves the previous history unchanged. `clear`
removes all retained exchanges and reports the removed count.

---

# Conversational Flow

For every request delegated to `ConversationResponder`, the responder captures
one stable history snapshot. The current request is not added before response
generation.

For provider-backed responses, the responder projects prior exchanges into
alternating provider-neutral `AIMessage` values and keeps the current request
only in `AIRequest.content`. After a successful response is validated, the
responder appends the complete user and assistant exchange exactly once.

Successful deterministic identity, capability, and limitation responses are
retained. Secret-refusal requests, clear requests, failures, operational
results, application status, confirmations, and unsafe-action rejections are
not retained.

Personal Profile read, show, and clear interactions are never retained. A
provider-backed response generated with a Personal Profile projection is also
excluded so profile-derived content cannot be retransmitted in a later
unrelated request.

---

# Action Isolation

Conversation History is available only to `ConversationResponder`. It is not
available to Request Classifier, Request Interpreter, Core decision inputs,
Decision Engine, Planner, Interactive Confirmation, Capability Runtime,
Capability Invocation, Execution Context, or System Layer.

Historical references therefore cannot supply an operational target or
authorize an action. Commands such as `abra isso` and `open it` remain unresolved
until a future explicitly approved operational-reference architecture exists.

---

# Language

Each turn records its resolved interaction language. The current request
determines the current response language. A process-local history may contain
Brazilian Portuguese and English exchanges without translating previous text.

---

# Clear Behavior

Exact normalized requests `limpar conversa` and `clear conversation` clear only
Conversation History and make no AI request. They return a localized
confirmation and are not themselves retained. Working Memory and confirmation
state are unchanged.

---

# Failures

Provider unavailability, timeout, authentication failure, rate limiting,
malformed output, invalid correlation, or invalid response content leaves
history unchanged. Snapshot or append structural failures are translated into
a sanitized conversation response failure. Exception messages contain no
conversation content.

---

# Privacy and Observability

History exists only in RAM. No conversation-history events are introduced.
Turns, exchanges, prompts, and responses must not appear in event payloads,
structured logs, exception messages, or object representations.

With Ollama, bounded history remains on the configured local provider endpoint.
With OpenAI, bounded history is sent to the selected cloud provider for that
conversation request. Neither provider persists history on behalf of ATREUS.

---

# Composition and Lifecycle

Bootstrap creates one `InMemoryConversationHistory` per runtime composition and
injects it into `ProviderBackedConversationResponder`. Multiple requests in the
same composition share that history. A new composition or process restart
starts empty.

Version 1 treats one process composition as one implicit conversation session.
It introduces no `session_id`, Session Manager, global mutable state, thread,
async task, polling, scheduler, or background worker.

---

# Testing Requirements

Tests cover immutable contracts, UTC normalization, complete-exchange
validation, FIFO pruning, exact count and character limits, oversized atomic
rejection, snapshot stability, clear behavior, responder projection, failure
atomicity, mixed languages, provider payload order, configuration priority,
privacy, composition lifecycle, and operational action isolation.

---

# Future Evolution

Explicit concurrent sessions, token-aware budgets, summaries, persistence,
selective promotion, semantic retrieval, and distributed synchronization
require separate architecture. Conversation History must never promote data to
Working Memory or Long-Term Memory automatically.

Conversation History must also never import from or promote content into
Personal Profile automatically.
