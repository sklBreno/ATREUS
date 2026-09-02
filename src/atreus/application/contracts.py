"""Local action mappings for approved application intent and target pairs."""

from atreus.application.models import (
    ApplicationAction,
    ApplicationActionDefinition,
    ApplicationIntent,
)
from atreus.capability.contracts import (
    APPLICATION_STATUS_CAPABILITY_ID,
    OPEN_APPLICATION_CAPABILITY_ID,
)
from atreus.system.models import ApplicationIdentifier

APPLICATION_ACTION_DEFINITIONS: tuple[ApplicationActionDefinition, ...] = (
    ApplicationActionDefinition(
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.CALCULATOR,
        OPEN_APPLICATION_CAPABILITY_ID,
        True,
    ),
    ApplicationActionDefinition(
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.NOTEPAD,
        OPEN_APPLICATION_CAPABILITY_ID,
        True,
    ),
    ApplicationActionDefinition(
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.SPOTIFY,
        OPEN_APPLICATION_CAPABILITY_ID,
        False,
    ),
    ApplicationActionDefinition(
        ApplicationIntent.APPLICATION_STATUS,
        ApplicationIdentifier.CALCULATOR,
        APPLICATION_STATUS_CAPABILITY_ID,
        True,
    ),
    ApplicationActionDefinition(
        ApplicationIntent.APPLICATION_STATUS,
        ApplicationIdentifier.NOTEPAD,
        APPLICATION_STATUS_CAPABILITY_ID,
        True,
    ),
    ApplicationActionDefinition(
        ApplicationIntent.APPLICATION_STATUS,
        ApplicationIdentifier.SPOTIFY,
        APPLICATION_STATUS_CAPABILITY_ID,
        False,
    ),
)

DETERMINISTIC_APPLICATION_COMMANDS: tuple[
    tuple[str, ApplicationIntent, ApplicationIdentifier],
    ...,
] = (
    (
        "open calculator",
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.CALCULATOR,
    ),
    (
        "open notepad",
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.NOTEPAD,
    ),
    (
        "open spotify",
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIdentifier.SPOTIFY,
    ),
)


def find_application_action_definition(
    intent_id: ApplicationIntent,
    application_id: ApplicationIdentifier,
) -> ApplicationActionDefinition | None:
    """Return the declared definition for one intent and application pair."""
    return next(
        (
            definition
            for definition in APPLICATION_ACTION_DEFINITIONS
            if definition.intent_id is intent_id
            and definition.application_id is application_id
        ),
        None,
    )


def supported_application_action(
    intent_id: ApplicationIntent,
    application_id: ApplicationIdentifier,
) -> ApplicationAction | None:
    """Return a typed action only when the local matrix supports the pair."""
    definition = find_application_action_definition(intent_id, application_id)
    if definition is None or not definition.supported:
        return None
    return ApplicationAction(
        intent_id=definition.intent_id,
        capability_id=definition.capability_id,
        application_id=definition.application_id,
    )


def is_supported_application_action(action: ApplicationAction) -> bool:
    """Return whether an action exactly matches one supported definition."""
    definition = find_application_action_definition(
        action.intent_id,
        action.application_id,
    )
    return (
        definition is not None
        and definition.supported
        and definition.capability_id == action.capability_id
    )


def deterministic_application_action(content: str) -> ApplicationAction | None:
    """Resolve only one exact approved deterministic application command."""
    definition = deterministic_application_action_definition(content)
    if definition is None or not definition.supported:
        return None
    return ApplicationAction(
        definition.intent_id,
        definition.capability_id,
        definition.application_id,
    )


def deterministic_application_action_definition(
    content: str,
) -> ApplicationActionDefinition | None:
    """Resolve one exact command to its declared support definition."""
    normalized_content = " ".join(content.casefold().split()).strip(" .!?")
    match = next(
        (
            (intent_id, application_id)
            for command, intent_id, application_id in DETERMINISTIC_APPLICATION_COMMANDS
            if command == normalized_content
        ),
        None,
    )
    if match is None:
        return None
    return find_application_action_definition(*match)
