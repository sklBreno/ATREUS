"""Bootstrap and full-flow tests for Personal Profile V0."""

from pathlib import Path

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIResponse,
)
from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.interfaces.ai_provider import AIProvider
from atreus.profile.exceptions import PersonalProfileLoadError
from atreus.profile.json_store import JsonPersonalProfileStore
from atreus.profile.models import personal_profile_is_empty
from tests.support import (
    NOW,
    FixedClock,
    RecordingApplicationLauncher,
    RecordingApplicationStateReader,
    RecordingLogWriter,
)
from tests.test_personal_profile_models import sample_profile


class PersonalProfileAIProvider(AIProvider):
    """Return deterministic conversation text and record provider requests."""

    def __init__(self) -> None:
        """Initialize an empty request collection."""
        self.requests: list[AIRequest] = []

    def availability(self) -> AIProviderAvailability:
        """Report deterministic test availability."""
        return AIProviderAvailability(AIProviderAvailabilityState.AVAILABLE)

    def generate(self, request: AIRequest) -> AIResponse:
        """Record and return one safe deterministic response."""
        self.requests.append(request)
        return AIResponse(
            request.ai_request_id,
            request.request_id,
            "Safe personalized response.",
            "test",
            "test-model",
            NOW,
        )


def profile_configuration(*, enabled: bool) -> ConfigurationManager:
    """Create one validated profile-aware runtime configuration."""
    return ConfigurationManager(
        loader=ConfigurationLoader(
            env_file_path=None,
            environment={
                "ATREUS_AI_ENABLED": "true",
                "ATREUS_AI_PROVIDER": "ollama",
                "ATREUS_PERSONAL_PROFILE_ENABLED": str(enabled).lower(),
            },
        )
    )


def make_bootstrap(
    path: Path,
    provider: PersonalProfileAIProvider,
    *,
    enabled: bool,
) -> Bootstrap:
    """Create one isolated production composition root."""
    return Bootstrap(
        configuration_provider=profile_configuration(enabled=enabled),
        application_launcher=RecordingApplicationLauncher(),
        application_state_reader=RecordingApplicationStateReader(),
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
        ai_provider=provider,
        personal_profile_path=path,
    )


def test_disabled_profile_composes_without_disk_access(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "profile.json"
    provider = PersonalProfileAIProvider()
    runtime = make_bootstrap(path, provider, enabled=False).compose()

    result = runtime.submit("show my profile")

    assert result.conversational_response is not None
    assert result.conversational_response.text == "Personal Profile is disabled."
    assert provider.requests == []
    assert not path.exists()


def test_enabled_profile_loads_file_once_and_reuses_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    JsonPersonalProfileStore(path, FixedClock()).replace(sample_profile())
    provider = PersonalProfileAIProvider()
    original_read_bytes = Path.read_bytes
    read_calls = 0

    def record_read(self: Path) -> bytes:
        nonlocal read_calls
        read_calls += 1
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", record_read)
    runtime = make_bootstrap(path, provider, enabled=True).compose()

    show = runtime.submit("show my profile")
    personalized = runtime.submit("Which local model fits my GPU?")
    unrelated = runtime.submit("What is a palindrome?")

    assert show.conversational_response is not None
    assert "Alex Example" in show.conversational_response.text
    assert personalized.conversational_response is not None
    assert unrelated.conversational_response is not None
    assert read_calls == 1
    assert "Example GPU" in provider.requests[0].instruction
    assert provider.requests[1].history == ()
    assert "user_profile_data" not in provider.requests[1].instruction


def test_malformed_enabled_profile_fails_composition_without_overwrite(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profile.json"
    path.write_text("private malformed profile", encoding="utf-8")
    previous = path.read_bytes()

    with pytest.raises(PersonalProfileLoadError) as raised:
        make_bootstrap(
            path,
            PersonalProfileAIProvider(),
            enabled=True,
        ).compose()

    assert "private malformed profile" not in str(raised.value)
    assert str(path) not in str(raised.value)
    assert path.read_bytes() == previous


def test_full_clear_flow_requires_dedicated_phrase_and_preserves_other_flows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profile.json"
    JsonPersonalProfileStore(path, FixedClock()).replace(sample_profile())
    runtime = make_bootstrap(
        path,
        PersonalProfileAIProvider(),
        enabled=True,
    ).compose()

    pending = runtime.submit("clear my profile")
    generic = runtime.submit("yes")
    still_populated = JsonPersonalProfileStore(path, FixedClock()).get_profile()
    cleared = runtime.submit("confirm clearing my profile")
    persisted = JsonPersonalProfileStore(path, FixedClock()).get_profile()

    assert pending.conversational_response is not None
    assert "pending" in pending.conversational_response.text
    assert generic.conversational_response is None
    assert not personal_profile_is_empty(still_populated)
    assert cleared.conversational_response is not None
    assert "was cleared" in cleared.conversational_response.text
    assert personal_profile_is_empty(persisted)


def test_profile_content_does_not_reach_structured_observability(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profile.json"
    JsonPersonalProfileStore(path, FixedClock()).replace(sample_profile())
    provider = PersonalProfileAIProvider()
    writer = RecordingLogWriter()
    runtime = Bootstrap(
        configuration_provider=profile_configuration(enabled=True),
        application_launcher=RecordingApplicationLauncher(),
        application_state_reader=RecordingApplicationStateReader(),
        clock=FixedClock(),
        log_writer=writer,
        ai_provider=provider,
        personal_profile_path=path,
    ).compose()

    runtime.submit("Which local model fits my GPU?")

    serialized_records = repr(writer.records)
    assert "Alex Example" not in serialized_records
    assert "Example GPU 12 GB" not in serialized_records
    assert "Project Atlas" not in serialized_records
    assert all("Profile" not in record.event_type for record in writer.records)
