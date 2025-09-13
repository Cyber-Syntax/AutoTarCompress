"""Tests for BackupConfig class and configuration management.

This module tests configuration loading, saving, validation, and path handling.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import BackupConfig


class TestBackupConfig:
    """Test BackupConfig functionality."""

    def test_config_initialization(self) -> None:
        """Test that BackupConfig initializes with proper defaults."""
        config = BackupConfig()
        # Path should be expanded automatically
        assert config.backup_folder.endswith("Documents/backup-for-cloud")
        assert config.config_dir.endswith(".config/autotarcompress")
        assert config.keep_backup == 1
        assert config.keep_enc_backup == 1
        assert config.dirs_to_backup == []
        assert config.ignore_list == []

    def test_config_path_expansion(self) -> None:
        """Test that paths are properly expanded in __post_init__."""
        config = BackupConfig()
        config.backup_folder = "~/test_backup"
        config.dirs_to_backup = ["~/Documents", "~/Pictures"]
        config.ignore_list = ["~/temp"]
        config.config_dir = "~/.config/test"

        # Trigger __post_init__ by creating a new instance
        config = BackupConfig(
            backup_folder="~/test_backup",
            dirs_to_backup=["~/Documents", "~/Pictures"],
            ignore_list=["~/temp"],
            config_dir="~/.config/test",
        )

        # Paths should be expanded
        assert not config.backup_folder.startswith("~")
        assert all(not path.startswith("~") for path in config.dirs_to_backup)
        assert all(not path.startswith("~") for path in config.ignore_list)
        assert not config.config_dir.startswith("~")

    def test_current_date_property(self) -> None:
        """Test that current_date returns expected format."""
        config = BackupConfig()
        date_str = config.current_date
        # Should be in format DD-MM-YYYY
        assert len(date_str) == 10
        assert date_str.count("-") == 2
        day, month, year = date_str.split("-")
        assert len(day) == 2
        assert len(month) == 2
        assert len(year) == 4

    def test_backup_path_property(self) -> None:
        """Test that backup_path generates correct path."""
        config = BackupConfig()
        backup_path = config.backup_path
        assert str(backup_path).endswith(".tar.xz")
        assert config.current_date in str(backup_path)

    def test_config_save(self, test_config: BackupConfig) -> None:
        """Test saving configuration to file."""
        test_config.dirs_to_backup = ["/test/dir1", "/test/dir2"]
        test_config.ignore_list = ["node_modules", ".git"]

        test_config.save()

        # Verify file was created and contains expected data
        assert test_config.config_path.exists()

        with open(test_config.config_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["dirs_to_backup"] == ["/test/dir1", "/test/dir2"]
        assert saved_data["ignore_list"] == ["node_modules", ".git"]
        assert "last_backup" not in saved_data  # Should not include removed field

    def test_config_load_existing(self, temp_dir: str) -> None:
        """Test loading configuration from existing file."""
        config_data = {
            "backup_folder": "~/test_backup",
            "config_dir": "~/.config/test",
            "keep_backup": 2,
            "keep_enc_backup": 3,
            "dirs_to_backup": ["~/Documents"],
            "ignore_list": ["node_modules"],
        }

        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        # Mock the config path to use our test file
        with patch.object(BackupConfig, "config_path", Path(config_path)):
            config = BackupConfig.load()

        assert config.keep_backup == 2
        assert config.keep_enc_backup == 3
        assert len(config.dirs_to_backup) == 1
        assert "node_modules" in config.ignore_list

    def test_config_load_with_invalid_json(self, temp_dir: str, caplog) -> None:
        """Test loading configuration with corrupted JSON."""
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        # Create corrupted JSON file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        with patch.object(BackupConfig, "config_path", Path(config_path)):
            config = BackupConfig.load()

        # Should return default config and log error
        assert config.backup_folder.endswith("Documents/backup-for-cloud")
        assert "Error reading config file" in caplog.text

    def test_config_load_filters_unknown_fields(self, temp_dir: str) -> None:
        """Test that loading old config with unknown fields works."""
        old_config_data = {
            "backup_folder": "~/Documents/backup-for-cloud/",
            "config_dir": "~/.config/autotarcompress",
            "keep_backup": 1,
            "keep_enc_backup": 1,
            "dirs_to_backup": ["~/Documents"],
            "ignore_list": ["node_modules"],
            "last_backup": "some_old_value",  # Should be filtered out
            "unknown_field": "should_be_ignored",  # Should be filtered out
        }

        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(old_config_data, f)

        with patch.object(BackupConfig, "config_path", Path(config_path)):
            config = BackupConfig.load()

        # Should load successfully without unknown fields
        assert not hasattr(config, "last_backup")
        assert not hasattr(config, "unknown_field")
        expected_docs_path = os.path.expanduser("~/Documents")
        assert config.dirs_to_backup == [expected_docs_path]

    def test_config_verify_valid(self, test_config: BackupConfig) -> None:
        """Test configuration verification when valid."""
        # Add backup directories to make config valid
        test_config.dirs_to_backup = ["/test/dir"]
        test_config.save()  # Create the config file

        # Create backup directory
        Path(test_config.backup_folder).mkdir(parents=True, exist_ok=True)

        # Mock the config_path to point to our test config
        with patch.object(BackupConfig, "config_path", test_config.config_path):
            is_valid, message = BackupConfig.verify_config()

        assert is_valid
        assert "Configuration is valid" in message

    def test_config_verify_missing_file(self) -> None:
        """Test config verification when config file is missing."""
        with patch.object(BackupConfig, "config_path", Path("/nonexistent/config.json")):
            is_valid, message = BackupConfig.verify_config()

        assert not is_valid
        assert "Configuration file not found" in message

    def test_config_verify_no_backup_dirs(self, test_config: BackupConfig) -> None:
        """Test config verification when no backup directories are configured."""
        test_config.dirs_to_backup = []
        test_config.save()

        with patch.object(BackupConfig, "config_path", test_config.config_path):
            is_valid, message = BackupConfig.verify_config()

        assert not is_valid
        assert "No backup directories configured" in message
