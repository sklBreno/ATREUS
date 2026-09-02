"""Core request orchestration for Runtime Phase B."""

from uuid import UUID, uuid4

from atreus.ai.exceptions import AIProviderException, RequestInterpretationException
from atreus.ai.models import REQUEST_INTERPRETER_SERVICE_ID, RequestInterpretation
from atreus.confirmation.models import (
    ConfirmationAction,
    ConfirmationPrompt,
    ConfirmationResolutionStatus,
)
from atreus.context.models import ContextSnapshot
from atreus.core.exceptions import (
    InconsistentClassificationError,
    InconsistentDecisionError,
    InconsistentPlanError,
)
from atreus.core.models import (
    CoreRequestResult,
    ErrorOccurred,
    RequestCompleted,
    RequestReceived,
)
from atreus.decision.models import Decision, DecisionInput, DecisionOutcome, UserPolicy
from atreus.execution.models import (
    CapabilityExecutionResult,
    CapabilityExecutionStatus,
    CapabilityInvocation,
)
from atreus.interfaces.capability_registry import CapabilityCatalog
from atreus.interfaces.capability_runtime import CapabilityRuntime
from atreus.interfaces.confirmation import ConfirmationCoordinator
from atreus.interfaces.context import ContextProvider
from atreus.interfaces.decision_engine import DecisionEngine
from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.interaction_language import InteractionLanguageResolver
from atreus.interfaces.memory import MemorySnapshotProvider
from atreus.interfaces.planner import Planner
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.interfaces.request_interpreter import RequestInterpreter
from atreus.planner.models import Plan, PlanningConstraints, PlanningRequest
from atreus.shared.platform import PlatformStateSnapshot
from atreus.shared.request import Request
from atreus.system.models import ApplicationIdentifier


class Core:
    """Coordinate explicit request flow without absorbing domain work."""

    def __init__(
        self,
        event_bus: EventBus,
        request_classifier: RequestClassifier,
        capability_catalog: CapabilityCatalog,
        decision_engine: DecisionEngine,
        planner: Planner,
        capability_runtime: CapabilityRuntime,
        context_provider: ContextProvider,
        memory_snapshot_provider: MemorySnapshotProvider,
        platform_state: PlatformStateSnapshot,
        user_policy: UserPolicy,
        planning_constraints: PlanningConstraints,
        execution_timeout_seconds: float | None,
        confirmation_coordinator: ConfirmationCoordinator,
        interaction_language_resolver: InteractionLanguageResolver,
        request_interpreter: RequestInterpreter | None = None,
    ) -> None:
        """Initialize Core with explicit runtime contracts.

        Args:
            event_bus: Synchronous domain event publication boundary.
            request_classifier: Request classification boundary.
            capability_catalog: Read-only capability discovery boundary.
            decision_engine: Request decision boundary.
            planner: Immutable plan creation boundary.
            capability_runtime: Controlled capability invocation boundary.
            context_provider: Current immutable context source.
            memory_snapshot_provider: Bounded process-local memory view source.
            platform_state: Current immutable Core-owned state snapshot.
            user_policy: Grants and user-control policy for orchestration.
            planning_constraints: Bounded policy for generated plans.
            execution_timeout_seconds: Optional injected invocation deadline.
            confirmation_coordinator: Single-use interactive authorization state.
            interaction_language_resolver: Deterministic prompt language boundary.
            request_interpreter: Optional bounded AI interpretation boundary.
        """
        self._event_bus = event_bus
        self._request_classifier = request_classifier
        self._capability_catalog = capability_catalog
        self._decision_engine = decision_engine
        self._planner = planner
        self._capability_runtime = capability_runtime
        self._context_provider = context_provider
        self._memory_snapshot_provider = memory_snapshot_provider
        self._platform_state = platform_state
        self._user_policy = user_policy
        self._planning_constraints = planning_constraints
        self._execution_timeout_seconds = execution_timeout_seconds
        self._confirmation_coordinator = confirmation_coordinator
        self._interaction_language_resolver = interaction_language_resolver
        self._request_interpreter = request_interpreter

    def handle_request(self, request: Request) -> CoreRequestResult:
        """Coordinate one request through decision, planning, and execution.

        Args:
            request: Immutable normalized request accepted for orchestration.

        Returns:
            A controlled result containing every completed pipeline contract.

        Raises:
            InconsistentClassificationError: If classification changes identity.
            InconsistentDecisionError: If decision correlation is invalid.
            InconsistentPlanError: If plan correlation is invalid.
        """
        self._event_bus.publish(
            RequestReceived(
                source="core",
                correlation_id=request.request_id,
                request_id=request.request_id,
            )
        )
        orchestration_step = "request_classification"
        try:
            classification = self._request_classifier.classify(request)
            if classification.request_id != request.request_id:
                raise InconsistentClassificationError(
                    "Classification request identity does not match Core input."
                )

            orchestration_step = "context_snapshot"
            context = self._context_provider.current_context()
            orchestration_step = "working_memory_snapshot"
            memory = self._memory_snapshot_provider.snapshot()
            orchestration_step = "confirmation_resolution"
            confirmation = self._confirmation_coordinator.resolve(
                request.request_id,
                request.content,
            )
            candidate_capabilities = self._capability_catalog.list_available()
            orchestration_step = "request_decision"
            decision = self._decision_engine.decide(
                DecisionInput(
                    request=request,
                    classification=classification,
                    context=context,
                    memory=memory,
                    platform_state=self._platform_state,
                    user_policy=self._user_policy,
                    candidate_capabilities=candidate_capabilities,
                    confirmation=(
                        confirmation
                        if confirmation.status
                        is not ConfirmationResolutionStatus.NOT_APPLICABLE
                        else None
                    ),
                )
            )
            if decision.request_id != request.request_id:
                raise InconsistentDecisionError(
                    "Decision request identity does not match Core input."
                )

            interpretation: RequestInterpretation | None = None
            if (
                confirmation.status
                is ConfirmationResolutionStatus.NOT_APPLICABLE
                and decision.outcome is DecisionOutcome.DELEGATE
                and decision.target == REQUEST_INTERPRETER_SERVICE_ID
                and self._request_interpreter is not None
            ):
                orchestration_step = "request_interpretation"
                try:
                    interpretation = self._request_interpreter.interpret(request)
                except (
                    AIProviderException,
                    RequestInterpretationException,
                ) as error:
                    self._publish_error(
                        request.request_id,
                        orchestration_step,
                        type(error).__name__,
                    )
                else:
                    orchestration_step = "interpreted_request_decision"
                    decision = self._decision_engine.decide(
                        DecisionInput(
                            request=request,
                            classification=classification,
                            context=context,
                            memory=memory,
                            platform_state=self._platform_state,
                            user_policy=self._user_policy,
                            candidate_capabilities=candidate_capabilities,
                            interpretation=interpretation,
                        )
                    )
                    if decision.request_id != request.request_id:
                        raise InconsistentDecisionError(
                            "Decision request identity does not match Core input."
                        )

            if (
                confirmation.status is ConfirmationResolutionStatus.ACCEPTED
                and decision.outcome is DecisionOutcome.EXECUTE
            ):
                raise InconsistentDecisionError(
                    "Accepted confirmation cannot authorize direct execution."
                )

            confirmation_prompt: ConfirmationPrompt | None = None
            if (
                interpretation is not None
                and decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
            ):
                orchestration_step = "confirmation_creation"
                confirmation_prompt = self._begin_confirmation(
                    request,
                    decision,
                    interpretation,
                )

            plan: Plan | None = None
            execution_results: tuple[CapabilityExecutionResult, ...] = ()
            if decision.outcome is DecisionOutcome.EXECUTE:
                orchestration_step = "direct_execution"
                execution_results = (
                    self._execute_direct(request, decision, context),
                )
            elif decision.outcome is DecisionOutcome.REQUEST_PLANNING:
                orchestration_step = "planning"
                planning_id = uuid4()
                confirmation_action = (
                    confirmation.pending.action
                    if confirmation.status is ConfirmationResolutionStatus.ACCEPTED
                    and confirmation.pending is not None
                    else None
                )
                plan = self._planner.create_plan(
                    PlanningRequest(
                        planning_id=planning_id,
                        request_id=request.request_id,
                        goal=(
                            confirmation_action.intent_id.value
                            if confirmation_action is not None
                            else request.content
                        ),
                        constraints=self._planning_constraints,
                        context=context,
                        memory=memory,
                        confirmation_action=confirmation_action,
                    )
                )
                if (
                    plan.plan_id != planning_id
                    or plan.request_id != request.request_id
                ):
                    raise InconsistentPlanError(
                        "Plan identity does not match the planning request."
                    )
                if not plan.requires_confirmation and not any(
                    step.requires_confirmation for step in plan.steps
                ):
                    orchestration_step = "plan_execution"
                    execution_results = self._execute_plan(plan, context)
        except Exception as error:
            self._publish_error(
                request.request_id,
                orchestration_step,
                type(error).__name__,
            )
            raise

        result = CoreRequestResult(
            request_id=request.request_id,
            classification=classification,
            decision=decision,
            plan=plan,
            execution_results=execution_results,
            confirmation_prompt=confirmation_prompt,
        )
        self._publish_completed(result)
        return result

    def _begin_confirmation(
        self,
        request: Request,
        decision: Decision,
        interpretation: RequestInterpretation,
    ) -> ConfirmationPrompt:
        if decision.target != interpretation.capability_id:
            raise InconsistentDecisionError(
                "Confirmation decision target does not match interpretation."
            )
        try:
            target_id = ApplicationIdentifier(interpretation.target_id)
        except ValueError as error:
            raise InconsistentDecisionError(
                "Confirmation interpretation target is not approved."
            ) from error
        action = ConfirmationAction(
            intent_id=interpretation.intent_id,
            capability_id=interpretation.capability_id,
            target_id=target_id,
        )
        pending = self._confirmation_coordinator.begin(
            request.request_id,
            action,
            self._interaction_language_resolver.resolve(request.content),
        )
        return ConfirmationPrompt(
            confirmation_id=pending.confirmation_id,
            intent_id=pending.action.intent_id,
            target_id=pending.action.target_id,
            expires_at=pending.expires_at,
            language=pending.language,
        )

    def _execute_direct(
        self,
        request: Request,
        decision: Decision,
        context: ContextSnapshot,
    ) -> CapabilityExecutionResult:
        if decision.target is None:
            raise InconsistentDecisionError(
                "Execute decisions require a capability target."
            )
        return self._capability_runtime.invoke(
            CapabilityInvocation(
                invocation_id=uuid4(),
                request_id=request.request_id,
                plan_id=None,
                step_id=None,
                capability_id=decision.target,
                arguments=(),
                context=context,
                timeout_seconds=self._execution_timeout_seconds,
                permission_grants=self._user_policy.permission_grants,
            )
        )

    def _execute_plan(
        self,
        plan: Plan,
        context: ContextSnapshot,
    ) -> tuple[CapabilityExecutionResult, ...]:
        results: list[CapabilityExecutionResult] = []
        successful_steps: set[str] = set()
        for step in plan.steps:
            if not set(step.depends_on).issubset(successful_steps):
                raise InconsistentPlanError(
                    f"Plan step '{step.step_id}' has unmet dependencies."
                )
            result = self._capability_runtime.invoke(
                CapabilityInvocation(
                    invocation_id=uuid4(),
                    request_id=plan.request_id,
                    plan_id=plan.plan_id,
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    arguments=step.arguments,
                    context=context,
                    timeout_seconds=self._execution_timeout_seconds,
                    permission_grants=self._user_policy.permission_grants,
                )
            )
            results.append(result)
            if result.status is not CapabilityExecutionStatus.SUCCEEDED:
                break
            successful_steps.add(step.step_id)
        return tuple(results)

    def _publish_completed(self, result: CoreRequestResult) -> None:
        self._event_bus.publish(
            RequestCompleted(
                source="core",
                correlation_id=result.request_id,
                request_id=result.request_id,
                decision_outcome=result.decision.outcome,
                execution_statuses=tuple(
                    execution.status for execution in result.execution_results
                ),
            )
        )

    def _publish_error(
        self,
        request_id: UUID,
        orchestration_step: str,
        error_type: str,
    ) -> None:
        self._event_bus.publish(
            ErrorOccurred(
                source="core",
                correlation_id=request_id,
                request_id=request_id,
                orchestration_step=orchestration_step,
                error_type=error_type,
            )
        )
