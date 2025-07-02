"""Main entry point for AutoTarCompress backup system.

This module contains the main application logic for the backup system,
including the command-line interface and initialization.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import List
from pathlib import Path

from src.commands import DecryptCommand, EncryptCommand, ExtractCommand
from src.facade import BackupFacade

def get_xdg_state_home() -> Path:
    """Get the XDG state home directory."""
    xdg_state_home = os.getenv("XDG_STATE_HOME")
    if not xdg_state_home or not Path(xdg_state_home).is_absolute():
        return Path.home() / ".local" / "state"
    return Path(xdg_state_home)

def setup_logging() -> None:
    """Configure logging for the application."""
    log_dir_base = get_xdg_state_home()

    log_dir = log_dir_base / "autotarcompress"
    log_dir.mkdir(parents=True, exist_ok=True)  # Use parents=True to create intermediate dirs
    log_file = "autotarcompress.log"
    log_file_path = log_dir / log_file

    # Configure file handler for all log levels
    file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024, backupCount=3)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configure console handler for ERROR and above only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # Only show errors and above in console
    console_formatter = logging.Formatter("%(message)s")  # Simpler format for console
    console_handler.setFormatter(console_formatter)

    # Get root logger and configure it
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers (in case this function is called multiple times)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add the configured handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info("Logging configured with DEBUG level")


def select_file(files: List[str], backup_folder: str) -> str:
    """Helper function to select a file from a list.

    Args:
        files: List of file names to choose from
        backup_folder: Base directory containing the files

    Returns:
        Full path to the selected file
    """
    for idx, file in enumerate(files, start=1):
        print(f"{idx}. {file}")
    choice = int(input("Enter your choice: ")) - 1
    return os.path.join(backup_folder, files[choice])


def main():
    """Main application entry point"""
    setup_logging()
    facade = BackupFacade()

    # Always expand backup folder path first
    expanded_backup_dir = os.path.expanduser(facade.config.backup_folder)

    # Create backup directory if missing
    if not os.path.exists(expanded_backup_dir):
        os.makedirs(expanded_backup_dir)  # Secure directory permissions

    # Initial configuration check
    if not os.path.exists(facade.config.config_path):
        logging.info("No configuration found. Starting initial setup.")
        facade.configure()
    else:
        logging.info("Loading existing configuration")
        facade.config = facade.config.load()

    while True:
        print("\n===== Backup Manager =====")
        print("1. Perform Backup")
        print("2. Encrypt Backup File")
        print("3. Decrypt Backup")
        print("4. Cleanup Old Backups")
        print("5. Extract Backup")
        print("6. Exit")

        try:
            choice = input("Enter your choice (1-6): ").strip()
            if choice == "6":
                print("Exiting...")
                sys.exit(0)

            choice = int(choice)
            if choice < 1 or choice > 6:
                raise ValueError

        except ValueError:
            print("Invalid input. Please enter a number between 1-6.")
            continue

        try:
            if choice == 1:
                facade.execute_command("backup")
            elif choice == 2:
                # List available backup files
                backup_files = [
                    f
                    for f in os.listdir(expanded_backup_dir)
                    if f.endswith(".tar.xz") and not f.endswith(".enc")
                ]
                if not backup_files:
                    print("No backup files available for encryption")
                    continue
                selected = select_file(backup_files, facade.config.backup_folder)
                EncryptCommand(facade.config, selected).execute()
            elif choice == 3:
                enc_files = [f for f in os.listdir(expanded_backup_dir) if f.endswith(".enc")]
                if not enc_files:
                    print("No encrypted backups found")
                    continue
                selected = select_file(enc_files, facade.config.backup_folder)
                DecryptCommand(facade.config, selected).execute()
            elif choice == 4:
                facade.execute_command("cleanup")
            elif choice == 5:
                backup_files = [
                    f
                    for f in os.listdir(expanded_backup_dir)
                    if f.endswith(".tar.xz") and not f.endswith(".enc")
                ]
                if not backup_files:
                    print("No backup files found")
                    continue
                selected = select_file(backup_files, facade.config.backup_folder)
                ExtractCommand(facade.config, selected).execute()

        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logging.error(f"Operation failed: {str(e)}")


if __name__ == "__main__":
    main()
