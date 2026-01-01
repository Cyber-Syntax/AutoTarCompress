"""User interface utilities for AutoTarCompress.

This module provides user interaction functions following the Single
Responsibility Principle. It handles file selection and user input validation.
"""

import logging
import os
import sys
from typing import NoReturn

# Menu configuration
MAX_MENU_CHOICE = 7


def select_file(files: list[str], backup_folder: str) -> str:
    """Prompt user to select a file from a list and return its full path.

    Args:
        files (list[str]): List of file names to choose from.
        backup_folder (str): Base directory containing the files.

    Returns:
        str: Full path to the selected file.

    Raises:
        ValueError: If user input is invalid.
        IndexError: If choice is out of range.

    """
    if not files:
        raise ValueError("No files available for selection")

    logger = logging.getLogger(__name__)
    logger.info("\nAvailable files:")
    for idx, file in enumerate(files, start=1):
        logger.info("%d. %s", idx, file)

    while True:
        try:
            choice_input = input("Enter your choice: ").strip()
            if not choice_input:
                logger.info("Please enter a number.")
                continue

            choice: int = int(choice_input) - 1
            if choice < 0 or choice >= len(files):
                logger.info(
                    "Please enter a number between 1 and %d.", len(files)
                )
                continue

            return os.path.join(backup_folder, files[choice])

        except ValueError:
            logger.info("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            raise


def get_menu_choice() -> int:
    """Get and validate user menu choice.

    Returns:
        int: Valid menu choice (1-7).

    Raises:
        KeyboardInterrupt: If user cancels with Ctrl+C.

    """
    logger = logging.getLogger(__name__)
    while True:
        try:
            choice: str = input("Enter your choice (1-7): ").strip()
            if not choice:
                logger.info("Please enter a number.")
                continue

            choice_int: int = int(choice)
            if choice_int < 1 or choice_int > MAX_MENU_CHOICE:
                logger.info(
                    "Invalid input. Please enter a number between 1-%d.",
                    MAX_MENU_CHOICE,
                )
                continue

            return choice_int

        except ValueError:
            logger.info(
                "Invalid input. Please enter a number between 1-%d.",
                MAX_MENU_CHOICE,
            )
        except KeyboardInterrupt:
            logger.info("Exiting...")
            raise


def display_main_menu() -> None:
    """Display the main application menu."""
    logger = logging.getLogger(__name__)
    logger.info("\n===== Backup Manager =====")
    logger.info("1. Perform Backup")
    logger.info("2. Encrypt Backup File")
    logger.info("3. Decrypt Backup")
    logger.info("4. Cleanup Old Backups")
    logger.info("5. Extract Backup")
    logger.info("6. Show Last Backup Info")
    logger.info("7. Exit")


def exit_application() -> NoReturn:
    """Exit the application gracefully."""
    logger = logging.getLogger(__name__)
    logger.info("Exiting...")
    sys.exit(0)
