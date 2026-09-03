# AI Provider

**Status:** Draft

**Version:** 1.2

**Last Updated:** 2026-09-02

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
- Enforcing bounded request timeouts.
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
- `purpose`: Approved bounded use of the provider.
- `instruction`: Explicit description of the requested AI operation.
- `content`: Input content for the operation.
- `timeout_seconds`: Positive execution deadline.
- `max_output_tokens`: Positive purpose-specific output bound.

AI Provider V0 defines `REQUEST_INTERPRETATION` and
`CONVERSATIONAL_RESPONSE`. `instruction` and `content` are excluded from
representations. Context and Working Memory are not part of `AIRequest` and are
not disclosed to the provider in V0.

Provider-specific fields such as model names, deployment identifiers, sampling
parameters, SDK objects, or API request classes are not part of the public
contract.

Version 1 requests one bounded textual response. Request interpretation uses a
small structured-output budget. Conversational generation uses at most 512
output tokens. Streaming and tool calling are future contracts.

---

# Provider-Neutral Response

`AIResponse` is immutable and contains:

- `ai_request_id`.
- `request_id`.
- `content`: Text returned by the provider.
- `provider_id`: Diagnostic identifier of the active implementation.
- `model_id`: Diagnostic model identifier when available.
- `completed_at`: UTC completion timestamp.

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

Version 1 supports one active provider implementation at a time. Bootstrap
selects `openai` or `ollama` from validated configuration. Runtime switching,
automatic fallback, provider priority, and AI routing require separate future
architecture.

# Request Interpreter V1

`RequestInterpreter` is the bounded service used by Core after Decision Engine
returns `DELEGATE(ai.request_interpreter)`. It accepts the original immutable
`Request`, invokes `AIProvider` at most once, validates the structured output,
and maps the approved intent to a local capability identifier.

V1 accepts only:

- Intents `OPEN_APPLICATION` and `APPLICATION_STATUS`.
- Targets already approved by the controlled application contract.

The provider may return only `intent_id`, `target_id`, and `confidence`. It
cannot provide executable names, paths, command lines, permission grants,
capability identifiers, shell content, or arbitrary arguments. The interpreter
maps the returned intent and target through the authoritative local action
matrix and verifies current Capability Catalog availability before returning
`RequestInterpretation` with a typed `ApplicationAction`.

The interpretation is non-executable. Core submits it to a second Decision
Engine evaluation. AI-originated open actions require Interactive Confirmation;
read-only status actions proceed to planning without confirmation. Capability
Runtime and System Layer never receive `RequestInterpretation` or raw provider
output.

Interactive Confirmation is a separate local boundary. AI Provider does not
parse yes/no input, detect the interaction language, render confirmation text,
store pending authorization, or observe the eventual result. Exact confirmation
responses make zero AI requests. The same locally approved
`ApplicationAction` is preserved through Decision Engine, confirmation when
required, and Planner; it is never reconstructed from raw text.

---

# Conversation Responder V0

`ConversationResponder` is the stateless service used by Core after Decision
Engine returns `DELEGATE(ai.conversation_responder)`. It answers stable identity,
capability, unsupported-capability, and secret-disclosure requests locally. For
other eligible questions and conversation, it invokes `AIProvider` at most once
with `CONVERSATIONAL_RESPONSE`.

The responder derives its minimal capability summary from the authoritative
local action matrix and current Capability Catalog. It does not ask AI what
ATREUS can do and never exposes executable names, paths, process details,
permissions, or native-system mappings.

Conversational generation is plain text, bounded to 512 output tokens, and has
no tools, web, filesystem, shell, Planner, Capability Runtime, or System Layer
access. Its result is user-facing text only. It cannot execute an action, create
a plan, grant permission, or claim that an action ran.

Context and Working Memory are not supplied to the responder or provider.
Version 0 retains no conversation history. See
`docs/architecture/conversational-ai.md`.

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

For `REQUEST_INTERPRETATION`, both adapters use a strict JSON Schema. The OpenAI
adapter uses official SDK Responses API Structured Outputs. The Ollama adapter
sends the equivalent schema through the local chat API `format` field and
validates the returned JSON before normalization. The schema rejects additional
fields and constrains the two approved intents, approved targets, and confidence
range. It contains no capability, executable, process, PID, path, argument, or
command field. The interpreter validates the decoded response again because
provider output remains untrusted and may name a locally unsupported
intent-target combination.

For `CONVERSATIONAL_RESPONSE`, each adapter requests bounded plain text and does
not supply the interpretation schema. Purpose dispatch remains internal to the
adapter; provider SDK or transport types do not cross the public contract.

No tools, web search, file search, MCP integration, shell, or executable
function is supplied to the model. Automatic SDK retries are disabled in V0.

Provider adapters contain integration details. No provider SDK types cross the
adapter boundary.

---

# Local AI / Ollama

Ollama is an optional local implementation of `AIProvider`. Bootstrap selects
it only when AI is enabled and `ai_provider` is `ollama`. The adapter calls the
configured local HTTP endpoint at `/api/chat`; it never invokes the Ollama CLI,
starts a process, or executes a shell.

V0 restricts the configured base URL to explicit HTTP endpoints on `localhost`
or `127.0.0.1`, disables redirects and proxy use, sends no credentials, performs
no retry, and enforces the request timeout. The default development endpoint is
`http://localhost:11434` and the default local model is `qwen3:8b`.

Every request sends `stream=false` and `think=false`. Any provider-specific
thinking field is ignored and is never returned or logged. The adapter supports
both current purposes: plain-text conversation and strict structured request
interpretation. Ollama availability is configuration-level in V0; connection,
timeout, server, malformed-response, and missing-model failures are normalized
during generation.

Ollama requires no API key. Selection is static for one runtime composition,
with no automatic fallback to OpenAI and no AI Router.

---

# Dependencies

The AI Provider abstraction depends on immutable AI contracts and, optionally,
the `EventBus` abstraction for lifecycle event publication.

Concrete adapters may depend on a local runtime, external SDK, or network
client, but those dependencies remain internal to the adapter. The Ollama
adapter uses only the Python standard-library HTTP client. Adapter transport
dependencies remain isolated and replaceable for tests.

AI Provider does not depend on Core, Planner, Memory, Context Engine, Capability
Registry, Capability Runtime, or System Layer. The Request Interpreter may
depend on the read-only Capability Catalog to validate the approved local
mapping before returning an interpretation.

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
- `purpose`.

## `AIRequestCompleted`

- Common event metadata.
- Correlation identifiers.
- `provider_id`.
- `model_id` when available.
- Duration and optional usage metrics.
- `purpose`.

## `AIRequestFailed`

- Common event metadata.
- Correlation identifiers.
- `provider_id`.
- Sanitized error code.
- `purpose`.

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
- Network failure.
- Malformed provider response.
- Invalid structured output.
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

Ollama adapter tests additionally cover the fixed local endpoint, POST payload,
strict schema, `stream=false`, `think=false`, thinking exclusion, response
limits, redirect rejection, malformed data, missing model, timeout, connection,
HTTP failures, and the absence of process or shell execution.

Natural Language Actions tests additionally cover strict intent and target
enums, rejection of extra or native fields, unsupported local combinations,
one provider call per eligible request, mandatory confirmation for open, and
direct read-only planning for status.

Conversational AI tests additionally cover purpose-specific plain-text
translation, deterministic bilingual self-knowledge, safe capability summaries,
secret refusal, one provider call for eligible general conversation, bounded
output, unavailable and failing providers, and absence of tools or content in
events and logs.

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

OpenAI reads `ATREUS_OPENAI_API_KEY` from the process environment during
Bootstrap composition. The value is injected into the OpenAI adapter and is
never copied into `Configuration`, `.env.example`, provider representations, or
public diagnostics. Ollama V0 uses no credential. Non-secret provider
selection, model, endpoint, and timeout settings remain in validated
Configuration.

Callers send only the minimum approved request content. Context and Working
Memory are excluded from AI Provider V0. Provider adapters must not add hidden
user data. External processing must remain transparent and subject to user
preferences.

Local-first behavior is preferred when it satisfies the requirement, but the
architecture does not mandate a permanent provider type.

---

# Future Evolution

Future versions may add streaming, other structured purposes, embeddings, tool
calling, multiple providers, fallback policy, local model lifecycle, or cost
controls after each contract is documented.

Such evolution must preserve provider replaceability and keep AI outside the
Core.

---

# Architectural Considerations

AI Provider is a capability boundary, not an architectural center. ATREUS must
continue operating in a reduced but predictable mode when AI is unavailable.

No architecture document or consumer may permanently select OpenAI, Anthropic,
Gemini, Ollama, or any other provider as the platform itself.
