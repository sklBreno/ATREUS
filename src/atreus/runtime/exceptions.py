"""Explicit failures raised by the local Runtime Host."""


class RuntimeHostError(Exception):
    """Base exception for Runtime Host lifecycle failures."""


class InvalidRuntimeLifecycleTransitionError(RuntimeHostError):
    """Raised when a requested Runtime Host transition is invalid."""


class RuntimeStartupError(RuntimeHostError):
    """Raised when the Runtime Host cannot complete startup."""


class RuntimeShutdownError(RuntimeHostError):
    """Raised when the Runtime Host cannot complete shutdown."""
