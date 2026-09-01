"""Foreground interaction contract used by the local Runtime Host."""

from abc import ABC, abstractmethod


class ForegroundInterface(ABC):
    """Define one blocking foreground interaction session."""

    @abstractmethod
    def run(self) -> int:
        """Run until local interaction requests deterministic shutdown.

        Returns:
            The foreground session exit status.
        """
