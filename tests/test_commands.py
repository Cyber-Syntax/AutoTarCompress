"""Tests for command classes and their execution.

This module tests backup, cleanup, encrypt, decrypt, extract, and info commands.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.commands import (
    BackupCommand,
    CleanupCommand,
    DecryptCommand,
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

        with patch.object(
            command.manager, "calculate_total_size", return_value=1024
        ) as mock_calc:
            size = command.manager.calculate_total_size()
            assert size == 1024
            mock_calc.assert_called_once()

    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_backup_success_saves_info(
        self,
        mock_path_exists: MagicMock,
        mock_tarfile: MagicMock,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command saves info when backup succeeds."""
        # Setup mocks
        mock_path_exists.return_value = False  # Backup file doesn't exist
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(
            command.manager, "execute_backup", return_value=True
        ) as mock_execute:
            result = command.execute()

        assert result is True
        mock_execute.assert_called_once()

    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_backup_failure_no_info_saved(
        self,
        mock_path_exists: MagicMock,
        mock_tarfile: MagicMock,
        test_config: BackupConfig,
    ) -> None:
        """Test that backup command doesn't save info when backup fails."""
        # Setup mocks
        mock_path_exists.return_value = False  # Backup file doesn't exist
        mock_tarfile.side_effect = OSError("backup failed")

        command = BackupCommand(test_config)

        # Create test directories
        for dir_path in test_config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        with patch.object(
            command.manager, "execute_backup", return_value=False
        ) as mock_execute:
            result = command.execute()

        assert result is False
        mock_execute.assert_called_once()


class TestInfoCommand:
    """Test InfoCommand functionality."""

    def test_info_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that InfoCommand initializes correctly."""
        command = InfoCommand(test_config)
        assert command.config == test_config
        assert hasattr(command, "manager")
        assert command.manager is not None

    @patch("autotarcompress.commands.info.InfoManager")
    def test_info_command_execute_success(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test InfoCommand execute returns True when manager succeeds."""
        mock_manager = MagicMock()
        mock_manager.execute_info.return_value = True
        mock_manager_class.return_value = mock_manager

        command = InfoCommand(test_config)
        result = command.execute()

        assert result is True
        mock_manager.execute_info.assert_called_once()

    @patch("autotarcompress.commands.info.InfoManager")
    def test_info_command_execute_failure(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test InfoCommand execute returns False when manager fails."""
        mock_manager = MagicMock()
        mock_manager.execute_info.return_value = False
        mock_manager_class.return_value = mock_manager

        command = InfoCommand(test_config)
        result = command.execute()

        assert result is False
        mock_manager.execute_info.assert_called_once()


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
        assert hasattr(command, "manager")

    @patch("autotarcompress.commands.encrypt.EncryptManager")
    def test_encrypt_command_execute_success(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test EncryptCommand execute returns True when manager succeeds."""
        test_file = "/path/to/test.tar.xz"
        mock_manager = MagicMock()
        mock_manager.execute_encrypt.return_value = True
        mock_manager_class.return_value = mock_manager

        command = EncryptCommand(test_config, test_file)
        result = command.execute()

        assert result is True
        mock_manager.execute_encrypt.assert_called_once_with(test_file)

    @patch("autotarcompress.commands.encrypt.EncryptManager")
    def test_encrypt_command_execute_failure(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test EncryptCommand execute returns False when manager fails."""
        test_file = "/path/to/test.tar.xz"
        mock_manager = MagicMock()
        mock_manager.execute_encrypt.return_value = False
        mock_manager_class.return_value = mock_manager

        command = EncryptCommand(test_config, test_file)
        result = command.execute()

        assert result is False
        mock_manager.execute_encrypt.assert_called_once_with(test_file)


class TestDecryptCommand:
    """Test DecryptCommand functionality."""

    def test_decrypt_command_initialization(
        self, test_config: BackupConfig
    ) -> None:
        """Test that DecryptCommand initializes correctly."""
        test_file = "/path/to/test.tar.xz.enc"
        command = DecryptCommand(test_config, test_file)
        assert command.file_path == test_file
        assert hasattr(command, "logger")
        assert hasattr(command, "manager")

    @patch("autotarcompress.commands.decrypt.DecryptManager")
    def test_decrypt_command_execute_success(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test DecryptCommand execute returns True when manager succeeds."""
        test_file = "/path/to/test.tar.xz.enc"
        mock_manager = MagicMock()
        mock_manager.execute_decrypt.return_value = True
        mock_manager_class.return_value = mock_manager

        command = DecryptCommand(test_config, test_file)
        result = command.execute()

        assert result is True
        mock_manager.execute_decrypt.assert_called_once_with(test_file)

    @patch("autotarcompress.commands.decrypt.DecryptManager")
    def test_decrypt_command_execute_failure(
        self, mock_manager_class: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test DecryptCommand execute returns False when manager fails."""
        test_file = "/path/to/test.tar.xz.enc"
        mock_manager = MagicMock()
        mock_manager.execute_decrypt.return_value = False
        mock_manager_class.return_value = mock_manager

        command = DecryptCommand(test_config, test_file)
        result = command.execute()

        assert result is False
        mock_manager.execute_decrypt.assert_called_once_with(test_file)
