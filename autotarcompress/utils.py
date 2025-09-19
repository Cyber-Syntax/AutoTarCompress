"""Utility classes for backup operations.

This module provides support components for calculating file sizes
and other utility operations.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_and_expand_paths(
    paths_to_check: list[str],
) -> tuple[list[str], list[str]]:
    """Validate and expand a list of candidate backup paths.

    Args:
        paths_to_check (list[str]): Candidate paths which may contain
            shell user-expansions such as ``~``.

    Returns:
        tuple[list[str], list[str]]: A tuple ``(existing_paths,
        missing_paths)``. ``existing_paths`` contains expanded absolute
        paths that exist on disk. ``missing_paths`` contains expanded
        absolute paths that do not exist.

    Notes:
        This function does not raise; the caller decides whether to
        abort or proceed. Existing paths are returned as strings to
        simplify insertion into shell commands.

    """
    existing: list[str] = []
    missing: list[str] = []

    # Iterate over the provided list, handling a possible ``None`` by
    # falling back to an empty sequence.
    for candidate in paths_to_check or []:
        if not candidate:
            continue
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            existing.append(str(candidate_path))
        else:
            missing.append(str(candidate_path))

    if missing:
        print(f"Some configured backup paths do not exist: {missing}")
        logger.warning(
            "Some configured backup paths do not exist: %s",
            missing,
        )

    print("Proceeding with existing directories only.")
    logger.info(
        "Proceeding with existing directories only: %s",
        existing,
    )
    return existing, missing


def ensure_backup_folder(folder: str) -> Path:
    """Ensure the backup folder exists, creating it if necessary.

    Args:
        folder (str): Path to the backup folder. May contain shell
            user-expansions such as ``~``.

    Returns:
        pathlib.Path: Expanded ``Path`` pointing to the ensured folder.

    Raises:
        OSError: If the folder cannot be created due to permission or
            filesystem errors.

    """
    path = Path(folder).expanduser()
    if not path.exists():
        print(f"Creating backup folder at {path}")
        logger.info(
            "Creating backup folder at %s",
            path,
        )
        path.mkdir(parents=True, exist_ok=True)
    return path


BYTES_IN_KB = 1024.0


class SizeCalculator:
    """Calculate and display total size of backup directories."""

    def __init__(self, directories: list[str], ignore_list: list[str]) -> None:
        """Initialize SizeCalculator.

        Args:
            directories (list[str]): Directories to include in size
                calculation.
            ignore_list (list[str]): Paths to ignore during
                calculation.

        """
        self.directories: list[Path] = [
            Path(os.path.expanduser(d)) for d in directories
        ]
        self.ignore_list: list[Path] = [
            Path(os.path.expanduser(p)) for p in ignore_list
        ]

    def calculate_total_size(self) -> int:
        """Sum the sizes of all directories, printing a summary.

        Returns:
            int: Total size in bytes.

        """
        print("\n\U0001f4c2 Backup Directories (Exist Only)")
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

        # Return True if the absolute path starts with any of the
        # ignored paths. Normalize both sides for reliable comparison.
        return any(
            str(absolute_path).startswith(str(ignored.absolute()))
            for ignored in self.ignore_list
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
