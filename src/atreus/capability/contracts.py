"""Immutable capability value contracts shared by planning and execution."""

from dataclasses import dataclass

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
