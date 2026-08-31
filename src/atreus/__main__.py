"""Official command-line entrypoint for the ATREUS runtime."""

from atreus.bootstrap.bootstrap import Bootstrap


def main() -> int:
    """Start the ATREUS foundation runtime.

    Returns:
        The process exit status.
    """
    Bootstrap().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
