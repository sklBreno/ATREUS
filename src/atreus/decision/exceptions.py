"""Exceptions raised by the Decision Engine."""


class DecisionEngineException(Exception):
    """Base exception for request and platform decision failures."""


class InconsistentDecisionInputError(DecisionEngineException):
    """Raised when decision inputs do not describe one coherent operation."""


class UnsupportedDecisionOutcomeError(DecisionEngineException):
    """Raised when a strategy produces an unsupported decision outcome."""


class DecisionPolicyEvaluationError(DecisionEngineException):
    """Raised when a valid input cannot be evaluated safely."""
