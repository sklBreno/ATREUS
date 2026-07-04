# ADR-001 — Hybrid Interaction Model

**Status:** Accepted

**Date:** 2026-07-02

---

# Context

One of the earliest architectural decisions of ATREUS concerns how user interactions should be interpreted.

Traditional assistants usually rely on one interaction model.

Some systems expect explicit commands.

Others depend almost entirely on natural language and Large Language Models.

Neither approach fully satisfies the goals of ATREUS.

The platform is intended to become a long-term personal intelligence system capable of responding efficiently to simple requests while also understanding complex intentions and natural conversations.

This requires a more flexible interaction model.

---

# Decision

ATREUS adopts a hybrid interaction model.

Every user request will first be classified before any execution takes place.

The system supports multiple categories of interaction instead of treating every message as plain text.

The initial request types are:

- Command
- Intention
- Question
- Task
- Conversation

The Request Classifier is responsible for identifying the request type and routing it to the appropriate module.

Examples:

Command

> "Open Visual Studio Code."

↓

Skill Manager

---

Intention

> "Let's work on ATREUS."

↓

Planner

↓

Multiple Skills

---

Question

> "What is Active Directory?"

↓

AI Provider

---

Task

> "Remind me tomorrow at 8 AM."

↓

Planner

↓

Task Scheduler

---

Conversation

> "Good morning."

↓

Conversation Engine

---

The user is not required to specify the request type explicitly.

Classification is performed automatically by the platform.

---

# Rationale

This architecture provides several advantages.

Simple commands can be executed immediately without requiring an AI model.

Complex intentions can be decomposed into multiple actions.

Questions can leverage AI only when necessary.

Tasks can be scheduled independently from conversations.

This separation improves performance, maintainability, modularity, and user experience.

It also prevents the platform from depending entirely on Large Language Models.

---

# Consequences

Positive:

- Faster execution of deterministic actions.
- Reduced AI dependency.
- Lower operational costs.
- Improved modularity.
- Easier expansion of new request types.
- Better separation of responsibilities.

Trade-offs:

- Requires an additional classification layer.
- Incorrect classifications may lead to inappropriate routing.
- The Request Classifier becomes a critical component of the platform.

---

# Alternatives Considered

## Command-only architecture

Rejected.

Although simple and efficient, it does not support natural interaction or proactive assistance.

---

## AI-only architecture

Rejected.

Sending every request directly to a language model introduces unnecessary latency, higher costs, and excessive dependence on external AI providers.

---

## Intent-only architecture

Rejected.

Intentions alone cannot accurately represent every interaction.

Direct commands, scheduled tasks, and casual conversations require different execution paths.

The hybrid model provides greater flexibility while maintaining a consistent user experience.

---

# Related Components

- Request Classifier
- Core
- Planner
- Skill Manager
- AI Provider
- Conversation Engine

---

# Future Considerations

The list of request types may expand in future versions.

Possible additions include:

- Notification
- System Event
- Automation Trigger
- Workflow
- Emergency

The hybrid model is designed to evolve without requiring changes to the platform's core architecture.