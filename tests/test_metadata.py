"""Tests for metadata module with SHA256 hash support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotarcompress.metadata import (
    BackupMetadata,
    get_file_hash,
    get_metadata_path,
    load_metadata,
    save_metadata,
    update_backup_metadata,
    update_decrypted_hash,
    update_encrypted_hash,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestBackupMetadata:
    """Tests for BackupMetadata dataclass."""

    def test_default_initialization(self) -> None:
        """Test BackupMetadata with default values."""
        metadata = BackupMetadata()

        assert metadata.last_backup_time is None
        assert metadata.last_backup_file is None
        assert metadata.backup_count == 0
        assert metadata.metadata_version == "2.0"
        assert metadata.file_hashes == {}

    def test_initialization_with_values(self) -> None:
        """Test BackupMetadata with custom values."""
        hashes = {
            "backup_archive": "abc123",
            "encrypted_file": "def456",
        }

        metadata = BackupMetadata(
            last_backup_time="2026-01-06T12:00:00+00:00",
            last_backup_file="/path/to/backup.tar.zst",
            backup_count=5,
            file_hashes=hashes,
        )

        assert metadata.last_backup_time == "2026-01-06T12:00:00+00:00"
        assert metadata.last_backup_file == "/path/to/backup.tar.zst"
        assert metadata.backup_count == 5
        assert metadata.metadata_version == "2.0"
        assert metadata.file_hashes == hashes

    def test_to_dict(self) -> None:
        """Test converting BackupMetadata to dictionary."""
        metadata = BackupMetadata(
            last_backup_time="2026-01-06T12:00:00+00:00",
            last_backup_file="/path/to/backup.tar.zst",
            backup_count=3,
            file_hashes={"backup_archive": "abc123"},
        )

        result = metadata.to_dict()

        assert result["last_backup_time"] == "2026-01-06T12:00:00+00:00"
        assert result["last_backup_file"] == "/path/to/backup.tar.zst"
        assert result["backup_count"] == 3
        assert result["metadata_version"] == "2.0"
        assert result["file_hashes"] == {"backup_archive": "abc123"}

    def test_from_dict_v2(self) -> None:
        """Test creating BackupMetadata from v2.0 dictionary."""
        data = {
            "last_backup_time": "2026-01-06T12:00:00+00:00",
            "last_backup_file": "/path/to/backup.tar.zst",
            "backup_count": 7,
            "metadata_version": "2.0",
            "file_hashes": {
                "backup_archive": "abc123",
                "encrypted_file": "def456",
            },
        }

        metadata = BackupMetadata.from_dict(data)

        assert metadata.last_backup_time == "2026-01-06T12:00:00+00:00"
        assert metadata.last_backup_file == "/path/to/backup.tar.zst"
        assert metadata.backup_count == 7
        assert metadata.metadata_version == "2.0"
        assert metadata.file_hashes == {
            "backup_archive": "abc123",
            "encrypted_file": "def456",
        }

    def test_from_dict_v1_backwards_compat(self) -> None:
        """Test loading v1.0 metadata (automatic migration to v2.0)."""
        data = {
            "last_backup_time": "2026-01-06T12:00:00+00:00",
            "last_backup_file": "/path/to/backup.tar.xz",
            "backup_count": 5,
            "metadata_version": "1.0",
        }

        metadata = BackupMetadata.from_dict(data)

        assert metadata.last_backup_time == "2026-01-06T12:00:00+00:00"
        assert metadata.last_backup_file == "/path/to/backup.tar.xz"
        assert metadata.backup_count == 5
        # v1.0 files are automatically migrated to v2.0
        assert metadata.metadata_version == "2.0"
        # File hashes should be empty for migrated v1.0
        assert metadata.file_hashes == {}


class TestMetadataFileOperations:
    """Tests for metadata file operations."""

    def test_get_metadata_path(self, tmp_path: Path) -> None:
        """Test getting metadata file path."""
        config_dir = tmp_path / "config"

        path = get_metadata_path(config_dir)

        assert path == config_dir / "metadata.json"

    def test_load_metadata_nonexistent(self, tmp_path: Path) -> None:
        """Test loading metadata when file doesn't exist."""
        config_dir = tmp_path / "config"

        metadata = load_metadata(config_dir)

        assert isinstance(metadata, BackupMetadata)
        assert metadata.backup_count == 0
        assert metadata.metadata_version == "2.0"
        assert metadata.file_hashes == {}

    def test_save_and_load_metadata(self, tmp_path: Path) -> None:
        """Test saving and loading metadata."""
        config_dir = tmp_path / "config"

        metadata = BackupMetadata(
            last_backup_time="2026-01-06T12:00:00+00:00",
            last_backup_file="/path/to/backup.tar.zst",
            backup_count=10,
            file_hashes={"backup_archive": "abc123"},
        )

        save_metadata(config_dir, metadata)

        loaded = load_metadata(config_dir)

        assert loaded.last_backup_time == metadata.last_backup_time
        assert loaded.last_backup_file == metadata.last_backup_file
        assert loaded.backup_count == metadata.backup_count
        assert loaded.metadata_version == "2.0"
        assert loaded.file_hashes == {"backup_archive": "abc123"}

    def test_save_metadata_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_metadata creates config directory if needed."""
        config_dir = tmp_path / "new_config"

        metadata = BackupMetadata(backup_count=1)
        save_metadata(config_dir, metadata)

        assert config_dir.exists()
        assert (config_dir / "metadata.json").exists()

    def test_load_corrupted_metadata(self, tmp_path: Path) -> None:
        """Test loading corrupted metadata file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Write invalid JSON
        metadata_file = config_dir / "metadata.json"
        metadata_file.write_text("not valid json")

        metadata = load_metadata(config_dir)

        # Should return default metadata
        assert isinstance(metadata, BackupMetadata)
        assert metadata.backup_count == 0


class TestMetadataUpdateFunctions:
    """Tests for metadata update functions."""

    def test_update_backup_metadata_without_hash(self, tmp_path: Path) -> None:
        """Test updating backup metadata without hash."""
        config_dir = tmp_path / "config"
        backup_file = tmp_path / "backup.tar.zst"

        update_backup_metadata(config_dir, backup_file, None)

        metadata = load_metadata(config_dir)

        assert metadata.backup_count == 1
        assert metadata.last_backup_file == str(backup_file)
        assert metadata.last_backup_time is not None
        # Hash should not be set (no filename key in file_hashes)
        assert metadata.file_hashes == {}

    def test_update_backup_metadata_with_hash(self, tmp_path: Path) -> None:
        """Test updating backup metadata with hash."""
        config_dir = tmp_path / "config"
        backup_file = tmp_path / "backup.tar.zst"
        test_hash = "a" * 64

        update_backup_metadata(config_dir, backup_file, test_hash)

        metadata = load_metadata(config_dir)

        assert metadata.backup_count == 1
        assert metadata.last_backup_file == str(backup_file)
        assert metadata.file_hashes["backup.tar.zst"] == test_hash

    def test_update_backup_metadata_increments_count(
        self, tmp_path: Path
    ) -> None:
        """Test that backup count increments correctly."""
        config_dir = tmp_path / "config"
        backup_file = tmp_path / "backup.tar.zst"

        # First backup
        update_backup_metadata(config_dir, backup_file, "hash1")
        metadata = load_metadata(config_dir)
        assert metadata.backup_count == 1

        # Second backup
        update_backup_metadata(config_dir, backup_file, "hash2")
        metadata = load_metadata(config_dir)
        assert metadata.backup_count == 2

    def test_update_encrypted_hash(self, tmp_path: Path) -> None:
        """Test updating encrypted file hash."""
        config_dir = tmp_path / "config"
        encrypted_file = tmp_path / "backup.tar.zst.enc"
        test_hash = "b" * 64

        update_encrypted_hash(config_dir, encrypted_file, test_hash)

        metadata = load_metadata(config_dir)
        assert metadata.file_hashes["backup.tar.zst.enc"] == test_hash

    def test_update_decrypted_hash(self, tmp_path: Path) -> None:
        """Test updating decrypted file hash."""
        config_dir = tmp_path / "config"
        decrypted_file = tmp_path / "backup-decrypted"
        test_hash = "c" * 64

        update_decrypted_hash(config_dir, decrypted_file, test_hash)

        metadata = load_metadata(config_dir)
        assert metadata.file_hashes["backup-decrypted"] == test_hash

    def test_get_file_hash_exists(self, tmp_path: Path) -> None:
        """Test getting file hash when it exists."""
        config_dir = tmp_path / "config"
        test_hash = "d" * 64

        # Set up metadata with hash
        metadata = BackupMetadata(file_hashes={"backup.tar.zst": test_hash})
        save_metadata(config_dir, metadata)

        result = get_file_hash(config_dir, "backup.tar.zst")

        assert result == test_hash

    def test_get_file_hash_missing(self, tmp_path: Path) -> None:
        """Test getting file hash when not available."""
        config_dir = tmp_path / "config"

        result = get_file_hash(config_dir, "nonexistent.tar.zst")

        assert result is None

    def test_multiple_hash_updates(self, tmp_path: Path) -> None:
        """Test updating multiple hashes sequentially."""
        config_dir = tmp_path / "config"
        backup_file = tmp_path / "backup.tar.zst"
        encrypted_file = tmp_path / "backup.tar.zst.enc"
        decrypted_file = tmp_path / "backup-decrypted"

        # Update backup with hash
        update_backup_metadata(config_dir, backup_file, "hash_backup")

        # Update encrypted hash
        update_encrypted_hash(config_dir, encrypted_file, "hash_encrypted")

        # Update decrypted hash
        update_decrypted_hash(config_dir, decrypted_file, "hash_decrypted")

        # Load and verify all hashes
        metadata = load_metadata(config_dir)
        assert metadata.file_hashes["backup.tar.zst"] == "hash_backup"
        assert metadata.file_hashes["backup.tar.zst.enc"] == "hash_encrypted"
        assert metadata.file_hashes["backup-decrypted"] == "hash_decrypted"
