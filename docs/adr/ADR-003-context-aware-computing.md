# ADR-003 — Context-Aware Computing

**Status:** Accepted

**Date:** 2026-07-02

---

# Context

Most digital assistants operate in a reactive manner.

They wait for explicit user commands before performing any action.

Although effective for simple interactions, this model ignores one of the most valuable sources of information available: context.

The same request may require different behavior depending on what the user is currently doing.

Likewise, there are situations where the system should proactively assist the user without requiring an explicit command.

For ATREUS to become a true personal intelligence platform, contextual awareness must be considered a core architectural capability rather than an optional feature.

---

# Decision

ATREUS adopts a Context-Aware Computing architecture.

The platform continuously evaluates the user's computing environment in order to understand the current operational context.

Context is treated as a first-class architectural concept.

Every major decision taken by the platform may consider the current context before execution.

Examples of contexts include:

- Working
- Studying
- Gaming
- Meeting
- Entertainment
- Idle

The Context Engine is responsible for detecting and maintaining the active context.

Other modules consume contextual information but never determine context themselves.

---

# Context Engine Responsibilities

The Context Engine is responsible for:

- Detecting the user's current activity.
- Monitoring changes in system state.
- Identifying transitions between contexts.
- Publishing context change events.
- Providing the current context to other platform components.

It does not execute actions.

It only provides situational awareness.

---

# Context Sources

The Context Engine may use multiple information sources, including:

- Running applications.
- Active window.
- CPU and GPU utilization.
- User activity.
- Scheduled calendar events.
- Time of day.
- Connected devices.
- User-defined preferences.
- Future platform integrations.

The platform should combine multiple signals instead of relying on a single indicator whenever possible.

---

# Context Usage

Context influences multiple platform behaviors.

Examples include:

Gaming

- Reduce CPU usage.
- Suppress notifications.
- Pause non-essential background tasks.

Working

- Enable productivity suggestions.
- Recommend automations.
- Surface relevant reminders.

Meeting

- Silence voice notifications.
- Avoid interruptions.
- Delay non-critical recommendations.

Studying

- Suggest learning resources.
- Track study sessions.
- Minimize distractions.

Idle

- Execute maintenance tasks.
- Perform synchronization.
- Learn usage patterns.

---

# Proactive Assistance

Context awareness enables responsible proactivity.

ATREUS may proactively offer assistance when sufficient contextual confidence exists.

Examples include:

- Suggest opening frequently used development tools.
- Recommend breaks after extended work sessions.
- Warn about low storage availability.
- Detect repetitive workflows.
- Offer relevant automations.

Proactive behavior should always remain predictable, transparent, and optional.

---

# Privacy Considerations

Context awareness must always respect user privacy.

Users remain in full control of:

- Which context sources are monitored.
- Which contextual behaviors are enabled.
- What information may be stored.
- How long contextual information is retained.

Context collection must never become hidden surveillance.

Transparency is a mandatory design principle.

---

# Rationale

Making context a fundamental architectural component enables ATREUS to become significantly more adaptive without increasing user effort.

Instead of requiring continuous manual interaction, the platform can intelligently adjust its behavior according to the user's current situation.

This improves usability while reducing unnecessary interruptions.

---

# Consequences

Positive:

- More natural interaction.
- Better proactive assistance.
- Reduced unnecessary notifications.
- Improved user experience.
- Better resource management.
- Foundation for future learning capabilities.

Trade-offs:

- Increased architectural complexity.
- Requires accurate context detection.
- Context classification may occasionally be incorrect.
- Additional privacy safeguards become necessary.

---

# Alternatives Considered

## Reactive-only Architecture

Rejected.

Waiting exclusively for explicit user commands prevents proactive assistance and ignores valuable contextual information.

---

## AI-Based Context Detection

Rejected.

Although AI may contribute to context understanding in specific scenarios, context detection should primarily rely on deterministic system information whenever possible.

This improves performance, predictability, privacy, and reliability.

---

## Manual Context Selection

Rejected.

Requiring the user to manually select their current context creates unnecessary friction and reduces the platform's intelligence.

Automatic detection remains the preferred approach.

---

# Related Components

- Context Engine
- Decision Engine
- Core
- Planner
- Memory
- Skill Manager
- Event Bus

---

# Future Considerations

Future versions of ATREUS may introduce:

- Multi-context detection.
- Context confidence scoring.
- Personalized context models.
- Environmental awareness.
- Cross-device context synchronization.

The Context Engine should continuously evolve without requiring changes to the platform's overall architecture.
