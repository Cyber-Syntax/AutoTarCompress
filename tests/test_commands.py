"""Tests for command classes and their execution.

This module tests backup, cleanup, encrypt, decrypt, extract, and info commands.
"""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.commands import (
    BackupCommand,
    CleanupCommand,
    EncryptCommand,
    InfoCommand,
)
from autotarcompress.config import BackupConfig


class TestBackupCommand:
    """Test BackupCommand functionality."""

    def test_backup_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that BackupCommand initializes correctly."""
        command = BackupCommand(test_config)
        assert command.config == test_config

    def test_backup_command_no_directories(
        self, test_config: BackupConfig
    ) -> None:
        """Test backup command fails when no directories are configured."""
        test_config.dirs_to_backup = []
        command = BackupCommand(test_config)

        result = command.execute()
        assert result is False

    def test_calculate_total_size(
        self, test_config: BackupConfig, test_data_dir: str
    ) -> None:
        """Test that backup command calculates total size correctly."""
        test_config.dirs_to_backup = [test_data_dir]
        command = BackupCommand(test_config)

        size = command._calculate_total_size()
        assert size > 0  # Should have some size from test files

    def test_format_size_conversion(self, test_config: BackupConfig) -> None:
        """Test size formatting with various byte sizes."""
        command = BackupCommand(test_config)

        test_cases = [
            (512, "512.00 B"),
            (1024, "1.00 KB"),
            (1048576, "1.00 MB"),  # 1024^2
            (1073741824, "1.00 GB"),  # 1024^3
            (1099511627776, "1.00 TB"),  # 1024^4
        ]

        for size_bytes, expected in test_cases:
            result = command._format_size(size_bytes)
            assert result == expected

    @patch("autotarcompress.commands.backup.validate_and_expand_paths")
    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_backup_success_saves_info(
        self,
        mock_path_exists: MagicMock,
        mock_tarfile: MagicMock,
        mock_validate: MagicMock,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command saves info when backup succeeds."""
        # Setup mocks
        mock_path_exists.return_value = False  # Backup file doesn't exist
        mock_validate.return_value = (test_config.dirs_to_backup, [])
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with (
            patch.object(command, "_save_backup_info") as mock_save_info,
            patch.object(command, "_calculate_total_size", return_value=1000),
        ):
            result = command.execute()

        assert result is True
        mock_save_info.assert_called_once_with(1000)

    @patch("autotarcompress.commands.backup.validate_and_expand_paths")
    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_backup_failure_no_info_saved(
        self,
        mock_path_exists: MagicMock,
        mock_tarfile: MagicMock,
        mock_validate: MagicMock,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command doesn't save info when backup fails."""
        # Setup mocks
        mock_path_exists.return_value = False  # Backup file doesn't exist
        mock_validate.return_value = (test_config.dirs_to_backup, [])
        mock_tarfile.side_effect = OSError("backup failed")

        command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with (
            patch.object(command, "_save_backup_info") as mock_save_info,
            patch.object(command, "_calculate_total_size", return_value=1000),
        ):
            result = command.execute()

        assert result is False
        mock_save_info.assert_not_called()


class TestInfoCommand:
    """Test InfoCommand functionality."""

    def test_info_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that InfoCommand initializes correctly."""
        command = InfoCommand(test_config)
        assert command.config == test_config

    def test_info_command_no_backup_info(
        self, test_config: BackupConfig, caplog
    ) -> None:
        """Test InfoCommand when no backup info file exists."""
        with caplog.at_level(logging.INFO):
            command = InfoCommand(test_config)
            command.execute()

        output = caplog.text

        assert "No backup information found." in output
        assert "This usually means no backups have been created yet." in output

    def test_info_command_displays_backup_info(
        self,
        test_config: BackupConfig,
        mock_backup_info: dict[str, str | int | list[str]],
        temp_dir: str,
        caplog,
    ) -> None:
        """Test that InfoCommand displays backup information correctly."""
        # Update mock_backup_info to use temp directory paths
        mock_backup_info["backup_path"] = os.path.join(
            temp_dir, "backups", "13-09-2025.tar.xz"
        )

        # Create the info file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        import json

        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        # Create the backup file to simulate it exists
        backup_file_path = Path(mock_backup_info["backup_path"])
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
        backup_file_path.touch()

        with caplog.at_level(logging.INFO):
            command = InfoCommand(test_config)
            command.execute()

        output = caplog.text

        assert "===== Last Backup Information =====" in output
        assert "13-09-2025.tar.xz" in output
        assert "2025-09-13T10:30:45.123456" in output
        assert "1.00 GB" in output
        assert "/home/user/Documents" in output
        assert "/home/user/Pictures" in output
        assert "✓ Backup file exists" in output

    def test_info_command_missing_backup_file(
        self,
        test_config: BackupConfig,
        mock_backup_info: dict[str, str | int | list[str]],
        caplog,
    ) -> None:
        """Test InfoCommand when backup file doesn't exist."""
        # Create the info file but not the actual backup file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        import json

        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(mock_backup_info, f)

        with caplog.at_level(logging.INFO):
            command = InfoCommand(test_config)
            command.execute()

        output = caplog.text

        assert "✗ Backup file not found" in output

    def test_load_backup_info_corrupted_json(
        self, test_config: BackupConfig, caplog
    ) -> None:
        """Test InfoCommand with corrupted JSON file."""
        # Create a corrupted info file
        info_file_path = Path(test_config.config_dir) / "metadata.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        command = InfoCommand(test_config)
        result = command._load_backup_info()

        assert result is None
        assert "Error reading backup info file" in caplog.text


class TestCleanupCommand:
    """Test CleanupCommand functionality."""

    def test_cleanup_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that CleanupCommand initializes correctly."""
        command = CleanupCommand(test_config)
        assert command.config == test_config

    def test_cleanup_removes_old_backups(
        self, test_config: BackupConfig, test_backup_files: list[str]
    ) -> None:
        """Test that cleanup command removes old backup files."""
        # Set keep_backup to 2, so it should keep 2 newest and remove 1 oldest
        test_config.keep_backup = 2

        command = CleanupCommand(test_config)

        # Count files before cleanup
        backup_files = [
            f
            for f in os.listdir(test_config.backup_folder)
            if f.endswith(".tar.xz") and not f.endswith(".enc")
        ]
        files_before = len(backup_files)

        command.execute()

        # Count files after cleanup
        backup_files_after = [
            f
            for f in os.listdir(test_config.backup_folder)
            if f.endswith(".tar.xz") and not f.endswith(".enc")
        ]
        files_after = len(backup_files_after)

        # Should have removed files if there were more than keep_backup
        if files_before > test_config.keep_backup:
            assert files_after == test_config.keep_backup
        else:
            assert files_after == files_before


class TestEncryptCommand:
    """Test EncryptCommand functionality."""

    def test_encrypt_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that EncryptCommand initializes correctly."""
        test_file = "/path/to/test.tar.xz"
        command = EncryptCommand(test_config, test_file)
        assert command.file_to_encrypt == test_file
        assert hasattr(command, "logger")

    @patch("autotarcompress.commands.encrypt.subprocess.run")
    @patch("getpass.getpass")
    def test_encrypt_command_execution(
        self,
        mock_getpass: MagicMock,
        mock_subprocess: MagicMock,
        test_config: BackupConfig,
    ) -> None:
        """Test that encrypt command executes correctly."""
        # Create a test backup file
        test_file = os.path.join(test_config.backup_folder, "test.tar.xz")
        with open(test_file, "w") as f:
            f.write("test content")

        # Mock password input
        mock_getpass.return_value = "test_password"

        # Mock subprocess with proper stderr attribute
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b"Encryption completed successfully"
        mock_subprocess.return_value = mock_result

        command = EncryptCommand(test_config, test_file)
        command.execute()

        # Verify subprocess was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "openssl" in call_args
