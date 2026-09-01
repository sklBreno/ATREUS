"""Planner contract exposed to Core orchestration."""

from abc import ABC, abstractmethod

from atreus.planner.models import Plan, PlanningRequest


class Planner(ABC):
    """Define deterministic creation of immutable capability plans."""

    @abstractmethod
    def create_plan(self, request: PlanningRequest) -> Plan:
        """Create a validated finite plan for one high-level goal.

        Args:
            request: Immutable goal, context, and planning constraints.

        Returns:
            A validated immutable sequential plan.
        """
