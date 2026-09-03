# ADR-006 — Explicit Local Personal Profile

**Status:** Accepted

**Date:** 2026-09-03

---

# Context

ATREUS needs stable user-approved facts and preferences for useful personal
conversation. Conversation History is bounded dialogue continuity, Working
Memory is volatile operational memory, and Context is the current observed
situation. None is an appropriate owner for an intentionally persisted user
profile.

Automatically learning personal information would introduce unresolved
privacy, authorization, correction, provenance, and retention policy.

# Decision

ATREUS introduces Personal Profile as a distinct opt-in module. Version 0 uses
a strict typed schema and atomic local JSON persistence outside the repository.
Profile data enters only through a complete structured file that the user
reviews and explicitly imports.

Conversation Responder may receive a deterministic bounded projection of only
clearly relevant approved fields. Request Interpreter and the operational
pipeline receive no profile. Profile data cannot authorize an action or infer
an execution target.

Read and show are deterministic and make no AI request. Clear requires a
dedicated expiring confirmation because the existing confirmation contract is
specific to application actions. Profile-derived exchanges are not retained in
Conversation History.

Version 0 publishes no profile events and excludes profile content from logs,
errors, representations, and AI lifecycle events.

# Consequences

Positive consequences:

- Stable personalization remains explicit and user-controlled.
- Local storage is human-readable, portable, and dependency-free.
- Cloud disclosure is selective and bounded.
- Operational authorization remains independent from personal data.
- Invalid imports and failed writes cannot partially mutate a valid profile.

Trade-offs:

- External imports require process restart before an existing composition sees
  the replacement.
- Profile-influenced exchanges do not provide short-term follow-up continuity.
- Granular editing, migration, learned facts, and synchronization remain future
  work.

# Alternatives Considered

Working Memory and Conversation History were rejected because their lifecycle
and semantics are intentionally volatile. Configuration was rejected because it
does not persist user data. SQLite was rejected as unnecessary for one bounded
document. TOML lacks standard-library writing support, and YAML would require
an external dependency. Automatic AI extraction was rejected because it would
violate explicit approval and data minimization.

# Related Components

- Personal Profile.
- Conversational AI.
- Conversation History.
- Working Memory.
- Configuration.
- Bootstrap.
- AI Provider.
- Interactive Confirmation.
