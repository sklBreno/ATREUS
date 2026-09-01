# AI Development Workflow

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-07-05

---

# Purpose

This document defines how Artificial Intelligence is used during the development of the ATREUS platform.

AI is considered a development assistant, not an architect.

Architectural decisions are made by the development team.

---

# Development Workflow

Every new feature follows the same workflow.

```
Idea

↓

Architecture

↓

Documentation

↓

Implementation

↓

Code Review

↓

Testing

↓

Commit

↓

Merge
```

---

# Responsibilities

## Product Owner

Defines goals and priorities.

---

## Software Architect

Defines:

- Architecture
- Design decisions
- Module responsibilities
- Documentation

---

## AI Engineer

Implements documented specifications.

Must never invent architecture.

Must never change documented behavior.

---

## Reviewer

Verifies:

- Architecture
- Code quality
- Readability
- Consistency
- Compliance with documentation

---

# AI Rules

AI must:

- Read documentation before implementation.
- Follow project standards.
- Respect module boundaries.
- Produce production-ready code.

AI must never:

- Invent architecture.
- Rename modules.
- Introduce unnecessary dependencies.
- Implement undocumented features.

---

# Documentation First

No module should be implemented before its architecture documentation exists.

Documentation is considered the source of truth.

---

# Human Review

Every AI-generated implementation must be reviewed before being merged.

No exception.

---

# Commit Policy

Only reviewed and tested implementations may be committed.

---

# Long-Term Goal

AI should accelerate implementation.

Architecture and engineering decisions remain human responsibilities.

The project should evolve through documented decisions rather than AI assumptions.