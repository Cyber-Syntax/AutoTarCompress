"""Utility classes for backup operations.

This module provides support components for calculating file sizes
and other utility operations.
"""

import logging
import shutil
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
