"""Immutable contracts for foreground interaction results and languages."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from atreus.interaction.exceptions import (
    InvalidAssistantCapabilitySummaryError,
    InvalidConversationalResponseError,
)


class InteractionLanguage(StrEnum):
    """Identify one language supported by the interactive V0 boundary."""

    PT_BR = "pt-BR"
    EN_US = "en-US"


@dataclass(frozen=True, slots=True)
class AssistantCapabilitySummary:
    """Expose a minimal user-facing projection of available capabilities."""

    openable_application_ids: tuple[str, ...]
    observable_application_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate normalized, unique application identifiers."""
        for values in (
            self.openable_application_ids,
            self.observable_application_ids,
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                for value in values
            ):
                raise InvalidAssistantCapabilitySummaryError(
                    "Capability summaries require normalized application identifiers."
                )
            if len(values) != len(set(values)):
                raise InvalidAssistantCapabilitySummaryError(
                    "Capability summary identifiers must be unique."
                )


@dataclass(frozen=True, slots=True)
class ConversationalResponse:
    """Represent one validated provider-neutral conversational response."""

    request_id: UUID
    text: str = field(repr=False)
    language: InteractionLanguage

    def __post_init__(self) -> None:
        """Validate response identity, text, and interaction language."""
        if not isinstance(self.request_id, UUID):
            raise InvalidConversationalResponseError(
                "Conversational response request_id must be a UUID."
            )
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidConversationalResponseError(
                "Conversational response text must be non-empty."
            )
        if not isinstance(self.language, InteractionLanguage):
            raise InvalidConversationalResponseError(
                "Conversational response language is invalid."
            )
