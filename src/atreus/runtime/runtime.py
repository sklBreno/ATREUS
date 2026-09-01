"""Production request boundary for the foreground ATREUS runtime."""

from uuid import uuid4

from atreus.core.core import Core
from atreus.core.models import CoreRequestResult
from atreus.interfaces.clock import Clock
from atreus.shared.request import Request


class InteractiveRuntime:
    """Create correlated text requests and submit them to Core orchestration."""

    def __init__(self, core: Core, clock: Clock) -> None:
        """Initialize the runtime with production orchestration dependencies.

        Args:
            core: Platform-independent request orchestrator.
            clock: Time source for request metadata.
        """
        self._core = core
        self._clock = clock

    def submit(self, content: str) -> CoreRequestResult:
        """Submit one text request through the production pipeline.

        Args:
            content: User-provided text accepted by the foreground runtime.

        Returns:
            The immutable result produced by Core orchestration.
        """
        return self._core.handle_request(
            Request(
                request_id=uuid4(),
                content=content,
                source="interactive_cli",
                received_at=self._clock.now(),
            )
        )
