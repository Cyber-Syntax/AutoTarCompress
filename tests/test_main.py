"""Tests for main module functionality.

This module tests the main application entry point and initialization.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import os
import sys
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.cli import app
from autotarcompress.cli.runner import (
    find_file_by_date,
    get_backup_files,
    get_encrypted_files,
    initialize_config,
)
from autotarcompress.config import BackupConfig
from autotarcompress.main import main


class TestMainModule:
    """Test main module functionality."""

    def test_initialize_config_no_existing_config(self) -> None:
        """Test initialize_config when no config file exists."""
        with (
            patch.object(BackupConfig, "load") as mock_load,
            patch.object(os.path, "exists", return_value=False),
            patch("autotarcompress.logger.setup_basic_logging"),
            patch("autotarcompress.logger.setup_application_logging"),
            patch.object(BackupConfig, "create_default") as mock_create,
        ):
            mock_config = BackupConfig()
            mock_load.return_value = mock_config
            mock_create.return_value = mock_config

            result = initialize_config()
            assert result is not None
            assert isinstance(result, BackupConfig)
            mock_create.assert_called_once()

    def test_initialize_config_existing_config(self) -> None:
        """Test initialize_config when config file exists."""
        with (
            patch.object(BackupConfig, "load") as mock_load,
            patch.object(os.path, "exists", return_value=True),
            patch("autotarcompress.logger.setup_application_logging"),
        ):
            mock_config = BackupConfig()
            mock_load.return_value = mock_config

            result = initialize_config()
            assert result is not None
            assert isinstance(result, BackupConfig)
            assert result == mock_config

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
        with patch("autotarcompress.cli.runner.initialize_config"):
            result = self.runner.invoke(app, ["encrypt"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_encrypt_multiple_options_error(self) -> None:
        """Test encrypt command with multiple options shows error."""
        with patch("autotarcompress.cli.runner.initialize_config"):
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
        with patch("autotarcompress.cli.runner.initialize_config"):
            result = self.runner.invoke(app, ["decrypt"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_extract_no_options_error(self) -> None:
        """Test extract command without any options shows error."""
        with patch("autotarcompress.cli.runner.initialize_config"):
            result = self.runner.invoke(app, ["extract"])
            assert result.exit_code == 1
            assert (
                "Must specify one of --latest, --date, or file argument"
                in result.stdout
            )

    def test_cleanup_multiple_options_error(self) -> None:
        """Test cleanup command with multiple options shows error."""
        with patch("autotarcompress.cli.runner.initialize_config"):
            result = self.runner.invoke(
                app, ["cleanup", "--all", "--keep", "5"]
            )
            assert result.exit_code == 1
            assert (
                "Only one of --all, --older-than, or --keep can be specified"
                in result.stdout
            )

    # TODO: These tests need to be rewritten for the new architecture without BackupFacade
    # @patch("autotarcompress.cli.runner.initialize_config")
    # def test_backup_command_success(self, mock_init_config: MagicMock) -> None:
    #     """Test successful backup command execution."""
    #     ...

    # @patch("autotarcompress.cli.runner.initialize_config")
    # def test_backup_command_failure(self, mock_init_config: MagicMock) -> None:
    #     """Test backup command failure handling."""
    #     ...

    # @patch("autotarcompress.cli.runner.initialize_config")
    # def test_info_command_success(self, mock_init_config: MagicMock) -> None:
    #     """Test successful info command execution."""
    #     ...

    # @patch("autotarcompress.cli.runner.initialize_config")
    # def test_cleanup_command_success(
    #     self, mock_init_config: MagicMock
    # ) -> None:
    #     """Test successful cleanup command execution."""
    #     ...

    # @patch("autotarcompress.cli.runner.initialize_config")
    # def test_cleanup_command_all_success(
    #     self, mock_init_config: MagicMock
    # ) -> None:
    #     """Test successful cleanup --all command execution."""
    #     ...


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


# TODO: TestMainFunctionality class needs to be rewritten for new architecture
# The old facade-based architecture has been replaced with direct command execution
# class TestMainFunctionality:
#     """Test main module functionality."""
#
#     def test_initialize_config_no_existing_config(self) -> None:
#         """Test initialize_config when no config file exists."""
#         ...
#
#     def test_initialize_config_existing_config(self) -> None:
#         """Test initialize_config when config file exists."""
#         ...
#
#     def test_get_backup_files(self) -> None:
#         """Test get_backup_files function."""
#         ...
#
#     def test_get_encrypted_files(self) -> None:
#         """Test get_encrypted_files function."""
#         ...
