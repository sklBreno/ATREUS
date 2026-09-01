"""Exceptions raised by the Planner."""


class PlanningException(Exception):
    """Base exception for plan creation failures."""


class InvalidPlanningRequestError(PlanningException):
    """Raised when planning inputs or constraints are invalid."""


class GoalNotPlannableError(PlanningException):
    """Raised when available metadata cannot represent the goal safely."""


class InvalidCapabilityReferenceError(PlanningException):
    """Raised when a plan references a missing or unavailable capability."""


class InvalidPlanStructureError(PlanningException):
    """Raised when generated steps violate structural plan rules."""


class UnsupportedPlanSemanticsError(PlanningException):
    """Raised when a goal requires unsupported Version 1 semantics."""
