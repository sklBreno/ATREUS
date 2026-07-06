# ATREUS Development Guide

**Status:** Approved  
**Version:** 1.1  
**Last Updated:** 2026-07-06

---

# Project Overview

ATREUS is an Adaptive Personal Intelligence Platform designed to assist users through contextual awareness, intelligent planning, modular capabilities, and continuous learning.

The objective is not to build a chatbot.

The objective is to build a long-term intelligent platform capable of understanding context, planning actions, executing capabilities, and continuously improving over time.

---

# Architecture Philosophy

ATREUS follows the following architectural principles:

- Modular Architecture
- SOLID Principles
- Clean Architecture
- Separation of Concerns
- Low Coupling
- High Cohesion

Every architectural decision must preserve these principles.

Architecture documentation is considered the source of truth.

---

# Documentation

Every implementation must be based on the project documentation.

Never implement functionality that contradicts documented behavior.

Documentation always takes precedence over assumptions.

---

# Required Reading

Before implementing any code, read the following documents in order:

1. README.md
2. docs/manifesto.md
3. docs/project-vision.md
4. docs/architecture/overview.md
5. docs/development-standards.md
6. docs/guides/module-development-standard.md
7. docs/guides/interface-standard.md
8. docs/guides/ai-development-workflow.md

After reading the core documentation, read the architecture document related to the requested task.

Examples:

- docs/architecture/configuration.md
- docs/architecture/memory.md
- docs/architecture/planner.md
- docs/architecture/core.md
- docs/architecture/event-bus.md
- docs/architecture/context-engine.md

---

# Coding Standards

Every source file must follow:

- Python 3.13+
- Full type hints
- Google-style docstrings
- Explicit naming
- Small functions
- Small classes
- Single Responsibility Principle
- Readable code over clever code

Avoid unnecessary complexity.

Prefer composition over inheritance whenever appropriate.

Use the Python standard library whenever possible.

---

# Project Language

All project artifacts must be written in English.

This includes:

- Source code
- Documentation
- Comments
- Commit messages
- Branch names
- Class names
- Function names
- Variables
- Exceptions

Conversations with the project owner may occur in Portuguese.

---

# Module Responsibilities

Each module must have a single, clearly defined responsibility.

Business logic must never be mixed with:

- Configuration
- Logging
- Persistence
- Infrastructure
- External services

Modules should remain highly cohesive and loosely coupled.

---

# Interfaces

Depend on abstractions rather than concrete implementations.

Interfaces define contracts.

Implementations define behavior.

Respect the Dependency Inversion Principle.

---

# Error Handling

Raise meaningful and explicit exceptions.

Avoid generic exceptions whenever possible.

Never silently ignore errors.

Every failure should provide enough information for troubleshooting.

---

# Logging

Never use `print()` for application logging.

Use the project's logging infrastructure.

Temporary debugging using `print()` is acceptable only during local development.

---

# Testing

Every implementation should be designed to be testable.

Prefer dependency injection.

Avoid hidden dependencies.

Implementations should support isolated unit testing.

---

# Git Workflow

Development follows a feature branch workflow.

Rules:

- Never commit directly to the main branch.
- Create one feature branch per task.
- Keep commits small and focused.
- Write descriptive commit messages.
- Submit changes for review before merging.

Examples:

```
feature/configuration-manager
feature/event-bus
feature/memory-store
```

---

# Future Evolution

Design for extensibility.

Do not implement features that are not currently required.

Avoid premature optimization.

Keep implementations simple and maintainable.

---

# AI Assistant Guidelines

When implementing code:

- Read AGENTS.md first.
- Read all required documentation before writing code.
- Read the architecture document for the requested module.
- Never invent architecture.
- Never rename documented modules.
- Never modify unrelated files.
- Never introduce unnecessary dependencies.
- Keep implementations simple.
- Respect the documented project structure.
- Follow Python best practices.
- Preserve consistency across the entire project.
- Implement only the requested functionality.
- Ask for clarification if documentation is ambiguous.

If documentation and implementation conflict, documentation always takes precedence.

---

# Final Principle

ATREUS is designed as a long-term software platform.

Prioritize:

1. Readability
2. Maintainability
3. Consistency
4. Testability
5. Extensibility

Short-term convenience must never compromise the long-term architecture of the project.