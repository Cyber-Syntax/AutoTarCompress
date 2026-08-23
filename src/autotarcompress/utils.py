"""Utility functions for backup operations.

This module provides utility functions for calculating file sizes,
validating paths, and other backup-related operations.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


BYTES_IN_KB = 1024.0
BUFFER_SIZE = 65536  # 64KB buffer for efficient file reading


def format_size(size_in_bytes: int) -> str:
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
        logger.warning(
            "Some configured backup paths do not exist: %s",
            missing,
        )

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
        logger.info(
            "Creating backup folder at %s",
            path,
        )
        path.mkdir(parents=True, exist_ok=True)
    return path


def is_pv_available() -> bool:
    """Check if pv (pipe viewer) command is available on the system.

    Returns:
        bool: True if pv is available, False otherwise.

    """
    return shutil.which("pv") is not None


def calculate_sha256(file_path: str | Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file to hash

    Returns:
        Hexadecimal string representation of SHA256 hash

    Raises:
        FileNotFoundError: If the file does not exist
        OSError: If there's an error reading the file
    """
    path = Path(file_path)

    if not path.exists():
        error_msg = f"File not found: {path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    if not path.is_file():
        error_msg = f"Path is not a file: {path}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug("Calculating SHA256 hash for: %s", path)

    sha256_hash = hashlib.sha256()

    try:
        with path.open("rb") as f:
            while chunk := f.read(BUFFER_SIZE):
                sha256_hash.update(chunk)
    except OSError:
        logger.exception("Failed to read file for hashing: %s", path)
        raise
    else:
        hash_value = sha256_hash.hexdigest()
        logger.debug("SHA256 hash calculated: %s", hash_value)
        return hash_value


def verify_hash(file_path: str | Path, expected_hash: str) -> bool:
    """Verify that a file's SHA256 hash matches the expected value.

    Args:
        file_path: Path to the file to verify
        expected_hash: Expected SHA256 hash (hexadecimal string)

    Returns:
        True if hash matches, False otherwise
    """
    try:
        actual_hash = calculate_sha256(file_path)
        matches = actual_hash == expected_hash
    except (FileNotFoundError, ValueError, OSError):
        logger.exception("Hash verification failed")
        return False
    else:
        if matches:
            logger.info(
                "Hash verification passed for: %s", Path(file_path).name
            )
        else:
            logger.warning(
                "Hash mismatch for %s. Expected: %s, Actual: %s",
                Path(file_path).name,
                expected_hash,
                actual_hash,
            )

        return matches
