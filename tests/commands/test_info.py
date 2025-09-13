"""Comprehensive tests for InfoCommand.

This module provides extensive test coverage for the InfoCommand class,
including JSON loading, info display formatting, error handling, and
file existence validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, mock_open, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.commands.info import InfoCommand
from src.config import BackupConfig


class TestInfoCommand:
    """Test suite for InfoCommand functionality."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock configuration for testing.

        Returns:
            BackupConfig: Mock configuration with test backup folder.


        """
        config = Mock(spec=BackupConfig)
        config.backup_folder = "/test/backup/folder"
        return config

    @pytest.fixture
    def info_command(self, mock_config: BackupConfig) -> InfoCommand:
        """Create an InfoCommand instance for testing.

        Args:
            mock_config: Mock backup configuration.


        Returns:
            InfoCommand: Instance for testing.


        """
        return InfoCommand(mock_config)

    @pytest.fixture
    def sample_backup_info(self) -> Dict[str, Any]:
        """Create sample backup information for testing.

        Returns:
            Dict containing sample backup metadata.


        """
        return {
            "backup_file": "backup_20241215_120000.tar.xz",
            "backup_path": "/test/backup/folder/backup_20241215_120000.tar.xz",
            "backup_date": "2024-12-15 12:00:00",
            "backup_size_human": "156.8 MB",
            "directories_backed_up": ["/home/user/documents", "/home/user/projects"],
        }

    def test_initialization(self, mock_config: BackupConfig) -> None:
        """Test InfoCommand initialization.

        Args:
            mock_config: Mock backup configuration.


        """
        command = InfoCommand(mock_config)

        assert command.config is mock_config
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "src.commands.info"

    @patch("builtins.print")
    @patch.object(InfoCommand, "_load_backup_info")
    @patch.object(InfoCommand, "_display_backup_info")
    def test_execute_with_backup_info(
        self,
        mock_display: Mock,
        mock_load: Mock,
        mock_print: Mock,
        info_command: InfoCommand,
        sample_backup_info: Dict[str, Any],
    ) -> None:
        """Test execute when backup info is available.

        Args:
            mock_display: Mock display method.

            mock_load: Mock load method.
            mock_print: Mock print function.
            info_command: InfoCommand instance.
            sample_backup_info: Sample backup data.

        """
        mock_load.return_value = sample_backup_info

        info_command.execute()

        mock_load.assert_called_once()
        mock_display.assert_called_once_with(sample_backup_info)
        mock_print.assert_not_called()

    @patch("builtins.print")
    @patch.object(InfoCommand, "_load_backup_info")
    @patch.object(InfoCommand, "_display_backup_info")
    def test_execute_no_backup_info(
        self, mock_display: Mock, mock_load: Mock, mock_print: Mock, info_command: InfoCommand
    ) -> None:
        """Test execute when no backup info is available.

        Args:
            mock_display: Mock display method.

            mock_load: Mock load method.
            mock_print: Mock print function.
            info_command: InfoCommand instance.

        """
        mock_load.return_value = None

        info_command.execute()

        mock_load.assert_called_once()
        mock_display.assert_not_called()
        expected_calls = [
            (("No backup information found.",), {}),
            (("This usually means no backups have been created yet.",), {}),
        ]
        from unittest.mock import call

        mock_print.assert_has_calls([call(*args, **kwargs) for args, kwargs in expected_calls])

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_backup_info_success(
        self,
        mock_file: Mock,
        mock_exists: Mock,
        info_command: InfoCommand,
        sample_backup_info: Dict[str, Any],
    ) -> None:
        """Test successful backup info loading.

        Args:
            mock_file: Mock file operations.

            mock_exists: Mock path existence check.
            info_command: InfoCommand instance.
            sample_backup_info: Sample backup data.

        """
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_backup_info)

        result = info_command._load_backup_info()

        assert result == sample_backup_info
        expected_path = Path("/test/backup/folder") / "last-backup-info.json"
        mock_exists.assert_called_once()
        mock_file.assert_called_once_with(expected_path, encoding="utf-8")

    @patch("pathlib.Path.exists")
    def test_load_backup_info_file_not_exists(
        self, mock_exists: Mock, info_command: InfoCommand
    ) -> None:
        """Test loading when info file doesn't exist.

        Args:
            mock_exists: Mock path existence check.

            info_command: InfoCommand instance.

        """
        mock_exists.return_value = False

        result = info_command._load_backup_info()

        assert result is None

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_backup_info_json_decode_error(
        self,
        mock_file: Mock,
        mock_exists: Mock,
        info_command: InfoCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test loading with JSON decode error.

        Args:
            mock_file: Mock file operations.

            mock_exists: Mock path existence check.
            info_command: InfoCommand instance.
            caplog: Pytest log capture fixture.

        """
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"

        with caplog.at_level(logging.ERROR):
            result = info_command._load_backup_info()

        assert result is None
        assert "Error reading backup info file" in caplog.text

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_backup_info_general_exception(
        self,
        mock_open_func: Mock,
        mock_exists: Mock,
        info_command: InfoCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test loading with general exception.

        Args:
            mock_open_func: Mock open function.

            mock_exists: Mock path existence check.
            info_command: InfoCommand instance.
            caplog: Pytest log capture fixture.

        """
        mock_exists.return_value = True
        mock_open_func.side_effect = PermissionError("Access denied")

        with caplog.at_level(logging.ERROR):
            result = info_command._load_backup_info()

        assert result is None
        assert "Failed to load backup info" in caplog.text

    @patch("builtins.print")
    @patch("pathlib.Path.exists")
    def test_display_backup_info_complete(
        self,
        mock_exists: Mock,
        mock_print: Mock,
        info_command: InfoCommand,
        sample_backup_info: Dict[str, Any],
    ) -> None:
        """Test display with complete backup information.

        Args:
            mock_exists: Mock path existence check.

            mock_print: Mock print function.
            info_command: InfoCommand instance.
            sample_backup_info: Sample backup data.

        """
        mock_exists.return_value = True

        info_command._display_backup_info(sample_backup_info)

        # Verify all expected information is printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]

        assert any("Last Backup Information" in call for call in print_calls)
        assert any("backup_20241215_120000.tar.xz" in call for call in print_calls)
        assert any("2024-12-15 12:00:00" in call for call in print_calls)
        assert any("156.8 MB" in call for call in print_calls)
        assert any("/home/user/documents" in call for call in print_calls)
        assert any("/home/user/projects" in call for call in print_calls)
        assert any("✓ Backup file exists" in call for call in print_calls)

    @patch("builtins.print")
    @patch("pathlib.Path.exists")
    def test_display_backup_info_file_not_found(
        self,
        mock_exists: Mock,
        mock_print: Mock,
        info_command: InfoCommand,
        sample_backup_info: Dict[str, Any],
    ) -> None:
        """Test display when backup file doesn't exist.

        Args:
            mock_exists: Mock path existence check.

            mock_print: Mock print function.
            info_command: InfoCommand instance.
            sample_backup_info: Sample backup data.

        """
        mock_exists.return_value = False

        info_command._display_backup_info(sample_backup_info)

        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("✗ Backup file not found" in call for call in print_calls)

    @patch("builtins.print")
    def test_display_backup_info_no_directories(
        self, mock_print: Mock, info_command: InfoCommand
    ) -> None:
        """Test display with no directories backed up.

        Args:
            mock_print: Mock print function.

            info_command: InfoCommand instance.

        """
        backup_info = {
            "backup_file": "test.tar.xz",
            "backup_path": None,
            "backup_date": "2024-12-15",
            "backup_size_human": "100 MB",
            "directories_backed_up": [],
        }

        info_command._display_backup_info(backup_info)

        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Directories Backed Up: None" in call for call in print_calls)
        assert any("Status: Unknown" in call for call in print_calls)

    @patch("builtins.print")
    def test_display_backup_info_missing_fields(
        self, mock_print: Mock, info_command: InfoCommand
    ) -> None:
        """Test display with missing backup info fields.

        Args:
            mock_print: Mock print function.

            info_command: InfoCommand instance.

        """
        backup_info: Dict[str, Any] = {}

        info_command._display_backup_info(backup_info)

        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Unknown" in call for call in print_calls)

    @given(
        st.dictionaries(
            keys=st.sampled_from(
                ["backup_file", "backup_path", "backup_date", "backup_size_human"]
            ),
            values=st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=4,
        )
    )
    def test_display_backup_info_property(self, backup_info: Dict[str, str]) -> None:
        """Property-based test for backup info display.

        Args:
            backup_info: Random backup information dictionary.

        """
        info_command = InfoCommand(BackupConfig())

        with patch("builtins.print") as mock_print, patch("pathlib.Path.exists", return_value=True):
            # Add required structure
            full_backup_info = {"directories_backed_up": [], **backup_info}

            # Should not raise exception
            info_command._display_backup_info(full_backup_info)

            # Should have printed something
            assert mock_print.called

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10))
    def test_directories_display_property(self, directories: list[str]) -> None:
        """Property-based test for directories display.

        Args:
            directories: Random list of directory paths.

        """
        info_command = InfoCommand(BackupConfig())
        backup_info = {"backup_file": "test.tar.xz", "directories_backed_up": directories}

        with patch("builtins.print") as mock_print, patch("pathlib.Path.exists", return_value=True):
            info_command._display_backup_info(backup_info)

            print_calls = [call[0][0] for call in mock_print.call_args_list]

            if directories:
                # Should show count
                count_line = next(
                    (call for call in print_calls if f"({len(directories)})" in call), None
                )
                assert count_line is not None

                # Should show each directory
                for directory in directories:
                    assert any(directory in call for call in print_calls)
            else:
                # Should show "None"
                assert any("Directories Backed Up: None" in call for call in print_calls)

    def test_backup_info_file_path_construction(self, info_command: InfoCommand) -> None:
        """Test that backup info file path is constructed correctly.

        Args:
            info_command: InfoCommand instance.

        """
        with patch("pathlib.Path.exists", return_value=False) as mock_exists:
            info_command._load_backup_info()

            # Verify the expected path was checked
            expected_path = Path("/test/backup/folder/last-backup-info.json")
            mock_exists.assert_called_once()
            # Get the path that was actually checked
            if mock_exists.call_args and mock_exists.call_args.args:
                checked_path = mock_exists.call_args.args[0]
                assert str(checked_path) == str(expected_path)

    @given(st.text(min_size=1, max_size=200))
    def test_json_loading_with_various_content(self, json_content: str) -> None:
        """Property-based test for JSON loading robustness.

        Args:
            json_content: Random JSON-like content.

        """
        info_command = InfoCommand(BackupConfig())

        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=json_content)
        ):
            # Should handle any content gracefully
            result = info_command._load_backup_info()

            # Result should be None for invalid JSON or valid dict for valid JSON
            assert result is None or isinstance(result, dict)
