"""Tests for backup info functionality.

This module contains tests for the InfoCommand and backup info tracking features.
"""

import json
import logging
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.commands.backup import BackupCommand
from autotarcompress.commands.info import InfoCommand
from autotarcompress.config import BackupConfig
from autotarcompress.utils.format import format_size


# Fixtures
@pytest.fixture
def temp_dir() -> Generator[str]:
    """Create a temporary directory for testing that gets cleaned up afterwards."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir: str) -> BackupConfig:
    """Create a test configuration for backup manager."""
    config = BackupConfig()
    config.backup_folder = os.path.join(temp_dir, "backups")
    config.config_dir = os.path.join(temp_dir, "config")
    config.dirs_to_backup = [
        os.path.join(temp_dir, "test_data1"),
        os.path.join(temp_dir, "test_data2"),
    ]
    config.ignore_list = ["node_modules", ".venv"]
    os.makedirs(config.backup_folder, exist_ok=True)
    os.makedirs(config.config_dir, exist_ok=True)
    return config


@pytest.fixture
def mock_backup_info() -> dict[str, Any]:
    """Create mock backup info data."""
    return {
        "backup_file": "13-09-2025.tar.xz",
        "backup_path": "/home/user/backups/13-09-2025.tar.xz",
        "backup_date": "2025-09-13T10:30:45.123456",
        "backup_size_bytes": 1073741824,  # 1 GB
        "backup_size_human": "1.00 GB",
        "directories_backed_up": [
            "/home/user/Documents",
            "/home/user/Pictures",
        ],
    }


class TestBackupInfoSaving:
    """Test backup info saving functionality in BackupCommand."""

    def test_save_backup_info_success(
        self, test_config: BackupConfig, temp_dir: str
    ) -> None:
        """Test successful saving of backup metadata."""
        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        # Mock datetime.now() to return a fixed time
        fixed_datetime = MagicMock()
        fixed_datetime.isoformat.return_value = "2025-09-13T10:30:45+00:00"
        fixed_datetime.strftime.return_value = "13-09-2025"

        # Create a test backup file
        expected_backup_path = (
            Path(test_config.backup_folder) / "13-09-2025.tar.zst"
        )
        expected_backup_path.parent.mkdir(parents=True, exist_ok=True)
        expected_backup_path.write_text("test backup content")

        with patch("autotarcompress.metadata.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            # Mock UTC too
            mock_datetime.UTC = MagicMock()

            # Call the new metadata method
            backup_command.manager.save_backup_metadata_with_hash(
                expected_backup_path
            )

        # Verify the metadata file was created
        metadata_path = Path(test_config.config_dir) / "metadata.json"
        assert metadata_path.exists()

        # Verify the content
        with open(metadata_path, encoding="utf-8") as f:
            saved_metadata = json.load(f)

        assert saved_metadata["last_backup_file"] == str(expected_backup_path)
        assert (
            saved_metadata["last_backup_time"] == "2025-09-13T10:30:45+00:00"
        )
        assert saved_metadata["backup_count"] == 1
        assert saved_metadata["metadata_version"] == "2.0"
        # Should have hash with backup filename as key
        assert "13-09-2025.tar.zst" in saved_metadata["file_hashes"]

    def test_save_backup_info_handles_errors(
        self, test_config: BackupConfig, caplog: Any
    ) -> None:
        """Test that backup metadata saving handles errors gracefully."""
        backup_command = BackupCommand(test_config)

        # Use temp dir for config but create an unreadable backup file
        backup_file = Path(test_config.backup_folder) / "test.tar.zst"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_text("test content")

        # Make the file unreadable to trigger hash calculation error
        backup_file.chmod(0o000)

        try:
            # This should not raise an exception but should log an error
            backup_command.manager.save_backup_metadata_with_hash(backup_file)

            assert (
                "Failed to calculate backup hash" in caplog.text
                or "Permission denied" in caplog.text
            )
        finally:
            # Restore permissions for cleanup
            backup_file.chmod(0o644)

    def test_format_size_various_sizes(self) -> None:
        """Test size formatting with various byte sizes."""
        test_cases = [
            (512, "512.00 B"),
            (1024, "1.00 KB"),
            (1048576, "1.00 MB"),  # 1024^2
            (1073741824, "1.00 GB"),  # 1024^3
            (1099511627776, "1.00 TB"),  # 1024^4
        ]

        for size_bytes, expected in test_cases:
            result = format_size(size_bytes)
            assert result == expected

    def test_backup_command_saves_info_on_success(
        self,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command delegates to manager for successful backup."""
        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(
            backup_command.manager, "execute_backup", return_value=True
        ) as mock_execute:
            result = backup_command.execute()

        assert result is True
        mock_execute.assert_called_once()

    def test_backup_command_no_info_on_failure(
        self,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command delegates to manager for failed backup."""
        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(
            backup_command.manager, "execute_backup", return_value=False
        ) as mock_execute:
            result = backup_command.execute()

        assert result is False
        mock_execute.assert_called_once()


class TestInfoCommand:
    """Test InfoCommand functionality."""

    def test_info_command_displays_existing_backup_info(
        self, test_config: BackupConfig, temp_dir: str, capsys: Any
    ) -> None:
        """Test that InfoCommand displays existing backup information correctly."""
        from autotarcompress.logger import setup_application_logging

        # Create mock backup info with paths in our temp directory
        mock_backup_info = {
            "backup_file": "13-09-2025.tar.xz",
            "backup_path": os.path.join(
                temp_dir, "backups", "13-09-2025.tar.xz"
            ),
            "backup_date": "2025-09-13T10:30:45.123456",
            "backup_size_bytes": 1073741824,  # 1 GB
            "backup_size_human": "1.00 GB",
            "directories_backed_up": [
                "/home/user/Documents",
                "/home/user/Pictures",
            ],
        }

        # Create the info file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        # Create the backup file to simulate it exists
        backup_file_path = Path(str(mock_backup_info["backup_path"]))
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
        backup_file_path.touch()

        setup_application_logging()
        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "===== Last Backup Information =====" in output
        assert "13-09-2025.tar.xz" in output
        assert "2025-09-13T10:30:45.123456" in output
        assert "1.00 GB" in output
        assert "/home/user/Documents" in output
        assert "/home/user/Pictures" in output
        assert "✓ Backup file exists" in output

    def test_info_command_handles_missing_backup_file(
        self,
        test_config: BackupConfig,
        mock_backup_info: dict[str, Any],
        capsys: Any,
    ) -> None:
        """Test InfoCommand when backup file doesn't exist."""
        from autotarcompress.logger import setup_application_logging

        # Create the info file but not the actual backup file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        setup_application_logging()
        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "✗ Backup file not found" in output

    def test_info_command_handles_no_backup_info(
        self, test_config: BackupConfig, capsys: Any
    ) -> None:
        """Test InfoCommand when no backup info file exists."""
        from autotarcompress.logger import setup_application_logging

        setup_application_logging()
        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "No backup information found." in output
        assert "This usually means no backups have been created yet." in output

    def test_info_command_handles_corrupted_json(
        self, test_config: BackupConfig, capsys: Any, caplog: Any
    ) -> None:
        """Test InfoCommand with corrupted JSON file."""
        from autotarcompress.logger import setup_application_logging

        # Create a corrupted info file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        setup_application_logging()
        with caplog.at_level(logging.ERROR):
            info_command = InfoCommand(test_config)
            info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "Error reading backup info file" in output


class TestBackupConfigWithoutLastBackup:
    """Test that BackupConfig no longer includes last_backup field."""

    def test_config_does_not_have_last_backup_field(self) -> None:
        """Test that BackupConfig doesn't have last_backup field."""
        config = BackupConfig()
        assert not hasattr(config, "last_backup")

    def test_config_save_does_not_include_last_backup(
        self, test_config: BackupConfig, temp_dir: str
    ) -> None:
        """Test that saving config doesn't include last_backup."""
        import configparser

        test_config.config_dir = temp_dir
        test_config.save()

        config = configparser.ConfigParser()
        config.read(test_config.config_path, encoding="utf-8")
        section = config["DEFAULT"]
        # INI config should not have 'last_backup' key
        assert "last_backup" not in section
        assert "backup_folder" in section
        assert "dirs_to_backup" in section

    def test_config_load_handles_old_config_with_last_backup(
        self, temp_dir: str
    ) -> None:
        """Test that loading old config with last_backup field still works (INI ignores unknowns)."""
        import configparser

        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.conf")

        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "backup_folder": "~/Documents/backup-for-cloud/",
            "config_dir": "~/.config/autotarcompress",
            "keep_backup": "1",
            "keep_enc_backup": "1",
            "dirs_to_backup": "~/Documents",
            "ignore_list": "node_modules",
            # Unknown fields like 'last_backup' are ignored by configparser
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        # Mock the config path to use our test file
        with patch.object(BackupConfig, "config_path", Path(config_path)):
            loaded = BackupConfig.load()

        # Should load successfully without last_backup field
        assert not hasattr(loaded, "last_backup")
        # Path will be expanded, so check the expanded version
        expected_docs_path = os.path.expanduser("~/Documents")
        assert loaded.dirs_to_backup == [expected_docs_path]


if __name__ == "__main__":
    pytest.main([__file__])
