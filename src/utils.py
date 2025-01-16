import os
from typing import List
from .config import Config


def list_backup_files(extension: str = ".tar.xz") -> List[str]:
    """List all backup files with the specified extension in the backup directory"""
    config = Config()
    backup_folder = getattr(config, "backup_folder")

    try:
        files = [
            f
            for f in os.listdir(os.path.expanduser(backup_folder))
            if f.endswith(extension)
        ]
        if not files:
            print("No backup files found.")
            return []
        for i, file in enumerate(files, start=1):
            print(f"{i}. {file}")
        return files
    except Exception as error:
        print(f"Error listing backup files: {type(error).__name__} - {error}")
        return []
