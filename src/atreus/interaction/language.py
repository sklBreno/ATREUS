"""Narrow deterministic interaction-language resolution."""

import re

from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.interaction_language import InteractionLanguageResolver

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_EN_US_EXACT_PHRASES = frozenset(
    {
        "explain that better",
        "go on",
        "why",
    }
)
_PT_BR_MARKERS = frozenset(
    {
        "abre",
        "aberta",
        "aberto",
        "abrir",
        "bloco",
        "calculadora",
        "cálculos",
        "contas",
        "escrever",
        "está",
        "fazer",
        "explique",
        "qual",
        "quem",
        "você",
        "voce",
        "mim",
        "notas",
        "para",
        "pode",
        "pra",
        "quero",
        "rodando",
        "umas",
    }
)
_EN_US_MARKERS = frozenset(
    {
        "calculations",
        "calculator",
        "clear",
        "conversation",
        "are",
        "explain",
        "go",
        "it",
        "could",
        "cmd",
        "do",
        "is",
        "notepad",
        "open",
        "more",
        "my",
        "powershell",
        "please",
        "prompt",
        "profile",
        "reveal",
        "run",
        "running",
        "show",
        "simply",
        "some",
        "system",
        "tell",
        "what",
        "why",
        "who",
        "want",
        "write",
        "clearing",
        "your",
        "you",
    }
)


class DeterministicInteractionLanguageResolver(InteractionLanguageResolver):
    """Recognize clear English interaction and default every ambiguity to pt-BR."""

    def resolve(self, content: str) -> InteractionLanguage:
        """Resolve language through bounded lexical evidence.

        Args:
            content: Original request content used only for language selection.

        Returns:
            English for clear English-only evidence, otherwise Brazilian
            Portuguese.
        """
        normalized = " ".join(content.casefold().split()).strip(" .!?")
        if normalized in _EN_US_EXACT_PHRASES:
            return InteractionLanguage.EN_US

        words = tuple(_WORD_PATTERN.findall(content.casefold()))
        portuguese_count = sum(word in _PT_BR_MARKERS for word in words)
        english_count = sum(word in _EN_US_MARKERS for word in words)
        if portuguese_count == 0 and english_count >= 2:
            return InteractionLanguage.EN_US
        return InteractionLanguage.PT_BR
