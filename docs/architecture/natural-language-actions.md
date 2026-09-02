# Natural Language Actions

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-09-02

---

# Purpose

Natural Language Actions V1 allows a bounded set of desktop application
requests to enter the existing ATREUS pipeline without making AI an execution
or authorization boundary.

V1 supports exactly:

- `OPEN_APPLICATION`
- `APPLICATION_STATUS`

Close, focus, minimize, maximize, arbitrary process operations, filesystem
actions, browser automation, and shell execution are deferred.

---

# Application Action Contract

`ApplicationAction` is the immutable provider-neutral action shared by request
interpretation, Decision Engine, Interactive Confirmation when required, and
Planner. It contains only:

- `intent_id`: An approved `ApplicationIntent`.
- `capability_id`: A locally selected Capability Registry identifier.
- `application_id`: An approved platform-neutral `ApplicationIdentifier`.

It never contains an executable, process name, process identifier, path,
command line, shell syntax, provider response, or permission grant.

The local typed action matrix is authoritative for intent and target support:

| Intent | Application | Capability | V1 support |
| --- | --- | --- | --- |
| `OPEN_APPLICATION` | `calculator` | `application.open` | Supported |
| `OPEN_APPLICATION` | `notepad` | `application.open` | Supported |
| `OPEN_APPLICATION` | `spotify` | `application.open` | Unsupported |
| `APPLICATION_STATUS` | `calculator` | `application.status` | Supported |
| `APPLICATION_STATUS` | `notepad` | `application.status` | Supported |
| `APPLICATION_STATUS` | `spotify` | `application.status` | Unsupported |

AI returns only an intent identifier, target identifier, and confidence. The
local interpreter validates that output and creates the action from this
matrix. AI cannot supply a capability identifier.

---

# Request Flow

Deterministic commands retain their zero-AI path:

```text
open calculator / open notepad
    -> Request Classifier
    -> Core
    -> Decision Engine
    -> Planner
    -> Capability Runtime
    -> application.open
```

Eligible natural application-open requests use one bounded AI interpretation:

```text
Natural open request
    -> Request Classifier
    -> Core
    -> Decision Engine
    -> Request Interpreter
    -> AI Provider
    -> local action validation
    -> Decision Engine
    -> ASK_FOR_CONFIRMATION
    -> later exact acceptance
    -> Decision Engine
    -> Planner
    -> Capability Runtime
    -> application.open
```

The exact same `ApplicationAction` instance is preserved from interpretation
through Decision Engine, pending confirmation, and planning. Raw request text
and raw provider output are never used to reconstruct the confirmed action.

Eligible natural status requests are read-only and do not require
confirmation:

```text
Natural status request
    -> Request Classifier
    -> Core
    -> Decision Engine
    -> Request Interpreter
    -> AI Provider
    -> local action validation
    -> Decision Engine
    -> Planner
    -> Capability Runtime
    -> application.status
    -> ApplicationStateReader
```

The provider is invoked at most once. Status rendering is deterministic and
does not make another AI request.

---

# Capabilities and Permissions

`application.open` is a side-effecting capability and requires
`application.control`.

`application.status` is read-only and requires `application.read`. Its result
contains the approved application identifier and one normalized state:

- `RUNNING`
- `NOT_RUNNING`
- `UNKNOWN`

Capability Runtime remains the authoritative invocation-time permission
enforcer. System Layer adapters enforce the same permission at the native
boundary. Confirmation never creates a grant.

---

# System Layer

Application launch and state observation use separate narrow interfaces:

- `ApplicationLauncher`
- `ApplicationStateReader`

The Windows launcher resolves only fixed internal mappings:

- `calculator` to `calc.exe`
- `notepad` to `notepad.exe`

The Windows state reader performs one fixed `tasklist.exe` observation with
`shell=False` and compares results only with internal approved identities:

- `calculator` to `CalculatorApp.exe` or `calc.exe`
- `notepad` to `notepad.exe`

The Calculator identity includes the installed Windows Calculator process name
verified during V1 development and the legacy launcher identity. Incomplete
native evidence produces `UNKNOWN`; a complete observation without an approved
identity produces `NOT_RUNNING`.

Spotify has no approved V1 launch or status mapping. No URI, browser, shell,
Start-Process, registry scan, or process-name guess is used as a workaround.

Application identifiers remain distinct from executable and process names.
User and AI input can never become a native command, path, process name, or PID.

---

# Language and Rendering

Brazilian Portuguese is the default interaction language. English is the
secondary language. Ambiguous language resolves to Brazilian Portuguese.

The foreground interface owns deterministic display names and status
sentences. Operational application identifiers remain untranslated and are not
derived from user text. AI is not used for confirmation or status rendering.

---

# Failure and Security Policy

Unknown intents, unknown targets, unsupported combinations, malformed provider
output, missing permissions, and suspicious or composed commands fail closed.
The bounded AI fallback is not entered for paths, executable syntax, PIDs,
arbitrary process requests, shell operators, multiple actions, PowerShell,
`cmd`, or allowlist-bypass language.

Native adapter failures become sanitized capability failures. Status does not
retry automatically. Open does not promise idempotency and does not perform a
mandatory pre-launch process check.

Existing events are sufficient for V1. Events and structured logs exclude raw
requests, raw AI responses, executables, native process names, PIDs, handles,
capability arguments, outputs, and permission grants.

---

# Future Evolution

Future milestones may add separately reviewed intents, targets, platform
adapters, and richer status evidence. `CLOSE_APPLICATION`,
`APPLICATION_FOCUS`, generic process control, and arbitrary native execution
are not part of V1 and must not be inferred from these contracts.
