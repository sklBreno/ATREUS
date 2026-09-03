"""Deterministic local Personal Profile interaction behavior."""

from datetime import timedelta

from atreus.interaction.models import ConversationalResponse, InteractionLanguage
from atreus.interfaces.clock import Clock
from atreus.interfaces.personal_profile import (
    PersonalProfileInteractionHandler,
    PersonalProfileStore,
)
from atreus.profile.confirmation import (
    InMemoryProfileClearConfirmationCoordinator,
)
from atreus.profile.exceptions import PersonalProfileException
from atreus.profile.models import (
    PersonalProfile,
    ProfileClearConfirmationStatus,
    personal_profile_is_empty,
)
from atreus.shared.request import Request

_READ_REQUESTS = frozenset(
    {
        "o que você sabe sobre mim",
        "o que voce sabe sobre mim",
        "mostrar meu perfil",
        "show my profile",
        "what do you know about me",
    }
)
_CLEAR_REQUESTS = frozenset({"clear my profile", "limpar meu perfil"})
_CONFIRM_REQUESTS = frozenset(
    {
        "confirm clearing my profile",
        "confirmar limpeza do meu perfil",
    }
)


class DeterministicPersonalProfileInteractionHandler(
    PersonalProfileInteractionHandler
):
    """Handle exact profile read and confirmed clear requests without AI."""

    def __init__(
        self,
        store: PersonalProfileStore,
        clock: Clock,
        clear_confirmation_ttl: timedelta,
        *,
        enabled: bool,
    ) -> None:
        """Initialize store, time source, enabled state, and clear coordinator."""
        self._store = store
        self._clock = clock
        self._enabled = enabled
        self._confirmation = InMemoryProfileClearConfirmationCoordinator(
            clock,
            clear_confirmation_ttl,
        )

    def handle(
        self,
        request: Request,
        language: InteractionLanguage,
    ) -> ConversationalResponse | None:
        """Return one local response for an exact profile request."""
        normalized = _normalize(request.content)
        if normalized in _READ_REQUESTS:
            return self._response(
                request,
                language,
                self._read_text(language),
            )
        if normalized in _CLEAR_REQUESTS:
            return self._response(
                request,
                language,
                self._begin_clear_text(request, language),
            )
        if normalized in _CONFIRM_REQUESTS:
            return self._response(
                request,
                language,
                self._confirm_clear_text(language),
            )
        return None

    def _read_text(self, language: InteractionLanguage) -> str:
        if not self._enabled:
            return _disabled_text(language)
        try:
            profile = self._store.get_profile()
        except PersonalProfileException:
            return _unavailable_text(language)
        if personal_profile_is_empty(profile):
            return _empty_text(language)
        return _render_profile(profile, language)

    def _begin_clear_text(
        self,
        request: Request,
        language: InteractionLanguage,
    ) -> str:
        if not self._enabled:
            return _disabled_text(language)
        try:
            if personal_profile_is_empty(self._store.get_profile()):
                return _empty_text(language)
        except PersonalProfileException:
            return _unavailable_text(language)
        self._confirmation.begin(request.request_id)
        if language is InteractionLanguage.EN_US:
            return (
                "Profile clear is pending. Type 'confirm clearing my profile' "
                "to permanently clear only your Personal Profile."
            )
        return (
            "A limpeza do perfil está pendente. Digite 'confirmar limpeza do meu "
            "perfil' para limpar permanentemente apenas seu Personal Profile."
        )

    def _confirm_clear_text(self, language: InteractionLanguage) -> str:
        if not self._enabled:
            return _disabled_text(language)
        check = self._confirmation.check()
        if check.status is ProfileClearConfirmationStatus.NO_PENDING:
            return (
                "No profile clear is pending."
                if language is InteractionLanguage.EN_US
                else "Nenhuma limpeza de perfil está pendente."
            )
        if check.status is ProfileClearConfirmationStatus.EXPIRED:
            return (
                "The profile clear confirmation expired."
                if language is InteractionLanguage.EN_US
                else "A confirmação de limpeza do perfil expirou."
            )
        pending = check.pending
        if pending is None:
            return _unavailable_text(language)
        try:
            self._store.clear(self._clock.now())
        except PersonalProfileException:
            return (
                "I could not clear your Personal Profile. No success was recorded."
                if language is InteractionLanguage.EN_US
                else (
                    "Não foi possível limpar seu Personal Profile. "
                    "Nenhum sucesso foi registrado."
                )
            )
        if not self._confirmation.consume(pending.confirmation_id):
            return _unavailable_text(language)
        return (
            "Your Personal Profile was cleared."
            if language is InteractionLanguage.EN_US
            else "Seu Personal Profile foi limpo."
        )

    @staticmethod
    def _response(
        request: Request,
        language: InteractionLanguage,
        text: str,
    ) -> ConversationalResponse:
        return ConversationalResponse(request.request_id, text, language)


def _render_profile(
    profile: PersonalProfile,
    language: InteractionLanguage,
) -> str:
    portuguese = language is InteractionLanguage.PT_BR
    lines = ["Seu perfil pessoal:" if portuguese else "Your personal profile:"]
    identity = profile.identity
    if identity is not None:
        _append_value(lines, "Nome" if portuguese else "Name", identity.display_name)
        _append_value(lines, "Localidade" if portuguese else "Locale", identity.locale)
        _append_value(lines, "Fuso horário" if portuguese else "Timezone", identity.timezone)
    education = profile.education
    if education is not None:
        _append_value(lines, "Formação" if portuguese else "Degree", education.current_degree)
        _append_value(lines, "Instituição" if portuguese else "Institution", education.institution)
        _append_values(lines, "Treinamento" if portuguese else "Training", education.technical_training)
    career = profile.career
    if career is not None:
        _append_value(lines, "Atuação" if portuguese else "Current role", career.current_role)
        _append_value(lines, "Contexto profissional" if portuguese else "Professional context", career.professional_context)
        _append_values(lines, "Cargos desejados" if portuguese else "Target roles", career.target_roles)
        _append_values(lines, "Áreas de interesse" if portuguese else "Areas of interest", career.areas_of_interest)
        _append_values(lines, "Objetivos" if portuguese else "Goals", career.goals)
    technical = profile.technical_environment
    if technical is not None:
        _append_value(lines, "Sistema operacional" if portuguese else "Operating system", technical.operating_system)
        _append_values(lines, "Hardware", technical.hardware)
        _append_values(lines, "Ferramentas" if portuguese else "Tools", technical.tools)
    learning = profile.learning_preferences
    if learning is not None:
        _append_value(lines, "Estilo de explicação" if portuguese else "Explanation style", learning.explanation_style)
        _append_values(lines, "Preferências de estudo" if portuguese else "Study preferences", learning.study_preferences)
    if profile.projects:
        heading = "Projetos" if portuguese else "Projects"
        for project in profile.projects:
            details = tuple(
                value
                for value in (project.description, project.status)
                if value is not None
            )
            suffix = f" ({'; '.join(details)})" if details else ""
            lines.append(f"- {heading}: {project.name}{suffix}")
    _append_values(lines, "Hobbies", profile.hobbies)
    interaction = profile.interaction_preferences
    if interaction is not None:
        _append_value(lines, "Idioma preferido" if portuguese else "Preferred language", interaction.preferred_language)
        _append_value(lines, "Estilo de resposta" if portuguese else "Response style", interaction.response_style)
    return "\n".join(lines)


def _append_value(lines: list[str], label: str, value: str | None) -> None:
    if value is not None:
        lines.append(f"- {label}: {value}")


def _append_values(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    if values:
        lines.append(f"- {label}: {', '.join(values)}")


def _normalize(content: str) -> str:
    return " ".join(content.casefold().split()).strip(" .!?")


def _disabled_text(language: InteractionLanguage) -> str:
    return (
        "Personal Profile is disabled."
        if language is InteractionLanguage.EN_US
        else "O Personal Profile está desabilitado."
    )


def _empty_text(language: InteractionLanguage) -> str:
    return (
        "Your Personal Profile is empty."
        if language is InteractionLanguage.EN_US
        else "Seu Personal Profile está vazio."
    )


def _unavailable_text(language: InteractionLanguage) -> str:
    return (
        "Your Personal Profile is unavailable."
        if language is InteractionLanguage.EN_US
        else "Seu Personal Profile está indisponível."
    )
