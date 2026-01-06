"""Tests for the BackupCommand class.

This module contains comprehensive tests for the backup command implementation,
including mocking external processes and testing error conditions.
"""

import logging
import os
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
    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    @patch("autotarcompress.commands.backup.validate_and_expand_paths")
    def test_execute_successful_backup(
        self,
        mock_validate: Mock,
        mock_exists: Mock,
        mock_tarfile_open: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test successful backup execution."""
        # Setup mocks
        mock_validate.return_value = (
            backup_command.config.dirs_to_backup,
            [],
        )
        mock_exists.return_value = False
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        # Mock tarfile context manager
        mock_tar = Mock()
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        with patch.object(backup_command, "_save_backup_info") as mock_save:
            result = backup_command.execute()

            assert result is True
            mock_save.assert_called_once_with(ONE_GB)
            mock_tarfile_open.assert_called_once()

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("pathlib.Path.exists")
    def test_execute_backup_file_exists_user_refuses_removal(
        self,
        mock_exists: Mock,
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

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    def test_execute_backup_file_exists_user_allows_removal(
        self,
        mock_unlink: Mock,
        mock_exists: Mock,
        mock_tarfile_open: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup succeeds when file exists and user allows removal."""
        mock_exists.return_value = True
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_total_size.return_value = ONE_GB
        mock_size_calc.return_value = mock_calc_instance

        # Mock tarfile context manager
        mock_tar = Mock()
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        with (
            patch("builtins.input", return_value="y"),
            patch.object(backup_command, "_save_backup_info"),
        ):
            result = backup_command.execute()

            assert result is True
            mock_unlink.assert_called_once()

    @patch("autotarcompress.commands.backup.SizeCalculator")
    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_execute_tarfile_error(
        self,
        mock_exists: Mock,
        mock_tarfile_open: Mock,
        mock_size_calc: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup fails when tarfile raises an error."""
        mock_exists.return_value = False
        mock_tarfile_open.side_effect = OSError("Permission denied")
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

    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    def test_run_backup_process_cpu_count_none(
        self,
        mock_exists: Mock,
        mock_tarfile: Mock,
        backup_command: BackupCommand,
    ) -> None:
        """Test backup process handles tarfile creation properly."""
        mock_exists.return_value = False

        # Mock tarfile context manager
        mock_tar = Mock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        backup_command._run_backup_process(ONE_KB)

        # Verify tarfile.open was called with zst compression
        mock_tarfile.assert_called_once()
        call_args = mock_tarfile.call_args
        assert "w:zst" in call_args[0]  # Check for zst compression mode

    @patch("pathlib.Path.open", new_callable=mock_open)
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
        mock_datetime.now.return_value.isoformat.return_value = (
            "2025-09-13T10:30:45.123456+00:00"
        )

        backup_command._save_backup_info(ONE_GB)

        # Verify json.dump was called
        assert mock_json_dump.called
        call_args = mock_json_dump.call_args[0]
        backup_info = call_args[0]

        assert backup_info["backup_size_bytes"] == ONE_GB
        assert backup_info["backup_size_human"] == "1.00 GB"
        assert backup_info["backup_date"] == "2025-09-13T10:30:45.123456+00:00"

    @patch("pathlib.Path.open", side_effect=OSError("Permission denied"))
    def test_save_backup_info_error(
        self,
        mock_file_open: Mock,
        backup_command: BackupCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test error handling in _save_backup_info method."""
        backup_command._save_backup_info(ONE_GB)

        # Check that an exception was logged
        # logging.exception automatically logs the exception
        assert len(caplog.records) > 0

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

    def test_should_exclude_absolute_path(
        self, backup_command: BackupCommand
    ) -> None:
        """Test _should_exclude method with absolute paths."""
        from pathlib import Path

        backup_command.config.ignore_list = ["/tmp/test"]
        assert backup_command._should_exclude(Path("/tmp/test/file.txt"))
        assert not backup_command._should_exclude(Path("/home/user/file.txt"))

    def test_should_exclude_glob_pattern(
        self, backup_command: BackupCommand
    ) -> None:
        """Test _should_exclude method with glob patterns."""
        from pathlib import Path

        backup_command.config.ignore_list = ["*.pyc", "*.log"]
        assert backup_command._should_exclude(Path("/tmp/test.pyc"))
        assert backup_command._should_exclude(Path("/tmp/app.log"))
        assert not backup_command._should_exclude(Path("/tmp/test.py"))

    def test_should_exclude_directory_name(
        self, backup_command: BackupCommand
    ) -> None:
        """Test _should_exclude method with directory names."""
        from pathlib import Path

        backup_command.config.ignore_list = ["node_modules", "__pycache__"]
        assert backup_command._should_exclude(
            Path("/project/node_modules/package")
        )
        assert backup_command._should_exclude(
            Path("/src/__pycache__/module.pyc")
        )
        assert not backup_command._should_exclude(Path("/project/src/file.py"))
