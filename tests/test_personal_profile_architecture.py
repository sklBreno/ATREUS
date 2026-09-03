"""Architecture guards for Personal Profile operational isolation."""

import inspect
from uuid import uuid4

from atreus.ai.models import AIRequest
from atreus.confirmation.models import PendingConfirmation
from atreus.decision.models import DecisionInput
from atreus.execution.models import CapabilityInvocation, ExecutionContext
from atreus.planner.models import PlanningRequest
from atreus.profile.models import PersonalProfile
from atreus.request_classifier.classifier import DeterministicRequestClassifier
from atreus.request_classifier.models import RequestType
from atreus.shared.request import Request
from tests.support import NOW


def test_operational_contracts_receive_no_personal_profile() -> None:
    for contract in (
        DecisionInput,
        PlanningRequest,
        CapabilityInvocation,
        ExecutionContext,
        PendingConfirmation,
        AIRequest,
    ):
        assert "profile" not in inspect.signature(contract).parameters


def test_operational_modules_import_no_personal_profile() -> None:
    modules = (
        "atreus.core.core",
        "atreus.ai.request_interpreter",
        "atreus.decision.decision_engine",
        "atreus.planner.planner",
        "atreus.execution.runtime",
        "atreus.confirmation.coordinator",
        "atreus.system.windows_application_launcher",
    )

    for module_name in modules:
        module = __import__(module_name, fromlist=["__name__"])
        source = inspect.getsource(module)
        assert "atreus.profile" not in source
        assert "PersonalProfile" not in source


def test_profile_models_import_no_memory_context_ai_or_system_modules() -> None:
    source = inspect.getsource(__import__(PersonalProfile.__module__, fromlist=["x"]))

    for forbidden in (
        "atreus.ai",
        "atreus.context",
        "atreus.memory",
        "atreus.system",
    ):
        assert forbidden not in source


def test_profile_module_defines_no_events_or_logging_dependencies() -> None:
    modules = (
        "atreus.profile.confirmation",
        "atreus.profile.interaction",
        "atreus.profile.json_store",
        "atreus.profile.models",
        "atreus.profile.projection",
        "atreus.profile.serialization",
    )

    for module_name in modules:
        source = inspect.getsource(__import__(module_name, fromlist=["x"]))
        assert "EventBus" not in source
        assert "LogWriter" not in source
        assert "StructuredLogRecord" not in source


def test_profile_cannot_resolve_ambiguous_operational_target() -> None:
    request = Request(uuid4(), "open it", "text", NOW)

    classification = DeterministicRequestClassifier().classify(request)

    assert classification.request_type is RequestType.COMMAND
    assert not hasattr(classification, "profile")
