# Module Development Standard

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-07-05

---

# Purpose

This document defines the standard structure for every module developed within the ATREUS platform.

Following a consistent structure improves readability, maintainability, scalability, and long-term evolution.

Every module in ATREUS must follow these standards.

---

# General Principles

Every module must:

- Have a single responsibility.
- Be easy to understand.
- Be easy to test.
- Be easy to replace.
- Be independent whenever possible.

Complexity should emerge only when necessary.

---

# Standard Structure

A module should follow the structure below whenever applicable.

```
module/

    manager.py

    models.py

    exceptions.py

    loader.py

    validator.py
```

Not every module requires every file.

Only create files that have a clear responsibility.

---

# Responsibilities

Each file must have one responsibility.

Example:

manager.py

Coordinates the module.

models.py

Defines data structures.

loader.py

Loads data.

validator.py

Validates data.

exceptions.py

Defines module-specific exceptions.

---

# Class Design

Classes should:

- Be small.
- Have one responsibility.
- Be highly cohesive.
- Avoid unnecessary inheritance.
- Prefer composition.

---

# Function Design

Functions should:

- Have descriptive names.
- Perform one task.
- Return predictable values.
- Avoid side effects.

---

# Type Hints

All public methods must use full type hints.

Example:

```python
def load(path: str) -> Configuration:
```

---

# Documentation

Every public class and method must include Google-style docstrings.

---

# Error Handling

Never ignore errors.

Raise meaningful exceptions.

Avoid:

```python
except:
    pass
```

Prefer:

```python
raise InvalidConfigurationError(...)
```

---

# Logging

Modules must never use print().

Use the project's logging system.

Temporary debugging using print() is acceptable only during development.

---

# Dependencies

Modules should depend on interfaces whenever possible.

Avoid direct dependencies on concrete implementations.

---

# Testing

Every module should be testable in isolation.

Design with dependency injection whenever possible.

---

# Code Style

Follow:

- Python 3.13+
- PEP 8
- Explicit naming
- Small classes
- Small methods

Readability is always preferred over cleverness.

---

# Future Evolution

Modules should be designed to support future extensions without requiring major refactoring.

Avoid implementing features before they are required.

Keep implementations minimal.

---

# Final Rule

Consistency is more valuable than personal preference.

Every module should look like it belongs to the same project.