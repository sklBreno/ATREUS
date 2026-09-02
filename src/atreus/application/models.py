"""Immutable provider-neutral application action contracts."""

from dataclasses import dataclass
from enum import StrEnum

from atreus.application.exceptions import InvalidApplicationActionError
from atreus.system.models import ApplicationIdentifier


class ApplicationIntent(StrEnum):
    """Identify one approved application action intent."""

    OPEN_APPLICATION = "OPEN_APPLICATION"
    APPLICATION_STATUS = "APPLICATION_STATUS"


@dataclass(frozen=True, slots=True)
class ApplicationAction:
    """Represent one locally approved provider-neutral application action."""

    intent_id: ApplicationIntent
    capability_id: str
    application_id: ApplicationIdentifier

    def __post_init__(self) -> None:
        """Validate the immutable action contract."""
        if not isinstance(self.intent_id, ApplicationIntent):
            raise InvalidApplicationActionError("Application intent is invalid.")
        if (
            not isinstance(self.capability_id, str)
            or not self.capability_id.strip()
            or self.capability_id != self.capability_id.strip()
        ):
            raise InvalidApplicationActionError(
                "Application capability_id must be a normalized non-empty string."
            )
        if not isinstance(self.application_id, ApplicationIdentifier):
            raise InvalidApplicationActionError(
                "Application identifier is not approved."
            )


@dataclass(frozen=True, slots=True)
class ApplicationActionDefinition:
    """Declare one local intent, target, capability, and support combination."""

    intent_id: ApplicationIntent
    application_id: ApplicationIdentifier
    capability_id: str
    supported: bool

    def __post_init__(self) -> None:
        """Validate the immutable action definition."""
        if not isinstance(self.intent_id, ApplicationIntent):
            raise InvalidApplicationActionError(
                "Application action definition intent is invalid."
            )
        if not isinstance(self.application_id, ApplicationIdentifier):
            raise InvalidApplicationActionError(
                "Application action definition identifier is invalid."
            )
        if (
            not isinstance(self.capability_id, str)
            or not self.capability_id.strip()
            or self.capability_id != self.capability_id.strip()
        ):
            raise InvalidApplicationActionError(
                "Application action definition capability_id is invalid."
            )
        if type(self.supported) is not bool:
            raise InvalidApplicationActionError(
                "Application action definition support flag must be boolean."
            )
