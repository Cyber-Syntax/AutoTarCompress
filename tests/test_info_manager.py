"""Tests for the InfoManager class.

This module contains comprehensive tests for the info manager
implementation, including mocking file operations and testing
error conditions.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from autotarcompress.config import BackupConfig
from autotarcompress.info_manager import InfoManager


class TestInfoManager:
    """Test cases for InfoManager class."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        config = BackupConfig()
        config.config_dir = "~/.config/autotarcompress"
        return config

    @pytest.fixture
    def info_manager(self, mock_config: BackupConfig) -> InfoManager:
        """Create an InfoManager instance for testing."""
        return InfoManager(mock_config)

    def test_info_manager_initialization(
        self, mock_config: BackupConfig
    ) -> None:
        """Test InfoManager initialization."""
        manager = InfoManager(mock_config)

        assert manager.config == mock_config
        assert isinstance(manager.logger, logging.Logger)

    def test_execute_info_no_metadata_file(
        self, info_manager: InfoManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute_info when metadata.json does not exist."""
        with (
            patch.object(info_manager, "_load_backup_info", return_value=None),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is False
        assert "No backup information found." in caplog.text
        assert (
            "This usually means no backups have been created yet."
            in caplog.text
        )

    def test_execute_info_with_valid_metadata(
        self,
        info_manager: InfoManager,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Test execute_info with valid metadata.json."""
        # Create a temporary metadata.json
        metadata = {
            "backup_file": "test-01-01-2025.tar.zst",
            "backup_path": str(tmp_path / "test-01-01-2025.tar.zst"),
            "backup_date": "01-01-2025",
            "backup_size_human": "1.2 MB",
            "directories_backed_up": ["/home/user/docs", "/home/user/code"],
        }

        with (
            patch.object(
                info_manager, "_load_backup_info", return_value=metadata
            ),
            patch.object(Path, "exists", return_value=True),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is True
        assert "===== Last Backup Information =====" in caplog.text
        assert "Backup File: test-01-01-2025.tar.zst" in caplog.text
        assert "Full Path:" in caplog.text
        assert "Backup Date: 01-01-2025" in caplog.text
        assert "Backup Size: 1.2 MB" in caplog.text
        assert "Directories Backed Up (2):" in caplog.text
        assert "/home/user/docs" in caplog.text
        assert "/home/user/code" in caplog.text
        assert "Status: ✓ Backup file exists" in caplog.text

    def test_execute_info_backup_file_not_exists(
        self,
        info_manager: InfoManager,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """Test execute_info when backup file does not exist."""
        metadata = {
            "backup_file": "test-01-01-2025.tar.zst",
            "backup_path": str(tmp_path / "test-01-01-2025.tar.zst"),
            "backup_date": "01-01-2025",
            "backup_size_human": "1.2 MB",
            "directories_backed_up": ["/home/user/docs"],
        }

        with (
            patch.object(
                info_manager, "_load_backup_info", return_value=metadata
            ),
            patch.object(Path, "exists", return_value=False),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is True
        assert "Status: ✗ Backup file not found" in caplog.text

    def test_execute_info_invalid_json(
        self, info_manager: InfoManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute_info with invalid JSON in metadata.json."""
        with (
            patch.object(info_manager, "_load_backup_info", return_value=None),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is False
        assert "No backup information found." in caplog.text

    def test_execute_info_file_read_error(
        self, info_manager: InfoManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute_info when file cannot be read."""
        with (
            patch.object(info_manager, "_load_backup_info", return_value=None),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is False
        assert "No backup information found." in caplog.text

    def test_execute_info_no_backup_file_key(
        self, info_manager: InfoManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test execute_info when metadata.json has no backup_file key."""
        metadata = {"some_other_key": "value"}

        with (
            patch.object(
                info_manager, "_load_backup_info", return_value=metadata
            ),
            caplog.at_level(logging.INFO),
        ):
            result = info_manager.execute_info()

        assert result is False
        assert "No backup information found." in caplog.text
