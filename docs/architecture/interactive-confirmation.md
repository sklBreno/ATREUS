# Interactive Confirmation

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-09-02

---

# Purpose

Interactive Confirmation V0 provides one explicit, single-use authorization
step before an AI-interpreted application-open action may be planned and
executed.

Confirmation is process-local authorization state. It is not a permission
grant, conversation history, Working Memory, Context, or capability execution.

---

# Scope

V0 supports only `OPEN_APPLICATION` actions originating from a validated
`RequestInterpretation`. Deterministic application commands keep their existing
local path and do not gain an additional confirmation step.

`APPLICATION_STATUS` is read-only and never creates a pending confirmation.
It returns to Decision Engine and Planner through the Natural Language Actions
flow with normal permission enforcement.

V0 intentionally excludes queues, multiple sessions, persistence, background
expiration, generic approvals, permission grants, and AI-based parsing.

---

# Interaction Language

ATREUS is Brazilian Portuguese first and supports English as the secondary
interaction language. `InteractionLanguage` defines `PT_BR` and `EN_US`.

Language resolution is narrow and deterministic. Clear English-only evidence
selects `EN_US`; Brazilian Portuguese and ambiguous input select `PT_BR`.
Neither AI nor the Windows locale determines the interaction language in V0.

The selected language is preserved in the structured `ConfirmationPrompt`.
Translated sentences are owned by the foreground interface and are not stored
in confirmation domain objects.

---

# Contracts

`ApplicationAction` is the shared provider-neutral action contract and
preserves exactly:

- `intent_id`: `OPEN_APPLICATION`.
- `capability_id`: `application.open`.
- `application_id`: An approved `ApplicationIdentifier`.

`PendingConfirmation` adds a confirmation identifier, original request
identifier, interaction language, and timezone-aware UTC creation and
expiration timestamps. It contains no raw request, AI output, provider prompt,
native executable, command line, permission grant, or SDK object.

`ConfirmationResolution` correlates one response request with one of:

- `NOT_APPLICABLE`: No pending action exists and the input is not an exact
  confirmation token. Normal request processing may continue.
- `NO_PENDING`: The input is an exact confirmation token but no action is
  pending. Processing ends without execution.
- `ACCEPTED`: An exact affirmative token consumed the pending action.
- `REJECTED`: An exact negative token consumed the pending action.
- `INVALIDATED`: Non-exact input consumed the pending action and cannot be
  reused as another command in the same request.
- `EXPIRED`: The pending action reached its expiration boundary and was
  consumed without execution.

`ConfirmationPrompt` contains only the confirmation identifier, intent,
approved target, expiration, and interaction language. The interface renders
human-readable text from those structured values.

All confirmation domain models are immutable, slotted, explicitly typed, and
use timezone-aware UTC timestamps.

---

# Coordinator

`ConfirmationCoordinator` owns the process-local confirmation lifecycle.
`InMemoryConfirmationCoordinator` maintains exactly one pending slot for one
runtime composition.

`begin()` creates a pending action only when no valid slot exists. It removes
an expired slot lazily and never replaces a valid pending action silently.

`resolve()` applies `strip()` and `casefold()` and accepts only complete tokens:

- Affirmative: `sim`, `s`, `confirmar`, `yes`, `y`, `confirm`.
- Negative: `não`, `nao`, `n`, `cancelar`, `no`, `cancel`.

Punctuation, suffixes, prefixes, composed instructions, and unrelated input do
not confirm. With a pending action, such input invalidates and consumes the
slot. The same submission is never reinterpreted as a new action.

Expiration is lazy and uses the injected `Clock`. The default lifetime is 120
seconds from validated Configuration and may be overridden through
`ATREUS_CONFIRMATION_TTL_SECONDS`. No timer, thread, scheduler, or background
worker is used.

---

# Request Flow

The first request follows the existing deterministic-first flow:

```text
Request
    -> Classifier
    -> Core captures one ContextSnapshot and one MemorySnapshot
    -> Decision Engine
    -> Request Interpreter, at most once when eligible
    -> Decision Engine
    -> ASK_FOR_CONFIRMATION
    -> ConfirmationCoordinator.begin
    -> structured ConfirmationPrompt
```

A later foreground response is a new request and therefore publishes its normal
request lifecycle events and receives its own single Context and Memory
snapshots. Core resolves confirmation before AI delegation.

`ACCEPTED` is supplied to Decision Engine in `DecisionInput.confirmation`.
Decision Engine revalidates correlation, action integrity, current capability
availability, user restrictions, configured permission policy, and operational
state. A valid acceptance returns `REQUEST_PLANNING`, never `EXECUTE`.

Core supplies the exact approved `ApplicationAction` instance to Planner.
Planner creates `application.open(application_id=<approved identifier>)`
without using the yes/no response or raw AI output. The consumed confirmation
is not restored if planning or execution later fails.

Capability Runtime remains the authoritative enforcer of permission grants,
dependencies, and availability before execution. System Layer continues to
enforce its native boundary. Confirmation cannot create or expand a permission
grant and does not freeze current system conditions.

---

# Dependencies

Core depends on `ConfirmationCoordinator` and `InteractionLanguageResolver`
through interfaces. Decision Engine and Planner consume immutable confirmation
contracts only. Bootstrap creates one coordinator per composition from the
validated TTL and injected `Clock`.

Capability Runtime, System Layer, Working Memory, Context Engine, and AI
Provider do not depend on the coordinator. Working Memory does not store pending
confirmation state.

---

# Events and Privacy

Interactive Confirmation V0 publishes no confirmation-specific events. Existing
`DecisionMade`, `RequestCompleted`, and sanitized `ErrorOccurred` events provide
the required observability.

Events and structured logs must not contain raw confirmation responses, raw AI
responses, translated prompt text, credentials, native commands, or exception
messages. Coordinator failures end the request before execution and surface
only sanitized orchestration metadata.

---

# Testing Requirements

Tests must cover immutable contracts, single-slot ownership, exact token sets,
lazy expiration, exact expiration boundaries, single-use consumption,
invalidation, replay prevention, PT-BR default behavior, clear English
selection, deterministic prompt rendering, permission preservation, current
availability revalidation, planner argument integrity, runtime isolation,
sanitized observability, and full offline flows with fake AI and System Layer
boundaries.

No confirmation test requires network access or a real provider credential.

---

# Future Evolution

Multiple sessions, durable authorization, richer interaction localization, and
additional confirmable action types require separate architecture and explicit
identity, concurrency, privacy, and permission policies.
