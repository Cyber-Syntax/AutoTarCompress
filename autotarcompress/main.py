"""Main entry point for AutoTarCompress backup system.

This module contains the main application logic for the backup system,
including the command-line interface and initialization.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from autotarcompress.commands import DecryptCommand, EncryptCommand, ExtractCommand
from autotarcompress.facade import BackupFacade


def get_xdg_state_home() -> Path:
    """Return the XDG state home directory path."""
    xdg_state_home: str | None = os.getenv("XDG_STATE_HOME")
    if not xdg_state_home or not Path(xdg_state_home).is_absolute():
        return Path.home() / ".local" / "state"
    return Path(xdg_state_home)


def setup_logging() -> None:
    """Configure logging for the application."""
    log_dir_base: Path = get_xdg_state_home()
    log_dir: Path = log_dir_base / "autotarcompress"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path: Path = log_dir / "autotarcompress.log"
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=1024 * 1024, backupCount=3
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers (in case this function is called multiple times)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logging.info("Logging configured with DEBUG level")


def select_file(files: list[str], backup_folder: str) -> str:
    """Prompt user to select a file from a list and return its full path.

    Args:
        files (list[str]): List of file names to choose from.
        backup_folder (str): Base directory containing the files.

    Returns:
        str: Full path to the selected file.

    """
    for idx, file in enumerate(files, start=1):
        print(f"{idx}. {file}")
    choice: int = int(input("Enter your choice: ")) - 1
    return os.path.join(backup_folder, files[choice])


def main() -> None:
    """Main application entry point for AutoTarCompress CLI."""
    setup_logging()
    facade: BackupFacade = BackupFacade()
    expanded_backup_dir: str = os.path.expanduser(facade.config.backup_folder)
    if not os.path.exists(expanded_backup_dir):
        os.makedirs(expanded_backup_dir)
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
        print("6. Show Last Backup Info")
        print("7. Exit")

        try:
            choice: str = input("Enter your choice (1-7): ").strip()
            if choice == "7":
                print("Exiting...")
                sys.exit(0)
            choice_int: int = int(choice)
            if choice_int < 1 or choice_int > 7:
                raise ValueError
        except ValueError:
            print("Invalid input. Please enter a number between 1-7.")
            continue

        try:
            if choice_int == 1:
                facade.execute_command("backup")
            elif choice_int == 2:
                backup_files: list[str] = [
                    f
                    for f in os.listdir(expanded_backup_dir)
                    if f.endswith(".tar.xz") and not f.endswith(".enc")
                ]
                if not backup_files:
                    print("No backup files available for encryption")
                    continue
                selected: str = select_file(backup_files, facade.config.backup_folder)
                EncryptCommand(facade.config, selected).execute()
            elif choice_int == 3:
                enc_files: list[str] = [
                    f for f in os.listdir(expanded_backup_dir) if f.endswith(".enc")
                ]
                if not enc_files:
                    print("No encrypted backups found")
                    continue
                selected: str = select_file(enc_files, facade.config.backup_folder)
                DecryptCommand(facade.config, selected).execute()
            elif choice_int == 4:
                facade.execute_command("cleanup")
            elif choice_int == 5:
                backup_files: list[str] = [
                    f
                    for f in os.listdir(expanded_backup_dir)
                    if f.endswith(".tar.xz") and not f.endswith(".enc")
                ]
                if not backup_files:
                    print("No backup files found")
                    continue
                selected: str = select_file(backup_files, facade.config.backup_folder)
                ExtractCommand(facade.config, selected).execute()
            elif choice_int == 6:
                facade.execute_command("info")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logging.error("Operation failed: %s", e)


if __name__ == "__main__":
    main()
