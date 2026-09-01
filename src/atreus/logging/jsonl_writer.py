"""UTF-8 JSON Lines persistence for ATREUS observability records."""

import json
from datetime import UTC
from pathlib import Path

from atreus.interfaces.log_writer import LogWriter
from atreus.logging.models import StructuredLogRecord

_LOG_LEVEL_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class JsonLinesLogWriter(LogWriter):
    """Append sanitized structured records to one UTF-8 JSON Lines file."""

    def __init__(self, path: Path, minimum_level: str) -> None:
        """Initialize the writer with an explicit destination and level.

        Args:
            path: Local file receiving one JSON object per line.
            minimum_level: Lowest configured record level to persist.

        Raises:
            ValueError: If the configured level is unsupported.
        """
        if minimum_level not in _LOG_LEVEL_PRIORITY:
            raise ValueError(f"Unsupported log level: {minimum_level!r}.")
        self._path = path
        self._minimum_priority = _LOG_LEVEL_PRIORITY[minimum_level]

    def write(self, record: StructuredLogRecord) -> None:
        """Append one eligible record in compact JSON Lines format.

        Args:
            record: Sanitized structured observability record.

        Raises:
            ValueError: If the record level or timestamp is invalid.
            OSError: If the destination cannot be created or written.
        """
        priority = _LOG_LEVEL_PRIORITY.get(record.level)
        if priority is None:
            raise ValueError(f"Unsupported record level: {record.level!r}.")
        if priority < self._minimum_priority:
            return
        if record.timestamp.tzinfo is None or record.timestamp.utcoffset() is None:
            raise ValueError("Structured log timestamps must be timezone-aware.")

        payload = self._payload(record)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as log_file:
            log_file.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            log_file.write("\n")

    @staticmethod
    def _payload(record: StructuredLogRecord) -> dict[str, str]:
        payload = {
            "timestamp": (
                record.timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ),
            "level": record.level,
            "event_type": record.event_type,
            "message": record.message,
        }
        optional_values = {
            "correlation_id": record.correlation_id,
            "request_id": record.request_id,
            "capability_id": record.capability_id,
            "decision_outcome": record.decision_outcome,
            "execution_status": record.execution_status,
            "reason_code": record.reason_code,
            "lifecycle_state": record.lifecycle_state,
        }
        payload.update(
            {
                name: str(value)
                for name, value in optional_values.items()
                if value is not None
            }
        )
        return payload
