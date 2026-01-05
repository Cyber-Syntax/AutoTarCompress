"""Backup metadata management for AutoTarCompress.

Handles storage and retrieval of backup execution metadata including
last backup time, file path, and backup count.
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
    """

    last_backup_time: str | None = None
    last_backup_file: str | None = None
    backup_count: int = 0
    metadata_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization."""
        return {
            "last_backup_time": self.last_backup_time,
            "last_backup_file": self.last_backup_file,
            "backup_count": self.backup_count,
            "metadata_version": self.metadata_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupMetadata:
        """Create BackupMetadata from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            BackupMetadata instance
        """
        return cls(
            last_backup_time=data.get("last_backup_time"),
            last_backup_file=data.get("last_backup_file"),
            backup_count=data.get("backup_count", 0),
            metadata_version=data.get("metadata_version", "1.0"),
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


def update_backup_metadata(config_dir: Path, backup_file: Path) -> None:
    """Update metadata after a successful backup.

    Args:
        config_dir: Path to the configuration directory
        backup_file: Path to the newly created backup file
    """
    metadata = load_metadata(config_dir)
    metadata.last_backup_time = datetime.now(tz=UTC).isoformat()
    metadata.last_backup_file = str(backup_file)
    metadata.backup_count += 1
    save_metadata(config_dir, metadata)
    logger.info(
        "Updated backup metadata: %s backups total", metadata.backup_count
    )
