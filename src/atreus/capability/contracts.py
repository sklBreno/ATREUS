"""Immutable capability value contracts shared by planning and execution."""

from dataclasses import dataclass

OPEN_APPLICATION_CAPABILITY_ID = "application.open"
APPLICATION_ID_ARGUMENT = "application_id"
OPEN_APPLICATION_COMMAND_TARGETS: tuple[tuple[str, str], ...] = (
    ("open calculator", "calculator"),
    ("open notepad", "notepad"),
    ("open spotify", "spotify"),
)

type CapabilityScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class CapabilityArgument:
    """Represent one named immutable capability input value."""

    name: str
    value: CapabilityScalar


type CapabilityArguments = tuple[CapabilityArgument, ...]


@dataclass(frozen=True, slots=True)
class CapabilityOutputItem:
    """Represent one named immutable capability output value."""

    name: str
    value: CapabilityScalar


type CapabilityOutput = tuple[CapabilityOutputItem, ...]
