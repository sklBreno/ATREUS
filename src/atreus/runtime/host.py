"""Synchronous lifecycle coordinator for the local ATREUS runtime."""

from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.foreground_interface import ForegroundInterface
from atreus.runtime.exceptions import (
    InvalidRuntimeLifecycleTransitionError,
    RuntimeHostError,
    RuntimeShutdownError,
    RuntimeStartupError,
)
from atreus.runtime.models import (
    RuntimeFailed,
    RuntimeLifecycleState,
    RuntimeStarted,
    RuntimeStarting,
    RuntimeStopped,
    RuntimeStopping,
)

_ALLOWED_TRANSITIONS: dict[
    RuntimeLifecycleState,
    frozenset[RuntimeLifecycleState],
] = {
    RuntimeLifecycleState.CREATED: frozenset(
        {
            RuntimeLifecycleState.STARTING,
            RuntimeLifecycleState.STOPPING,
        }
    ),
    RuntimeLifecycleState.STARTING: frozenset(
        {
            RuntimeLifecycleState.RUNNING,
            RuntimeLifecycleState.FAILED,
        }
    ),
    RuntimeLifecycleState.RUNNING: frozenset(
        {
            RuntimeLifecycleState.STOPPING,
            RuntimeLifecycleState.FAILED,
        }
    ),
    RuntimeLifecycleState.STOPPING: frozenset(
        {
            RuntimeLifecycleState.STOPPED,
            RuntimeLifecycleState.FAILED,
        }
    ),
    RuntimeLifecycleState.STOPPED: frozenset(
        {RuntimeLifecycleState.FAILED}
    ),
    RuntimeLifecycleState.FAILED: frozenset(),
}


class RuntimeHost:
    """Own the foreground process lifecycle without owning request work."""

    def __init__(
        self,
        foreground_interface: ForegroundInterface,
        event_bus: EventBus,
    ) -> None:
        """Initialize a created host with explicit boundaries.

        Args:
            foreground_interface: Blocking local interaction boundary.
            event_bus: Synchronous lifecycle event publication boundary.
        """
        self._foreground_interface = foreground_interface
        self._event_bus = event_bus
        self._state = RuntimeLifecycleState.CREATED

    @property
    def state(self) -> RuntimeLifecycleState:
        """Return the current immutable lifecycle value."""
        return self._state

    def start(self) -> None:
        """Transition a newly created host into the running state.

        Raises:
            InvalidRuntimeLifecycleTransitionError: If startup was requested
                outside the created state.
            RuntimeStartupError: If startup cannot complete.
        """
        if self._state is not RuntimeLifecycleState.CREATED:
            raise InvalidRuntimeLifecycleTransitionError(
                f"Cannot start Runtime Host from {self._state.value}."
            )
        try:
            self._transition(RuntimeLifecycleState.STARTING)
            self._event_bus.publish(
                RuntimeStarting(
                    source="runtime_host",
                    lifecycle_state=self._state,
                )
            )
            self._transition(RuntimeLifecycleState.RUNNING)
            self._event_bus.publish(
                RuntimeStarted(
                    source="runtime_host",
                    lifecycle_state=self._state,
                )
            )
        except Exception as error:
            self._fail("startup", type(error).__name__)
            raise RuntimeStartupError("Runtime Host startup failed.") from None

    def stop(self) -> None:
        """Stop the host deterministically when shutdown is applicable.

        Repeated calls after stopping or failure are idempotent. A created host
        may be stopped before it begins accepting requests.

        Raises:
            InvalidRuntimeLifecycleTransitionError: If shutdown is requested
                while startup is incomplete.
            RuntimeShutdownError: If shutdown cannot complete.
        """
        if self._state in {
            RuntimeLifecycleState.STOPPING,
            RuntimeLifecycleState.STOPPED,
            RuntimeLifecycleState.FAILED,
        }:
            return
        if self._state not in {
            RuntimeLifecycleState.CREATED,
            RuntimeLifecycleState.RUNNING,
        }:
            raise InvalidRuntimeLifecycleTransitionError(
                f"Cannot stop Runtime Host from {self._state.value}."
            )
        try:
            self._transition(RuntimeLifecycleState.STOPPING)
            self._event_bus.publish(
                RuntimeStopping(
                    source="runtime_host",
                    lifecycle_state=self._state,
                )
            )
            self._transition(RuntimeLifecycleState.STOPPED)
            self._event_bus.publish(
                RuntimeStopped(
                    source="runtime_host",
                    lifecycle_state=self._state,
                )
            )
        except Exception as error:
            self._fail("shutdown", type(error).__name__)
            raise RuntimeShutdownError("Runtime Host shutdown failed.") from None

    def run(self) -> int:
        """Start, run the foreground interface, and guarantee shutdown.

        Returns:
            Zero for clean shutdown or one for a fatal lifecycle failure.
        """
        try:
            self.start()
        except RuntimeHostError:
            return 1

        try:
            exit_code = self._foreground_interface.run()
        except (EOFError, KeyboardInterrupt):
            exit_code = 0
        except Exception as error:
            self._fail("foreground_interface", type(error).__name__)
            return 1

        if exit_code != 0:
            self._fail("foreground_interface", "NonZeroExitStatus")
            return 1

        try:
            self.stop()
        except RuntimeHostError:
            return 1
        return 0

    def _transition(self, target: RuntimeLifecycleState) -> None:
        if target not in _ALLOWED_TRANSITIONS[self._state]:
            raise InvalidRuntimeLifecycleTransitionError(
                f"Invalid Runtime Host transition: "
                f"{self._state.value} -> {target.value}."
            )
        self._state = target

    def _fail(self, stage: str, error_type: str) -> None:
        if self._state is RuntimeLifecycleState.FAILED:
            return
        self._transition(RuntimeLifecycleState.FAILED)
        try:
            self._event_bus.publish(
                RuntimeFailed(
                    source="runtime_host",
                    lifecycle_state=self._state,
                    failure_stage=stage,
                    error_type=error_type,
                )
            )
        except Exception:
            # A broken lifecycle event boundary has no safe secondary sink.
            return
