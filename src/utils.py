"""Utility classes for backup operations.

This module provides support components for calculating file sizes
and other utility operations.
"""

import logging
import os
from typing import List


class SizeCalculator:
    """Calculate total size of directories to be backed up and display results."""

    def __init__(self, directories: List[str], ignore_list: List[str]):
        # Expand user paths (e.g., ~) and normalize the directories and ignore list.
        self.directories = [os.path.expanduser(d) for d in directories]
        self.ignore_list = [os.path.expanduser(p) for p in ignore_list]

    def calculate_total_size(self) -> int:
        """
        Iterate over all directories and sum up their sizes.

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

    def _calculate_directory_size(self, directory: str) -> int:
        """
        Calculate the size of a directory recursively.

        Args:
            directory (str): The path of the directory to calculate size.

        Returns:
            The total size in bytes of files within the directory.
        """
        total = 0
        try:
            # Walk the directory tree.
            for root, dirs, files in os.walk(directory):
                if self._should_ignore(root):
                    dirs[:] = []  # Prevent descending into subdirectories.
                    continue

                for f in files:
                    file_path = os.path.join(root, f)
                    if self._should_ignore(file_path):
                        continue
                    try:
                        total += os.path.getsize(file_path)
                    except OSError as e:
                        logging.warning(f"⚠️ Error accessing file {file_path}: {e}")
        except Exception as e:
            logging.warning(f"⚠️ Error accessing directory {directory}: {e}")
        return total

    def _should_ignore(self, path: str) -> bool:
        """
        Determine whether the given path should be ignored based on the ignore list.

        The check is performed using the normalized path to avoid mismatches due to path formatting.

        Args:
            path (str): The file or directory path to check.

        Returns:
            True if the path starts with any of the ignore paths, False otherwise.
        """
        # Normalize the path for a consistent comparison.
        normalized_path = os.path.normpath(path)
        return any(
            normalized_path.startswith(os.path.normpath(ignored)) for ignored in self.ignore_list
        )

    def _format_size(self, size_in_bytes: int) -> str:
        """
        Convert a size in bytes to a human-readable format (KB, MB, GB).

        Args:
            size_in_bytes (int): The size in bytes.

        Returns:
            str: The formatted size string.
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"
