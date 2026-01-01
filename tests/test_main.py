"""Tests for main module functionality.

This module tests the main application entry point and initialization.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.cli import app
from autotarcompress.config import BackupConfig
from autotarcompress.facade import BackupFacade
from autotarcompress.main import main
from autotarcompress.runner import (
    find_file_by_date,
    get_backup_files,
    get_encrypted_files,
    handle_encrypt_operation,
    handle_extract_operation,
    initialize_config,
)


class TestMainModule:
    """Test main module functionality."""

    def test_initialize_config_no_existing_config(self) -> None:
        """Test initialize_config when no config file exists."""
        with (
            patch.object(BackupFacade, "__init__", return_value=None),
            patch.object(os.path, "exists", return_value=False),
            patch("autotarcompress.logger.setup_basic_logging"),
            patch("autotarcompress.logger.setup_application_logging"),
        ):
            facade_mock = MagicMock()
            facade_mock.config = MagicMock()
            facade_mock.config.config_path = "/fake/path"
            facade_mock.config.get_log_level.return_value = "INFO"
            facade_mock.configure = MagicMock()

            with patch.object(
                BackupFacade, "__new__", return_value=facade_mock
            ):
                result = initialize_config()
                assert result is not None
                facade_mock.configure.assert_called_once()

    def test_initialize_config_existing_config(self) -> None:
        """Test initialize_config when config file exists."""
        with (
            patch.object(BackupFacade, "__init__", return_value=None),
            patch.object(os.path, "exists", return_value=True),
            patch("autotarcompress.logger.setup_application_logging"),
        ):
            facade_mock = MagicMock()
            facade_mock.config = MagicMock()
            facade_mock.config.config_path = "/fake/path"
            facade_mock.config.get_log_level.return_value = (
                20  # INFO level integer
            )
            loaded_config_mock = MagicMock()
            loaded_config_mock.get_log_level.return_value = 20
            facade_mock.config.load.return_value = loaded_config_mock

            with patch.object(
                BackupFacade, "__new__", return_value=facade_mock
            ):
                result = initialize_config()
                assert result is not None
                # Just check that the result is the facade, not internal behavior
                assert result == facade_mock

    def test_get_backup_files(self) -> None:
        """Test get_backup_files returns correct file list."""
        test_files = [
            "backup1.tar.xz",
            "backup2.tar.xz",
            "backup3.enc",
            "other.txt",
        ]
        expected_files = ["backup1.tar.xz", "backup2.tar.xz"]

        with (
            patch("os.listdir", return_value=test_files),
            patch("os.path.expanduser", return_value="/expanded/path"),
        ):
            result = get_backup_files("/test/path")
            assert result == expected_files

    def test_get_encrypted_files(self) -> None:
        """Test get_encrypted_files returns correct file list."""
        test_files = [
            "backup1.tar.xz",
            "backup2.enc",
            "backup3.enc",
            "other.txt",
        ]
        expected_files = ["backup2.enc", "backup3.enc"]

        with (
            patch("os.listdir", return_value=test_files),
            patch("os.path.expanduser", return_value="/expanded/path"),
        ):
            result = get_encrypted_files("/test/path")
            assert result == expected_files

    def test_handle_encrypt_operation_no_files(self) -> None:
        """Test handle_encrypt_operation when no backup files are available."""
        facade_mock = MagicMock()
        facade_mock.config.backup_folder = "/test/folder"

        with (
            patch("autotarcompress.runner.get_backup_files", return_value=[]),
            patch("builtins.print") as mock_print,
        ):
            result = handle_encrypt_operation(facade_mock)
            assert result is None
            mock_print.assert_called_with(
                "No backup files available for encryption"
            )

    def test_handle_extract_operation_no_files(self) -> None:
        """Test handle_extract_operation when no backup files are available."""
        facade_mock = MagicMock()
        facade_mock.config.backup_folder = "/test/folder"

        with (
            patch("autotarcompress.runner.get_backup_files", return_value=[]),
            patch("builtins.print") as mock_print,
        ):
            result = handle_extract_operation(facade_mock)
            assert result is None
            mock_print.assert_called_with("No backup files found")

    def test_main_function_calls_app(self) -> None:
        """Test that main function calls the typer app."""
        with patch("autotarcompress.cli.app") as mock_app:
            main()
            mock_app.assert_called_once()


class TestCLICommands:
    """Test CLI command functionality using Typer's test runner."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_config = BackupConfig()
        self.test_config.backup_folder = "/tmp/test_backups"
        self.test_config.config_dir = tempfile.mkdtemp()

    def test_cli_help(self) -> None:
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AutoTarCompress" in result.stdout
        assert "backup" in result.stdout
        assert "encrypt" in result.stdout
        assert "decrypt" in result.stdout
        assert "extract" in result.stdout
        assert "cleanup" in result.stdout
        assert "info" in result.stdout
        assert "interactive" in result.stdout

    def test_backup_command_help(self) -> None:
        """Test backup command help."""
        result = self.runner.invoke(app, ["backup", "--help"])
        assert result.exit_code == 0
        assert "Create a backup archive" in result.stdout

    def test_encrypt_command_help(self) -> None:
        """Test encrypt command help."""
        result = self.runner.invoke(app, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "--latest" in result.stdout
        assert "--date" in result.stdout
        assert "Specific backup file to encrypt" in result.stdout

    def test_encrypt_no_options_error(self) -> None:
        """Test encrypt command without any options shows error."""
        with patch("autotarcompress.runner.initialize_config"):
            result = self.runner.invoke(app, ["encrypt"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_encrypt_multiple_options_error(self) -> None:
        """Test encrypt command with multiple options shows error."""
        with patch("autotarcompress.runner.initialize_config"):
            result = self.runner.invoke(
                app, ["encrypt", "--latest", "--date", "01-01-2023"]
            )
            assert result.exit_code == 1
            assert (
                "Only one of --latest, --date, or file argument can be specified"
                in result.stdout
            )

    def test_decrypt_no_options_error(self) -> None:
        """Test decrypt command without any options shows error."""
        with patch("autotarcompress.runner.initialize_config"):
            result = self.runner.invoke(app, ["decrypt"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_extract_no_options_error(self) -> None:
        """Test extract command without any options shows error."""
        with patch("autotarcompress.runner.initialize_config"):
            result = self.runner.invoke(app, ["extract"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_cleanup_multiple_options_error(self) -> None:
        """Test cleanup command with multiple options shows error."""
        with patch("autotarcompress.runner.initialize_config"):
            result = self.runner.invoke(
                app, ["cleanup", "--all", "--keep", "5"]
            )
            assert result.exit_code == 1
            assert (
                "Only one of --all, --older-than, or --keep can be specified"
                in result.stdout
            )

    @patch("autotarcompress.runner.initialize_config")
    def test_backup_command_success(self, mock_init_config: MagicMock) -> None:
        """Test successful backup command execution."""
        mock_facade = MagicMock()
        mock_facade.execute_command.return_value = True
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["backup"])
        assert result.exit_code == 0
        mock_facade.execute_command.assert_called_once_with("backup")

    @patch("autotarcompress.runner.initialize_config")
    def test_backup_command_failure(self, mock_init_config: MagicMock) -> None:
        """Test backup command failure handling."""
        mock_facade = MagicMock()
        mock_facade.execute_command.return_value = False
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["backup"])
        assert result.exit_code == 1

    @patch("autotarcompress.runner.initialize_config")
    def test_info_command_success(self, mock_init_config: MagicMock) -> None:
        """Test successful info command execution."""
        mock_facade = MagicMock()
        mock_facade.execute_command.return_value = True
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["info"])
        assert result.exit_code == 0
        mock_facade.execute_command.assert_called_once_with("info")

    @patch("autotarcompress.runner.initialize_config")
    def test_cleanup_command_success(
        self, mock_init_config: MagicMock
    ) -> None:
        """Test successful cleanup command execution."""
        mock_facade = MagicMock()
        mock_facade.execute_command.return_value = True
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["cleanup"])
        assert result.exit_code == 0
        mock_facade.execute_command.assert_called_once_with(
            "cleanup", cleanup_all=False
        )

    @patch("autotarcompress.runner.initialize_config")
    def test_cleanup_command_all_success(
        self, mock_init_config: MagicMock
    ) -> None:
        """Test successful cleanup --all command execution."""
        mock_facade = MagicMock()
        mock_facade.execute_command.return_value = True
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["cleanup", "--all"])
        assert result.exit_code == 0
        mock_facade.execute_command.assert_called_once_with(
            "cleanup", cleanup_all=True
        )

    @patch("autotarcompress.runner.run_main_loop")
    @patch("autotarcompress.runner.initialize_config")
    def test_interactive_command(
        self, mock_init_config: MagicMock, mock_run_loop: MagicMock
    ) -> None:
        """Test interactive command execution."""
        mock_facade = MagicMock()
        mock_init_config.return_value = mock_facade

        result = self.runner.invoke(app, ["interactive"])
        assert result.exit_code == 0
        mock_run_loop.assert_called_once_with(mock_facade)


class TestUtilityFunctions:
    """Test utility functions for CLI operations."""

    def test_find_file_by_date_found(self) -> None:
        """Test find_file_by_date when file exists."""
        files = [
            "backup_01-01-2023_10-30-45.tar.xz",
            "backup_02-01-2023_11-45-30.tar.xz",
            "backup_03-01-2023_14-20-15.tar.xz",
        ]

        result = find_file_by_date(files, "02-01-2023")
        assert result == "backup_02-01-2023_11-45-30.tar.xz"

    def test_find_file_by_date_not_found(self) -> None:
        """Test find_file_by_date when file doesn't exist."""
        files = [
            "backup_01-01-2023_10-30-45.tar.xz",
            "backup_03-01-2023_14-20-15.tar.xz",
        ]

        with patch("typer.echo") as mock_echo:
            result = find_file_by_date(files, "02-01-2023")
            assert result is None
            mock_echo.assert_not_called()  # Only called on invalid format

    def test_find_file_by_date_invalid_format(self) -> None:
        """Test find_file_by_date with invalid date format."""
        files = ["backup_01-01-2023.tar.xz"]

        with patch("typer.echo") as mock_echo:
            result = find_file_by_date(files, "invalid-date")
            assert result is None
            mock_echo.assert_called_once_with(
                "Error: Invalid date format 'invalid-date'. Use dd-mm-yyyy"
            )

    def test_find_file_by_date_wrong_parts_count(self) -> None:
        """Test find_file_by_date with wrong number of date parts."""
        files = ["backup_01-01-2023.tar.xz"]

        with patch("typer.echo") as mock_echo:
            result = find_file_by_date(files, "01-01")
            assert result is None
            mock_echo.assert_called_once_with(
                "Error: Invalid date format '01-01'. Use dd-mm-yyyy"
            )


class TestMainFunctionality:
    """Test main module functionality."""

    def test_initialize_config_no_existing_config(self) -> None:
        """Test initialize_config when no config file exists."""
        with (
            patch("os.path.exists", return_value=False),
            patch("autotarcompress.logger.setup_basic_logging"),
            patch("autotarcompress.logger.setup_application_logging"),
            patch("autotarcompress.runner.BackupFacade") as mock_facade_class,
        ):
            mock_facade = MagicMock()
            mock_facade.config.config_path = "/fake/path"
            mock_facade.config.get_log_level.return_value = 20  # INFO level
            mock_facade.configure = (
                MagicMock()
            )  # Mock configure to prevent user input
            mock_facade_class.return_value = mock_facade

            result = initialize_config()

            # Just check that it returns a facade without crashing
            assert result is not None

    def test_initialize_config_existing_config(self) -> None:
        """Test initialize_config when config file exists."""
        with (
            patch("os.path.exists", return_value=True),
            patch("autotarcompress.logger.setup_application_logging"),
        ):
            mock_facade = MagicMock()
            mock_config = MagicMock()
            mock_loaded_config = MagicMock()

            mock_facade.config = mock_config
            mock_config.config_path = "/fake/path"
            mock_config.load.return_value = mock_loaded_config
            mock_loaded_config.get_log_level.return_value = 30  # WARNING level

            with patch(
                "autotarcompress.facade.BackupFacade", return_value=mock_facade
            ):
                result = initialize_config()

                # Just check it returns something without error
                assert result is not None

    def test_get_backup_files(self) -> None:
        """Test get_backup_files function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                "backup1.tar.xz",
                "backup2.tar.xz",
                "backup3.tar.xz.enc",  # Should be excluded
                "other.txt",  # Should be excluded
            ]

            for file in test_files:
                Path(temp_dir, file).touch()

            result = get_backup_files(temp_dir)
            expected = ["backup1.tar.xz", "backup2.tar.xz"]
            assert sorted(result) == sorted(expected)

    def test_get_encrypted_files(self) -> None:
        """Test get_encrypted_files function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                "backup1.tar.xz.enc",
                "backup2.tar.xz.enc",
                "backup3.tar.xz",  # Should be excluded
                "other.enc",
            ]

            for file in test_files:
                Path(temp_dir, file).touch()

            result = get_encrypted_files(temp_dir)
            expected = [
                "backup1.tar.xz.enc",
                "backup2.tar.xz.enc",
                "other.enc",
            ]
            assert sorted(result) == sorted(expected)
