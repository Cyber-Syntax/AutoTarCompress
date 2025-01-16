import os
from typing import List
from .config import Config
import logging


def list_backup_files(extension: str) -> List[str]:
    """List all backup files with the specified extension in the backup directory."""

    config = Config()
    backup_folder = os.path.expanduser(config.backup_folder)

    try:
        files = [f for f in os.listdir(backup_folder) if f.endswith(extension)]
        if not files:
            print(f"No files with extension '{extension}' found.")
            return []
        for i, file in enumerate(files, start=1):
            print(f"{i}. {file}")
        return files
    except Exception as error:
        print(f"Error listing backup files: {type(error).__name__} - {error}")
        return []


def select_file(extension: str) -> str:
    """
    Prompt the user to select a file with the given extension.

    Args:
        extension (str): The file extension to filter files.

    Returns:
        str: The full path of the selected file.
    """
    files = list_backup_files(extension=extension)
    if not files:
        logging.error(f"No files available with extension '{extension}'.")
        raise ValueError(f"No files found with extension '{extension}'.")

    print("=====================================")

    while True:
        try:
            choice = int(input("Enter your choice (number): "))
            if 1 <= choice <= len(files):
                selected_file = os.path.join(
                    os.path.expanduser(Config().backup_folder), files[choice - 1]
                )
                logging.info(f"Selected file: {selected_file}")
                return selected_file
            else:
                logging.warning("Invalid choice. Try again.")
        except ValueError:
            logging.warning("Invalid input. Please enter a valid number.")
        except KeyboardInterrupt:
            logging.info("Operation cancelled by user.")
            raise
