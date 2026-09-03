"""Provider-neutral boundaries for explicit Personal Profile behavior."""

from abc import ABC, abstractmethod
from datetime import datetime

from atreus.interaction.models import ConversationalResponse, InteractionLanguage
from atreus.profile.models import PersonalProfile, PersonalProfileProjection
from atreus.shared.request import Request


class PersonalProfileProvider(ABC):
    """Provide the current validated immutable Personal Profile."""

    @abstractmethod
    def get_profile(self) -> PersonalProfile:
        """Return the current Personal Profile."""


class PersonalProfileStore(PersonalProfileProvider, ABC):
    """Persist explicit replacements and clears of a Personal Profile."""

    @abstractmethod
    def replace(self, profile: PersonalProfile) -> PersonalProfile:
        """Persist and return one complete validated replacement profile."""

    @abstractmethod
    def clear(self, cleared_at: datetime) -> PersonalProfile:
        """Persist and return one empty profile."""


class PersonalProfileProjectionProvider(ABC):
    """Select bounded declarative profile data for one conversation."""

    @abstractmethod
    def project(
        self,
        content: str,
        language: InteractionLanguage,
    ) -> PersonalProfileProjection | None:
        """Return a relevant provider-safe projection or no projection."""


class PersonalProfileInteractionHandler(ABC):
    """Handle exact local Personal Profile interaction commands."""

    @abstractmethod
    def handle(
        self,
        request: Request,
        language: InteractionLanguage,
    ) -> ConversationalResponse | None:
        """Return a local response when the request is a profile command."""
