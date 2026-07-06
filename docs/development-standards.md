# Development Standards

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-07-06

---

# Purpose

This document defines the general software development standards for the ATREUS project.

All source code must follow these conventions to ensure consistency, readability, maintainability, and long-term scalability.

---

# Programming Language

The project uses:

- Python 3.13+

No compatibility with previous Python versions is required unless explicitly documented.

---

# Code Style

The project follows:

- PEP 8
- Explicit naming
- Four-space indentation
- UTF-8 encoding
- Type hints for all public APIs

Readability is preferred over clever implementations.

---

# Documentation

Every public class and function should include Google-style docstrings.

Documentation must explain intent rather than implementation details.

---

# Naming Conventions

Use descriptive names.

Examples:

- ConfigurationManager
- MemoryStore
- EventBus

Avoid abbreviations whenever possible.

---

# Type Hints

Public methods must use complete type hints.

Example:

```python
def load(path: Path) -> Configuration:
```

---

# Error Handling

Raise explicit exceptions.

Avoid generic exception handling.

Do not silently ignore errors.

---

# Logging

Application logging must use the project's logging infrastructure.

Avoid using print() outside temporary debugging.

---

# Architecture

Follow the documented architecture.

Never introduce architectural changes without updating documentation.

Documentation is the source of truth.

---

# Dependencies

Keep dependencies minimal.

Avoid unnecessary third-party libraries.

Prefer the Python standard library whenever appropriate.

---

# Testing

Design modules so they can be tested independently.

Favor dependency injection over tightly coupled implementations.

---

# AI Usage

AI-generated code must always be reviewed before being merged.

Generated code must comply with all project documentation.

---

# Git Workflow

Small commits.

Descriptive commit messages.

One logical change per commit.

Never commit broken code.

---

# Final Principle

Code should be written for humans first and computers second.

Maintainability is considered more important than brevity.