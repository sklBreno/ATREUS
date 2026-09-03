"""Narrow deterministic interaction-language resolution."""

import re

from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.interaction_language import InteractionLanguageResolver

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
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
        "are",
        "explain",
        "could",
        "cmd",
        "do",
        "is",
        "notepad",
        "open",
        "powershell",
        "please",
        "prompt",
        "reveal",
        "run",
        "running",
        "show",
        "some",
        "system",
        "what",
        "who",
        "want",
        "write",
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
        words = tuple(_WORD_PATTERN.findall(content.casefold()))
        portuguese_count = sum(word in _PT_BR_MARKERS for word in words)
        english_count = sum(word in _EN_US_MARKERS for word in words)
        if portuguese_count == 0 and english_count >= 2:
            return InteractionLanguage.EN_US
        return InteractionLanguage.PT_BR
