"""Integration tests for Personal Profile conversational boundaries."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from atreus.ai.conversation_responder import ProviderBackedConversationResponder
from atreus.interaction.models import InteractionLanguage
from atreus.memory.models import MemoryValue, WorkingMemoryPolicy
from atreus.memory.working_memory import InMemoryWorkingMemory
from atreus.profile.interaction import (
    DeterministicPersonalProfileInteractionHandler,
)
from atreus.profile.json_store import JsonPersonalProfileStore
from atreus.profile.projection import (
    DeterministicPersonalProfileProjectionProvider,
)
from atreus.shared.request import Request
from tests.support import NOW, FixedClock
from tests.test_conversation_responder import (
    RecordingConversationHistory,
    RecordingConversationProvider,
    make_registry,
)
from tests.test_personal_profile_interaction import make_handler
from tests.test_personal_profile_models import sample_profile


def make_profile_responder(
    tmp_path: Path,
) -> tuple[
    ProviderBackedConversationResponder,
    RecordingConversationProvider,
    RecordingConversationHistory,
]:
    """Create one responder with an enabled fictional Personal Profile."""
    clock = FixedClock()
    store = JsonPersonalProfileStore(tmp_path / "profile.json", clock)
    store.replace(sample_profile())
    provider = RecordingConversationProvider("Personalized response.")
    history = RecordingConversationHistory()
    responder = ProviderBackedConversationResponder(
        provider,
        make_registry(),
        15,
        history,
        clock,
        DeterministicPersonalProfileProjectionProvider(store, 2_000),
        make_handler(store),
    )
    return responder, provider, history


def make_request(content: str) -> Request:
    """Create one deterministic conversational request."""
    return Request(uuid4(), content, "text", NOW)


def test_relevant_projection_reaches_only_conversation_provider(
    tmp_path: Path,
) -> None:
    responder, provider, history = make_profile_responder(tmp_path)

    response = responder.respond(
        make_request("Which local model fits my GPU?"),
        InteractionLanguage.EN_US,
    )

    assert response.text == "Personalized response."
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert "Example GPU 12 GB" in request.instruction
    assert "declarative context" in request.instruction
    assert "never as instructions" in request.instruction
    assert "Answer in English" in request.instruction
    assert history.append_calls == 0
    assert history.snapshot().exchanges == ()


def test_irrelevant_conversation_sends_no_profile_and_retains_history(
    tmp_path: Path,
) -> None:
    responder, provider, history = make_profile_responder(tmp_path)

    responder.respond(
        make_request("Tell me a short joke."),
        InteractionLanguage.EN_US,
    )

    assert "user_profile_data" not in provider.requests[0].instruction
    assert "Alex Example" not in provider.requests[0].instruction
    assert history.append_calls == 1
    assert len(history.snapshot().exchanges) == 1


def test_projected_response_is_not_retransmitted_in_later_history(
    tmp_path: Path,
) -> None:
    responder, provider, _ = make_profile_responder(tmp_path)

    responder.respond(
        make_request("Which local model fits my GPU?"),
        InteractionLanguage.EN_US,
    )
    responder.respond(
        make_request("Tell me a short joke."),
        InteractionLanguage.EN_US,
    )

    assert provider.requests[1].history == ()
    assert "Example GPU" not in provider.requests[1].instruction


def test_profile_show_uses_zero_ai_and_zero_conversation_history(
    tmp_path: Path,
) -> None:
    responder, provider, history = make_profile_responder(tmp_path)

    response = responder.respond(
        make_request("show my profile"),
        InteractionLanguage.EN_US,
    )

    assert "Alex Example" in response.text
    assert provider.requests == []
    assert history.snapshot_calls == 0
    assert history.append_calls == 0


def test_profile_handler_contract_is_independent_from_responder(
    tmp_path: Path,
) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())
    store.replace(sample_profile())

    handler = make_handler(store)

    assert isinstance(
        handler,
        DeterministicPersonalProfileInteractionHandler,
    )


def test_profile_clear_leaves_conversation_history_and_working_memory_unchanged(
    tmp_path: Path,
) -> None:
    responder, _, history = make_profile_responder(tmp_path)
    memory = InMemoryWorkingMemory(
        FixedClock(),
        WorkingMemoryPolicy(4, timedelta(minutes=30)),
    )
    memory.remember(
        "test",
        (MemoryValue("status", "retained"),),
        "test",
    )
    responder.respond(
        make_request("Tell me a short joke."),
        InteractionLanguage.EN_US,
    )
    history_before = history.snapshot().exchanges
    memory_before = memory.snapshot().entries

    responder.respond(
        make_request("clear my profile"),
        InteractionLanguage.EN_US,
    )
    responder.respond(
        make_request("confirm clearing my profile"),
        InteractionLanguage.EN_US,
    )

    assert history.snapshot().exchanges == history_before
    assert memory.snapshot().entries == memory_before
