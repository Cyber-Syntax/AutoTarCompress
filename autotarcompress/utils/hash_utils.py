"""Hash utilities for file integrity verification.

Provides SHA256 hash calculation for backup archives, encrypted files,
and decrypted files to ensure data integrity throughout the lifecycle.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BUFFER_SIZE = 65536  # 64KB buffer for efficient file reading


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
