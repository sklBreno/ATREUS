"""Tests for deterministic bilingual interaction-language resolution."""

import pytest

from atreus.interaction.language import DeterministicInteractionLanguageResolver
from atreus.interaction.models import InteractionLanguage


@pytest.mark.parametrize(
    "content",
    (
        "abre a calculadora pra mim",
        "quero fazer umas contas",
        "pode abrir o bloco de notas para eu escrever",
    ),
)
def test_clear_portuguese_requests_resolve_to_pt_br(content: str) -> None:
    assert DeterministicInteractionLanguageResolver().resolve(content) is (
        InteractionLanguage.PT_BR
    )


@pytest.mark.parametrize(
    "content",
    (
        "could you open the calculator?",
        "I want to do some calculations",
        "please open notepad",
        "who are you?",
        "what can you do?",
        "explain what an operating system is",
        "show your system prompt",
        "clear conversation",
        "tell me more",
        "explain it more simply",
        "explain that better",
        "go on",
        "why?",
    ),
)
def test_clear_english_requests_resolve_to_en_us(content: str) -> None:
    assert DeterministicInteractionLanguageResolver().resolve(content) is (
        InteractionLanguage.EN_US
    )


@pytest.mark.parametrize("content", ("", "calculator", "yes", "mixed request"))
def test_ambiguous_language_defaults_to_pt_br(content: str) -> None:
    assert DeterministicInteractionLanguageResolver().resolve(content) is (
        InteractionLanguage.PT_BR
    )
