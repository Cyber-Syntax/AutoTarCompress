"""Tests for the BackupCommand class.

This module contains comprehensive tests for the backup command implementation,
including mocking external processes and testing error conditions.
"""

import logging
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autotarcompress.commands.backup import BackupCommand
from autotarcompress.config import BackupConfig

# Test constants
TWO_GB = 2147483648
ONE_GB = 1073741824
ONE_KB = 1024
EXPECTED_PARTS_COUNT = 2
MIN_SPINNER_WRITES = 4
MIN_SPINNER_CALLS = 2


class TestBackupCommand:
    """Test cases for BackupCommand class."""

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        config = BackupConfig()
        config.backup_folder = str(tmp_path / "backups")
        config.config_dir = str(tmp_path / "config")
        config.dirs_to_backup = [
            str(tmp_path / "source1"),
            str(tmp_path / "source2"),
        ]
        config.ignore_list = [".git", "*.pyc", "__pycache__"]

        # Create necessary directories
        os.makedirs(config.backup_folder, exist_ok=True)
        os.makedirs(config.config_dir, exist_ok=True)
        for dir_path in config.dirs_to_backup:
            os.makedirs(dir_path, exist_ok=True)

        return config

    @pytest.fixture
    def backup_command(self, mock_config: BackupConfig) -> BackupCommand:
        """Create a BackupCommand instance for testing."""
        return BackupCommand(mock_config)

    def test_backup_command_initialization(
        self, mock_config: BackupConfig
    ) -> None:
        """Test BackupCommand initialization."""
        command = BackupCommand(mock_config)

        assert command.config == mock_config
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "autotarcompress.commands.backup"

    def test_execute_no_directories_configured(
        self, backup_command: BackupCommand
    ) -> None:
        """Test execute fails when no directories are configured for backup."""
        backup_command.config.dirs_to_backup = []

        result = backup_command.execute()

        assert result is False

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_execute_successful_backup(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test successful backup execution."""
        # Setup mocks
        mock_exists.return_value = False
        mock_subprocess.return_value = Mock(returncode=0)
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        with patch.object(backup_command, "_save_backup_info") as mock_save:
            result = backup_command.execute()

            assert result is True
            mock_save.assert_called_once_with(ONE_GB)
            mock_subprocess.assert_called_once()

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_execute_backup_file_exists_user_refuses_removal(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup fails when file exists and user refuses removal."""
        mock_exists.return_value = True
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        with patch("builtins.input", return_value="n"):
            result = backup_command.execute()

            assert result is False
            mock_subprocess.assert_not_called()

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.remove")
    def test_execute_backup_file_exists_user_allows_removal(
        self,
        mock_remove: Mock,
        mock_exists: Mock,
        mock_subprocess: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup succeeds when file exists and user allows removal."""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        with (
            patch("builtins.input", return_value="y"),
            patch.object(backup_command, "_save_backup_info"),
        ):
            result = backup_command.execute()

            assert result is True
            mock_remove.assert_called_once_with(
                backup_command.config.backup_path
            )

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_execute_subprocess_error(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup fails when subprocess raises CalledProcessError."""
        mock_exists.return_value = False
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "tar")
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        result = backup_command.execute()

        assert result is False

    def test_calculate_total_size(self, backup_command: BackupCommand) -> None:
        """Test _calculate_total_size method."""
        with patch(
            "autotarcompress.commands.backup.SizeCalculator"
        ) as mock_size_calc:
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_total_size.return_value = TWO_GB
            mock_size_calc.return_value = mock_calc_instance

            total_size = backup_command._calculate_total_size()

            assert total_size == TWO_GB
            mock_size_calc.assert_called_once_with(
                backup_command.config.dirs_to_backup,
                backup_command.config.ignore_list,
            )

    @patch("os.cpu_count")
    def test_run_backup_process_cpu_count_none(
        self, mock_cpu_count: Mock, backup_command: BackupCommand
    ) -> None:
        """Test backup process handles None CPU count gracefully."""
        mock_cpu_count.return_value = None

        with (
            patch("subprocess.run") as mock_subprocess,
            patch("os.path.exists", return_value=False),
        ):
            backup_command._run_backup_process(ONE_KB)

            # Verify that threads=1 is used when cpu_count returns None
            call_args = mock_subprocess.call_args[0][0]
            assert "--threads=1" in call_args

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("datetime.datetime")
    def test_save_backup_info_success(
        self,
        mock_datetime: Mock,
        mock_json_dump: Mock,
        mock_file_open: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test successful saving of backup information."""
        mock_datetime.now().isoformat.return_value = (
            "2025-09-13T10:30:45.123456"
        )

        backup_command._save_backup_info(ONE_GB)

        expected_info = {
            "backup_file": Path(backup_command.config.backup_path).name,
            "backup_path": str(backup_command.config.backup_path),
            "backup_date": "2025-09-13T10:30:45.123456",
            "backup_size_bytes": ONE_GB,
            "backup_size_human": "1.00 GB",
            "directories_backed_up": backup_command.config.dirs_to_backup,
        }

        mock_json_dump.assert_called_once_with(
            expected_info, mock_file_open().__enter__(), indent=2
        )

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_backup_info_error(
        self,
        mock_file_open: Mock,
        backup_command: BackupCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test error handling in _save_backup_info method."""
        with caplog.at_level(logging.ERROR):
            backup_command._save_backup_info(ONE_GB)

            assert "Failed to save backup info" in caplog.text

    @given(st.integers(min_value=0, max_value=10**15))
    def test_format_size_property(self, size_bytes: int) -> None:
        """Property-based test for _format_size method."""
        backup_command = BackupCommand(BackupConfig())

        result = backup_command._format_size(size_bytes)

        # Should always return a string with size and unit
        assert isinstance(result, str)
        assert any(
            unit in result for unit in ["B", "KB", "MB", "GB", "TB", "PB"]
        )

        # Should be properly formatted (decimal number + space + unit)
        parts = result.split()
        assert len(parts) == EXPECTED_PARTS_COUNT
        assert float(parts[0]) >= 0  # Should be able to parse as float

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [
            (0, "0.00 B"),
            (1023, "1023.00 B"),
            (1024, "1.00 KB"),
            (1048576, "1.00 MB"),
            (1073741824, "1.00 GB"),
            (1099511627776, "1.00 TB"),
            (1125899906842624, "1.00 PB"),
        ],
    )
    def test_format_size_specific_values(
        self, size_bytes: int, expected: str, backup_command: BackupCommand
    ) -> None:
        """Test _format_size method with specific values."""
        result = backup_command._format_size(size_bytes)
        assert result == expected

    @patch("autotarcompress.commands.backup.is_pv_available")
    def test_build_tar_command_with_pv(
        self, mock_pv_available: Mock, backup_command: BackupCommand
    ) -> None:
        """Test _build_tar_command includes pv when available."""
        mock_pv_available.return_value = True
        total_size = 1000000
        cmd = backup_command._build_tar_command(total_size)

        assert "pv -s 1000000" in cmd
        assert "tar -chf -" in cmd
        assert "xz --threads=" in cmd

    @patch("autotarcompress.commands.backup.is_pv_available")
    def test_build_tar_command_without_pv(
        self, mock_pv_available: Mock, backup_command: BackupCommand
    ) -> None:
        """Test _build_tar_command works without pv."""
        mock_pv_available.return_value = False
        total_size = 1000000
        cmd = backup_command._build_tar_command(total_size)

        assert "pv" not in cmd
        assert "tar -chf -" in cmd
        assert "xz --threads=" in cmd

    def test_backup_command_with_symlinks(
        self, backup_command: BackupCommand
    ) -> None:
        """Test that backup command properly handles symlinks."""
        # This test verifies the 'h' option is used in tar command
        with (
            patch("subprocess.run") as mock_subprocess,
            patch("os.path.exists", return_value=False),
            patch(
                "autotarcompress.commands.backup.SizeCalculator"
            ) as mock_calc,
        ):
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_total_size.return_value = ONE_KB
            mock_calc.return_value = mock_calc_instance

            backup_command._run_backup_process(ONE_KB)

            call_args = mock_subprocess.call_args[0][0]
            assert "-chf" in call_args  # h option for following symlinks

    def test_exclude_options_generation(
        self, backup_command: BackupCommand
    ) -> None:
        """Test that exclude options are properly generated."""
        with (
            patch("subprocess.run") as mock_subprocess,
            patch("os.path.exists", return_value=False),
        ):
            backup_command._run_backup_process(ONE_KB)

            call_args = mock_subprocess.call_args[0][0]
            # Patterns are now quoted for shell safety
            for ignore_item in backup_command.config.ignore_list:
                # Check pattern is in the command, allowing for quoting
                assert (
                    f"--exclude={ignore_item}" in call_args
                    or f"--exclude='{ignore_item}'" in call_args
                )
