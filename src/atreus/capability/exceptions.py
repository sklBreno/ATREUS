"""Exceptions raised by the Capability Registry."""


class CapabilityRegistryException(Exception):
    """Base exception for Capability Registry failures."""


class InvalidCapabilityIdentifierError(CapabilityRegistryException):
    """Raised when a capability identifier is invalid."""


class InvalidCapabilityMetadataError(CapabilityRegistryException):
    """Raised when capability metadata violates the catalog contract."""


class DuplicateCapabilityError(CapabilityRegistryException):
    """Raised when an identifier is already registered."""


class UnknownCapabilityError(CapabilityRegistryException):
    """Raised when a mutation targets an unknown capability."""


class RegistrySealedError(CapabilityRegistryException):
    """Raised when registration is attempted after sealing."""


class CapabilityDependencyCycleError(CapabilityRegistryException):
    """Raised when capability dependencies contain a cycle."""
