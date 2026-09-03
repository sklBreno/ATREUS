"""Deterministic bounded Personal Profile projection for conversation."""

import json

from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.personal_profile import (
    PersonalProfileProjectionProvider,
    PersonalProfileProvider,
)
from atreus.profile.exceptions import InvalidPersonalProfileError
from atreus.profile.models import PersonalProfile, PersonalProfileProjection

_TECHNICAL_MARKERS = frozenset(
    {
        "computer",
        "computador",
        "device",
        "dispositivo",
        "ferramenta",
        "gpu",
        "hardware",
        "local model",
        "modelo local",
        "operating system",
        "sistema operacional",
        "software",
        "technical",
        "técnic",
        "tecnic",
        "tool",
    }
)
_CAREER_MARKERS = frozenset(
    {
        "career",
        "carreira",
        "emprego",
        "job",
        "profession",
        "profiss",
        "role",
        "trabalho",
        "work",
    }
)
_LEARNING_MARKERS = frozenset(
    {
        "aprender",
        "aprendizado",
        "curso",
        "degree",
        "education",
        "estud",
        "explain",
        "explic",
        "faculdade",
        "learn",
        "study",
        "training",
    }
)
_PROJECT_MARKERS = frozenset({"project", "projects", "projeto", "projetos"})
_INTERACTION_MARKERS = frozenset(
    {
        "answer style",
        "como responder",
        "idioma",
        "language preference",
        "response style",
        "estilo de resposta",
    }
)
_OPENING = "[user_profile_data]"
_CLOSING = "[/user_profile_data]"


class DeterministicPersonalProfileProjectionProvider(
    PersonalProfileProjectionProvider
):
    """Select only clearly relevant approved profile categories."""

    def __init__(
        self,
        profile_provider: PersonalProfileProvider,
        maximum_characters: int,
    ) -> None:
        """Initialize profile source and positive projection character bound."""
        if type(maximum_characters) is not int or maximum_characters <= 0:
            raise InvalidPersonalProfileError(
                "Personal Profile projection limit must be positive."
            )
        self._profile_provider = profile_provider
        self._maximum_characters = maximum_characters

    def project(
        self,
        content: str,
        language: InteractionLanguage,
    ) -> PersonalProfileProjection | None:
        """Return a bounded category-specific projection for one request."""
        if not isinstance(content, str) or not isinstance(
            language,
            InteractionLanguage,
        ):
            raise InvalidPersonalProfileError(
                "Personal Profile projection input is invalid."
            )
        normalized = " ".join(content.casefold().split())
        profile = self._profile_provider.get_profile()
        lines: list[str] = []
        if _matches(normalized, _TECHNICAL_MARKERS):
            lines.extend(_technical_lines(profile))
        if _matches(normalized, _CAREER_MARKERS):
            lines.extend(_career_lines(profile))
            lines.extend(_education_lines(profile))
        if _matches(normalized, _LEARNING_MARKERS):
            lines.extend(_education_lines(profile))
            lines.extend(_learning_lines(profile))
        if _matches(normalized, _PROJECT_MARKERS):
            lines.extend(_project_lines(profile, normalized))
        if _matches(normalized, _INTERACTION_MARKERS):
            lines.extend(_interaction_lines(profile))
        selected = tuple(dict.fromkeys(lines))
        projected = _bounded_document(selected, self._maximum_characters)
        return PersonalProfileProjection(projected) if projected is not None else None


def _matches(content: str, markers: frozenset[str]) -> bool:
    return any(marker in content for marker in markers)


def _line(name: str, value: str) -> str:
    return f"{name}: {json.dumps(value, ensure_ascii=False)}"


def _lines(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_line(name, value) for value in values)


def _technical_lines(profile: PersonalProfile) -> tuple[str, ...]:
    value = profile.technical_environment
    if value is None:
        return ()
    lines: list[str] = []
    if value.operating_system is not None:
        lines.append(_line("technical_environment.operating_system", value.operating_system))
    lines.extend(_lines("technical_environment.hardware", value.hardware))
    lines.extend(_lines("technical_environment.tools", value.tools))
    return tuple(lines)


def _career_lines(profile: PersonalProfile) -> tuple[str, ...]:
    value = profile.career
    if value is None:
        return ()
    lines: list[str] = []
    if value.current_role is not None:
        lines.append(_line("career.current_role", value.current_role))
    if value.professional_context is not None:
        lines.append(_line("career.professional_context", value.professional_context))
    lines.extend(_lines("career.target_roles", value.target_roles))
    lines.extend(_lines("career.areas_of_interest", value.areas_of_interest))
    lines.extend(_lines("career.goals", value.goals))
    return tuple(lines)


def _education_lines(profile: PersonalProfile) -> tuple[str, ...]:
    value = profile.education
    if value is None:
        return ()
    lines: list[str] = []
    if value.current_degree is not None:
        lines.append(_line("education.current_degree", value.current_degree))
    if value.institution is not None:
        lines.append(_line("education.institution", value.institution))
    lines.extend(_lines("education.technical_training", value.technical_training))
    return tuple(lines)


def _learning_lines(profile: PersonalProfile) -> tuple[str, ...]:
    value = profile.learning_preferences
    if value is None:
        return ()
    lines: list[str] = []
    if value.explanation_style is not None:
        lines.append(_line("learning_preferences.explanation_style", value.explanation_style))
    lines.extend(
        _lines("learning_preferences.study_preferences", value.study_preferences)
    )
    return tuple(lines)


def _project_lines(profile: PersonalProfile, content: str) -> tuple[str, ...]:
    projects = tuple(
        project
        for project in profile.projects
        if project.name.casefold() in content
    )
    if not projects:
        projects = profile.projects
    lines: list[str] = []
    for project in projects:
        lines.append(_line("projects.name", project.name))
        if project.description is not None:
            lines.append(_line("projects.description", project.description))
        if project.status is not None:
            lines.append(_line("projects.status", project.status))
    return tuple(lines)


def _interaction_lines(profile: PersonalProfile) -> tuple[str, ...]:
    value = profile.interaction_preferences
    if value is None:
        return ()
    lines: list[str] = []
    if value.preferred_language is not None:
        lines.append(
            _line("interaction_preferences.preferred_language", value.preferred_language)
        )
    if value.response_style is not None:
        lines.append(_line("interaction_preferences.response_style", value.response_style))
    return tuple(lines)


def _bounded_document(lines: tuple[str, ...], limit: int) -> str | None:
    if not lines:
        return None
    selected: list[str] = []
    for line in lines:
        candidate = "\n".join((_OPENING, *selected, line, _CLOSING))
        if len(candidate) > limit:
            break
        selected.append(line)
    if not selected:
        return None
    return "\n".join((_OPENING, *selected, _CLOSING))
