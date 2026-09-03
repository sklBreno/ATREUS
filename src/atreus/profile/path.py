"""Platform-aware local storage path resolution for Personal Profile."""

import os
from collections.abc import Mapping
from pathlib import Path

from atreus.profile.exceptions import PersonalProfileLoadError


def resolve_personal_profile_path(
    environment: Mapping[str, str] | None = None,
    operating_system: str | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the safe per-user Personal Profile path outside the repository.

    Args:
        environment: Environment used only for standard user-data directories.
        operating_system: Optional injected ``os.name`` value for tests.
        home: Optional injected user home directory for tests.

    Returns:
        An absolute per-user path for ``profile.json``.
    """
    selected_environment = os.environ if environment is None else environment
    selected_system = os.name if operating_system is None else operating_system
    selected_home = Path.home() if home is None else home
    if selected_system == "nt":
        configured_base = selected_environment.get("LOCALAPPDATA")
        base = (
            Path(configured_base)
            if configured_base
            else selected_home / "AppData" / "Local"
        )
    else:
        configured_base = selected_environment.get("XDG_DATA_HOME")
        base = (
            Path(configured_base)
            if configured_base
            else selected_home / ".local" / "share"
        )
    if not base.is_absolute():
        raise PersonalProfileLoadError(
            "Personal Profile user-data directory must be absolute."
        )
    return base / "ATREUS" / "profile.json"
