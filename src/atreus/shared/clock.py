"""Standard UTC clock implementation."""

from datetime import UTC, datetime

from atreus.interfaces.clock import Clock


class UTCClock(Clock):
    """Read timezone-aware timestamps from the Python standard library."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC timestamp."""
        return datetime.now(UTC)
