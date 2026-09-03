# Conversational AI

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-09-02

---

# Purpose

Conversational AI V0 provides one stateless, provider-backed response for
eligible questions and conversational requests. It adds a production response
boundary without turning AI into an authorization, planning, execution, or
memory component.

ATREUS remains a personal intelligence platform rather than a chatbot. The
conversation path is one bounded interaction capability within the existing
Core-owned request flow.

---

# Scope

Version 0 supports:

- Brazilian Portuguese as the primary and default language.
- English as the secondary language.
- Deterministic identity, capability-summary, unsupported-capability, and
  secret-refusal responses.
- One bounded provider request for other eligible questions or conversation.
- Sanitized localized failure when conversational generation is unavailable.

Version 0 is stateless. It has no conversation history, retrieval, memory
promotion, tool calling, streaming, web access, filesystem access, or external
action execution.

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
    -> deterministic self-knowledge or one AI Provider request
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

ContextSnapshot and MemorySnapshot are intentionally excluded from `AIRequest`
in V0. The responder receives neither contract and does not retain request or
response history.

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

---

# Failure Handling

Unavailable providers, normalized provider errors, malformed output, invalid
response identity, and responder failures produce no conversational response.
Core publishes its existing sanitized `ErrorOccurred` orchestration event and
the foreground interface renders a localized generic failure.

Provider exception messages, prompts, raw request content, raw response text,
credentials, Context, and Working Memory must not appear in events or structured
logs.

Deterministic identity, capability, and secret responses remain available when
the external provider is unavailable because they require no provider call.

---

# Observability

No conversation-specific event is introduced in V0. Existing AI lifecycle
events include `purpose` so operators can distinguish interpretation from
conversation without recording content:

- `AIRequestStarted`.
- `AIRequestCompleted`.
- `AIRequestFailed`.

Existing request lifecycle events describe Core orchestration. Event payloads
contain no conversation text.

---

# Composition

Bootstrap creates one `ProviderBackedConversationResponder` from the selected
`AIProvider`, the read-only Capability Catalog, and validated timeout policy. It
injects the responder into Core through `ConversationResponder`.

Bootstrap remains a composition root. It contains no conversational decision,
prompt rendering, response text, or provider-specific business logic.

---

# Testing Requirements

Tests must cover deterministic bilingual self-knowledge, capability summaries,
secret refusal, unsupported-capability honesty, one provider call for general
conversation, provider-purpose translation, response validation, unavailable
and failing providers, sanitization, operational precedence, malicious-looking
input isolation, and full offline Core and console flows.

Tests use fake providers and System Layer boundaries. Ollama HTTP tests use an
isolated transport double. Automated tests require no running local model,
network credential, or real desktop action.

---

# Future Evolution

Conversation history, explicit continuity, selective Working Memory use,
Long-Term Memory retrieval, streaming, richer localization, current-information
retrieval, and tool-assisted answers require separate architecture and explicit
privacy, authorization, disclosure, and observability policies.

AI must never write directly to Working Memory or Long-Term Memory, and a
conversational response must never become executable without returning through
the normal Decision Engine, Planner, Capability Runtime, permission, and
confirmation boundaries.
