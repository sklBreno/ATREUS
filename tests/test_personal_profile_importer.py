"""Tests for explicit reviewed Personal Profile import tooling."""

from pathlib import Path

import pytest

from atreus.profile.exceptions import PersonalProfileImportError
from atreus.profile.importer import (
    apply_profile_import,
    main,
    validate_profile_import,
)
from atreus.profile.json_store import JsonPersonalProfileStore
from atreus.profile.serialization import (
    MAX_PERSONAL_PROFILE_FILE_BYTES,
    PersonalProfileJsonCodec,
)
from tests.support import FixedClock
from tests.test_personal_profile_models import sample_profile


def write_candidate(path: Path) -> None:
    """Write one valid fictional reviewed profile candidate."""
    path.write_bytes(PersonalProfileJsonCodec.encode(sample_profile()))


def test_validate_import_returns_profile_and_performs_zero_mutation(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.json"
    destination = tmp_path / "profile.json"
    write_candidate(candidate)

    profile = validate_profile_import(candidate)

    assert profile == sample_profile()
    assert not destination.exists()


@pytest.mark.parametrize(
    "data",
    (
        b"malformed",
        b'{"schema_version":2,"updated_at":"2026-09-03T12:00:00Z"}',
        b'{"schema_version":1,"updated_at":"2026-09-03T12:00:00Z",'
        b'"secret":"value"}',
    ),
)
def test_validate_import_rejects_invalid_documents(
    tmp_path: Path,
    data: bytes,
) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(data)

    with pytest.raises(PersonalProfileImportError) as raised:
        validate_profile_import(candidate)

    assert "value" not in str(raised.value)
    assert str(candidate) not in str(raised.value)


def test_validate_import_rejects_oversized_document(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(b"x" * (MAX_PERSONAL_PROFILE_FILE_BYTES + 1))

    with pytest.raises(PersonalProfileImportError, match="size"):
        validate_profile_import(candidate)


def test_apply_requires_explicit_confirmation_and_preserves_destination(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.json"
    destination = tmp_path / "profile.json"
    write_candidate(candidate)
    destination.write_text("existing", encoding="utf-8")

    with pytest.raises(PersonalProfileImportError, match="confirmation"):
        apply_profile_import(candidate, destination, confirmed=False)

    assert destination.read_text(encoding="utf-8") == "existing"


def test_apply_persists_validated_profile_atomically(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    destination = tmp_path / "profile.json"
    write_candidate(candidate)

    imported = apply_profile_import(candidate, destination, confirmed=True)

    assert imported == sample_profile()
    assert JsonPersonalProfileStore(
        destination,
        FixedClock(),
    ).get_profile() == imported


def test_failed_apply_leaves_existing_destination_unchanged(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    destination = tmp_path / "profile.json"
    candidate.write_bytes(b"invalid")
    destination.write_bytes(PersonalProfileJsonCodec.encode(sample_profile()))
    previous = destination.read_bytes()

    with pytest.raises(PersonalProfileImportError):
        apply_profile_import(candidate, destination, confirmed=True)

    assert destination.read_bytes() == previous


def test_import_cli_validate_and_apply_require_explicit_confirm(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.json"
    destination = tmp_path / "profile.json"
    output: list[str] = []
    errors: list[str] = []
    write_candidate(candidate)

    assert main(
        ("validate", str(candidate)),
        destination_path=destination,
        output_writer=output.append,
        error_writer=errors.append,
    ) == 0
    assert not destination.exists()
    assert main(
        ("apply", str(candidate)),
        destination_path=destination,
        output_writer=output.append,
        error_writer=errors.append,
    ) == 2
    assert not destination.exists()
    assert main(
        ("apply", str(candidate), "--confirm"),
        destination_path=destination,
        output_writer=output.append,
        error_writer=errors.append,
    ) == 0

    assert destination.exists()
    assert output == (
        [
            "Personal Profile import document is valid.",
            "Personal Profile imported successfully.",
        ]
    )
    assert errors == ["Personal Profile import requires --confirm."]
