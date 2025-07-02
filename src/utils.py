"""Utility classes for backup operations.

This module provides support components for calculating file sizes
and other utility operations.
"""

import logging
import os
from pathlib import Path
from typing import List, Union


class SizeCalculator:
    """Calculate total size of directories to be backed up and display results."""

    def __init__(self, directories: List[str], ignore_list: List[str]):
        # Expand user paths (e.g., ~) and normalize as Path objects
        self.directories = [Path(os.path.expanduser(d)) for d in directories]
        self.ignore_list = [Path(os.path.expanduser(p)) for p in ignore_list]

    def calculate_total_size(self) -> int:
        """Iterate over all directories and sum up their sizes.

        Returns:
            Total size in bytes.

        """
        print("\n📂 **Backup Size Summary**")
        print("=" * 40)

        total = 0
        for directory in self.directories:
            dir_size = self._calculate_directory_size(directory)
            total += dir_size
            print(f"📁 {directory}: {self._format_size(dir_size)}")

        print("=" * 40)
        print(f"✅ Total Backup Size: {self._format_size(total)}\n")
        return total

    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate the size of a directory recursively.

        Args:
            directory: The path of the directory to calculate size.

        Returns:
            The total size in bytes of files within the directory.

        """
        total = 0
        try:
            # Walk the directory tree
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                if self._should_ignore(root_path):
                    dirs[:] = []  # Prevent descending into subdirectories.
                    continue

                for file in files:
                    file_path = root_path / file
                    if self._should_ignore(file_path):
                        continue
                    try:
                        total += file_path.stat().st_size
                    except OSError as e:
                        logging.warning(f"⚠️ Error accessing file {file_path}: {e}")

        except Exception as e:
            logging.warning(f"⚠️ Error accessing directory {directory}: {e}")

        return total

    def _should_ignore(self, path: Union[Path, str]) -> bool:
        """Determine whether the given path should be ignored based on the ignore list.

        The check is performed using the normalized path to avoid mismatches due to path formatting.

        Args:
            path: The file or directory path to check.

        Returns:
            True if the path starts with any of the ignore paths, False otherwise.

        """
        if isinstance(path, str):
            path = Path(path)

        # Convert to absolute path for consistent comparison
        absolute_path = path.absolute()

        return any(
            str(absolute_path).startswith(str(ignored.absolute())) for ignored in self.ignore_list
        )

    def _format_size(self, size_in_bytes: int) -> str:
        """Convert a size in bytes to a human-readable format (KB, MB, GB).

        Args:
            size_in_bytes: The size in bytes.

        Returns:
            The formatted size string.

        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"
