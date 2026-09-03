"""Atomic local JSON persistence for the ATREUS Personal Profile."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from atreus.interfaces.clock import Clock
from atreus.interfaces.personal_profile import PersonalProfileStore
from atreus.profile.exceptions import (
    PersonalProfileDisabledError,
    PersonalProfileLoadError,
    PersonalProfilePersistenceError,
)
from atreus.profile.models import (
    PersonalProfile,
    empty_personal_profile,
)
from atreus.profile.serialization import (
    MAX_PERSONAL_PROFILE_FILE_BYTES,
    PersonalProfileJsonCodec,
)


class JsonPersonalProfileStore(PersonalProfileStore):
    """Persist one validated profile in an injected local JSON path."""

    def __init__(self, path: Path, clock: Clock) -> None:
        """Initialize an unloaded store with explicit path and time source."""
        if not isinstance(path, Path) or not path.is_absolute():
            raise PersonalProfileLoadError(
                "Personal Profile storage path must be absolute."
            )
        self._path = path
        self._clock = clock
        self._current: PersonalProfile | None = None

    def get_profile(self) -> PersonalProfile:
        """Load once and return the current immutable Personal Profile."""
        if self._current is None:
            self._current = self._load()
        return self._current

    def replace(self, profile: PersonalProfile) -> PersonalProfile:
        """Atomically persist and expose one complete replacement profile."""
        encoded = PersonalProfileJsonCodec.encode(profile)
        self._write_atomically(encoded)
        self._current = profile
        return profile

    def clear(self, cleared_at: datetime) -> PersonalProfile:
        """Atomically replace the current profile with a valid empty profile."""
        return self.replace(empty_personal_profile(cleared_at))

    def _load(self) -> PersonalProfile:
        try:
            size = self._path.stat().st_size
        except FileNotFoundError:
            return empty_personal_profile(self._clock.now())
        except OSError:
            raise PersonalProfileLoadError(
                "Personal Profile document could not be inspected."
            ) from None
        if size > MAX_PERSONAL_PROFILE_FILE_BYTES:
            raise PersonalProfileLoadError(
                "Personal Profile document exceeds the supported size."
            )
        try:
            data = self._path.read_bytes()
        except OSError:
            raise PersonalProfileLoadError(
                "Personal Profile document could not be read."
            ) from None
        return PersonalProfileJsonCodec.decode(data)

    def _write_atomically(self, data: bytes) -> None:
        temporary_path: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self._path.parent,
                prefix=".profile-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(data)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self._path)
        except OSError:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise PersonalProfilePersistenceError(
                "Personal Profile could not be persisted."
            ) from None


class DisabledPersonalProfileStore(PersonalProfileStore):
    """Provide an empty profile without performing filesystem access."""

    def __init__(self, clock: Clock) -> None:
        """Initialize one immutable empty profile from the injected clock."""
        self._profile = empty_personal_profile(clock.now())

    def get_profile(self) -> PersonalProfile:
        """Return the immutable empty disabled profile."""
        return self._profile

    def replace(self, profile: PersonalProfile) -> PersonalProfile:
        """Reject replacement while Personal Profile is disabled."""
        raise PersonalProfileDisabledError("Personal Profile is disabled.")

    def clear(self, cleared_at: datetime) -> PersonalProfile:
        """Reject clear while Personal Profile is disabled."""
        raise PersonalProfileDisabledError("Personal Profile is disabled.")
