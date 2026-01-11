"""Utility to calculate and display total size of backup directories."""

import fnmatch
import logging
import os
from pathlib import Path

from .format import format_size

logger = logging.getLogger(__name__)


class SizeCalculator:
    """Calculate and display total size of backup directories."""

    def __init__(self, directories: list[str], ignore_list: list[str]) -> None:
        """Initialize SizeCalculator.

        Args:
            directories (list[str]): Directories to include in size
                calculation.
            ignore_list (list[str]): Patterns or paths to ignore during
                calculation. Can be absolute paths or patterns like
                'node_modules' or '*.pyc'.

        """
        self.directories: list[Path] = [
            Path(Path(d).expanduser()) for d in directories
        ]
        # Keep as strings to support both patterns and absolute paths
        self.ignore_list: list[str] = ignore_list

    def calculate_total_size(self) -> int:
        """Sum the sizes of all directories, printing a summary.

        Returns:
            int: Total size in bytes.

        """
        logger.info("\n\U0001f4c2 Backup Directories (Exist Only)")
        logger.info("=" * 40)
        total: int = 0
        for directory in self.directories:
            dir_size: int = self._calculate_directory_size(directory)
            total += dir_size
            logger.info("\U0001f4c1 %s: %s", directory, format_size(dir_size))
        logger.info("=" * 40)
        logger.info("\u2705 Total Backup Size: %s", format_size(total))
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
                                logger.debug(
                                    "Skipping broken symlink: %s -> %s",
                                    file_path,
                                    file_path.readlink(),
                                )
                        except OSError as e:
                            logger.debug(
                                "Error handling symlink %s: %s",
                                file_path,
                                e,
                            )
                    else:
                        # Regular file
                        try:
                            total += file_path.stat().st_size
                        except OSError as e:
                            logger.warning(
                                "\u26a0\ufe0f Error accessing file %s: %s",
                                file_path,
                                e,
                            )
        except OSError as e:
            logger.warning(
                "\u26a0\ufe0f Error accessing directory %s: %s",
                directory,
                e,
            )
        return total

    def _should_ignore(self, path: Path | str) -> bool:
        """Return True if path should be ignored based on ignore list.

        Supports both:
        - Absolute paths (e.g., /home/user/.stversions)
        - Patterns (e.g., node_modules, *.pyc, __pycache__)

        Args:
            path (Path | str): File or directory path to check.

        Returns:
            True if the path matches any ignore pattern or starts with
            any absolute ignore path, False otherwise.

        """
        if isinstance(path, str):
            path = Path(path)

        # Convert to absolute path for consistent comparison
        absolute_path = path.absolute()
        absolute_str = str(absolute_path)

        for pattern in self.ignore_list:
            # If pattern is an absolute path, check if path starts with it
            if pattern.startswith(("/", "~")):
                # Absolute path comparison
                pattern_path = Path(pattern).expanduser().absolute()
                if absolute_str.startswith(str(pattern_path)):
                    return True
            else:
                # Pattern matching - check if any path component matches
                # Split path into parts and check each part
                path_parts = absolute_path.parts
                for part in path_parts:
                    if fnmatch.fnmatch(part, pattern):
                        return True
                # Also check full filename for patterns like *.pyc
                if fnmatch.fnmatch(absolute_path.name, pattern):
                    return True

        return False
