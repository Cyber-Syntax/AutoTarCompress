"""User interface utilities for AutoTarCompress.

This module provides user interaction functions following the Single
Responsibility Principle. It handles file selection and user input validation.
"""

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

    print("\nAvailable files:")
    for idx, file in enumerate(files, start=1):
        print(f"{idx}. {file}")

    while True:
        try:
            choice_input = input("Enter your choice: ").strip()
            if not choice_input:
                print("Please enter a number.")
                continue

            choice: int = int(choice_input) - 1
            if choice < 0 or choice >= len(files):
                print(f"Please enter a number between 1 and {len(files)}.")
                continue

            return os.path.join(backup_folder, files[choice])

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            raise


def get_menu_choice() -> int:
    """Get and validate user menu choice.

    Returns:
        int: Valid menu choice (1-7).

    Raises:
        KeyboardInterrupt: If user cancels with Ctrl+C.

    """
    while True:
        try:
            choice: str = input("Enter your choice (1-7): ").strip()
            if not choice:
                print("Please enter a number.")
                continue

            choice_int: int = int(choice)
            if choice_int < 1 or choice_int > MAX_MENU_CHOICE:
                print(f"Invalid input. Please enter a number between 1-{MAX_MENU_CHOICE}.")
                continue

            return choice_int

        except ValueError:
            print(f"Invalid input. Please enter a number between 1-{MAX_MENU_CHOICE}.")
        except KeyboardInterrupt:
            print("\nExiting...")
            raise


def display_main_menu() -> None:
    """Display the main application menu."""
    print("\n===== Backup Manager =====")
    print("1. Perform Backup")
    print("2. Encrypt Backup File")
    print("3. Decrypt Backup")
    print("4. Cleanup Old Backups")
    print("5. Extract Backup")
    print("6. Show Last Backup Info")
    print("7. Exit")


def exit_application() -> NoReturn:
    """Exit the application gracefully."""
    print("Exiting...")
    sys.exit(0)
