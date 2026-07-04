# ATREUS Development Guide

Version: 1.0

---

# Project Overview

ATREUS is an Adaptive Personal Intelligence Platform designed to assist users through contextual awareness, intelligent planning, modular capabilities, and continuous learning.

The objective is not to build a chatbot.

The objective is to build a long-term intelligent platform capable of understanding context, planning actions, executing capabilities, and continuously improving over time.

---

# Architecture Philosophy

ATREUS follows:

- Modular Architecture
- SOLID Principles
- Clean Architecture
- Separation of Concerns
- Low Coupling
- High Cohesion

Every architectural decision must preserve these principles.

---

# Documentation

Before implementing any module, always consult:

docs/architecture/

Architecture documents define the expected behavior of each component.

Never implement functionality that contradicts the documentation.

---

# Coding Standards

Every source file must follow:

- Python 3.13+
- Full type hints
- Google-style docstrings
- Small functions
- Small classes
- Explicit naming
- No unnecessary complexity

Avoid clever solutions.

Prefer readable code.

---

# Project Language

All project artifacts must be written in English.

This includes:

- Source code
- Documentation
- Comments
- Commit messages
- Class names
- Variables
- Methods

Conversations with the project owner may occur in Portuguese.

---

# Module Responsibilities

Every module must have one clear responsibility.

Business logic must never be mixed with:

- Configuration
- Logging
- Infrastructure
- Persistence

---

# Interfaces

Depend on abstractions rather than concrete implementations.

Interfaces define contracts.

Implementations define behavior.

---

# Error Handling

Raise meaningful exceptions.

Avoid silent failures.

Avoid generic exceptions.

---

# Logging

Never use print() for application logging.

Use the project's logging infrastructure.

print() is acceptable only for temporary debugging during development.

---

# Testing

Every implementation should be designed to be testable.

Prefer dependency injection over hardcoded dependencies.

---

# Future Evolution

Code should be written with extensibility in mind.

However, avoid implementing features that are not currently required.

Follow the documented architecture.

Do not anticipate future requirements with unnecessary complexity.

---

# AI Assistant Guidelines

When implementing code:

- Read the architecture documentation first.
- Never invent new architecture.
- Never rename documented modules.
- Never introduce unnecessary dependencies.
- Keep implementations simple.
- Respect the project structure.
- Follow Python best practices.
- Preserve consistency across the project.

If documentation and implementation conflict, documentation always takes precedence.