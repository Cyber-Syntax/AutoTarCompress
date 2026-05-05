"""Main entry point for AutoTarCompress CLI.

This module exposes a small ``main()`` function for packaging entry
points and ensures a consistent import context when executed directly.

When the file is run as a script (``python autotarcompress/main.py``)
there can be subtle differences in how the package is imported which
affect Typer's command registration and global options. To avoid that
class of problem we re-exec the interpreter using ``-m
autotarcompress.main`` so the package is imported in module mode. This
makes the CLI help and commands stable while developing.
"""

import os
import sys
from importlib import import_module

from typer.main import get_command


def main() -> None:
    """Run the Typer CLI application.

    The Typer application is defined in ``autotarcompress.cli``. We try
    to obtain the underlying Click application using `typer.main.get_command`
    and invoke that to mirror Typer's normal runtime behaviour. If any
    unexpected error occurs we fall back to calling the Typer app
    directly.
    """
    # Import by module name so the package is always imported the same way.
    cli_module = import_module("autotarcompress.cli")  # type: Any
    app = cli_module.app  # type: Any

    try:
        # Build and run the underlying Click application. This matches
        # Typer's internal invocation and gives consistent help output.

        click_app = get_command(app)
        click_app()
    except Exception:
        # Robust fallback to invoking the Typer app directly.
        app()


if __name__ == "__main__":
    # If executed directly (not with -m) the import system may load the
    # package in a way that causes duplicated modules and thus missing
    # command registrations. Re-execing with -m ensures a consistent
    # package import context.
    if __package__ is None or __package__ == "":
        os.execv(
            sys.executable,
            [sys.executable, "-m", "autotarcompress.main", *sys.argv[1:]],
        )
    else:
        main()
