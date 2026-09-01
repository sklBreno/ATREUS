"""Exceptions raised by the ATREUS Working Memory module."""


class MemoryException(Exception):
    """Base exception for Working Memory failures."""


class InvalidMemoryValueError(MemoryException):
    """Raised when a memory value violates its immutable contract."""


class InvalidMemoryEntryError(MemoryException):
    """Raised when a memory entry contains inconsistent data."""


class InvalidMemorySnapshotError(MemoryException):
    """Raised when a memory snapshot violates its immutable contract."""


class InvalidWorkingMemoryPolicyError(MemoryException):
    """Raised when Working Memory policy values are invalid."""


class InvalidMemoryIdentifierError(MemoryException):
    """Raised when an operation receives an invalid entry identifier."""
