"""Tests for strict atomic Personal Profile JSON persistence."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from atreus.profile.exceptions import (
    PersonalProfileDisabledError,
    PersonalProfileLoadError,
    PersonalProfilePersistenceError,
    UnsupportedPersonalProfileVersionError,
)
from atreus.profile.json_store import (
    DisabledPersonalProfileStore,
    JsonPersonalProfileStore,
)
from atreus.profile.models import personal_profile_is_empty
from atreus.profile.path import resolve_personal_profile_path
from atreus.profile.serialization import (
    MAX_PERSONAL_PROFILE_FILE_BYTES,
    PersonalProfileJsonCodec,
)
from tests.support import NOW, FixedClock
from tests.test_personal_profile_models import sample_profile


def test_missing_file_returns_one_cached_empty_profile(tmp_path: Path) -> None:
    store = JsonPersonalProfileStore(tmp_path / "profile.json", FixedClock())

    first = store.get_profile()
    second = store.get_profile()

    assert first is second
    assert personal_profile_is_empty(first)
    assert not (tmp_path / "profile.json").exists()


def test_valid_profile_round_trips_as_deterministic_utf8_json(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    profile = replace(
        sample_profile(),
        hobbies=("Programação",),
    )
    store = JsonPersonalProfileStore(path, FixedClock())

    assert store.replace(profile) is profile
    loaded = JsonPersonalProfileStore(path, FixedClock()).get_profile()

    assert loaded == profile
    assert path.read_bytes() == PersonalProfileJsonCodec.encode(profile)
    assert "Programação" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "document",
    (
        b"not-json",
        b'{"schema_version":1,"updated_at":"2026-09-03T12:00:00Z",'
        b'"unknown":"value"}',
        b'{"schema_version":1,"updated_at":"2026-09-03T12:00:00Z",'
        b'"identity":{"unknown":"value"}}',
    ),
)
def test_store_rejects_malformed_or_unknown_structures(
    tmp_path: Path,
    document: bytes,
) -> None:
    path = tmp_path / "profile.json"
    path.write_bytes(document)

    with pytest.raises(PersonalProfileLoadError) as raised:
        JsonPersonalProfileStore(path, FixedClock()).get_profile()

    assert "value" not in str(raised.value)
    assert str(path) not in str(raised.value)


def test_store_rejects_unsupported_schema_without_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    document = b'{"schema_version":2,"updated_at":"2026-09-03T12:00:00Z"}'
    path.write_bytes(document)

    with pytest.raises(UnsupportedPersonalProfileVersionError):
        JsonPersonalProfileStore(path, FixedClock()).get_profile()

    assert path.read_bytes() == document


def test_store_rejects_oversized_document_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_bytes(b"x" * (MAX_PERSONAL_PROFILE_FILE_BYTES + 1))

    with pytest.raises(PersonalProfileLoadError, match="size"):
        JsonPersonalProfileStore(path, FixedClock()).get_profile()


def test_read_permission_failure_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    path.write_bytes(PersonalProfileJsonCodec.encode(sample_profile()))

    def fail_read(self: Path) -> bytes:
        raise PermissionError("private path detail")

    monkeypatch.setattr(Path, "read_bytes", fail_read)

    with pytest.raises(PersonalProfileLoadError) as raised:
        JsonPersonalProfileStore(path, FixedClock()).get_profile()

    assert "private path detail" not in str(raised.value)
    assert str(path) not in str(raised.value)


def test_atomic_replace_failure_preserves_file_cache_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    original = sample_profile()
    store = JsonPersonalProfileStore(path, FixedClock())
    store.replace(original)
    previous_bytes = path.read_bytes()
    replacement = replace(original, hobbies=("New hobby",))

    def fail_replace(source: Path, destination: Path) -> None:
        raise PermissionError("private destination detail")

    monkeypatch.setattr("atreus.profile.json_store.os.replace", fail_replace)

    with pytest.raises(PersonalProfilePersistenceError) as raised:
        store.replace(replacement)

    assert "private destination detail" not in str(raised.value)
    assert path.read_bytes() == previous_bytes
    assert store.get_profile() is original
    assert tuple(tmp_path.glob(".profile-*.tmp")) == ()


def test_atomic_write_flushes_with_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        "atreus.profile.json_store.os.fsync",
        lambda descriptor: calls.append(descriptor),
    )

    JsonPersonalProfileStore(
        tmp_path / "profile.json",
        FixedClock(),
    ).replace(sample_profile())

    assert len(calls) == 1


def test_clear_atomically_persists_valid_empty_profile(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    store = JsonPersonalProfileStore(path, FixedClock())
    store.replace(sample_profile())

    cleared = store.clear(NOW)

    assert personal_profile_is_empty(cleared)
    assert store.get_profile() is cleared
    assert PersonalProfileJsonCodec.decode(path.read_bytes()) == cleared


def test_disabled_store_performs_no_disk_access(tmp_path: Path) -> None:
    store = DisabledPersonalProfileStore(FixedClock())

    assert personal_profile_is_empty(store.get_profile())
    with pytest.raises(PersonalProfileDisabledError, match="disabled"):
        store.replace(sample_profile())
    assert tuple(tmp_path.iterdir()) == ()


def test_path_resolution_uses_safe_per_user_directories(tmp_path: Path) -> None:
    windows = resolve_personal_profile_path(
        {"LOCALAPPDATA": str(tmp_path)},
        "nt",
        tmp_path,
    )
    posix = resolve_personal_profile_path(
        {"XDG_DATA_HOME": str(tmp_path)},
        "posix",
        tmp_path,
    )

    assert windows == tmp_path / "ATREUS" / "profile.json"
    assert posix == windows
    assert windows.is_absolute()


def test_json_schema_uses_required_version_and_immutable_collections() -> None:
    data = json.loads(PersonalProfileJsonCodec.encode(sample_profile()))

    assert data["schema_version"] == 1
    assert isinstance(data["projects"], list)
    assert isinstance(PersonalProfileJsonCodec.decode(
        PersonalProfileJsonCodec.encode(sample_profile())
    ).projects, tuple)
