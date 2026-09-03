"""Strict JSON serialization for Personal Profile schema version 1."""

import json
from datetime import datetime
from typing import cast

from atreus.profile.exceptions import (
    InvalidPersonalProfileError,
    PersonalProfileLoadError,
    UnsupportedPersonalProfileVersionError,
)
from atreus.profile.models import (
    PERSONAL_PROFILE_SCHEMA_VERSION,
    PersonalProfile,
    ProfileCareer,
    ProfileEducation,
    ProfileIdentity,
    ProfileInteractionPreferences,
    ProfileLearningPreferences,
    ProfileProject,
    ProfileTechnicalEnvironment,
)

MAX_PERSONAL_PROFILE_FILE_BYTES = 262_144

_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "updated_at",
        "identity",
        "education",
        "career",
        "technical_environment",
        "learning_preferences",
        "projects",
        "hobbies",
        "interaction_preferences",
    }
)


class PersonalProfileJsonCodec:
    """Encode and decode the strict version 1 Personal Profile JSON schema."""

    @staticmethod
    def encode(profile: PersonalProfile) -> bytes:
        """Serialize one validated profile deterministically as UTF-8 JSON."""
        if not isinstance(profile, PersonalProfile):
            raise InvalidPersonalProfileError(
                "Personal Profile serialization requires a PersonalProfile."
            )
        document = {
            "career": _encode_career(profile.career),
            "education": _encode_education(profile.education),
            "hobbies": list(profile.hobbies),
            "identity": _encode_identity(profile.identity),
            "interaction_preferences": _encode_interaction_preferences(
                profile.interaction_preferences
            ),
            "learning_preferences": _encode_learning_preferences(
                profile.learning_preferences
            ),
            "projects": [_encode_project(project) for project in profile.projects],
            "schema_version": profile.schema_version,
            "technical_environment": _encode_technical_environment(
                profile.technical_environment
            ),
            "updated_at": profile.updated_at.isoformat().replace("+00:00", "Z"),
        }
        encoded = (
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_PERSONAL_PROFILE_FILE_BYTES:
            raise InvalidPersonalProfileError(
                "Personal Profile document exceeds the supported size."
            )
        return encoded

    @staticmethod
    def decode(data: bytes) -> PersonalProfile:
        """Decode and validate one strict UTF-8 profile document."""
        if not isinstance(data, bytes):
            raise PersonalProfileLoadError(
                "Personal Profile document must be supplied as bytes."
            )
        if len(data) > MAX_PERSONAL_PROFILE_FILE_BYTES:
            raise PersonalProfileLoadError(
                "Personal Profile document exceeds the supported size."
            )
        try:
            text = data.decode("utf-8")
            decoded: object = json.loads(
                text,
                parse_constant=_reject_non_finite_number,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError):
            raise PersonalProfileLoadError(
                "Personal Profile document is malformed."
            ) from None
        root = _object(decoded, _ROOT_FIELDS, "root")
        schema_version = _required_integer(root, "schema_version")
        if schema_version != PERSONAL_PROFILE_SCHEMA_VERSION:
            raise UnsupportedPersonalProfileVersionError(
                "Personal Profile schema version is unsupported."
            )
        try:
            return PersonalProfile(
                schema_version=schema_version,
                updated_at=_required_datetime(root, "updated_at"),
                identity=_decode_identity(root.get("identity")),
                education=_decode_education(root.get("education")),
                career=_decode_career(root.get("career")),
                technical_environment=_decode_technical_environment(
                    root.get("technical_environment")
                ),
                learning_preferences=_decode_learning_preferences(
                    root.get("learning_preferences")
                ),
                projects=_projects(root.get("projects", [])),
                hobbies=_strings(root.get("hobbies", []), "hobbies"),
                interaction_preferences=_decode_interaction_preferences(
                    root.get("interaction_preferences")
                ),
            )
        except InvalidPersonalProfileError as error:
            raise PersonalProfileLoadError(
                "Personal Profile document contains invalid values."
            ) from error


def _reject_non_finite_number(value: str) -> object:
    raise ValueError(f"Unsupported numeric constant: {value}")


def _object(
    value: object,
    allowed_fields: frozenset[str],
    name: str,
) -> dict[str, object]:
    if type(value) is not dict:
        raise PersonalProfileLoadError(
            f"Personal Profile {name} must be a JSON object."
        )
    result = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in result):
        raise PersonalProfileLoadError(
            f"Personal Profile {name} property name is invalid."
        )
    typed = cast(dict[str, object], result)
    unexpected = set(typed) - allowed_fields
    if unexpected:
        raise PersonalProfileLoadError(
            f"Personal Profile {name} contains unknown properties."
        )
    return typed


def _required_integer(values: dict[str, object], field_name: str) -> int:
    value = values.get(field_name)
    if type(value) is not int:
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} must be an integer."
        )
    return value


def _required_datetime(values: dict[str, object], field_name: str) -> datetime:
    value = values.get(field_name)
    if not isinstance(value, str):
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} must be a timestamp."
        )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} is invalid."
        ) from None


def _optional_string(values: dict[str, object], field_name: str) -> str | None:
    value = values.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} must be text or null."
        )
    return value


def _strings(value: object, field_name: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} must be an array."
        )
    values = cast(list[object], value)
    if any(not isinstance(item, str) for item in values):
        raise PersonalProfileLoadError(
            f"Personal Profile {field_name} must contain only text."
        )
    return tuple(cast(list[str], values))


def _projects(value: object) -> tuple[ProfileProject, ...]:
    if type(value) is not list:
        raise PersonalProfileLoadError("Personal Profile projects must be an array.")
    return tuple(_decode_project(item) for item in cast(list[object], value))


def _decode_identity(value: object) -> ProfileIdentity | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset({"display_name", "locale", "timezone"}),
        "identity",
    )
    return ProfileIdentity(
        display_name=_optional_string(values, "display_name"),
        locale=_optional_string(values, "locale"),
        timezone=_optional_string(values, "timezone"),
    )


def _decode_education(value: object) -> ProfileEducation | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset({"current_degree", "institution", "technical_training"}),
        "education",
    )
    return ProfileEducation(
        current_degree=_optional_string(values, "current_degree"),
        institution=_optional_string(values, "institution"),
        technical_training=_strings(
            values.get("technical_training", []),
            "technical_training",
        ),
    )


def _decode_career(value: object) -> ProfileCareer | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset(
            {
                "current_role",
                "professional_context",
                "target_roles",
                "areas_of_interest",
                "goals",
            }
        ),
        "career",
    )
    return ProfileCareer(
        current_role=_optional_string(values, "current_role"),
        professional_context=_optional_string(values, "professional_context"),
        target_roles=_strings(values.get("target_roles", []), "target_roles"),
        areas_of_interest=_strings(
            values.get("areas_of_interest", []),
            "areas_of_interest",
        ),
        goals=_strings(values.get("goals", []), "goals"),
    )


def _decode_technical_environment(
    value: object,
) -> ProfileTechnicalEnvironment | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset({"operating_system", "hardware", "tools"}),
        "technical_environment",
    )
    return ProfileTechnicalEnvironment(
        operating_system=_optional_string(values, "operating_system"),
        hardware=_strings(values.get("hardware", []), "hardware"),
        tools=_strings(values.get("tools", []), "tools"),
    )


def _decode_learning_preferences(
    value: object,
) -> ProfileLearningPreferences | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset({"explanation_style", "study_preferences"}),
        "learning_preferences",
    )
    return ProfileLearningPreferences(
        explanation_style=_optional_string(values, "explanation_style"),
        study_preferences=_strings(
            values.get("study_preferences", []),
            "study_preferences",
        ),
    )


def _decode_project(value: object) -> ProfileProject:
    values = _object(
        value,
        frozenset({"name", "description", "status"}),
        "project",
    )
    name = values.get("name")
    if not isinstance(name, str):
        raise PersonalProfileLoadError("Personal Profile project name is required.")
    return ProfileProject(
        name=name,
        description=_optional_string(values, "description"),
        status=_optional_string(values, "status"),
    )


def _decode_interaction_preferences(
    value: object,
) -> ProfileInteractionPreferences | None:
    if value is None:
        return None
    values = _object(
        value,
        frozenset({"preferred_language", "response_style"}),
        "interaction_preferences",
    )
    return ProfileInteractionPreferences(
        preferred_language=_optional_string(values, "preferred_language"),
        response_style=_optional_string(values, "response_style"),
    )


def _encode_identity(value: ProfileIdentity | None) -> object:
    if value is None:
        return None
    return {
        "display_name": value.display_name,
        "locale": value.locale,
        "timezone": value.timezone,
    }


def _encode_education(value: ProfileEducation | None) -> object:
    if value is None:
        return None
    return {
        "current_degree": value.current_degree,
        "institution": value.institution,
        "technical_training": list(value.technical_training),
    }


def _encode_career(value: ProfileCareer | None) -> object:
    if value is None:
        return None
    return {
        "areas_of_interest": list(value.areas_of_interest),
        "current_role": value.current_role,
        "goals": list(value.goals),
        "professional_context": value.professional_context,
        "target_roles": list(value.target_roles),
    }


def _encode_technical_environment(
    value: ProfileTechnicalEnvironment | None,
) -> object:
    if value is None:
        return None
    return {
        "hardware": list(value.hardware),
        "operating_system": value.operating_system,
        "tools": list(value.tools),
    }


def _encode_learning_preferences(
    value: ProfileLearningPreferences | None,
) -> object:
    if value is None:
        return None
    return {
        "explanation_style": value.explanation_style,
        "study_preferences": list(value.study_preferences),
    }


def _encode_project(value: ProfileProject) -> object:
    return {
        "description": value.description,
        "name": value.name,
        "status": value.status,
    }


def _encode_interaction_preferences(
    value: ProfileInteractionPreferences | None,
) -> object:
    if value is None:
        return None
    return {
        "preferred_language": value.preferred_language,
        "response_style": value.response_style,
    }
