"""Exceptions raised by the ATREUS Personal Profile module."""


class PersonalProfileException(Exception):
    """Base exception for Personal Profile failures."""


class InvalidPersonalProfileError(PersonalProfileException):
    """Raised when a Personal Profile contract is invalid."""


class PersonalProfileLoadError(PersonalProfileException):
    """Raised when a persisted Personal Profile cannot be loaded safely."""


class PersonalProfilePersistenceError(PersonalProfileException):
    """Raised when a Personal Profile cannot be persisted atomically."""


class UnsupportedPersonalProfileVersionError(PersonalProfileLoadError):
    """Raised when a profile document uses an unsupported schema version."""


class PersonalProfileDisabledError(PersonalProfileException):
    """Raised when a mutating operation targets a disabled profile."""


class PersonalProfileImportError(PersonalProfileException):
    """Raised when a reviewed profile document cannot be imported safely."""


class InvalidProfileClearConfirmationError(PersonalProfileException):
    """Raised when a profile-clear confirmation contract is invalid."""
