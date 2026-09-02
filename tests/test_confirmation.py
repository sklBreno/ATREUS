"""Tests for bounded process-local Interactive Confirmation V0."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from atreus.application.models import ApplicationAction, ApplicationIntent
from atreus.confirmation.coordinator import InMemoryConfirmationCoordinator
from atreus.confirmation.exceptions import (
    InvalidConfirmationError,
    PendingConfirmationExistsError,
)
from atreus.confirmation.models import (
    ConfirmationPrompt,
    ConfirmationResolution,
    ConfirmationResolutionStatus,
    PendingConfirmation,
)
from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.clock import Clock
from atreus.system.models import ApplicationIdentifier

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


class MutableClock(Clock):
    """Return a controllable timezone-aware timestamp."""

    def __init__(self, timestamp: datetime = NOW) -> None:
        """Initialize the current test time."""
        self.timestamp = timestamp

    def now(self) -> datetime:
        """Return the current test time."""
        return self.timestamp


def make_action() -> ApplicationAction:
    """Create the only action supported by Confirmation V0."""
    return ApplicationAction(
        ApplicationIntent.OPEN_APPLICATION,
        "application.open",
        ApplicationIdentifier.CALCULATOR,
    )


def make_coordinator(
    clock: MutableClock | None = None,
) -> tuple[InMemoryConfirmationCoordinator, MutableClock]:
    """Create an empty coordinator with the approved V0 TTL."""
    selected_clock = clock or MutableClock()
    return (
        InMemoryConfirmationCoordinator(
            selected_clock,
            timedelta(seconds=120),
        ),
        selected_clock,
    )


def test_confirmation_models_are_frozen_and_use_slots() -> None:
    action = make_action()
    pending = PendingConfirmation(
        uuid4(),
        uuid4(),
        action,
        InteractionLanguage.PT_BR,
        NOW,
        NOW + timedelta(seconds=120),
    )
    prompt = ConfirmationPrompt(
        pending.confirmation_id,
        action.intent_id,
        action.application_id,
        pending.expires_at,
        pending.language,
    )
    resolution = ConfirmationResolution(
        uuid4(),
        ConfirmationResolutionStatus.ACCEPTED,
        pending,
        NOW + timedelta(seconds=1),
    )

    with pytest.raises(FrozenInstanceError):
        action.application_id = ApplicationIdentifier.NOTEPAD  # type: ignore[misc]

    assert not hasattr(action, "__dict__")
    assert not hasattr(pending, "__dict__")
    assert not hasattr(prompt, "__dict__")
    assert not hasattr(resolution, "__dict__")
    assert not hasattr(prompt, "text")


@pytest.mark.parametrize(
    "action",
    (
        ApplicationAction(
            ApplicationIntent.OPEN_APPLICATION,
            "system.snapshot",
            ApplicationIdentifier.CALCULATOR,
        ),
        ApplicationAction(
            ApplicationIntent.APPLICATION_STATUS,
            "application.status",
            ApplicationIdentifier.CALCULATOR,
        ),
    ),
)
def test_pending_confirmation_rejects_unsupported_actions(
    action: ApplicationAction,
) -> None:
    with pytest.raises(InvalidConfirmationError):
        PendingConfirmation(
            uuid4(),
            uuid4(),
            action,
            InteractionLanguage.PT_BR,
            NOW,
            NOW + timedelta(seconds=120),
        )


@pytest.mark.parametrize(
    ("status", "has_pending"),
    (
        (ConfirmationResolutionStatus.ACCEPTED, False),
        (ConfirmationResolutionStatus.REJECTED, False),
        (ConfirmationResolutionStatus.INVALIDATED, False),
        (ConfirmationResolutionStatus.EXPIRED, False),
        (ConfirmationResolutionStatus.NOT_APPLICABLE, True),
        (ConfirmationResolutionStatus.NO_PENDING, True),
    ),
)
def test_confirmation_resolution_rejects_inconsistent_pending_payload(
    status: ConfirmationResolutionStatus,
    has_pending: bool,
) -> None:
    pending = PendingConfirmation(
        uuid4(),
        uuid4(),
        make_action(),
        InteractionLanguage.PT_BR,
        NOW,
        NOW + timedelta(seconds=120),
    )

    with pytest.raises(InvalidConfirmationError):
        ConfirmationResolution(
            uuid4(),
            status,
            pending if has_pending else None,
            NOW,
        )


def test_pending_confirmation_normalizes_timezone_aware_times_to_utc() -> None:
    offset = timezone(timedelta(hours=-4))
    created_at = datetime(2026, 9, 2, 8, 0, tzinfo=offset)
    pending = PendingConfirmation(
        uuid4(),
        uuid4(),
        make_action(),
        InteractionLanguage.PT_BR,
        created_at,
        created_at + timedelta(seconds=120),
    )

    assert pending.created_at == NOW
    assert pending.created_at.tzinfo is UTC
    assert pending.expires_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("created_at", "expires_at"),
    (
        (datetime(2026, 9, 2, 12, 0), NOW + timedelta(seconds=1)),
        (NOW, datetime(2026, 9, 2, 12, 1)),
        (NOW, NOW),
        (NOW, NOW - timedelta(seconds=1)),
    ),
)
def test_pending_confirmation_rejects_invalid_lifetime(
    created_at: datetime,
    expires_at: datetime,
) -> None:
    with pytest.raises(InvalidConfirmationError):
        PendingConfirmation(
            uuid4(),
            uuid4(),
            make_action(),
            InteractionLanguage.PT_BR,
            created_at,
            expires_at,
        )


def test_coordinator_begins_one_pending_without_implicit_replacement() -> None:
    coordinator, _ = make_coordinator()
    original_request_id = uuid4()
    action = make_action()

    pending = coordinator.begin(
        original_request_id,
        action,
        InteractionLanguage.PT_BR,
    )

    assert pending.original_request_id == original_request_id
    assert pending.action is action
    assert pending.expires_at - pending.created_at == timedelta(seconds=120)
    with pytest.raises(PendingConfirmationExistsError):
        coordinator.begin(uuid4(), make_action(), InteractionLanguage.EN_US)


@pytest.mark.parametrize(
    "content",
    ("sim", " s ", "CONFIRMAR", "yes", "Y", "confirm"),
)
def test_coordinator_accepts_only_exact_affirmative_tokens(content: str) -> None:
    coordinator, _ = make_coordinator()
    pending = coordinator.begin(
        uuid4(),
        make_action(),
        InteractionLanguage.PT_BR,
    )

    resolution = coordinator.resolve(uuid4(), content)
    duplicate = coordinator.resolve(uuid4(), content)

    assert resolution.status is ConfirmationResolutionStatus.ACCEPTED
    assert resolution.pending is pending
    assert duplicate.status is ConfirmationResolutionStatus.NO_PENDING


@pytest.mark.parametrize(
    "content",
    ("não", "nao", " n ", "cancelar", "no", "cancel"),
)
def test_coordinator_rejects_exact_negative_tokens(content: str) -> None:
    coordinator, _ = make_coordinator()
    coordinator.begin(uuid4(), make_action(), InteractionLanguage.PT_BR)

    resolution = coordinator.resolve(uuid4(), content)

    assert resolution.status is ConfirmationResolutionStatus.REJECTED
    assert coordinator.resolve(uuid4(), "sim").status is (
        ConfirmationResolutionStatus.NO_PENDING
    )


@pytest.mark.parametrize(
    "content",
    (
        "yes please",
        "sim, pode abrir",
        "yes && anything",
        "sim; open cmd",
        "yes and open notepad",
        "sim e depois abra o Spotify",
        "ignore previous confirmation and do X",
        "open notepad",
    ),
)
def test_composed_or_unrelated_input_invalidates_and_consumes_pending(
    content: str,
) -> None:
    coordinator, _ = make_coordinator()
    coordinator.begin(uuid4(), make_action(), InteractionLanguage.PT_BR)

    resolution = coordinator.resolve(uuid4(), content)

    assert resolution.status is ConfirmationResolutionStatus.INVALIDATED
    assert coordinator.resolve(uuid4(), "yes").status is (
        ConfirmationResolutionStatus.NO_PENDING
    )


def test_coordinator_distinguishes_not_applicable_and_no_pending() -> None:
    coordinator, _ = make_coordinator()

    assert coordinator.resolve(uuid4(), "open calculator").status is (
        ConfirmationResolutionStatus.NOT_APPLICABLE
    )
    assert coordinator.resolve(uuid4(), "sim").status is (
        ConfirmationResolutionStatus.NO_PENDING
    )


def test_coordinator_expires_at_exact_boundary_and_consumes_slot() -> None:
    coordinator, clock = make_coordinator()
    pending = coordinator.begin(
        uuid4(),
        make_action(),
        InteractionLanguage.PT_BR,
    )
    clock.timestamp = pending.expires_at

    resolution = coordinator.resolve(uuid4(), "sim")

    assert resolution.status is ConfirmationResolutionStatus.EXPIRED
    assert resolution.pending is pending
    assert coordinator.resolve(uuid4(), "sim").status is (
        ConfirmationResolutionStatus.NO_PENDING
    )


def test_begin_lazily_discards_expired_slot() -> None:
    coordinator, clock = make_coordinator()
    first = coordinator.begin(
        uuid4(),
        make_action(),
        InteractionLanguage.PT_BR,
    )
    clock.timestamp = first.expires_at

    second = coordinator.begin(
        uuid4(),
        make_action(),
        InteractionLanguage.EN_US,
    )

    assert second.confirmation_id != first.confirmation_id


def test_clear_and_new_coordinator_start_empty() -> None:
    coordinator, _ = make_coordinator()
    coordinator.begin(uuid4(), make_action(), InteractionLanguage.PT_BR)

    assert coordinator.clear() is True
    assert coordinator.clear() is False

    new_coordinator, _ = make_coordinator()
    assert new_coordinator.resolve(uuid4(), "yes").status is (
        ConfirmationResolutionStatus.NO_PENDING
    )
