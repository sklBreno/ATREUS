"""Tests for provider-neutral application action contracts."""

from dataclasses import FrozenInstanceError

import pytest

from atreus.application.contracts import (
    APPLICATION_ACTION_DEFINITIONS,
    find_application_action_definition,
    is_supported_application_action,
    supported_application_action,
)
from atreus.application.exceptions import InvalidApplicationActionError
from atreus.application.models import (
    ApplicationAction,
    ApplicationActionDefinition,
    ApplicationIntent,
)
from atreus.system.models import ApplicationIdentifier


def test_application_action_is_immutable_and_contains_no_native_details() -> None:
    action = ApplicationAction(
        ApplicationIntent.OPEN_APPLICATION,
        "application.open",
        ApplicationIdentifier.CALCULATOR,
    )

    with pytest.raises(FrozenInstanceError):
        action.capability_id = "application.status"  # type: ignore[misc]

    assert hasattr(action, "__slots__")
    assert not hasattr(action, "executable")
    assert not hasattr(action, "process_name")
    assert not hasattr(action, "process_id")
    assert not hasattr(action, "path")
    assert not hasattr(action, "command")


@pytest.mark.parametrize(
    ("intent_id", "capability_id", "application_id"),
    (
        ("OPEN_APPLICATION", "application.open", ApplicationIdentifier.CALCULATOR),
        (ApplicationIntent.OPEN_APPLICATION, " ", ApplicationIdentifier.CALCULATOR),
        (ApplicationIntent.OPEN_APPLICATION, " application.open", ApplicationIdentifier.CALCULATOR),
        (ApplicationIntent.OPEN_APPLICATION, "application.open", "calculator"),
    ),
)
def test_application_action_rejects_invalid_contract_values(
    intent_id: object,
    capability_id: object,
    application_id: object,
) -> None:
    with pytest.raises(InvalidApplicationActionError):
        ApplicationAction(
            intent_id,  # type: ignore[arg-type]
            capability_id,  # type: ignore[arg-type]
            application_id,  # type: ignore[arg-type]
        )


def test_action_matrix_declares_every_v1_intent_target_combination() -> None:
    declared = {
        (definition.intent_id, definition.application_id): (
            definition.capability_id,
            definition.supported,
        )
        for definition in APPLICATION_ACTION_DEFINITIONS
    }

    assert declared == {
        (
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.CALCULATOR,
        ): ("application.open", True),
        (
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.NOTEPAD,
        ): ("application.open", True),
        (
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.SPOTIFY,
        ): ("application.open", False),
        (
            ApplicationIntent.APPLICATION_STATUS,
            ApplicationIdentifier.CALCULATOR,
        ): ("application.status", True),
        (
            ApplicationIntent.APPLICATION_STATUS,
            ApplicationIdentifier.NOTEPAD,
        ): ("application.status", True),
        (
            ApplicationIntent.APPLICATION_STATUS,
            ApplicationIdentifier.SPOTIFY,
        ): ("application.status", False),
    }


@pytest.mark.parametrize(
    ("intent_id", "application_id", "capability_id"),
    (
        (
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.CALCULATOR,
            "application.open",
        ),
        (
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.NOTEPAD,
            "application.open",
        ),
        (
            ApplicationIntent.APPLICATION_STATUS,
            ApplicationIdentifier.CALCULATOR,
            "application.status",
        ),
        (
            ApplicationIntent.APPLICATION_STATUS,
            ApplicationIdentifier.NOTEPAD,
            "application.status",
        ),
    ),
)
def test_supported_action_is_resolved_from_local_matrix(
    intent_id: ApplicationIntent,
    application_id: ApplicationIdentifier,
    capability_id: str,
) -> None:
    action = supported_application_action(intent_id, application_id)

    assert action is not None
    assert action.intent_id is intent_id
    assert action.application_id is application_id
    assert action.capability_id == capability_id
    assert is_supported_application_action(action)


@pytest.mark.parametrize("intent_id", tuple(ApplicationIntent))
def test_spotify_combinations_are_explicitly_unsupported(
    intent_id: ApplicationIntent,
) -> None:
    definition = find_application_action_definition(
        intent_id,
        ApplicationIdentifier.SPOTIFY,
    )

    assert definition is not None
    assert definition.supported is False
    assert supported_application_action(
        intent_id,
        ApplicationIdentifier.SPOTIFY,
    ) is None


def test_action_definition_rejects_non_boolean_support_flag() -> None:
    with pytest.raises(InvalidApplicationActionError):
        ApplicationActionDefinition(
            ApplicationIntent.OPEN_APPLICATION,
            ApplicationIdentifier.CALCULATOR,
            "application.open",
            1,  # type: ignore[arg-type]
        )
