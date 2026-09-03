# Personal Profile

**Status:** Draft

**Version:** 1.0

**Last Updated:** 2026-09-03

---

# Purpose

Personal Profile V0 stores explicit, relatively stable facts and preferences
that the user reviewed and approved. It is local, structured, versioned,
reviewable, replaceable, and removable.

Personal Profile is not Conversation History, Working Memory, current Context,
Configuration, self-knowledge, or future Long-Term Memory. No information is
promoted automatically between these boundaries.

# Version 0 Scope

V0 supports:

- Opt-in local JSON persistence.
- Strict immutable typed models using schema version 1.
- Explicit import from a reviewed structured file.
- Deterministic bilingual read and show requests.
- Deterministic bounded conversational projection.
- Dedicated expiring confirmation before profile clear.

V0 has no automatic learning, conversational extraction, natural-language
field mutation, AI-generated writes, semantic retrieval, embeddings, vector
database, synchronization, or Long-Term Memory.

# Data Contracts

`PersonalProfile` contains optional immutable sections for identity, education,
career, technical environment, learning preferences, projects, hobbies, and
interaction preferences. Collections are tuples. All strings are normalized,
bounded, and reject control characters. `updated_at` is timezone-aware UTC.

Profile content is excluded from object representations. The file requires
`schema_version = 1`. Unknown properties and unsupported versions fail closed.
V0 does not attach confidence, provenance, or per-fact timestamps because a
complete profile becomes authoritative only through explicit reviewed import.

The schema has no dedicated field for credentials, passwords, API keys,
banking data, credit cards, government identifiers, medical information, raw
messages, or secrets. Free-form descriptions remain user-reviewed input; V0
does not attempt unreliable generic secret detection.

# Public Interfaces

`PersonalProfileProvider` exposes only `get_profile()`.

`PersonalProfileStore` extends that boundary with complete `replace()` and
`clear()` operations. The domain interface contains no filesystem path.

`PersonalProfileProjectionProvider` selects a bounded provider-safe projection
for one conversational request. `PersonalProfileInteractionHandler` handles
only exact local profile requests and returns a conversational response when
applicable.

# JSON Persistence

`JsonPersonalProfileStore` receives an absolute path and `Clock` through
dependency injection. The default Windows location is
`%LOCALAPPDATA%\ATREUS\profile.json`. POSIX composition uses
`$XDG_DATA_HOME/ATREUS/profile.json` or
`~/.local/share/ATREUS/profile.json`.

Persistence uses UTF-8 deterministic JSON and a 256 KiB input bound. Writes use
a temporary file in the destination directory, flush, `fsync`, and
`os.replace`. A failed write removes its temporary file where possible and
leaves both the previous file and current in-memory profile unchanged. Clear
atomically writes a valid empty version 1 profile rather than deleting an
arbitrary file.

The store loads once per composition and then exposes its cached immutable
profile. A missing file produces a valid empty profile. Malformed JSON,
unsupported schema, oversized input, and permission failure produce sanitized
explicit errors and never overwrite the source document. V0 has no hot reload.

# Configuration and Composition

Personal Profile is disabled by default. Configuration provides:

- `personal_profile_enabled`, default `False`.
- `personal_profile_projection_max_characters`, default `2000`.
- `personal_profile_clear_confirmation_ttl_seconds`, default `120`.

The matching environment names follow the standard process environment over
`.env` over defaults priority. Profile values are never Configuration values or
environment variables. V0 has no public profile-path override.

When disabled, Bootstrap composes an empty no-disk store. When enabled,
Bootstrap resolves the per-user data path, creates one JSON store, loads one
profile, and shares that store with the projection and interaction boundaries.
Tests and special composition may inject a path directly. Bootstrap remains
only the composition root.

# Reviewed Import

The administrative importer accepts the persisted version 1 schema directly:

```text
python -m atreus.profile.importer validate <reviewed-file>
python -m atreus.profile.importer apply <reviewed-file> --confirm
```

Validation constructs the complete immutable profile and performs no mutation.
Apply requires explicit confirmation, validates before writing, and replaces
the destination atomically. The importer has no ChatGPT, OpenAI, AI Provider,
conversation extraction, or natural-language write integration.

# Conversational Projection

Only `ConversationResponder` may receive a profile projection. The deterministic
projection provider uses narrow topic markers for technical, career, education,
learning, project, and interaction requests. It returns `None` when no category
is clearly relevant.

Selected values are JSON-quoted inside explicit `user_profile_data` delimiters.
The system instruction identifies them as declarative user data, never policy,
instructions, authorization, or proof of execution. The current request
language remains authoritative. The configured character limit is applied
before an `AIRequest` is created.

Ollama receives only the selected projection through its local endpoint. When
OpenAI is selected, only that same bounded projection is disclosed to the
cloud provider. The complete profile is never sent automatically.

A response generated with a profile projection is not appended to Conversation
History. Deterministic profile read, show, and clear exchanges are also not
retained. This prevents profile-derived content from being retransmitted in a
later unrelated request.

# Read and Clear Interaction

Exact read requests are handled locally with no AI call:

- `o que você sabe sobre mim?`
- `mostrar meu perfil`
- `what do you know about me?`
- `show my profile`

Rendering is localized, deterministic, and displays only populated sections.
ATREUS self-knowledge remains a separate response path.

`limpar meu perfil` and `clear my profile` create one process-local pending
clear and perform no mutation. A valid pending request must be followed by the
exact dedicated phrase `confirmar limpeza do meu perfil` or
`confirm clearing my profile`. Generic `sim`, `yes`, `s`, and `y` never clear a
profile. The confirmation expires lazily after its configured lifetime and is
consumed only after successful persistence. Replay and confirmation without a
pending request are non-destructive.

The existing Interactive Confirmation contract is application-specific and is
not reused. Profile clear does not clear Conversation History, Working Memory,
Configuration, Context, or operational confirmation state.

# Operational Isolation

Personal Profile is unavailable to Request Interpreter, Decision Engine,
Planner, operational Confirmation, Capability Runtime, CapabilityInvocation,
ExecutionContext, and System Layer. It cannot grant permission, authorize an
action, infer an operational target, or resolve references such as `open it`.

Request Classifier recognizes only the exact profile interaction phrases as
safe internal conversation. It never receives augmented content or profile
data. Core continues to route the existing `ConversationResponder` boundary and
does not know that a profile exists.

# Privacy and Observability

Profile data is local, opt-in, and never synchronized automatically. Profile
fields, projections, display names, project names, hardware values, imported
documents, and storage paths do not appear in events, logs, exceptions, or
default object representations.

V0 publishes no profile event. Existing AI lifecycle and request events retain
their content-free schemas. User-facing profile display and administrative
import status are interaction output, not application logging.

# Testing Requirements

Tests cover immutable contracts, strict JSON decoding, unknown-field rejection,
UTF-8 round trips, size bounds, atomic replacement, temporary cleanup, failure
preservation, explicit import confirmation, path isolation, deterministic
projection, provider disclosure, read/show without AI, clear confirmation,
expiration, replay safety, Conversation History exclusion, operational
isolation, configuration priority, privacy, and full regression behavior.

# Future Evolution

V1 may add explicit granular edits, correction and forget commands, and profile
change history. Later work may add a user-approved candidate queue and explicit
policy for interaction with Long-Term Memory. Semantic retrieval, learned facts,
mobile synchronization, distributed profile service, identity, permissions,
version conflicts, and migration require separate architecture.

AI may suggest candidates in a future approved workflow but must never write
directly to Personal Profile.
