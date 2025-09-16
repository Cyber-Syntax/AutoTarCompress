"""Main entry point for AutoTarCompress CLI.

This module provides the main entry point for the AutoTarCompress application.
It delegates execution to the Typer application implemented in
``autotarcompress.cli``.
"""

from autotarcompress import cli


def main() -> None:
    """Run the Typer CLI app.

    This function is intentionally small so it can be used as an entry
    point in packaging (`pyproject.toml` references
    `autotarcompress.main:main`).
    """
    cli.app()


if __name__ == "__main__":
    main()
