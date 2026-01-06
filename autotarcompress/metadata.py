"""Backup metadata management for AutoTarCompress.

Handles storage and retrieval of backup execution metadata including
last backup time, file path, backup count, and file integrity hashes.
"""

from __future__ import annotations

import json
import logging
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
            file_hashes=file_hashes if file_hashes else {},
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


def save_metadata(config_dir: Path, metadata: BackupMetadata) -> None:
    """Save backup metadata to metadata.json.

    Args:
        config_dir: Path to the configuration directory
        metadata: BackupMetadata instance to save
    """
    metadata_path = get_metadata_path(config_dir)

    # Ensure config directory exists
    Path(config_dir).expanduser().mkdir(parents=True, exist_ok=True)

    try:
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        logger.debug("Saved metadata to %s", metadata_path)
    except OSError:
        logger.exception("Failed to save metadata to %s", metadata_path)


def update_backup_metadata(
    config_dir: Path,
    backup_file: Path,
    backup_hash: str | None = None,
) -> None:
    """Update metadata after a successful backup.

    Args:
        config_dir: Path to the configuration directory
        backup_file: Path to the newly created backup file
        backup_hash: SHA256 hash of the backup archive (optional)
    """
    metadata = load_metadata(config_dir)
    metadata.last_backup_time = datetime.now(tz=UTC).isoformat()
    metadata.last_backup_file = str(backup_file)
    metadata.backup_count += 1

    if backup_hash:
        if metadata.file_hashes is None:
            metadata.file_hashes = {}
        # Use the backup filename as the key
        filename = Path(backup_file).name
        metadata.file_hashes[filename] = backup_hash
        logger.debug("Stored hash for %s: %s", filename, backup_hash[:16])

    save_metadata(config_dir, metadata)
    logger.info(
        "Updated backup metadata: %s backups total", metadata.backup_count
    )


def update_encrypted_hash(
    config_dir: Path, encrypted_file: Path, encrypted_hash: str
) -> None:
    """Update metadata with encrypted file hash.

    Args:
        config_dir: Path to the configuration directory
        encrypted_file: Path to the encrypted file
        encrypted_hash: SHA256 hash of the encrypted file
    """
    metadata = load_metadata(config_dir)

    if metadata.file_hashes is None:
        metadata.file_hashes = {}

    # Use the encrypted filename as the key
    filename = Path(encrypted_file).name
    metadata.file_hashes[filename] = encrypted_hash
    save_metadata(config_dir, metadata)
    logger.debug("Stored hash for %s: %s", filename, encrypted_hash[:16])


def update_decrypted_hash(
    config_dir: Path, decrypted_file: Path, decrypted_hash: str
) -> None:
    """Update metadata with decrypted file hash.

    Args:
        config_dir: Path to the configuration directory
        decrypted_file: Path to the decrypted file
        decrypted_hash: SHA256 hash of the decrypted file
    """
    metadata = load_metadata(config_dir)

    if metadata.file_hashes is None:
        metadata.file_hashes = {}

    # Use the decrypted filename as the key
    filename = Path(decrypted_file).name
    metadata.file_hashes[filename] = decrypted_hash
    save_metadata(config_dir, metadata)
    logger.debug("Stored hash for %s: %s", filename, decrypted_hash[:16])


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
