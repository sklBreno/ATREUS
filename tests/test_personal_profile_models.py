"""Tests for immutable Personal Profile domain contracts."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from atreus.profile.exceptions import InvalidPersonalProfileError
from atreus.profile.models import (
    PersonalProfile,
    PersonalProfileProjection,
    ProfileCareer,
    ProfileEducation,
    ProfileIdentity,
    ProfileInteractionPreferences,
    ProfileLearningPreferences,
    ProfileProject,
    ProfileTechnicalEnvironment,
    empty_personal_profile,
    personal_profile_is_empty,
)
from tests.support import NOW


def sample_profile() -> PersonalProfile:
    """Create one complete fictional Personal Profile test fixture."""
    return PersonalProfile(
        schema_version=1,
        updated_at=NOW,
        identity=ProfileIdentity("Alex Example", "pt-BR", "America/Cuiaba"),
        education=ProfileEducation(
            "Information Systems",
            "Example Institute",
            ("Network fundamentals",),
        ),
        career=ProfileCareer(
            "IT student",
            "Studies local infrastructure.",
            ("Infrastructure analyst",),
            ("Infrastructure",),
            ("Build reliable systems",),
        ),
        technical_environment=ProfileTechnicalEnvironment(
            "Windows 11",
            ("Example GPU 12 GB",),
            ("Python", "PowerShell"),
        ),
        learning_preferences=ProfileLearningPreferences(
            "Concise explanations",
            ("Practical examples",),
        ),
        projects=(ProfileProject("Project Atlas", "Local assistant.", "active"),),
        hobbies=("Gaming",),
        interaction_preferences=ProfileInteractionPreferences(
            "pt-BR",
            "Direct",
        ),
    )


def test_personal_profile_models_are_frozen_slotted_and_hide_content() -> None:
    profile = sample_profile()

    with pytest.raises(FrozenInstanceError):
        profile.hobbies = ()  # type: ignore[misc]

    assert not hasattr(profile, "__dict__")
    assert "Alex Example" not in repr(profile)
    assert "Information Systems" not in repr(profile.education)
    assert "Project Atlas" not in repr(profile.projects[0])


def test_personal_profile_normalizes_timestamp_to_utc() -> None:
    local_time = datetime(2026, 9, 3, 8, 0, tzinfo=timezone(timedelta(hours=-4)))

    profile = empty_personal_profile(local_time)

    assert profile.updated_at == datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    assert personal_profile_is_empty(profile)


@pytest.mark.parametrize(
    "profile",
    (
        lambda: PersonalProfile(schema_version=2, updated_at=NOW),
        lambda: PersonalProfile(schema_version=1, updated_at=datetime(2026, 1, 1)),
        lambda: PersonalProfile(  # type: ignore[arg-type]
            schema_version=1,
            updated_at=NOW,
            hobbies=["Gaming"],
        ),
        lambda: PersonalProfile(
            schema_version=1,
            updated_at=NOW,
            projects=(ProfileProject("Duplicate"), ProfileProject("duplicate")),
        ),
    ),
)
def test_personal_profile_rejects_invalid_root_contracts(profile: object) -> None:
    with pytest.raises(InvalidPersonalProfileError):
        profile()


@pytest.mark.parametrize(
    "constructor",
    (
        lambda: ProfileIdentity(),
        lambda: ProfileIdentity(" "),
        lambda: ProfileIdentity("hidden\x00value"),
        lambda: ProfileEducation(technical_training=("Python", "python")),
        lambda: ProfileCareer(goals=("x" * 2_001,)),
        lambda: ProfileTechnicalEnvironment(hardware=("x" * 201,)),
        lambda: ProfileLearningPreferences(  # type: ignore[arg-type]
            study_preferences=["Examples"]
        ),
        lambda: ProfileProject(" "),
        lambda: ProfileInteractionPreferences(),
    ),
)
def test_profile_sections_reject_invalid_or_mutable_values(
    constructor: object,
) -> None:
    with pytest.raises(InvalidPersonalProfileError):
        constructor()


def test_projection_is_immutable_and_hides_private_content() -> None:
    projection = PersonalProfileProjection(
        '[user_profile_data]\ntechnical_environment.tools: "Python"\n'
        "[/user_profile_data]"
    )

    with pytest.raises(FrozenInstanceError):
        projection.content = "changed"  # type: ignore[misc]

    assert "Python" not in repr(projection)


def test_projection_rejects_control_characters() -> None:
    with pytest.raises(InvalidPersonalProfileError):
        PersonalProfileProjection("[user_profile_data]\x7f[/user_profile_data]")


def test_sensitive_categories_are_absent_from_profile_schema() -> None:
    profile = sample_profile()

    for forbidden in (
        "password",
        "api_key",
        "credential",
        "banking",
        "credit_card",
        "government_id",
        "medical_data",
        "raw_messages",
        "secret",
    ):
        assert not hasattr(profile, forbidden)
