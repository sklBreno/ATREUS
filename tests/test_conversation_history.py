"""Tests for bounded process-local conversation history."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from atreus.conversation.exceptions import (
    InvalidConversationExchangeError,
    InvalidConversationHistoryPolicyError,
    InvalidConversationHistorySnapshotError,
    InvalidConversationTurnError,
)
from atreus.conversation.history import InMemoryConversationHistory
from atreus.conversation.models import (
    ConversationExchange,
    ConversationHistoryPolicy,
    ConversationHistorySnapshot,
    ConversationRole,
    ConversationTurn,
)
from atreus.interaction.models import InteractionLanguage
from tests.support import NOW, FixedClock


def make_turn(
    role: ConversationRole,
    content: str,
    *,
    request_id: object | None = None,
    created_at: datetime = NOW,
    language: InteractionLanguage = InteractionLanguage.PT_BR,
) -> ConversationTurn:
    """Create one valid turn with optional contract overrides."""
    return ConversationTurn(
        turn_id=uuid4(),
        request_id=uuid4() if request_id is None else request_id,  # type: ignore[arg-type]
        role=role,
        content=content,
        language=language,
        created_at=created_at,
    )


def make_exchange(
    user_content: str = "question",
    assistant_content: str = "answer",
    *,
    language: InteractionLanguage = InteractionLanguage.PT_BR,
) -> ConversationExchange:
    """Create one complete correlated exchange."""
    request_id = uuid4()
    return ConversationExchange(
        make_turn(
            ConversationRole.USER,
            user_content,
            request_id=request_id,
            language=language,
        ),
        make_turn(
            ConversationRole.ASSISTANT,
            assistant_content,
            request_id=request_id,
            language=language,
        ),
    )


def test_models_are_frozen_slotted_utc_and_hide_content() -> None:
    offset_time = datetime(
        2026,
        9,
        2,
        8,
        0,
        tzinfo=timezone(timedelta(hours=-4)),
    )
    turn = make_turn(
        ConversationRole.USER,
        "private conversation text",
        created_at=offset_time,
    )
    exchange = ConversationExchange(
        turn,
        make_turn(
            ConversationRole.ASSISTANT,
            "private answer text",
            request_id=turn.request_id,
            created_at=offset_time,
        ),
    )
    snapshot = ConversationHistorySnapshot(offset_time, (exchange,))
    policy = ConversationHistoryPolicy(6, 12_000)

    with pytest.raises(FrozenInstanceError):
        turn.content = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        policy.max_exchanges = 1  # type: ignore[misc]

    assert turn.created_at.tzinfo is UTC
    assert snapshot.captured_at.tzinfo is UTC
    assert hasattr(turn, "__slots__")
    assert hasattr(exchange, "__slots__")
    assert hasattr(snapshot, "__slots__")
    assert hasattr(policy, "__slots__")
    assert "private conversation text" not in repr(snapshot)
    assert "private answer text" not in repr(snapshot)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("turn_id", "invalid"),
        ("request_id", "invalid"),
        ("role", "USER"),
        ("content", " "),
        ("content", "unsafe\x00text"),
        ("language", "pt-BR"),
        ("created_at", datetime(2026, 9, 2, 12, 0)),
    ),
)
def test_turn_rejects_invalid_contract_values(
    field_name: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "turn_id": uuid4(),
        "request_id": uuid4(),
        "role": ConversationRole.USER,
        "content": "content",
        "language": InteractionLanguage.EN_US,
        "created_at": NOW,
    }
    values[field_name] = value

    with pytest.raises(InvalidConversationTurnError):
        ConversationTurn(**values)  # type: ignore[arg-type]


def test_exchange_rejects_invalid_roles_identity_language_and_chronology() -> None:
    first_request_id = uuid4()
    second_request_id = uuid4()
    user = make_turn(
        ConversationRole.USER,
        "question",
        request_id=first_request_id,
    )
    assistant = make_turn(
        ConversationRole.ASSISTANT,
        "answer",
        request_id=first_request_id,
    )

    invalid_pairs = (
        (assistant, user),
        (
            user,
            make_turn(
                ConversationRole.ASSISTANT,
                "answer",
                request_id=second_request_id,
            ),
        ),
        (
            user,
            make_turn(
                ConversationRole.ASSISTANT,
                "answer",
                request_id=first_request_id,
                language=InteractionLanguage.EN_US,
            ),
        ),
        (
            make_turn(
                ConversationRole.USER,
                "question",
                request_id=first_request_id,
                created_at=NOW + timedelta(seconds=1),
            ),
            assistant,
        ),
    )

    for invalid_user, invalid_assistant in invalid_pairs:
        with pytest.raises(InvalidConversationExchangeError):
            ConversationExchange(invalid_user, invalid_assistant)


def test_snapshot_and_policy_reject_invalid_values() -> None:
    with pytest.raises(InvalidConversationHistorySnapshotError):
        ConversationHistorySnapshot(datetime(2026, 9, 2, 12, 0), ())
    with pytest.raises(InvalidConversationHistorySnapshotError):
        ConversationHistorySnapshot(NOW, [])  # type: ignore[arg-type]

    for max_exchanges, max_characters in (
        (0, 1),
        (-1, 1),
        (True, 1),
        (1, 0),
        (1, -1),
        (1, True),
    ):
        with pytest.raises(InvalidConversationHistoryPolicyError):
            ConversationHistoryPolicy(  # type: ignore[arg-type]
                max_exchanges,
                max_characters,
            )


def test_store_starts_empty_and_appends_oldest_first() -> None:
    store = InMemoryConversationHistory(
        FixedClock(),
        ConversationHistoryPolicy(3, 100),
    )
    first = make_exchange("first", "answer one")
    second = make_exchange("second", "answer two")

    assert store.snapshot().exchanges == ()
    assert store.try_append(first) is True
    assert store.try_append(second) is True
    assert store.snapshot().exchanges == (first, second)


def test_store_enforces_exact_count_boundary_with_fifo_pruning() -> None:
    store = InMemoryConversationHistory(
        FixedClock(),
        ConversationHistoryPolicy(2, 100),
    )
    first = make_exchange("1", "a")
    second = make_exchange("2", "b")
    third = make_exchange("3", "c")

    store.try_append(first)
    store.try_append(second)
    assert store.snapshot().exchanges == (first, second)

    store.try_append(third)

    assert store.snapshot().exchanges == (second, third)


def test_store_enforces_character_boundary_by_complete_exchange() -> None:
    store = InMemoryConversationHistory(
        FixedClock(),
        ConversationHistoryPolicy(5, 8),
    )
    first = make_exchange("aa", "bb")
    second = make_exchange("cc", "dd")
    third = make_exchange("eee", "fff")

    store.try_append(first)
    store.try_append(second)
    assert store.snapshot().exchanges == (first, second)

    store.try_append(third)

    assert store.snapshot().exchanges == (third,)


def test_oversized_or_invalid_append_does_not_mutate_history() -> None:
    store = InMemoryConversationHistory(
        FixedClock(),
        ConversationHistoryPolicy(2, 8),
    )
    retained = make_exchange("aa", "bb")
    store.try_append(retained)

    assert store.try_append(make_exchange("oversized", "answer")) is False
    with pytest.raises(InvalidConversationExchangeError):
        store.try_append(object())  # type: ignore[arg-type]

    assert store.snapshot().exchanges == (retained,)


def test_snapshot_is_stable_and_clear_returns_removed_count() -> None:
    store = InMemoryConversationHistory(
        FixedClock(),
        ConversationHistoryPolicy(3, 100),
    )
    first = make_exchange("first", "answer")
    second = make_exchange("second", "answer")
    store.try_append(first)
    previous = store.snapshot()
    store.try_append(second)

    assert previous.exchanges == (first,)
    assert store.clear() == 2
    assert store.clear() == 0
    assert store.snapshot().exchanges == ()
