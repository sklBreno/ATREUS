"""Official command-line entrypoint for the ATREUS interactive runtime."""

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.runtime.console import InputReader, InteractiveConsole, OutputWriter


def main(
    input_reader: InputReader = input,
    output_writer: OutputWriter = print,
) -> int:
    """Start the foreground ATREUS interactive runtime.

    Args:
        input_reader: Foreground text input callable.
        output_writer: User-facing text output callable.

    Returns:
        The process exit status.
    """
    runtime = Bootstrap().compose()
    return InteractiveConsole(
        runtime.submit,
        input_reader=input_reader,
        output_writer=output_writer,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
