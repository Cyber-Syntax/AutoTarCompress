"""CLI module for AutoTarCompress.

This file contains the Typer application and CLI command handlers.
The heavier application logic and interactive helpers live in
``autotarcompress.runner`` to avoid circular imports.
"""

import os
from typing import Optional

import typer
from typing_extensions import Annotated

from autotarcompress import __version__, runner
from autotarcompress.commands import (
    DecryptCommand,
    EncryptCommand,
    ExtractCommand,
)
from autotarcompress.facade import BackupFacade

# Create the main Typer app
app = typer.Typer(
    name="autotarcompress",
    help="AutoTarCompress - A robust backup and archive management tool",
    add_completion=False,
)


def get_version() -> str:
    """Return the application version."""
    return __version__


def _version_callback(ctx: typer.Context, _param, value: bool) -> None:
    """Typer callback to handle the global --version option.

    This callback is invoked eagerly. When the flag is present we print
    the version and exit immediately.
    """
    if not value or ctx.resilient_parsing:
        return
    typer.echo(get_version())
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            is_eager=True,
            callback=_version_callback,
            help="Show the application version",
        ),
    ] = False,
) -> None:
    """Allow a global --version option.

    When invoked with the `--version` flag the callback prints the
    version and exits. When run without subcommands it is a no-op.
    """
    if ctx.invoked_subcommand is None:
        return


@app.command(name="version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(get_version())


@app.command()
def backup() -> None:
    """Create a backup archive of configured directories."""
    facade: BackupFacade = runner.initialize_config()
    success = facade.execute_command("backup")
    if not success:
        raise typer.Exit(1)


@app.command()
def encrypt(
    latest: Annotated[
        bool,
        typer.Option(
            "--latest",
            help="Encrypt the latest backup file",
        ),
    ] = False,
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date",
            help=("Encrypt backup from specific date (dd-mm-yyyy)"),
        ),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Argument(help="Specific backup file to encrypt"),
    ] = None,
) -> None:
    """Encrypt a backup file."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo(
            "Error: Only one of --latest, --date, or file argument "
            "can be specified"
        )
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo(
            "Error: Must specify one of --latest, --date, or file argument"
        )
        raise typer.Exit(1)

    facade: BackupFacade = runner.initialize_config()
    try:
        handle_encrypt_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def decrypt(
    latest: Annotated[
        bool,
        typer.Option(
            "--latest",
            help="Decrypt the latest encrypted backup",
        ),
    ] = False,
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date",
            help=("Decrypt backup from specific date (dd-mm-yyyy)"),
        ),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Argument(help="Specific encrypted file to decrypt"),
    ] = None,
) -> None:
    """Decrypt an encrypted backup file."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo(
            "Error: Only one of --latest, --date, or file argument "
            "can be specified"
        )
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo(
            "Error: Must specify one of --latest, --date, or file argument"
        )
        raise typer.Exit(1)

    facade: BackupFacade = runner.initialize_config()
    try:
        handle_decrypt_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def extract(
    latest: Annotated[
        bool,
        typer.Option("--latest", help="Extract the latest backup"),
    ] = False,
    date: Annotated[
        Optional[str],
        typer.Option(
            "--date",
            help=("Extract backup from specific date (dd-mm-yyyy)"),
        ),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Argument(help="Specific backup file to extract"),
    ] = None,
) -> None:
    """Extract a backup archive."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo(
            "Error: Only one of --latest, --date, or file argument "
            "can be specified"
        )
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo(
            "Error: Must specify one of --latest, --date, or file argument"
        )
        raise typer.Exit(1)

    facade: BackupFacade = runner.initialize_config()
    try:
        handle_extract_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def cleanup(
    all_backups: Annotated[
        bool,
        typer.Option("--all", help="Remove all old backups"),
    ] = False,
    older_than: Annotated[
        Optional[int],
        typer.Option(
            "--older-than",
            help="Remove backups older than N days",
        ),
    ] = None,
    keep: Annotated[
        Optional[int],
        typer.Option(
            "--keep",
            help="Keep only the N most recent backups",
        ),
    ] = None,
) -> None:
    """Clean up old backup files."""
    # Validate mutually exclusive options
    options_count = sum(
        [
            all_backups,
            older_than is not None,
            keep is not None,
        ]
    )
    if options_count > 1:
        typer.echo(
            "Error: Only one of --all, --older-than, or --keep "
            "can be specified"
        )
        raise typer.Exit(1)

    facade: BackupFacade = runner.initialize_config()
    success = facade.execute_command("cleanup", cleanup_all=all_backups)
    if not success:
        raise typer.Exit(1)


@app.command()
def info() -> None:
    """Show information about the last backup."""
    facade: BackupFacade = runner.initialize_config()
    success = facade.execute_command("info")
    if not success:
        raise typer.Exit(1)


@app.command()
def interactive() -> None:
    """Launch the interactive menu (legacy mode)."""
    facade: BackupFacade = runner.initialize_config()
    runner.run_main_loop(facade)


def find_file_by_date(files: list[str], target_date: str) -> Optional[str]:
    """Find backup file by date pattern.

    Reused here for CLI helpers.
    """
    return runner.find_file_by_date(files, target_date)


def handle_encrypt_operation_cli(
    facade: BackupFacade,
    latest: bool,
    date: Optional[str],
    file: Optional[str],
) -> None:
    """Handle backup file encryption operation for CLI."""
    backup_files: list[str] = runner.get_backup_files(
        facade.config.backup_folder
    )
    if not backup_files:
        typer.echo("No backup files available for encryption")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        backup_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)),
            reverse=True,
        )
        selected_file = backup_files[0]

    elif date:
        selected_file = find_file_by_date(backup_files, date)
        if not selected_file:
            typer.echo(f"No backup file found for date {date}")
            raise typer.Exit(1)

    elif file:
        if file in backup_files:
            selected_file = file
        else:
            typer.echo(f"File '{file}' not found in backup directory")
            raise typer.Exit(1)

    if selected_file:
        full_path = os.path.join(
            os.path.expanduser(facade.config.backup_folder),
            selected_file,
        )
        EncryptCommand(facade.config, full_path).execute()


def handle_decrypt_operation_cli(
    facade: BackupFacade,
    latest: bool,
    date: Optional[str],
    file: Optional[str],
) -> None:
    """Handle backup file decryption operation for CLI."""
    enc_files: list[str] = runner.get_encrypted_files(
        facade.config.backup_folder
    )
    if not enc_files:
        typer.echo("No encrypted backups found")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        enc_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)),
            reverse=True,
        )
        selected_file = enc_files[0]

    elif date:
        selected_file = find_file_by_date(enc_files, date)
        if not selected_file:
            typer.echo(f"No encrypted backup file found for date {date}")
            raise typer.Exit(1)

    elif file:
        if file in enc_files:
            selected_file = file
        else:
            typer.echo(f"File '{file}' not found in backup directory")
            raise typer.Exit(1)

    if selected_file:
        full_path = os.path.join(
            os.path.expanduser(facade.config.backup_folder),
            selected_file,
        )
        DecryptCommand(facade.config, full_path).execute()


def handle_extract_operation_cli(
    facade: BackupFacade,
    latest: bool,
    date: Optional[str],
    file: Optional[str],
) -> None:
    """Handle backup file extraction operation for CLI."""
    backup_files: list[str] = runner.get_backup_files(
        facade.config.backup_folder
    )
    if not backup_files:
        typer.echo("No backup files found")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        backup_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)),
            reverse=True,
        )
        selected_file = backup_files[0]

    elif date:
        selected_file = find_file_by_date(backup_files, date)
        if not selected_file:
            typer.echo(f"No backup file found for date {date}")
            raise typer.Exit(1)

    elif file:
        if file in backup_files:
            selected_file = file
        else:
            typer.echo(f"File '{file}' not found in backup directory")
            raise typer.Exit(1)

    if selected_file:
        full_path = os.path.join(
            os.path.expanduser(facade.config.backup_folder),
            selected_file,
        )
        ExtractCommand(facade.config, full_path).execute()
