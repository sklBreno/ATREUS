"""Explicit reviewed-file import command for the ATREUS Personal Profile."""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from atreus.profile.exceptions import (
    PersonalProfileException,
    PersonalProfileImportError,
)
from atreus.profile.json_store import JsonPersonalProfileStore
from atreus.profile.models import PersonalProfile
from atreus.profile.path import resolve_personal_profile_path
from atreus.profile.serialization import (
    MAX_PERSONAL_PROFILE_FILE_BYTES,
    PersonalProfileJsonCodec,
)
from atreus.shared.clock import UTCClock

type TextWriter = Callable[[str], None]


def _write_stderr(text: str) -> None:
    """Write one sanitized importer message to standard error."""
    print(text, file=sys.stderr)


def validate_profile_import(source_path: Path) -> PersonalProfile:
    """Read and validate a reviewed profile document without mutation.

    Args:
        source_path: Explicit candidate JSON document selected by the user.

    Returns:
        The complete validated immutable candidate profile.

    Raises:
        PersonalProfileImportError: If the document cannot be read or validated.
    """
    if not isinstance(source_path, Path):
        raise PersonalProfileImportError(
            "Personal Profile import source is invalid."
        )
    try:
        size = source_path.stat().st_size
        if size > MAX_PERSONAL_PROFILE_FILE_BYTES:
            raise PersonalProfileImportError(
                "Personal Profile import exceeds the supported size."
            )
        data = source_path.read_bytes()
        return PersonalProfileJsonCodec.decode(data)
    except PersonalProfileImportError:
        raise
    except PersonalProfileException as error:
        raise PersonalProfileImportError(
            "Personal Profile import document is invalid."
        ) from error
    except OSError:
        raise PersonalProfileImportError(
            "Personal Profile import document could not be read."
        ) from None


def apply_profile_import(
    source_path: Path,
    destination_path: Path,
    *,
    confirmed: bool,
) -> PersonalProfile:
    """Validate fully and atomically apply an explicitly confirmed import."""
    if confirmed is not True:
        raise PersonalProfileImportError(
            "Personal Profile import requires explicit confirmation."
        )
    profile = validate_profile_import(source_path)
    try:
        return JsonPersonalProfileStore(destination_path, UTCClock()).replace(profile)
    except PersonalProfileException as error:
        raise PersonalProfileImportError(
            "Personal Profile import could not be persisted."
        ) from error


def main(
    arguments: Sequence[str] | None = None,
    *,
    destination_path: Path | None = None,
    output_writer: TextWriter = print,
    error_writer: TextWriter = _write_stderr,
) -> int:
    """Validate or explicitly apply one reviewed Personal Profile document."""
    parser = _argument_parser()
    parsed = parser.parse_args(arguments)
    source_path = Path(parsed.file)
    try:
        if parsed.operation == "validate":
            validate_profile_import(source_path)
            output_writer("Personal Profile import document is valid.")
            return 0
        if not parsed.confirm:
            error_writer("Personal Profile import requires --confirm.")
            return 2
        target = destination_path or resolve_personal_profile_path()
        apply_profile_import(source_path, target, confirmed=True)
        output_writer("Personal Profile imported successfully.")
        return 0
    except PersonalProfileException:
        error_writer("Personal Profile import failed.")
        return 1


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or import one reviewed Personal Profile JSON document."
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("file")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("file")
    apply_parser.add_argument("--confirm", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
