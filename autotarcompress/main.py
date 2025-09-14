"""Main entry point for AutoTarCompress backup system.

This module contains the main application logic for the backup system,
including the command-line interface and initialization.
"""

import logging
import os

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

# Menu option constants
MENU_BACKUP = 1
MENU_ENCRYPT = 2
MENU_DECRYPT = 3
MENU_CLEANUP = 4
MENU_EXTRACT = 5
MENU_INFO = 6
MENU_EXIT = 7


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
        return

    selected: str = select_file(backup_files, facade.config.backup_folder)
    EncryptCommand(facade.config, selected).execute()


def handle_decrypt_operation(facade: BackupFacade) -> None:
    """Handle backup file decryption operation.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    enc_files: list[str] = get_encrypted_files(facade.config.backup_folder)
    if not enc_files:
        print("No encrypted backups found")
        return

    selected: str = select_file(enc_files, facade.config.backup_folder)
    DecryptCommand(facade.config, selected).execute()


def handle_extract_operation(facade: BackupFacade) -> None:
    """Handle backup file extraction operation.

    Args:
        facade (BackupFacade): Application facade instance.

    """
    backup_files: list[str] = get_backup_files(facade.config.backup_folder)
    if not backup_files:
        print("No backup files found")
        return

    selected: str = select_file(backup_files, facade.config.backup_folder)
    ExtractCommand(facade.config, selected).execute()


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
        except (OSError, FileNotFoundError, PermissionError) as e:
            logging.error("File operation failed: %s", e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)


def main() -> None:
    """Initialize and run the AutoTarCompress application."""
    facade: BackupFacade = initialize_config()
    run_main_loop(facade)


if __name__ == "__main__":
    main()
