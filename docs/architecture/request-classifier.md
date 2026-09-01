# Request Classifier

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-17

---

# Purpose

The Request Classifier identifies the type of every user request before the
platform decides how to respond.

It implements the hybrid interaction model established by ADR-001 while
remaining independent from execution, planning, and response generation.

---

# Responsibilities

The Request Classifier is responsible for:

- Accepting a normalized user request.
- Assigning exactly one Version 1 request type.
- Providing a confidence value for the classification.
- Producing an immutable classification result.
- Reporting classification failures explicitly.
- Publishing `RequestClassified` when an Event Bus is available.

---

# Non-Responsibilities

The Request Classifier is not responsible for:

- Routing execution to another module.
- Executing commands or capabilities.
- Creating plans.
- Answering questions.
- Conducting conversations.
- Making platform decisions.
- Reading or writing Memory.
- Changing Context Engine state.

The Core owns routing and flow. The Decision Engine determines the appropriate
outcome from the classification and the rest of the current platform state.

---

# Request Types

Version 1 defines exactly these request types:

- `COMMAND`: A direct request for an immediately identifiable operation.
- `INTENTION`: A desired state or broad objective that may require
  interpretation or planning.
- `QUESTION`: A request for information or explanation.
- `CONVERSATION`: A social or conversational interaction without an explicit
  operational goal.
- `TASK`: Work that carries constraints such as timing, completion criteria, or
  multiple actions.

The classifier must not create new request types at runtime. Unknown or
ambiguous requests receive the best supported classification with low
confidence; downstream policy decides whether clarification is required.

---

# Inputs

The classifier accepts an immutable `Request` containing:

- `request_id`: Unique request identifier.
- `content`: Normalized textual content.
- `source`: Interaction source identifier, such as `text` or `voice`.
- `received_at`: UTC timestamp.

Input adapters are responsible for converting source-specific input into this
contract. The classifier does not perform speech recognition or user-interface
processing.

Empty or whitespace-only content is invalid.

---

# Outputs

The classifier returns an immutable `ClassifiedRequest` containing:

- `request_id`: Identifier of the classified request.
- `request_type`: One of the five Version 1 request types.
- `confidence`: Numeric value from `0.0` to `1.0`.

The original request content is not duplicated in the classification result.
The Core retains the request and correlates it by `request_id`.

Classification does not include a destination module or executable action.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class RequestClassifier(ABC):
    def classify(self, request: Request) -> ClassifiedRequest: ...
```

Consumers depend on this abstraction rather than a concrete classification
strategy.

---

# Internal Flow

```text
Normalized Request
    │
    ▼
Input Validation
    │
    ▼
Classification Strategy
    │
    ▼
Request Type + Confidence
    │
    ▼
Immutable ClassifiedRequest
```

Version 1 should prefer deterministic rules for clear commands, questions, and
task patterns. Classification strategies may be composed, but their precedence
must be deterministic and covered by tests.

AI-based classification is not required in Version 1. A future implementation
may use an `AIProvider` abstraction only as a bounded fallback; it must not make
the classifier dependent on a specific provider.

---

# Dependencies

The Request Classifier depends on:

- Request and classification data contracts.
- Optionally, the `EventBus` abstraction for domain event publication.

It does not depend on Core, Planner, Capability Runtime, Memory, Context Engine,
or a concrete AI provider.

---

# Events

The Request Classifier owns:

## `RequestClassified`

Published after successful classification.

Fields:

- Common event metadata.
- `request_id`.
- `request_type`.
- `confidence`.

The event must not contain raw request content.

Classification failures are returned to the Core as explicit exceptions. The
Core may publish `ErrorOccurred` because request lifecycle failure is part of
Core orchestration.

---

# Error Handling

The module must define a `RequestClassificationException` base error with
specific errors for invalid input and classification failure.

The classifier must never silently convert invalid input into a conversational
request. A failure must contain enough non-sensitive information for diagnosis,
including the request identifier when available.

---

# Testing Requirements

Tests must cover:

- Commands.
- Intentions.
- Questions.
- Conversations.
- Tasks.
- Ambiguous requests and confidence behavior.
- Empty and invalid input.
- Deterministic precedence between classification strategies.
- Classification result immutability.
- Event publication without raw request content.
- Independence from execution modules.

---

# Performance Considerations

Classification is on the critical path of every interaction and must remain
fast, local, and deterministic whenever possible.

Version 1 must not require a network call for normal classification. Expensive
language processing must be optional and bounded. The classifier retains no
unbounded request history.

---

# Security and Privacy Considerations

Request content may contain personal or sensitive information.

The classifier processes only the content needed for classification. It does
not persist requests, and it must not log raw content by default. Events expose
only classification metadata.

Any future AI fallback requires explicit privacy policy and must use the
provider abstraction without sending unnecessary context.

---

# Future Evolution

Future versions may add new request types, personalized strategies, multilingual
classification, or an AI-backed fallback after the architecture is updated.

Adding a request type is a contract change and requires coordinated updates to
Decision Engine policy and tests.

---

# Architectural Considerations

ADR-001 originally described the classifier as routing requests. Under the
current orchestration rule, classification produces information and the Core
owns routing. This preserves the hybrid interaction decision without allowing
the classifier to become an orchestrator.

`Conversation` remains a request type. It does not require or imply a dedicated
conversation module in Version 1.
