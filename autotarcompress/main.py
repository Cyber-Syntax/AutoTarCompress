"""Main entry point for AutoTarCompress backup system.

This module contains the main application logic for the backup system,
including both the legacy interactive interface and the new CLI interface.
"""

import logging
import os
from typing import Optional

import typer
from typing_extensions import Annotated

from autotarcompress.commands import (
    DecryptCommand,
    EncryptCommand,
    ExtractCommand,
)
from autotarcompress.facade import BackupFacade
from autotarcompress.logger import (
    setup_application_logging,
    setup_basic_logging,
)
from autotarcompress.ui import (
    display_main_menu,
    exit_application,
    get_menu_choice,
    select_file,
)

# Create the main Typer app
app = typer.Typer(
    name="autotarcompress",
    help="AutoTarCompress - A robust backup and archive management tool",
    add_completion=False,
)

# Menu option constants for legacy interface
MENU_BACKUP = 1
MENU_ENCRYPT = 2
MENU_DECRYPT = 3
MENU_CLEANUP = 4
MENU_EXTRACT = 5
MENU_INFO = 6
MENU_EXIT = 7

# Date format validation constant
DATE_PARTS_COUNT = 3


@app.command()
def backup() -> None:
    """Create a backup archive of configured directories."""
    facade: BackupFacade = initialize_config()
    success = facade.execute_command("backup")
    if not success:
        raise typer.Exit(1)


@app.command()
def encrypt(
    latest: Annotated[
        bool, typer.Option("--latest", help="Encrypt the latest backup file")
    ] = False,
    date: Annotated[
        Optional[str], typer.Option("--date", help="Encrypt backup from specific date (dd-mm-yyyy)")
    ] = None,
    file: Annotated[Optional[str], typer.Argument(help="Specific backup file to encrypt")] = None,
) -> None:
    """Encrypt a backup file."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo("Error: Only one of --latest, --date, or file argument can be specified")
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo("Error: Must specify one of --latest, --date, or file argument")
        raise typer.Exit(1)

    facade: BackupFacade = initialize_config()
    try:
        handle_encrypt_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def decrypt(
    latest: Annotated[
        bool, typer.Option("--latest", help="Decrypt the latest encrypted backup")
    ] = False,
    date: Annotated[
        Optional[str], typer.Option("--date", help="Decrypt backup from specific date (dd-mm-yyyy)")
    ] = None,
    file: Annotated[
        Optional[str], typer.Argument(help="Specific encrypted file to decrypt")
    ] = None,
) -> None:
    """Decrypt an encrypted backup file."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo("Error: Only one of --latest, --date, or file argument can be specified")
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo("Error: Must specify one of --latest, --date, or file argument")
        raise typer.Exit(1)

    facade: BackupFacade = initialize_config()
    try:
        handle_decrypt_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def extract(
    latest: Annotated[bool, typer.Option("--latest", help="Extract the latest backup")] = False,
    date: Annotated[
        Optional[str], typer.Option("--date", help="Extract backup from specific date (dd-mm-yyyy)")
    ] = None,
    file: Annotated[Optional[str], typer.Argument(help="Specific backup file to extract")] = None,
) -> None:
    """Extract a backup archive."""
    # Validate mutually exclusive options
    options_count = sum([latest, date is not None, file is not None])
    if options_count > 1:
        typer.echo("Error: Only one of --latest, --date, or file argument can be specified")
        raise typer.Exit(1)
    if options_count == 0:
        typer.echo("Error: Must specify one of --latest, --date, or file argument")
        raise typer.Exit(1)

    facade: BackupFacade = initialize_config()
    try:
        handle_extract_operation_cli(facade, latest, date, file)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None


@app.command()
def cleanup(
    all_backups: Annotated[bool, typer.Option("--all", help="Remove all old backups")] = False,
    older_than: Annotated[
        Optional[int], typer.Option("--older-than", help="Remove backups older than N days")
    ] = None,
    keep: Annotated[
        Optional[int], typer.Option("--keep", help="Keep only the N most recent backups")
    ] = None,
) -> None:
    """Clean up old backup files."""
    # Validate mutually exclusive options
    options_count = sum([all_backups, older_than is not None, keep is not None])
    if options_count > 1:
        typer.echo("Error: Only one of --all, --older-than, or --keep can be specified")
        raise typer.Exit(1)

    facade: BackupFacade = initialize_config()
    success = facade.execute_command("cleanup")
    if not success:
        raise typer.Exit(1)


@app.command()
def info() -> None:
    """Show information about the last backup."""
    facade: BackupFacade = initialize_config()
    success = facade.execute_command("info")
    if not success:
        raise typer.Exit(1)


@app.command()
def interactive() -> None:
    """Launch the interactive menu (legacy mode)."""
    facade: BackupFacade = initialize_config()
    run_main_loop(facade)


def find_file_by_date(files: list[str], target_date: str) -> Optional[str]:
    """Find backup file by date pattern.

    Args:
        files: List of backup files.
        target_date: Date in dd-mm-yyyy format.

    Returns:
        Matching filename or None if not found.

    """
    try:
        # Convert dd-mm-yyyy to dd-mm-yyyy pattern for filename matching
        date_parts = target_date.split("-")
        if len(date_parts) != DATE_PARTS_COUNT:
            raise ValueError("Invalid date format")

        day, month, year = date_parts
        date_pattern = f"{day}-{month}-{year}"

        for file in files:
            if date_pattern in file:
                return file
    except ValueError:
        typer.echo(f"Error: Invalid date format '{target_date}'. Use dd-mm-yyyy")

    return None


def handle_encrypt_operation_cli(
    facade: BackupFacade, latest: bool, date: Optional[str], file: Optional[str]
) -> None:
    """Handle backup file encryption operation for CLI.

    Args:
        facade: Application facade instance.
        latest: Whether to encrypt latest backup.
        date: Date string for date-based selection.
        file: Specific file to encrypt.

    """
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        typer.echo("No backup files available for encryption")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        # Sort by modification time, get most recent
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        backup_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)), reverse=True
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
        full_path = os.path.join(os.path.expanduser(facade.config.backup_folder), selected_file)
        EncryptCommand(facade.config, full_path).execute()


def handle_decrypt_operation_cli(
    facade: BackupFacade, latest: bool, date: Optional[str], file: Optional[str]
) -> None:
    """Handle backup file decryption operation for CLI.

    Args:
        facade: Application facade instance.
        latest: Whether to decrypt latest encrypted backup.
        date: Date string for date-based selection.
        file: Specific file to decrypt.

    """
    enc_files: list[str] = get_encrypted_files(facade.config.backup_folder)
    if not enc_files:
        typer.echo("No encrypted backups found")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        # Sort by modification time, get most recent
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        enc_files.sort(key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)), reverse=True)
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
        full_path = os.path.join(os.path.expanduser(facade.config.backup_folder), selected_file)
        DecryptCommand(facade.config, full_path).execute()


def handle_extract_operation_cli(
    facade: BackupFacade, latest: bool, date: Optional[str], file: Optional[str]
) -> None:
    """Handle backup file extraction operation for CLI.

    Args:
        facade: Application facade instance.
        latest: Whether to extract latest backup.
        date: Date string for date-based selection.
        file: Specific file to extract.

    """
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        typer.echo("No backup files found")
        raise typer.Exit(1)

    selected_file: Optional[str] = None

    if latest:
        # Sort by modification time, get most recent
        expanded_dir = os.path.expanduser(facade.config.backup_folder)
        backup_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(expanded_dir, f)), reverse=True
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
        full_path = os.path.join(os.path.expanduser(facade.config.backup_folder), selected_file)
        ExtractCommand(facade.config, full_path).execute()


def initialize_config() -> BackupFacade:
    """Initialize configuration and logging for the application.

    Returns:
        BackupFacade: Configured facade instance.

    """
    facade: BackupFacade = BackupFacade()

    # Load config if it exists, otherwise use defaults
    if not os.path.exists(facade.config.config_path):
        # Basic logging for initial setup
        setup_basic_logging()
        logging.info("No configuration found. Starting initial setup.")
        facade.configure()
    else:
        facade.config = facade.config.load()

    # Setup logging with configured level
    setup_application_logging(facade.config.get_log_level())
    return facade


def get_backup_files(backup_folder: str) -> list[str]:
    """Get list of backup files in the specified folder.

    Args:
        backup_folder (str): Path to backup folder.

    Returns:
        list[str]: List of .tar.xz files (excluding encrypted ones).

    """
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [
        f
        for f in os.listdir(expanded_backup_dir)
        if f.endswith(".tar.xz") and not f.endswith(".enc")
    ]


def get_encrypted_files(backup_folder: str) -> list[str]:
    """Get list of encrypted backup files in the specified folder.

    Args:
        backup_folder (str): Path to backup folder.

    Returns:
        list[str]: List of .enc files.

    """
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [f for f in os.listdir(expanded_backup_dir) if f.endswith(".enc")]


def handle_encrypt_operation(facade: BackupFacade) -> None:
    """Handle backup file encryption operation.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        print("No backup files available for encryption")
        return None

    selected: str = select_file(backup_files, facade.config.backup_folder)
    EncryptCommand(facade.config, selected).execute()
    return None


def handle_decrypt_operation(facade: BackupFacade) -> None:
    """Handle backup file decryption operation.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    enc_files: list[str] = get_encrypted_files(facade.config.backup_folder)
    if not enc_files:
        print("No encrypted backups found")
        return None

    selected: str = select_file(enc_files, facade.config.backup_folder)
    DecryptCommand(facade.config, selected).execute()
    return None


def handle_extract_operation(facade: BackupFacade) -> None:
    """Handle backup file extraction operation.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        print("No backup files found")
        return None

    selected: str = select_file(backup_files, facade.config.backup_folder)
    ExtractCommand(facade.config, selected).execute()
    return None


def process_menu_choice(choice: int, facade: BackupFacade) -> None:
    """Process the user's menu choice.

    Args:
        choice (int): Menu choice number.
        facade (BackupFacade): Application facade instance.

    """
    if choice == MENU_BACKUP:
        facade.execute_command("backup")
    elif choice == MENU_ENCRYPT:
        handle_encrypt_operation(facade)
    elif choice == MENU_DECRYPT:
        handle_decrypt_operation(facade)
    elif choice == MENU_CLEANUP:
        facade.execute_command("cleanup")
    elif choice == MENU_EXTRACT:
        handle_extract_operation(facade)
    elif choice == MENU_INFO:
        facade.execute_command("info")
    elif choice == MENU_EXIT:
        exit_application()


def run_main_loop(facade: BackupFacade) -> None:
    """Run the main application loop.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    # Ensure backup directory exists
    expanded_backup_dir: str = os.path.expanduser(facade.config.backup_folder)
    if not os.path.exists(expanded_backup_dir):
        os.makedirs(expanded_backup_dir)

    while True:
        try:
            display_main_menu()
            choice: int = get_menu_choice()
            process_menu_choice(choice, facade)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except (OSError, FileNotFoundError, PermissionError, ValueError) as e:
            logging.error("Operation failed: %s", e)


def main() -> None:
    """Run the Typer CLI app."""
    app()


if __name__ == "__main__":
    main()
