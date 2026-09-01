# AI Provider

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-08-31

---

# Purpose

AI Provider defines the replaceable boundary through which ATREUS may request
language-model processing when deterministic platform capabilities are not
sufficient.

AI is an optional component, not the Core. The architecture must remain
independent of any vendor, hosted service, local model, transport, or SDK.

---

# Responsibilities

An AI Provider implementation is responsible for:

- Reporting current provider availability.
- Accepting provider-neutral AI requests.
- Translating those requests into its internal provider format.
- Enforcing request deadlines and cancellation.
- Translating provider responses into a stable ATREUS response contract.
- Normalizing provider-specific failures.
- Reporting provider and model identity for diagnostics.
- Publishing sanitized request lifecycle events.

---

# Non-Responsibilities

AI Provider is not responsible for:

- Orchestrating the platform.
- Classifying every request by default.
- Making authorization or permission decisions.
- Executing capabilities.
- Creating platform plans unless a future Planner implementation explicitly
  uses the abstraction.
- Persisting prompts or responses in Memory.
- Selecting what user context may be disclosed.
- Owning user-facing conversation state.
- Selecting or applying operational-state transitions or performance-profile
  changes.
- Becoming the source of truth for platform behavior.

---

# Provider-Neutral Request

`AIRequest` is immutable and contains:

- `ai_request_id`: Unique AI operation identifier.
- `request_id`: Correlated platform request identifier.
- `instruction`: Explicit description of the requested AI operation.
- `content`: Input content for the operation.
- `context`: Immutable, minimal collection of approved `AIContextItem` values.
- `timeout_seconds`: Positive execution deadline.

`AIContextItem` contains a stable name and an immutable textual value. Callers
must select and minimize context before constructing the request.

Provider-specific fields such as model names, deployment identifiers, sampling
parameters, SDK objects, or API request classes are not part of the public
contract.

Version 1 requests one bounded textual response. Streaming and tool calling are
future contracts.

---

# Provider-Neutral Response

`AIResponse` is immutable and contains:

- `ai_request_id`.
- `request_id`.
- `content`: Text returned by the provider.
- `provider_id`: Diagnostic identifier of the active implementation.
- `model_id`: Diagnostic model identifier when available.
- `usage`: Optional provider-neutral `AIUsage` metrics.
- `completed_at`: UTC completion timestamp.

`AIUsage` may contain input and output unit counts when the provider exposes
them. Consumers must not require usage data for correctness.

Provider identity is observational metadata. Consumers must not branch business
logic based on a vendor name.

---

# Availability Contract

`AIProviderAvailability` contains:

- `state`: `AVAILABLE`, `DEGRADED`, or `UNAVAILABLE`.
- `reason_code`: Optional sanitized reason.

An unavailable AI Provider is a normal provider availability condition.
Deterministic ATREUS capabilities must remain usable without AI.

---

# Public Interface

The Version 1 contract is conceptually equivalent to:

```python
class AIProvider(ABC):
    def availability(self) -> AIProviderAvailability: ...

    def generate(self, request: AIRequest) -> AIResponse: ...
```

Bootstrap selects and injects an implementation. Consumers never instantiate a
vendor client directly.

Version 1 supports one active provider implementation at a time. Provider
selection and fallback chains require separate future architecture.

---

# Internal Flow

```text
AIRequest
    │
    ▼
Contract and Availability Validation
    │
    ▼
Provider-Specific Translation
    │
    ▼
Bounded Provider Invocation
    │
    ▼
Response or Error Normalization
    │
    ▼
AIResponse
```

Provider adapters contain integration details. No provider SDK types cross the
adapter boundary.

---

# Dependencies

The AI Provider abstraction depends on immutable AI contracts and, optionally,
the `EventBus` abstraction for lifecycle event publication.

Concrete adapters may depend on a local runtime, external SDK, or network
client, but those dependencies remain internal to the adapter. They must be
injected and replaceable.

AI Provider does not depend on Core, Planner, Memory, Context Engine, Capability
Registry, Capability Runtime, or System Layer.

Capabilities that require AI receive the `AIProvider` abstraction through
dependency injection.

---

# Events

AI Provider owns:

## `AIProviderAvailabilityChanged`

- Common event metadata.
- `provider_id`.
- Previous availability state.
- Current availability state.
- Sanitized reason code when present.

## `AIRequestStarted`

- Common event metadata.
- `ai_request_id`.
- `request_id`.
- `provider_id`.

## `AIRequestCompleted`

- Common event metadata.
- Correlation identifiers.
- `provider_id`.
- `model_id` when available.
- Duration and optional usage metrics.

## `AIRequestFailed`

- Common event metadata.
- Correlation identifiers.
- `provider_id`.
- Sanitized error code.

Events must not contain instructions, content, context values, credentials, or
response text.

---

# Error Handling

The abstraction defines an `AIProviderException` base error with normalized
errors for:

- Provider unavailable.
- Invalid request.
- Authentication failure.
- Rate limiting.
- Timeout.
- Cancellation.
- Invalid provider response.
- Internal provider failure.

Concrete vendor exceptions never cross the public boundary. Normalized errors
must retain a safe causal chain for diagnostics without exposing credentials or
private content.

The Core decides whether to report failure, ask the user, or use a deterministic
alternative. The provider does not choose a fallback workflow.

---

# Testing Requirements

Contract tests for every provider implementation must cover:

- Availability states.
- Request translation.
- Successful response normalization.
- Provider and model diagnostic metadata.
- Missing optional usage data.
- Every normalized failure category.
- Deadline and cancellation behavior.
- Request, response, and event immutability.
- Sanitization of events and logs.
- Absence of vendor SDK types in public contracts.

Consumer tests use fake `AIProvider` implementations and must not require real
credentials or network access.

---

# Performance Considerations

AI calls are expensive relative to deterministic local operations and must be
used only when they add value.

Every request has a deadline. The provider must not retry indefinitely or retain
unbounded request history. Operational state and performance profile are
independent controls. When the `PERFORMANCE` performance profile is active or
the operational state is `STANDBY`, Core may delay or reject non-essential AI
work before invocation. AI Provider respects that orchestration decision and
does not select or apply either value.

Version 1 does not require streaming, batching, speculative calls, or concurrent
provider fallback.

---

# Security and Privacy Considerations

Credentials remain inside the concrete adapter's approved secret-loading
boundary and must never appear in configuration objects, requests, events,
errors, or logs.

Callers send only the minimum approved content and context. Provider adapters
must not add hidden user data. External processing must remain transparent and
subject to user preferences.

Local-first behavior is preferred when it satisfies the requirement, but the
architecture does not mandate a permanent provider type.

---

# Future Evolution

Future versions may add streaming, structured output, embeddings, tool calling,
multiple providers, fallback policy, local model lifecycle, or cost controls
after each contract is documented.

Such evolution must preserve provider replaceability and keep AI outside the
Core.

---

# Architectural Considerations

AI Provider is a capability boundary, not an architectural center. ATREUS must
continue operating in a reduced but predictable mode when AI is unavailable.

No architecture document or consumer may permanently select OpenAI, Anthropic,
Gemini, Ollama, or any other provider as the platform itself.
