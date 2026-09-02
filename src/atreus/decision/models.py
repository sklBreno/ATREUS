"""Immutable contracts owned by the Decision Engine."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from atreus.ai.models import RequestInterpretation
from atreus.capability.models import CapabilityMetadata
from atreus.context.models import ContextSnapshot
from atreus.events.models import Event
from atreus.memory.models import MemorySnapshot
from atreus.request_classifier.models import ClassifiedRequest
from atreus.shared.platform import (
    OperationalState,
    PerformanceProfile,
    PlatformStateSnapshot,
)
from atreus.shared.request import Request
from atreus.system.models import SystemSnapshot


class DecisionOutcome(StrEnum):
    """Identify one supported Version 1 request decision outcome."""

    EXECUTE = "EXECUTE"
    ASK_FOR_CONFIRMATION = "ASK_FOR_CONFIRMATION"
    SUGGEST = "SUGGEST"
    IGNORE = "IGNORE"
    DELEGATE = "DELEGATE"
    REQUEST_PLANNING = "REQUEST_PLANNING"


@dataclass(frozen=True, slots=True)
class UserPolicy:
    """Represent the user-control policy relevant to request decisions."""

    permission_grants: tuple[str, ...]
    blocked_capability_ids: tuple[str, ...]
    allow_interruption: bool
    allow_delegation: bool
    delegation_service_id: str | None = None


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Provide injected deterministic decision thresholds."""

    minimum_confidence: float


@dataclass(frozen=True, slots=True)
class DecisionInput:
    """Collect one coherent immutable request decision snapshot."""

    request: Request
    classification: ClassifiedRequest
    context: ContextSnapshot
    memory: MemorySnapshot
    platform_state: PlatformStateSnapshot
    user_policy: UserPolicy
    candidate_capabilities: tuple[CapabilityMetadata, ...]
    interpretation: RequestInterpretation | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    """Represent the next request orchestration step selected by policy."""

    request_id: UUID
    outcome: DecisionOutcome
    target: str | None
    reason_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionMade(Event):
    """Report a successful request decision without request content."""

    request_id: UUID
    outcome: DecisionOutcome
    target: str | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class PlatformBehaviorPolicy:
    """Restrict allowed operational states and performance profiles."""

    allowed_operational_states: tuple[OperationalState, ...]
    allowed_performance_profiles: tuple[PerformanceProfile, ...]


@dataclass(frozen=True, slots=True)
class PlatformBehaviorDecisionInput:
    """Collect immutable inputs for platform behavior evaluation."""

    evaluation_id: UUID
    platform_state: PlatformStateSnapshot
    context: ContextSnapshot
    system_signals: tuple[SystemSnapshot, ...]
    configuration_policy: PlatformBehaviorPolicy
    user_policy: UserPolicy
    trigger: str


@dataclass(frozen=True, slots=True)
class PlatformBehaviorDecision:
    """Represent desired state and profile values without applying them."""

    evaluation_id: UUID
    desired_operational_state: OperationalState
    operational_state_reason_code: str
    desired_performance_profile: PerformanceProfile
    performance_profile_reason_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PlatformBehaviorDecisionMade(Event):
    """Report desired platform behavior without claiming applied changes."""

    evaluation_id: UUID
    desired_operational_state: OperationalState
    operational_state_reason_code: str
    desired_performance_profile: PerformanceProfile
    performance_profile_reason_code: str
