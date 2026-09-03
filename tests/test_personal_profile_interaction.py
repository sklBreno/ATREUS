"""Tests for deterministic Personal Profile read and clear interaction."""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.clock import Clock
from atreus.interfaces.personal_profile import PersonalProfileStore
from atreus.profile.exceptions import PersonalProfilePersistenceError
from atreus.profile.interaction import (
    DeterministicPersonalProfileInteractionHandler,
)
from atreus.profile.json_store import JsonPersonalProfileStore
from atreus.profile.models import PersonalProfile, personal_profile_is_empty
from atreus.shared.request import Request
from tests.support import NOW, FixedClock
from tests.test_personal_profile_models import sample_profile


class MutableClock(Clock):
    """Expose an explicitly advanced deterministic timestamp."""

    def __init__(self, timestamp: datetime = NOW) -> None:
        """Initialize the current timestamp."""
        self.timestamp = timestamp

    def now(self) -> datetime:
        """Return the current timestamp."""
        return self.timestamp


class FailingClearStore(PersonalProfileStore):
    """Retain a profile while failing every clear operation safely."""

    def __init__(self) -> None:
        """Initialize one populated profile."""
        self.profile = sample_profile()

    def get_profile(self) -> PersonalProfile:
        """Return the populated profile."""
        return self.profile

    def replace(self, profile: PersonalProfile) -> PersonalProfile:
        """Replace the current test profile."""
        self.profile = profile
        return profile

    def clear(self, cleared_at: datetime) -> PersonalProfile:
        """Raise one sanitized persistence failure."""
        raise PersonalProfilePersistenceError("private storage detail")


class AdvancingClearStore(PersonalProfileStore):
    """Advance time while atomically clearing one test profile."""

    def __init__(self, clock: MutableClock) -> None:
        """Initialize one populated profile and shared mutable clock."""
        self.profile = sample_profile()
        self._clock = clock

    def get_profile(self) -> PersonalProfile:
        """Return the current test profile."""
        return self.profile

    def replace(self, profile: PersonalProfile) -> PersonalProfile:
        """Replace the current test profile."""
        self.profile = profile
        return profile

    def clear(self, cleared_at: datetime) -> PersonalProfile:
        """Clear successfully after advancing past the confirmation expiry."""
        self._clock.timestamp += timedelta(seconds=120)
        self.profile = PersonalProfile(schema_version=1, updated_at=cleared_at)
        return self.profile


def make_request(content: str) -> Request:
    """Create one deterministic text request."""
    return Request(uuid4(), content, "text", NOW)


def make_handler(
    store: PersonalProfileStore,
    clock: Clock | None = None,
    *,
    enabled: bool = True,
) -> DeterministicPersonalProfileInteractionHandler:
    """Create one handler with a two-minute confirmation lifetime."""
    return DeterministicPersonalProfileInteractionHandler(
        store,
        clock or FixedClock(),
        timedelta(seconds=120),
        enabled=enabled,
    )


def test_show_profile_is_localized_and_stably_ordered(tmp_path: Path) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())
    store.replace(sample_profile())
    handler = make_handler(store)

    portuguese = handler.handle(
        make_request("o que você sabe sobre mim?"),
        InteractionLanguage.PT_BR,
    )
    english = handler.handle(
        make_request("show my profile"),
        InteractionLanguage.EN_US,
    )

    assert portuguese is not None
    assert english is not None
    assert portuguese.text.startswith("Seu perfil pessoal:")
    assert english.text.startswith("Your personal profile:")
    assert portuguese.text.index("Alex Example") < portuguese.text.index("Project Atlas")
    assert "schema_version" not in english.text
    assert "profile.json" not in english.text


def test_disabled_and_empty_profiles_return_explicit_local_responses(
    tmp_path: Path,
) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())

    disabled = make_handler(store, enabled=False).handle(
        make_request("show my profile"),
        InteractionLanguage.EN_US,
    )
    empty = make_handler(store).handle(
        make_request("mostrar meu perfil"),
        InteractionLanguage.PT_BR,
    )

    assert disabled is not None and disabled.text == "Personal Profile is disabled."
    assert empty is not None and "vazio" in empty.text


def test_clear_request_requires_exact_dedicated_confirmation(
    tmp_path: Path,
) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())
    store.replace(sample_profile())
    handler = make_handler(store)

    pending = handler.handle(
        make_request("limpar meu perfil"),
        InteractionLanguage.PT_BR,
    )
    generic_yes = handler.handle(make_request("sim"), InteractionLanguage.PT_BR)

    assert pending is not None and "confirmar limpeza" in pending.text
    assert generic_yes is None
    assert not personal_profile_is_empty(store.get_profile())

    cleared = handler.handle(
        make_request("confirmar limpeza do meu perfil"),
        InteractionLanguage.PT_BR,
    )

    assert cleared is not None and "foi limpo" in cleared.text
    assert personal_profile_is_empty(store.get_profile())


def test_confirmation_without_pending_and_replay_do_nothing(tmp_path: Path) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())
    store.replace(sample_profile())
    handler = make_handler(store)

    no_pending = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )
    handler.handle(make_request("clear my profile"), InteractionLanguage.EN_US)
    handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )
    replay = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )

    assert no_pending is not None and "No profile clear" in no_pending.text
    assert replay is not None and "No profile clear" in replay.text


def test_expired_confirmation_fails_without_clearing(tmp_path: Path) -> None:
    clock = MutableClock()
    store = JsonPersonalProfileStore(tmp_path / "profile.json", clock)
    store.replace(sample_profile())
    handler = make_handler(store, clock)
    handler.handle(make_request("clear my profile"), InteractionLanguage.EN_US)
    clock.timestamp += timedelta(seconds=120)

    response = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )

    assert response is not None and "expired" in response.text
    assert not personal_profile_is_empty(store.get_profile())


def test_clear_failure_does_not_report_success_or_consume_confirmation() -> None:
    store = FailingClearStore()
    handler = make_handler(store)
    handler.handle(make_request("clear my profile"), InteractionLanguage.EN_US)

    first = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )
    second = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )

    assert first is not None and "could not clear" in first.text
    assert second is not None and "could not clear" in second.text
    assert "private storage detail" not in first.text
    assert not personal_profile_is_empty(store.get_profile())


def test_confirmed_clear_reports_success_when_ttl_expires_during_write() -> None:
    clock = MutableClock()
    store = AdvancingClearStore(clock)
    handler = make_handler(store, clock)
    handler.handle(make_request("clear my profile"), InteractionLanguage.EN_US)

    response = handler.handle(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )

    assert response is not None and response.text == "Your Personal Profile was cleared."
    assert personal_profile_is_empty(store.get_profile())
