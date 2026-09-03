# Conversational AI

**Status:** Approved  
**Version:** 1.1
**Last Updated:** 2026-09-02

---

# Purpose

Conversational AI V1 provides bounded provider-backed responses with short-term
continuity for eligible questions and conversational requests. It does not turn
AI into an authorization, planning, execution, Working Memory, or Long-Term
Memory component.

ATREUS remains a personal intelligence platform rather than a chatbot. The
conversation path is one bounded interaction capability within the existing
Core-owned request flow.

---

# Scope

Version 1 supports:

- Brazilian Portuguese as the primary and default language.
- English as the secondary language.
- Deterministic identity, capability-summary, unsupported-capability, and
  secret-refusal responses.
- One bounded provider request for other eligible questions or conversation.
- Bounded process-local history of complete successful conversational
  exchanges.
- Exact bilingual commands for clearing the current conversation.
- Exact local Personal Profile read, show, and confirmed-clear interaction when
  that opt-in module is enabled.
- Category-specific bounded profile projection for relevant provider-backed
  conversation.
- Sanitized localized failure when conversational generation is unavailable.

Version 1 has no persistent history, retrieval, memory promotion, tool calling,
streaming, web access, filesystem access, or external action execution.

---

# Contracts

`ConversationResponder` is the provider-neutral service boundary invoked by
Core. It accepts the original immutable `Request` and the resolved
`InteractionLanguage`, and returns one immutable `ConversationalResponse`.

`ConversationalResponse` contains only:

- `request_id`: Correlation with the original request.
- `text`: Validated user-facing response text.
- `language`: The resolved interaction language.

`AssistantCapabilitySummary` is an immutable, minimal projection derived from
the local typed application-action matrix and current Capability Catalog. It
contains only approved platform-neutral application identifiers that can be
opened or observed. It contains no executable, process, path, permission,
provider, or native-system detail.

`ConversationHistorySnapshot` is a stable oldest-first view of complete recent
exchanges. It is captured and consumed only by the responder. See
`docs/architecture/conversation-history.md`.

`PersonalProfileProjection` is a bounded declarative text projection selected
from explicit user-approved fields. The responder receives it through
`PersonalProfileProjectionProvider`; it never receives a filesystem store
implementation.

---

# Request Flow

```text
Request
    -> Request Classifier
    -> Core captures one ContextSnapshot and one MemorySnapshot
    -> Decision Engine
    -> DELEGATE(ai.conversation_responder)
    -> Core
    -> ConversationResponder
    -> exact Personal Profile interaction, when applicable
    -> one bounded ConversationHistorySnapshot
    -> deterministic self-knowledge or one relevant profile projection
    -> one AI Provider request when needed
    -> atomic complete-exchange append after successful validation
    -> ConversationalResponse
    -> foreground interface
```

Decision Engine selects only the service target and never produces response
text. Core invokes the responder at most once and validates correlation and
language before returning the response.

The conversational path never enters Planner, Capability Runtime, Capability
Invocation, ExecutionContext, or System Layer. It cannot execute an action or
create a permission grant. Operational commands and confirmation responses
retain precedence over conversational delegation.

Bounded Brazilian Portuguese open imperatives and English application-status
questions are operational requests even when AI is unavailable. Explicit
PowerShell, `cmd`, command-prompt, and shell imperatives are rejected locally as
unsupported rather than being redirected to conversation or clarification.
Capability questions such as `can you open calculator?` remain non-executive.

---

# AI Provider Use

Conversational generation uses `AIRequestPurpose.CONVERSATIONAL_RESPONSE` and
the existing provider-neutral `AIProvider` interface. Bootstrap may select the
OpenAI cloud adapter or the optional local Ollama adapter. Each adapter selects
request translation by purpose:

- `REQUEST_INTERPRETATION` uses strict Structured Outputs and a small output
  budget.
- `CONVERSATIONAL_RESPONSE` uses bounded plain text with a maximum of 512 output
  tokens.

The Ollama adapter calls only its configured local HTTP endpoint, sends
`stream=false` and `think=false`, and ignores provider-specific thinking data.
It requires no API key. Provider selection is explicit for one composition;
V0 has no automatic fallback, runtime switching, or AI Router.

The provider receives no tools, function calls, web access, file access, shell,
Planner, Capability Runtime, or System Layer interface. Provider output is text
only and cannot authorize or trigger a second workflow.

ContextSnapshot and MemorySnapshot remain excluded from `AIRequest`. For
conversational generation only, `AIRequest.history` contains bounded alternating
`USER` and `ASSISTANT` messages derived from complete prior exchanges. The
current request remains only in `AIRequest.content`.

Request interpretation requires empty history. Conversation History is not
available to Request Interpreter, Decision Engine, Planner, Confirmation,
Capability Runtime, or System Layer.

Personal Profile remains equally unavailable to those operational components.
For conversation only, selected values may appear inside the private
`AIRequest.instruction` as JSON-quoted declarative data with explicit boundaries
and a configured maximum size. User request language remains authoritative.
When no category is clearly relevant, no profile data is supplied.

---

# Self-Knowledge and Safety

Stable self-knowledge is answered locally to avoid provider hallucination:

- ATREUS identity.
- Current approved application-opening and application-status support.
- Explicit absence of unsupported web, filesystem, voice, and home-control
  access.
- Refusal to disclose credentials, API keys, or internal instructions.

The capability summary is computed from approved local contracts and current
catalog availability. AI is not the source of truth for platform capabilities.

General provider instructions require concise language-matched answers, forbid
false execution claims and unsupported capability claims, and require an
explicit limitation for information that would need current web verification.
These instructions reduce risk but do not create an execution boundary; the
absence of tools and downstream execution is authoritative.

---

# Language

The existing deterministic `InteractionLanguageResolver` selects `PT_BR` or
`EN_US`. Ambiguous input resolves to Brazilian Portuguese. The selected value
is passed explicitly to the responder and returned in the response contract.

Conversation does not infer language through AI and does not change the
language rules for Interactive Confirmation or deterministic action rendering.

History preserves each exchange in its original language. The current request
selects the current response language, so one process-local conversation may
contain both Brazilian Portuguese and English.

Exact normalized requests `limpar conversa` and `clear conversation` clear only
Conversation History, make no AI request, and are not retained. Working Memory
and Interactive Confirmation are unaffected.

Exact Personal Profile read, show, clear-request, and clear-confirmation phrases
are also handled locally and are never retained in Conversation History. The
profile clear confirmation deliberately does not accept generic `sim` or `yes`.

---

# Failure Handling

Unavailable providers, normalized provider errors, malformed output, invalid
response identity, and responder failures produce no conversational response.
Core publishes its existing sanitized `ErrorOccurred` orchestration event and
the foreground interface renders a localized generic failure.

Provider exception messages, prompts, raw request content, raw response text,
credentials, Context, and Working Memory must not appear in events or structured
logs.

History remains only in RAM. Ollama receives bounded history through its local
endpoint. OpenAI receives the same bounded history through the selected cloud
provider for the current conversation request.

Ollama receives selected profile data only through its local endpoint. OpenAI
receives only the same bounded selected projection. Responses produced with a
profile projection are not appended to history, preventing later unrelated
redisclosure.

Deterministic identity, capability, and secret responses remain available when
the external provider is unavailable because they require no provider call.
Successful identity, capability, and limitation exchanges may be retained for
follow-up continuity. Secret refusals, failures, clear requests, and operational
results are never retained.

---

# Observability

No conversation-specific event is introduced in V1. Existing AI lifecycle
events include `purpose` so operators can distinguish interpretation from
conversation without recording content:

- `AIRequestStarted`.
- `AIRequestCompleted`.
- `AIRequestFailed`.

Existing request lifecycle events describe Core orchestration. Event payloads
contain no conversation text.

Personal Profile V0 introduces no event. Profile fields, projections, storage
paths, and imported documents never appear in event or structured-log payloads.

---

# Composition

Bootstrap creates one process-local `InMemoryConversationHistory` and one
`ProviderBackedConversationResponder` from the selected `AIProvider`, the
read-only Capability Catalog, injected Clock, and validated policies. It injects
only the responder into Core through `ConversationResponder`.

When Personal Profile is enabled, Bootstrap additionally injects its projection
provider and deterministic interaction handler into the responder. The Core
contract is unchanged.

Bootstrap remains a composition root. It contains no conversational decision,
prompt rendering, response text, or provider-specific business logic.

---

# Testing Requirements

Tests must cover deterministic bilingual self-knowledge, bounded history,
complete-exchange atomicity, FIFO pruning, exact clear commands, mixed-language
continuity, provider-purpose translation, response validation, unavailable and
failing providers, sanitization, operational precedence, historical-reference
isolation, and full offline Core and console flows.

Tests use fake providers and System Layer boundaries. Ollama HTTP tests use an
isolated transport double. Automated tests require no running local model,
network credential, or real desktop action.

Personal Profile tests additionally cover exact local read/show, dedicated
clear confirmation, selective projection, provider disclosure boundaries,
history exclusion, no operational propagation, and content-free observability.

---

# Future Evolution

Explicit concurrent sessions, persistent history, selective Working Memory use,
Long-Term Memory retrieval, streaming, richer localization, current-information
retrieval, and tool-assisted answers require separate architecture and explicit
privacy, authorization, disclosure, and observability policies.

Granular profile edits, automatic candidate extraction, learned facts, and
profile-to-memory promotion also require separate architecture and user approval.

AI must never write directly to Working Memory or Long-Term Memory, and a
conversational response must never become executable without returning through
the normal Decision Engine, Planner, Capability Runtime, permission, and
confirmation boundaries.
