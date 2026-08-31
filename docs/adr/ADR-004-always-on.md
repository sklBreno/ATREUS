# ADR-004 — Always-On Architecture

**Status:** Accepted

**Date:** 2026-07-02

**Last Updated:** 2026-08-31

---

# Context

Traditional assistants usually operate on demand.

They remain inactive until explicitly launched or invoked by the user.

While this approach minimizes resource consumption, it also prevents continuous context awareness, proactive assistance, and long-term learning.

ATREUS is intended to become a persistent personal intelligence platform capable of understanding the user's environment throughout the day.

To achieve this objective, the platform must remain available at all times while respecting system performance and user preferences.

---

# Decision

ATREUS adopts an Always-On Architecture.

The platform starts automatically when the operating system boots and remains active as a background service throughout the user session.

Rather than continuously performing expensive computations, ATREUS operates as a lightweight event-driven platform.

Most modules remain idle until triggered by relevant events.

---

# Operational Model

ATREUS follows three operational states: `ACTIVE`, `PASSIVE`, and `STANDBY`.

The Core owns the current operational state because it owns platform lifecycle
and orchestration. Context Engine provides context, System Layer provides system
signals, and Decision Engine may determine a desired transition. Core validates
and applies the transition.

## `ACTIVE`

The platform is fully operational.

It monitors approved contextual information, processes user requests, and
coordinates approved capabilities through Capability Runtime when appropriate.

---

## `PASSIVE`

The platform remains available but performs only lightweight monitoring.

No unnecessary processing occurs.

This is the default state during normal computer usage.

---

## `STANDBY`

The platform minimizes its resource consumption.

Only essential background services remain active.

A transition to `STANDBY` may be proposed by Decision Engine using context,
configuration, user policy, and signals such as:

- Gaming
- High CPU workloads
- High GPU workloads
- Battery-saving scenarios
- User-defined conditions

No single signal applies the transition directly. Core remains responsible for
validating and applying the selected operational state.

---

# Startup Behavior

When the operating system starts:

1. ATREUS initializes automatically.
2. Core services are loaded.
3. Configuration is validated.
4. Context detection begins.
5. Event monitoring starts.
6. Optional modules are loaded on demand.

The platform should become operational as quickly as possible without delaying system startup.

---

# Event-Driven Operation

ATREUS should avoid continuous polling whenever possible.

Instead, it reacts to approved events such as:

- User requests
- Context changes
- System notifications
- File system events
- Device connections
- Calendar events

Time-based behavior requires separately approved architecture. A future time
source may publish an approved event, after which Core can coordinate an
available capability through explicit interfaces. Version 1 does not define a
dedicated scheduling module.

This minimizes resource consumption while improving responsiveness.

---

# Resource Management

The platform should continuously monitor its own impact on the system.

Goals include:

- Low CPU utilization
- Low memory consumption
- Minimal disk activity
- Minimal battery impact

Whenever resource usage exceeds predefined thresholds, ATREUS should reduce background activity.

Performance is considered a first-class architectural concern.

---

# User Control

The Always-On behavior is fully configurable.

Users may choose:

- Start automatically with the operating system.
- Disable automatic startup.
- Select which modules start automatically.
- Configure Standby conditions.
- Pause the platform temporarily.

The user always remains in control.

---

# Rationale

Maintaining a persistent presence enables ATREUS to provide context awareness, continuous learning, and proactive assistance without requiring explicit activation.

An event-driven architecture ensures these capabilities are delivered efficiently while minimizing resource consumption.

---

# Consequences

Positive:

- Immediate availability.
- Continuous context awareness.
- Better proactive assistance.
- Faster response times.
- Long-term learning becomes possible.

Trade-offs:

- Requires careful resource management.
- Startup sequence becomes more complex.
- Background services require additional monitoring.
- Improper implementation could negatively impact performance.

---

# Alternatives Considered

## Manual Startup

Rejected.

Requiring the user to manually launch the platform prevents continuous context awareness and reduces usability.

---

## Always Active Processing

Rejected.

Continuously executing heavy background tasks would waste system resources and reduce overall performance.

ATREUS should remain event-driven instead.

---

## Interval-Only Activation

Rejected.

Running the platform only from predefined time-based triggers would delay
context detection and reduce responsiveness. Future approved time-based events
may complement Always-On operation but do not replace it.

---

# Related Components

- Core
- Context Engine
- Decision Engine
- Event Bus
- System Layer

---

# Future Considerations

Future versions may introduce:

- Adaptive startup optimization.
- Dynamic module loading.
- Multi-device synchronization.
- Distributed background processing.
- Energy-aware orchestration policies.

The Always-On Architecture should remain lightweight, configurable, and respectful of the user's computing environment.
