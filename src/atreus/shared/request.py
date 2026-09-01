"""Immutable request contract shared by ATREUS input and orchestration modules."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Request:
    """Represent one normalized user request."""

    request_id: UUID
    content: str
    source: str
    received_at: datetime
