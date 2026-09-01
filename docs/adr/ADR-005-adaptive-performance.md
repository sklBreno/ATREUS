# ADR-005 — Adaptive Performance

**Status:** Accepted

**Date:** 2026-07-02

**Last Updated:** 2026-08-31

---

# Context

ATREUS is intended to remain available throughout the user's computing session.

However, continuous availability should never come at the expense of system performance.

Users frequently execute resource-intensive applications such as games, development environments, rendering software, virtual machines, and data processing workloads.

During these situations, ATREUS must automatically adapt its behavior to minimize its impact on the system.

Performance is therefore considered an essential aspect of user experience rather than a technical optimization.

---

# Decision

ATREUS adopts an Adaptive Performance model.

Decision Engine evaluates system signals, current context, validated
configuration, and user policy to determine the desired performance profile.

Instead of maintaining a fixed performance profile, the platform dynamically adjusts its behavior according to current conditions.

Core records and propagates the selected profile. Each module adapts its own
permitted activity to the active profile. Performance adaptation is automatic
but always configurable by the user.

---

# Performance Profiles

ATREUS operates using three performance profiles.

Performance profiles are separate from the `ACTIVE`, `PASSIVE`, and `STANDBY`
operational states owned by Core.

## `PERFORMANCE`

Selected when approved context and system signals indicate demanding workloads.

Examples include:

- Gaming
- Video rendering
- Virtual machines
- Heavy software compilation
- AI inference
- High CPU or GPU utilization

Behavior:

- Suspend non-essential background tasks.
- Disable proactive suggestions.
- Reduce monitoring frequency.
- Delay maintenance activities.
- Minimize CPU and memory usage.

---

## `BALANCED`

Configured baseline performance profile.

Behavior:

- Normal monitoring.
- Context detection.
- Event processing.
- Proactive assistance.
- Standard background activity.

This profile provides the best balance between responsiveness and resource usage.

---

## `IDLE`

Selected when context, system signals, configuration, and user policy permit
eligible deferred activity.

The `IDLE` performance profile is not the same concept as the Context Engine's
`IDLE` user context.

Behavior:

- Execute maintenance tasks.
- Synchronize data.
- Learn usage patterns.
- Clean temporary information.
- Perform deferred operations.

Background processing should prioritize tasks that are not time-sensitive.

---

# Adaptive Decision Making

Decision Engine should consider multiple factors simultaneously when selecting
the desired performance profile.

Examples include:

- CPU utilization.
- GPU utilization.
- Available memory.
- Battery level.
- Power source.
- Active applications.
- Current user context.
- User-defined preferences.

No single metric should determine the active profile.

Decision Engine should evaluate the overall environment before returning a
profile decision. It does not apply the change; Core records and propagates the
approved profile.

---

# User Experience

Performance adaptation should occur automatically whenever possible.

The user should not need to select a profile manually or disable background
processing.

Changes between profiles should be smooth, predictable, and transparent.

Users may override automatic behavior at any time.

---

# Rationale

Adaptive Performance allows ATREUS to remain continuously available without negatively affecting the user's primary activity.

Instead of maximizing its own performance, the platform prioritizes the user's experience.

This philosophy reinforces the project's principle that assistance should never become interference.

---

# Consequences

Positive:

- Lower CPU utilization.
- Reduced memory consumption.
- Better gaming experience.
- Improved battery life.
- Lower system impact.
- Better overall responsiveness.

Trade-offs:

- Requires continuous performance monitoring.
- Adaptive decisions increase implementation complexity.
- Incorrect profile detection may temporarily reduce functionality.

---

# Alternatives Considered

## Fixed Performance Profile

Rejected.

A static resource profile cannot satisfy the different requirements of work, gaming, study, and idle periods.

---

## Manual Performance Selection

Rejected.

Requiring the user to manually switch profiles introduces unnecessary friction and reduces automation.

Automatic adaptation is preferred.

---

## Maximum Performance at All Times

Rejected.

Maintaining full platform activity continuously wastes resources and conflicts with the project's design philosophy.

---

# Related Components

- Context Engine
- Decision Engine
- System Layer
- Event Bus
- Core

---

# Future Considerations

Future versions may include:

- Machine learning-based performance prediction.
- Personalized resource optimization.
- Hardware-aware tuning.
- Cloud-assisted workload distribution.
- Energy optimization profiles.

Adaptive Performance should continuously evolve while remaining transparent and fully configurable.
