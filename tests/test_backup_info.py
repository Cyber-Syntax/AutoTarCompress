"""Tests for backup info functionality.

This module contains tests for the InfoCommand and backup info tracking features.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autotarcompress.commands.backup import BackupCommand
from autotarcompress.commands.info import InfoCommand
from autotarcompress.config import BackupConfig


# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing that gets cleaned up afterwards."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir):
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
def mock_backup_info():
    """Create mock backup info data."""
    return {
        "backup_file": "13-09-2025.tar.xz",
        "backup_path": "/home/user/backups/13-09-2025.tar.xz",
        "backup_date": "2025-09-13T10:30:45.123456",
        "backup_size_bytes": 1073741824,  # 1 GB
        "backup_size_human": "1.00 GB",
        "directories_backed_up": ["/home/user/Documents", "/home/user/Pictures"],
    }


class TestBackupInfoSaving:
    """Test backup info saving functionality in BackupCommand."""

    def test_save_backup_info_success(self, test_config, temp_dir):
        """Test successful saving of backup info."""
        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        # Mock datetime.now() to return a fixed time for both places it's used
        fixed_datetime = MagicMock()
        fixed_datetime.isoformat.return_value = "2025-09-13T10:30:45"
        fixed_datetime.strftime.return_value = "13-09-2025"

        with patch("autotarcompress.commands.backup.datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            # Also mock it for the config's current_date property
            with patch("autotarcompress.config.datetime.datetime") as mock_config_datetime:
                mock_config_datetime.now.return_value = fixed_datetime

                # Call the private method directly for testing
                backup_command._save_backup_info(1073741824)  # 1 GB

        # Verify the info file was created
        info_file_path = Path(test_config.backup_folder) / "last-backup-info.json"
        assert info_file_path.exists()

        # Verify the content
        with open(info_file_path, encoding="utf-8") as f:
            saved_info = json.load(f)

        expected_backup_path = Path(test_config.backup_folder) / "13-09-2025.tar.xz"

        assert saved_info["backup_file"] == "13-09-2025.tar.xz"
        assert saved_info["backup_path"] == str(expected_backup_path)
        assert saved_info["backup_date"] == "2025-09-13T10:30:45"
        assert saved_info["backup_size_bytes"] == 1073741824
        assert saved_info["backup_size_human"] == "1.00 GB"
        assert saved_info["directories_backed_up"] == test_config.dirs_to_backup

    def test_save_backup_info_handles_errors(self, test_config, caplog):
        """Test that backup info saving handles errors gracefully."""
        backup_command = BackupCommand(test_config)

        # Create an invalid backup folder path
        test_config.backup_folder = "/invalid/path/that/does/not/exist"

        # This should not raise an exception but should log an error
        backup_command._save_backup_info(1000)

        assert "Failed to save backup info" in caplog.text

    def test_format_size_various_sizes(self, test_config):
        """Test size formatting with various byte sizes."""
        backup_command = BackupCommand(test_config)

        test_cases = [
            (512, "512.00 B"),
            (1024, "1.00 KB"),
            (1048576, "1.00 MB"),  # 1024^2
            (1073741824, "1.00 GB"),  # 1024^3
            (1099511627776, "1.00 TB"),  # 1024^4
        ]

        for size_bytes, expected in test_cases:
            result = backup_command._format_size(size_bytes)
            assert result == expected

    @patch("autotarcompress.commands.backup.subprocess.run")
    @patch("autotarcompress.commands.backup.os.path.exists")
    def test_backup_command_saves_info_on_success(self, mock_exists, mock_subprocess, test_config):
        """Test that backup command saves info when backup succeeds."""
        # Setup mocks
        mock_exists.return_value = False  # Backup file doesn't exist
        mock_subprocess.return_value = MagicMock(returncode=0)  # Success

        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(backup_command, "_save_backup_info") as mock_save_info:
            with patch.object(backup_command, "_calculate_total_size", return_value=1000):
                result = backup_command.execute()

        assert result is True
        mock_save_info.assert_called_once_with(1000)

    @patch("autotarcompress.commands.backup.subprocess.run")
    @patch("autotarcompress.commands.backup.os.path.exists")
    def test_backup_command_no_info_on_failure(self, mock_exists, mock_subprocess, test_config):
        """Test that backup command doesn't save info when backup fails."""
        # Setup mocks
        mock_exists.return_value = False  # Backup file doesn't exist
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(1, "backup failed")  # Failure

        backup_command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(backup_command, "_save_backup_info") as mock_save_info, patch.object(
            backup_command, "_calculate_total_size", return_value=1000
        ):
            result = backup_command.execute()

        assert result is False
        mock_save_info.assert_not_called()


class TestInfoCommand:
    """Test InfoCommand functionality."""

    def test_info_command_displays_existing_backup_info(self, test_config, temp_dir, capsys):
        """Test that InfoCommand displays existing backup information correctly."""
        # Create mock backup info with paths in our temp directory
        mock_backup_info = {
            "backup_file": "13-09-2025.tar.xz",
            "backup_path": os.path.join(temp_dir, "backups", "13-09-2025.tar.xz"),
            "backup_date": "2025-09-13T10:30:45.123456",
            "backup_size_bytes": 1073741824,  # 1 GB
            "backup_size_human": "1.00 GB",
            "directories_backed_up": ["/home/user/Documents", "/home/user/Pictures"],
        }

        # Create the info file
        info_file_path = Path(test_config.backup_folder) / "last-backup-info.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        # Create the backup file to simulate it exists
        backup_file_path = Path(mock_backup_info["backup_path"])
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
        backup_file_path.touch()

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

    def test_info_command_handles_missing_backup_file(self, test_config, mock_backup_info, capsys):
        """Test InfoCommand when backup file doesn't exist."""
        # Create the info file but not the actual backup file
        info_file_path = Path(test_config.backup_folder) / "last-backup-info.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "✗ Backup file not found" in output

    def test_info_command_handles_no_backup_info(self, test_config, capsys):
        """Test InfoCommand when no backup info file exists."""
        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "No backup information found." in output
        assert "This usually means no backups have been created yet." in output

    def test_info_command_handles_corrupted_json(self, test_config, capsys, caplog):
        """Test InfoCommand with corrupted JSON file."""
        # Create a corrupted info file
        info_file_path = Path(test_config.backup_folder) / "last-backup-info.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        info_command = InfoCommand(test_config)
        info_command.execute()

        captured = capsys.readouterr()
        output = captured.out

        assert "No backup information found." in output
        assert "Error reading backup info file" in caplog.text

    def test_load_backup_info_returns_none_for_missing_file(self, test_config):
        """Test _load_backup_info returns None when file doesn't exist."""
        info_command = InfoCommand(test_config)
        result = info_command._load_backup_info()
        assert result is None

    def test_load_backup_info_returns_data_for_valid_file(self, test_config, mock_backup_info):
        """Test _load_backup_info returns data for valid file."""
        # Create the info file
        info_file_path = Path(test_config.backup_folder) / "last-backup-info.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        info_command = InfoCommand(test_config)
        result = info_command._load_backup_info()

        assert result is not None
        assert result["backup_file"] == "13-09-2025.tar.xz"
        assert result["backup_size_bytes"] == 1073741824

    def test_display_backup_info_with_empty_directories(self, test_config, capsys):
        """Test display of backup info with empty directories list."""
        backup_info = {
            "backup_file": "test.tar.xz",
            "backup_path": "/path/to/test.tar.xz",
            "backup_date": "2025-09-13T10:30:45",
            "backup_size_human": "500.00 MB",
            "directories_backed_up": [],
        }

        info_command = InfoCommand(test_config)
        info_command._display_backup_info(backup_info)

        captured = capsys.readouterr()
        output = captured.out

        assert "Directories Backed Up: None" in output


class TestBackupConfigWithoutLastBackup:
    """Test that BackupConfig no longer includes last_backup field."""

    def test_config_does_not_have_last_backup_field(self):
        """Test that BackupConfig doesn't have last_backup field."""
        config = BackupConfig()
        assert not hasattr(config, "last_backup")

    def test_config_save_does_not_include_last_backup(self, test_config, temp_dir):
        """Test that saving config doesn't include last_backup."""
        test_config.config_dir = temp_dir
        test_config.save()

        with open(test_config.config_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "last_backup" not in saved_data
        assert "backup_folder" in saved_data
        assert "dirs_to_backup" in saved_data

    def test_config_load_handles_old_config_with_last_backup(self, temp_dir):
        """Test that loading old config with last_backup field still works."""
        # Create old config format with last_backup
        old_config_data = {
            "backup_folder": "~/Documents/backup-for-cloud/",
            "config_dir": "~/.config/autotarcompress",
            "keep_backup": 1,
            "keep_enc_backup": 1,
            "dirs_to_backup": ["~/Documents"],
            "ignore_list": ["node_modules"],
            "last_backup": "some_old_value",  # This should be ignored
        }

        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(old_config_data, f)

        # Mock the config path to use our test file
        with patch.object(BackupConfig, "config_path", Path(config_path)):
            config = BackupConfig.load()

        # Should load successfully without last_backup field
        assert not hasattr(config, "last_backup")
        # Path will be expanded, so check the expanded version
        expected_docs_path = os.path.expanduser("~/Documents")
        assert config.dirs_to_backup == [expected_docs_path]


if __name__ == "__main__":
    pytest.main([__file__])
