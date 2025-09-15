"""Utility classes for backup operations.

This module provides support components for calculating file sizes
and other utility operations.
"""

import logging
import os
from pathlib import Path

BYTES_IN_KB = 1024.0

class SizeCalculator:
    """Calculate and display total size of backup directories."""

    def __init__(self, directories: list[str], ignore_list: list[str]) -> None:
        """Initialize SizeCalculator.

        Args:
            directories (list[str]): Directories to include in size calculation.
            ignore_list (list[str]): Paths to ignore during calculation.

        """
        self.directories: list[Path] = [Path(os.path.expanduser(d)) for d in directories]
        self.ignore_list: list[Path] = [Path(os.path.expanduser(p)) for p in ignore_list]

    def calculate_total_size(self) -> int:
        """Sum the sizes of all directories, printing a summary.

        Returns:
            int: Total size in bytes.

        """
        print("\n\U0001f4c2 **Backup Size Summary**")
        print("=" * 40)
        total: int = 0
        for directory in self.directories:
            dir_size: int = self._calculate_directory_size(directory)
            total += dir_size
            print(f"\U0001f4c1 {directory}: {self._format_size(dir_size)}")
        print("=" * 40)
        print(f"\u2705 Total Backup Size: {self._format_size(total)}\n")
        return total

    def _calculate_directory_size(self, directory: Path) -> int:
        """Recursively calculate the size of a directory.

        Args:
            directory (Path): Directory to calculate size for.

        Returns:
            int: Total size in bytes of files in the directory.

        """
        total: int = 0
        try:
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                if self._should_ignore(root_path):
                    dirs[:] = []
                    continue
                for file in files:
                    file_path = root_path / file
                    if self._should_ignore(file_path):
                        continue

                    # Handle symlinks properly
                    if file_path.is_symlink():
                        try:
                            # Check if symlink target exists
                            if file_path.exists():
                                # Valid symlink, get size of target
                                total += file_path.stat().st_size
                            else:
                                # Broken symlink, skip silently
                                logging.debug(
                                    "Skipping broken symlink: %s -> %s",
                                    file_path,
                                    file_path.readlink(),
                                )
                        except OSError as e:
                            logging.debug("Error handling symlink %s: %s", file_path, e)
                    else:
                        # Regular file
                        try:
                            total += file_path.stat().st_size
                        except OSError as e:
                            logging.warning(
                                "\u26a0\ufe0f Error accessing file %s: %s", file_path, e
                            )
        except OSError as e:
            logging.warning("\u26a0\ufe0f Error accessing directory %s: %s", directory, e)
        return total

    def _should_ignore(self, path: Path | str) -> bool:
        """Return True if path should be ignored based on ignore list.

        Args:
            path (Path | str): File or directory path to check.
        The check is performed using the normalized path to avoid mismatches
        due to path formatting.

        Args:
            path: The file or directory path to check.

        Returns:
            True if the path starts with any of the ignore paths,
            False otherwise.

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
        size = float(size_in_bytes)

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < BYTES_IN_KB:
                return f"{size:.2f} {unit}"
            size /= BYTES_IN_KB
        return f"{size:.2f} PB"
