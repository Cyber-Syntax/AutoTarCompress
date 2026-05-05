"""Backup metadata management for AutoTarCompress.

Handles storage and retrieval of backup execution metadata including
last backup time, file path, backup count, and file integrity hashes.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Metadata about backup execution history.

    Attributes:
        last_backup_time: ISO format timestamp of most recent backup
        last_backup_file: Full path to the most recently created backup
        backup_count: Total number of backups created
        metadata_version: Schema version for future compatibility
        file_hashes: Dictionary of SHA256 hashes for integrity verification
            Keys: backup_archive, encrypted_file, decrypted_file
    """

    last_backup_time: str | None = None
    last_backup_file: str | None = None
    backup_count: int = 0
    metadata_version: str = "2.0"
    file_hashes: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Initialize file_hashes dictionary if None."""
        if self.file_hashes is None:
            self.file_hashes = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization."""
        return {
            "last_backup_time": self.last_backup_time,
            "last_backup_file": self.last_backup_file,
            "backup_count": self.backup_count,
            "metadata_version": self.metadata_version,
            "file_hashes": self.file_hashes or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupMetadata:
        """Create BackupMetadata from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            BackupMetadata instance

        Note:
            Supports both v1.0 and v2.0 metadata formats.
            v1.0 files will be migrated to v2.0 automatically.
        """
        # Always use v2.0 for new instances (migrate from v1.0)
        file_hashes = data.get("file_hashes", {})

        return cls(
            last_backup_time=data.get("last_backup_time"),
            last_backup_file=data.get("last_backup_file"),
            backup_count=data.get("backup_count", 0),
            metadata_version="2.0",
            file_hashes=file_hashes or {},
        )


def get_metadata_path(config_dir: Path) -> Path:
    """Get the path to the metadata.json file.

    Args:
        config_dir: Path to the configuration directory

    Returns:
        Path to metadata.json file
    """
    return Path(config_dir).expanduser() / "metadata.json"


def load_metadata(config_dir: Path) -> BackupMetadata:
    """Load backup metadata from metadata.json.

    Args:
        config_dir: Path to the configuration directory

    Returns:
        BackupMetadata instance with loaded or default data
    """
    metadata_path = get_metadata_path(config_dir)

    if not metadata_path.exists():
        logger.debug(
            "No metadata file found at %s, returning empty metadata",
            metadata_path,
        )
        return BackupMetadata()

    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return BackupMetadata.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Failed to load metadata from %s: %s. Returning empty metadata.",
            metadata_path,
            e,
        )
        return BackupMetadata()


@contextlib.contextmanager
def _file_lock(path: Path):
    """Acquire an exclusive cross-process file lock.

    Creates a separate .lock file alongside the target file.
    The lock file is cleaned up when the lock is released.

    Uses fcntl.flock which is Unix-only (Linux/macOS).

    Args:
        path: Path to the file you want to protect.  The lock file
              will be created at <path>.lock.

    Yields:
        Nothing — just provides the lock as a context manager.

    Example:
        with _file_lock(metadata_path):
            # only one process runs this block at a time
            data = read_something()
            write_something(data)
    """
    lock_path = str(path) + ".lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)

    # clean up the lock file after releasing the lock.
    # missing_ok=True means no error if another process already removed it.
    try:
        Path(lock_path).unlink(missing_ok=True)
    except OSError:
        # Non-fatal — the lock has already been released above.
        logger.debug("Could not remove lock file: %s", lock_path)


def _write_metadata(metadata_path: Path, metadata: BackupMetadata) -> None:
    """Write metadata to disk using a temp file + atomic rename.

    This function does NOT acquire the file lock.
    The caller is responsible for holding the lock before calling this.

    Using a temp file + os.replace() means that if the process crashes
    mid-write, the old metadata.json is never corrupted — the rename
    only happens after the write is fully complete.

    Args:
        metadata_path: Full path to metadata.json
        metadata: The BackupMetadata object to write
    """
    tmp_path = metadata_path.with_suffix(".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, indent=2)

    # os.replace is atomic on Linux — readers always see a complete file
    os.replace(tmp_path, metadata_path)


def save_metadata(config_dir: Path, metadata: BackupMetadata) -> None:
    """Save backup metadata to metadata.json (process-safe).

    Acquires an exclusive file lock, then writes atomically.
    Safe to call from multiple processes simultaneously.

    Args:
        config_dir: Path to the configuration directory
        metadata: BackupMetadata object to save
    """
    metadata_path = get_metadata_path(config_dir)
    Path(config_dir).expanduser().mkdir(parents=True, exist_ok=True)

    try:
        with _file_lock(metadata_path):  # ← acquires lock once
            _write_metadata(metadata_path, metadata)  # ← no second lock

        logger.debug("Saved metadata to %s", metadata_path)

    except OSError:
        logger.exception("Failed to save metadata to %s", metadata_path)


def _update_metadata(config_dir: Path, updater) -> None:
    """Atomic metadata update (read-modify-write under a single lock).

    Acquires the lock once, reads the current metadata, applies the
    updater function, then writes the result — all under the same lock.
    This prevents two processes from overwriting each other's changes.

    Args:
        config_dir: Path to the configuration directory
        updater: Callable that receives a BackupMetadata object and
                 modifies it in-place (no return value needed)
    """
    metadata_path = get_metadata_path(config_dir)
    Path(config_dir).expanduser().mkdir(parents=True, exist_ok=True)

    with _file_lock(metadata_path):  # ← lock acquired ONCE here
        metadata = load_metadata(config_dir)
        updater(metadata)
        _write_metadata(metadata_path, metadata)  # ← no second lock


def update_backup_metadata(
    config_dir: Path,
    backup_file: Path,
    backup_hash: str | None = None,
) -> None:
    """Update metadata with backup file information.

    Args:
        config_dir: Path to the configuration directory
        backup_file: Path to the backup file
        backup_hash: SHA256 hash of the backup file (optional)
    """

    def _apply(metadata: BackupMetadata) -> None:
        metadata.last_backup_time = datetime.now(tz=UTC).isoformat()
        metadata.last_backup_file = str(backup_file)
        metadata.backup_count += 1

        if metadata.file_hashes is None:
            metadata.file_hashes = {}

        if backup_hash:
            filename = Path(backup_file).name
            metadata.file_hashes[filename] = backup_hash
            logger.debug("Stored hash for %s: %s", filename, backup_hash[:16])

    _update_metadata(config_dir, _apply)

    logger.info("Updated backup metadata safely")


def update_encrypted_hash(
    config_dir: Path, encrypted_file: Path, encrypted_hash: str
) -> None:
    """Update metadata with encrypted file hash.

    Args:
        config_dir: Path to the configuration directory
        encrypted_file: Path to the encrypted file
        encrypted_hash: SHA256 hash of the encrypted file
    """

    def _apply(metadata: BackupMetadata) -> None:
        if metadata.file_hashes is None:
            metadata.file_hashes = {}

        filename = Path(encrypted_file).name
        metadata.file_hashes[filename] = encrypted_hash
        logger.debug("Stored hash for %s: %s", filename, encrypted_hash[:16])

    _update_metadata(config_dir, _apply)


def update_decrypted_hash(
    config_dir: Path, decrypted_file: Path, decrypted_hash: str
) -> None:
    """Update metadata with decrypted file hash.

    Args:
        config_dir: Path to the configuration directory
        decrypted_file: Path to the decrypted file
        decrypted_hash: SHA256 hash of the decrypted file
    """

    def _apply(metadata: BackupMetadata) -> None:
        if metadata.file_hashes is None:
            metadata.file_hashes = {}

        filename = Path(decrypted_file).name
        metadata.file_hashes[filename] = decrypted_hash
        logger.debug("Stored hash for %s: %s", filename, decrypted_hash[:16])

    _update_metadata(config_dir, _apply)


def get_file_hash(config_dir: Path, filename: str) -> str | None:
    """Get the stored hash of a specific file.

    Args:
        config_dir: Path to the configuration directory
        filename: Name of the file to get hash for

    Returns:
        SHA256 hash of the file, or None if not available
    """
    metadata = load_metadata(config_dir)

    if metadata.file_hashes is None:
        return None

    return metadata.file_hashes.get(filename)


def get_backup_archive_hash(config_dir: Path, backup_file: Path) -> str | None:
    """Get the stored hash of the backup archive.

    Args:
        config_dir: Path to the configuration directory
        backup_file: Path to the backup file

    Returns:
        SHA256 hash of backup archive, or None if not available
    """
    filename = Path(backup_file).name
    return get_file_hash(config_dir, filename)
