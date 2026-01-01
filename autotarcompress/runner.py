"""Shared runner utilities for AutoTarCompress.

This module contains helpers that were previously in `main.py` and are
reused by both the CLI and the interactive legacy interface.
"""

from __future__ import annotations

import logging
import os

import typer

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


def find_file_by_date(files: list[str], target_date: str) -> str | None:
    """Find backup file by date pattern.

    Args:
        files: List of backup files.
        target_date: Date in dd-mm-yyyy format.

    Returns:
        Matching filename or None if not found.

    """
    try:
        date_parts = target_date.split("-")
        if len(date_parts) != DATE_PARTS_COUNT:
            raise ValueError("Invalid date format")

        day, month, year = date_parts
        date_pattern = f"{day}-{month}-{year}"

        for file in files:
            if date_pattern in file:
                return file
    except ValueError:
        typer.echo(
            f"Error: Invalid date format '{target_date}'. Use dd-mm-yyyy"
        )

    return None


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
    """Get list of backup files in the specified folder."""
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [
        f
        for f in os.listdir(expanded_backup_dir)
        if f.endswith(".tar.xz") and not f.endswith(".enc")
    ]


def get_encrypted_files(backup_folder: str) -> list[str]:
    """Get list of encrypted backup files in the specified folder."""
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [f for f in os.listdir(expanded_backup_dir) if f.endswith(".enc")]


def handle_encrypt_operation(facade: BackupFacade) -> None:
    """Handle backup file encryption operation (interactive)."""
    logger = logging.getLogger(__name__)
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        logger.info("No backup files available for encryption")
        return

    selected: str = select_file(backup_files, facade.config.backup_folder)
    from autotarcompress.commands import EncryptCommand

    EncryptCommand(facade.config, selected).execute()
    return


def handle_decrypt_operation(facade: BackupFacade) -> None:
    """Handle backup file decryption operation (interactive)."""
    logger = logging.getLogger(__name__)
    enc_files: list[str] = get_encrypted_files(facade.config.backup_folder)
    if not enc_files:
        logger.info("No encrypted backups found")
        return

    selected: str = select_file(enc_files, facade.config.backup_folder)
    from autotarcompress.commands import DecryptCommand

    DecryptCommand(facade.config, selected).execute()
    return


def handle_extract_operation(facade: BackupFacade) -> None:
    """Handle backup file extraction operation (interactive)."""
    logger = logging.getLogger(__name__)
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        logger.info("No backup files found")
        return

    selected: str = select_file(backup_files, facade.config.backup_folder)
    from autotarcompress.commands import ExtractCommand

    ExtractCommand(facade.config, selected).execute()
    return


def process_menu_choice(choice: int, facade: BackupFacade) -> None:
    """Process the user's menu choice."""
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
    """Run the main application loop."""
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
            logger = logging.getLogger(__name__)
            logger.info("Operation cancelled by user")
        except (OSError, FileNotFoundError, PermissionError, ValueError) as e:
            logging.exception("Operation failed: %s", e)
