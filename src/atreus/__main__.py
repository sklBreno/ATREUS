"""Official command-line entrypoint for the ATREUS interactive runtime."""

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.runtime.console import InputReader, OutputWriter


def main(
    input_reader: InputReader = input,
    output_writer: OutputWriter = print,
    bootstrap: Bootstrap | None = None,
) -> int:
    """Start the foreground ATREUS interactive runtime.

    Args:
        input_reader: Foreground text input callable.
        output_writer: User-facing text output callable.
        bootstrap: Optional production composition root.

    Returns:
        The process exit status.
    """
    composition_root = bootstrap if bootstrap is not None else Bootstrap()
    host = composition_root.compose_host(
        input_reader=input_reader,
        output_writer=output_writer,
    )
    return host.run()


if __name__ == "__main__":
    raise SystemExit(main())
