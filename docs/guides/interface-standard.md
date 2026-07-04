# Interface Standard

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-07-05

---

# Purpose

This document defines the standards for designing and implementing interfaces within the ATREUS platform.

Its objective is to ensure consistency, maintainability, low coupling, and long-term scalability across the entire project.

Every interface created in ATREUS must follow the rules defined in this document.

---

# Philosophy

Interfaces define contracts, not implementations.

They describe **what** a component must provide, but never **how** it works.

The implementation remains completely independent from the contract.

---

# Design Principles

All interfaces must follow these principles:

- Single Responsibility Principle (SRP)
- Dependency Inversion Principle (DIP)
- Low Coupling
- High Cohesion
- Simplicity
- Explicit Contracts
- Easy Testability

---

# Interface Location

All interfaces must be placed inside:

```
src/
└── atreus/
    └── interfaces/
```

Example:

```
interfaces/
    configuration.py
    logger.py
    memory.py
    planner.py
    event_bus.py
```

---

# Naming Convention

Interfaces must use descriptive names.

Avoid prefixes such as `I`.

Preferred examples:

```
ConfigurationProvider
Logger
MemoryStore
Planner
EventBus
CapabilityRegistry
```

Avoid:

```
IConfiguration
ILogger
IMemory
```

Python conventions do not require the use of an `I` prefix.

---

# Implementation Location

Implementations must remain inside their own modules.

Example:

```
interfaces/
    configuration.py

configuration/
    configuration_manager.py
```

The implementation should inherit from the interface.

---

# Interface Responsibilities

Interfaces should:

- Define behavior.
- Define public methods.
- Define expected return types.
- Define expected parameters.

Interfaces should never:

- Store application state.
- Execute business logic.
- Access files.
- Access databases.
- Perform network operations.

---

# Abstract Base Classes

ATREUS uses Python Abstract Base Classes (ABC) for interface definitions.

Example:

```python
from abc import ABC, abstractmethod

class ConfigurationProvider(ABC):

    @abstractmethod
    def load(self) -> None:
        """Load configuration."""
```

---

# Type Hints

Every interface method must include complete type hints.

Example:

```python
def get(self, key: str) -> str | None:
```

---

# Documentation

Every interface must include:

- Class docstring
- Method docstrings
- Type hints

Google-style docstrings should be used.

---

# Dependency Rule

Application modules must depend on interfaces rather than concrete implementations.

Correct:

```
Core
    │
    ▼
ConfigurationProvider
```

Incorrect:

```
Core
    │
    ▼
ConfigurationManager
```

---

# Testing

Interfaces themselves are not tested.

Tests must validate concrete implementations against the interface contract.

---

# Future Evolution

Interfaces should remain as stable as possible.

New functionality should be introduced by extending implementations rather than frequently modifying interface definitions.

Breaking interface changes should be avoided whenever possible.

---

# Architectural Considerations

Interfaces represent one of the most stable layers of the ATREUS architecture.

They provide clear contracts between components, allowing implementations to evolve independently while preserving compatibility across the platform.

Maintaining stable interfaces is essential for the long-term maintainability and extensibility of ATREUS.