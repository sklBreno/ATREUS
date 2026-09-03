"""Immutable contracts owned by the ATREUS Personal Profile module."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from atreus.profile.exceptions import (
    InvalidPersonalProfileError,
    InvalidProfileClearConfirmationError,
)

PERSONAL_PROFILE_SCHEMA_VERSION = 1
PROFILE_SHORT_TEXT_MAX_CHARACTERS = 200
PROFILE_LONG_TEXT_MAX_CHARACTERS = 2_000
PROFILE_COLLECTION_MAX_ITEMS = 32
PROFILE_PROJECT_MAX_ITEMS = 16


@dataclass(frozen=True, slots=True)
class ProfileIdentity:
    """Represent explicit low-risk user identity information."""

    display_name: str | None = field(default=None, repr=False)
    locale: str | None = field(default=None, repr=False)
    timezone: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate optional identity fields."""
        _validate_optional_text(self.display_name, "display_name")
        _validate_optional_text(self.locale, "locale")
        _validate_optional_text(self.timezone, "timezone")
        _require_populated_section(
            (self.display_name, self.locale, self.timezone),
            "identity",
        )


@dataclass(frozen=True, slots=True)
class ProfileEducation:
    """Represent explicit education and training information."""

    current_degree: str | None = field(default=None, repr=False)
    institution: str | None = field(default=None, repr=False)
    technical_training: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        """Validate optional education fields."""
        _validate_optional_text(self.current_degree, "current_degree")
        _validate_optional_text(self.institution, "institution")
        _validate_text_tuple(self.technical_training, "technical_training")
        _require_populated_section(
            (self.current_degree, self.institution, *self.technical_training),
            "education",
        )


@dataclass(frozen=True, slots=True)
class ProfileCareer:
    """Represent explicit professional context and goals."""

    current_role: str | None = field(default=None, repr=False)
    professional_context: str | None = field(default=None, repr=False)
    target_roles: tuple[str, ...] = field(default=(), repr=False)
    areas_of_interest: tuple[str, ...] = field(default=(), repr=False)
    goals: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        """Validate optional career fields."""
        _validate_optional_text(self.current_role, "current_role")
        _validate_optional_text(
            self.professional_context,
            "professional_context",
            PROFILE_LONG_TEXT_MAX_CHARACTERS,
        )
        _validate_text_tuple(self.target_roles, "target_roles")
        _validate_text_tuple(self.areas_of_interest, "areas_of_interest")
        _validate_text_tuple(
            self.goals,
            "goals",
            PROFILE_LONG_TEXT_MAX_CHARACTERS,
        )
        _require_populated_section(
            (
                self.current_role,
                self.professional_context,
                *self.target_roles,
                *self.areas_of_interest,
                *self.goals,
            ),
            "career",
        )


@dataclass(frozen=True, slots=True)
class ProfileTechnicalEnvironment:
    """Represent explicit platform-neutral technical environment details."""

    operating_system: str | None = field(default=None, repr=False)
    hardware: tuple[str, ...] = field(default=(), repr=False)
    tools: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        """Validate optional technical environment fields."""
        _validate_optional_text(self.operating_system, "operating_system")
        _validate_text_tuple(self.hardware, "hardware")
        _validate_text_tuple(self.tools, "tools")
        _require_populated_section(
            (self.operating_system, *self.hardware, *self.tools),
            "technical_environment",
        )


@dataclass(frozen=True, slots=True)
class ProfileLearningPreferences:
    """Represent explicit learning and explanation preferences."""

    explanation_style: str | None = field(default=None, repr=False)
    study_preferences: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        """Validate optional learning preference fields."""
        _validate_optional_text(self.explanation_style, "explanation_style")
        _validate_text_tuple(self.study_preferences, "study_preferences")
        _require_populated_section(
            (self.explanation_style, *self.study_preferences),
            "learning_preferences",
        )


@dataclass(frozen=True, slots=True)
class ProfileProject:
    """Represent one explicitly approved user project."""

    name: str = field(repr=False)
    description: str | None = field(default=None, repr=False)
    status: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate project fields."""
        _validate_text(self.name, "project name")
        _validate_optional_text(
            self.description,
            "project description",
            PROFILE_LONG_TEXT_MAX_CHARACTERS,
        )
        _validate_optional_text(self.status, "project status")


@dataclass(frozen=True, slots=True)
class ProfileInteractionPreferences:
    """Represent explicit non-operational interaction preferences."""

    preferred_language: str | None = field(default=None, repr=False)
    response_style: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate optional interaction preference fields."""
        _validate_optional_text(self.preferred_language, "preferred_language")
        _validate_optional_text(self.response_style, "response_style")
        _require_populated_section(
            (self.preferred_language, self.response_style),
            "interaction_preferences",
        )


@dataclass(frozen=True, slots=True)
class PersonalProfile:
    """Represent one explicit, user-approved, versioned Personal Profile."""

    schema_version: int
    updated_at: datetime
    identity: ProfileIdentity | None = field(default=None, repr=False)
    education: ProfileEducation | None = field(default=None, repr=False)
    career: ProfileCareer | None = field(default=None, repr=False)
    technical_environment: ProfileTechnicalEnvironment | None = field(
        default=None,
        repr=False,
    )
    learning_preferences: ProfileLearningPreferences | None = field(
        default=None,
        repr=False,
    )
    projects: tuple[ProfileProject, ...] = field(default=(), repr=False)
    hobbies: tuple[str, ...] = field(default=(), repr=False)
    interaction_preferences: ProfileInteractionPreferences | None = field(
        default=None,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Validate schema, section types, collections, and UTC timestamp."""
        if type(self.schema_version) is not int or (
            self.schema_version != PERSONAL_PROFILE_SCHEMA_VERSION
        ):
            raise InvalidPersonalProfileError(
                "Personal Profile schema_version must be 1."
            )
        object.__setattr__(self, "updated_at", _normalize_utc(self.updated_at))
        _validate_optional_section(self.identity, ProfileIdentity, "identity")
        _validate_optional_section(self.education, ProfileEducation, "education")
        _validate_optional_section(self.career, ProfileCareer, "career")
        _validate_optional_section(
            self.technical_environment,
            ProfileTechnicalEnvironment,
            "technical_environment",
        )
        _validate_optional_section(
            self.learning_preferences,
            ProfileLearningPreferences,
            "learning_preferences",
        )
        _validate_optional_section(
            self.interaction_preferences,
            ProfileInteractionPreferences,
            "interaction_preferences",
        )
        if not isinstance(self.projects, tuple) or any(
            not isinstance(project, ProfileProject) for project in self.projects
        ):
            raise InvalidPersonalProfileError(
                "Personal Profile projects must be an immutable tuple."
            )
        if len(self.projects) > PROFILE_PROJECT_MAX_ITEMS:
            raise InvalidPersonalProfileError(
                "Personal Profile contains too many projects."
            )
        project_names = tuple(project.name.casefold() for project in self.projects)
        if len(project_names) != len(set(project_names)):
            raise InvalidPersonalProfileError(
                "Personal Profile project names must be unique."
            )
        _validate_text_tuple(self.hobbies, "hobbies")


@dataclass(frozen=True, slots=True)
class PersonalProfileProjection:
    """Carry one bounded provider-safe declarative profile projection."""

    content: str = field(repr=False)

    def __post_init__(self) -> None:
        """Validate the non-empty bounded projection text."""
        if (
            not isinstance(self.content, str)
            or not self.content.strip()
            or self.content != self.content.strip()
            or any(
                (ord(character) < 32 and character != "\n")
                or ord(character) == 127
                for character in self.content
            )
        ):
            raise InvalidPersonalProfileError(
                "Personal Profile projection must be normalized safe text."
            )


class ProfileClearConfirmationStatus(StrEnum):
    """Identify one deterministic profile-clear confirmation state."""

    AVAILABLE = "AVAILABLE"
    NO_PENDING = "NO_PENDING"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class PendingProfileClear:
    """Represent one process-local pending Personal Profile clear."""

    confirmation_id: UUID
    original_request_id: UUID
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        """Validate identifiers and the UTC confirmation lifetime."""
        if not isinstance(self.confirmation_id, UUID) or not isinstance(
            self.original_request_id,
            UUID,
        ):
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation identifiers must be UUIDs."
            )
        created_at = _normalize_confirmation_utc(self.created_at)
        expires_at = _normalize_confirmation_utc(self.expires_at)
        if expires_at <= created_at:
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation must expire after creation."
            )
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ProfileClearConfirmationCheck:
    """Represent a non-consuming check of pending clear confirmation state."""

    status: ProfileClearConfirmationStatus
    pending: PendingProfileClear | None

    def __post_init__(self) -> None:
        """Validate status and pending payload consistency."""
        if not isinstance(self.status, ProfileClearConfirmationStatus):
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation status is invalid."
            )
        requires_pending = self.status is ProfileClearConfirmationStatus.AVAILABLE
        if requires_pending != isinstance(self.pending, PendingProfileClear):
            raise InvalidProfileClearConfirmationError(
                "Profile clear confirmation payload is inconsistent."
            )


def empty_personal_profile(updated_at: datetime) -> PersonalProfile:
    """Create one valid empty version 1 Personal Profile."""
    return PersonalProfile(
        schema_version=PERSONAL_PROFILE_SCHEMA_VERSION,
        updated_at=updated_at,
    )


def personal_profile_is_empty(profile: PersonalProfile) -> bool:
    """Return whether a validated profile contains no approved user fields."""
    if not isinstance(profile, PersonalProfile):
        raise InvalidPersonalProfileError("Personal Profile type is invalid.")
    return not any(
        (
            profile.identity,
            profile.education,
            profile.career,
            profile.technical_environment,
            profile.learning_preferences,
            profile.projects,
            profile.hobbies,
            profile.interaction_preferences,
        )
    )


def _validate_optional_section(
    value: object,
    expected_type: type[object],
    field_name: str,
) -> None:
    if value is not None and not isinstance(value, expected_type):
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} section is invalid."
        )


def _require_populated_section(values: tuple[object, ...], name: str) -> None:
    if not any(value is not None and value != () for value in values):
        raise InvalidPersonalProfileError(
            f"Personal Profile {name} section cannot be empty."
        )


def _validate_optional_text(
    value: str | None,
    field_name: str,
    maximum_characters: int = PROFILE_SHORT_TEXT_MAX_CHARACTERS,
) -> None:
    if value is not None:
        _validate_text(value, field_name, maximum_characters)


def _validate_text_tuple(
    values: tuple[str, ...],
    field_name: str,
    maximum_characters: int = PROFILE_SHORT_TEXT_MAX_CHARACTERS,
) -> None:
    if not isinstance(values, tuple):
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} must be an immutable tuple."
        )
    if len(values) > PROFILE_COLLECTION_MAX_ITEMS:
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} contains too many values."
        )
    for value in values:
        _validate_text(value, field_name, maximum_characters)
    normalized = tuple(value.casefold() for value in values)
    if len(normalized) != len(set(normalized)):
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} values must be unique."
        )


def _validate_text(
    value: str,
    field_name: str,
    maximum_characters: int = PROFILE_SHORT_TEXT_MAX_CHARACTERS,
    *,
    allow_newlines: bool = False,
) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} must be normalized non-empty text."
        )
    if len(value) > maximum_characters:
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} exceeds its character limit."
        )
    if any(
        (ord(character) < 32 and not (allow_newlines and character == "\n"))
        or ord(character) == 127
        for character in value
    ):
        raise InvalidPersonalProfileError(
            f"Personal Profile {field_name} contains control characters."
        )


def _normalize_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or (
        value.tzinfo is None or value.utcoffset() is None
    ):
        raise InvalidPersonalProfileError(
            "Personal Profile updated_at must be timezone-aware."
        )
    return value.astimezone(UTC)


def _normalize_confirmation_utc(value: datetime) -> datetime:
    try:
        return _normalize_utc(value)
    except InvalidPersonalProfileError:
        raise InvalidProfileClearConfirmationError(
            "Profile clear confirmation timestamps must be timezone-aware."
        ) from None
