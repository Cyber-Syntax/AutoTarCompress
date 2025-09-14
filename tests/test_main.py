"""Tests for main module functionality.

This module tests the main application entry point and initialization.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autotarcompress.main import (
    get_backup_files,
    get_encrypted_files,
    initialize_config,
)


class TestMainFunctionality:
    """Test main module functionality."""

    def test_initialize_config_no_existing_config(self) -> None:
        """Test initialize_config when no config file exists."""
        with patch("os.path.exists", return_value=False), patch(
            "autotarcompress.main.setup_basic_logging"
        ) as mock_basic_logging, patch(
            "autotarcompress.main.setup_application_logging"
        ) as mock_app_logging:
            mock_facade = MagicMock()
            mock_facade.config.config_path = "/fake/path"
            mock_facade.config.get_log_level.return_value = 20  # INFO level

            with patch("autotarcompress.main.BackupFacade", return_value=mock_facade):
                result = initialize_config()

                mock_basic_logging.assert_called_once()
                mock_facade.configure.assert_called_once()
                mock_app_logging.assert_called_once_with(20)
                assert result == mock_facade

    def test_initialize_config_existing_config(self) -> None:
        """Test initialize_config when config file exists."""
        with patch("os.path.exists", return_value=True), patch(
            "autotarcompress.main.setup_application_logging"
        ) as mock_app_logging:
            mock_facade = MagicMock()
            mock_config = MagicMock()
            mock_loaded_config = MagicMock()

            mock_facade.config = mock_config
            mock_config.config_path = "/fake/path"
            mock_config.load.return_value = mock_loaded_config
            mock_loaded_config.get_log_level.return_value = 30  # WARNING level

            with patch("autotarcompress.main.BackupFacade", return_value=mock_facade):
                result = initialize_config()

                mock_config.load.assert_called_once()
                mock_app_logging.assert_called_once_with(30)
                assert result == mock_facade
                # Verify config was replaced with loaded config
                assert mock_facade.config == mock_loaded_config

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
            expected = ["backup1.tar.xz.enc", "backup2.tar.xz.enc", "other.enc"]
            assert sorted(result) == sorted(expected)
