"""Tests for BackupConfig class and configuration management.

This module tests configuration loading, saving, validation, and path handling.
"""

import configparser
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autotarcompress.config import BackupConfig


class TestBackupConfig:
    """Test BackupConfig functionality."""

    def test_config_initialization(self) -> None:
        """Test that BackupConfig initializes with proper defaults."""
        config = BackupConfig()
        # Path should be expanded automatically
        assert config.backup_folder.endswith("Documents/backup-for-cloud")
        assert config.config_dir.endswith(".config/autotarcompress")
        assert config.keep_backup == 0
        assert config.keep_enc_backup == 1
        assert isinstance(config.dirs_to_backup, list)
        assert isinstance(config.ignore_list, list)

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

        config = configparser.ConfigParser()
        config.read(test_config.config_path, encoding="utf-8")
        section = config["DEFAULT"]

        def parse_multiline_list(val: str) -> list[str]:
            if not val:
                return []
            return [line.strip() for line in val.strip().splitlines() if line.strip()]

        dirs_to_backup = parse_multiline_list(section.get("dirs_to_backup", ""))
        ignore_list = parse_multiline_list(section.get("ignore_list", ""))
        assert dirs_to_backup == ["/test/dir1", "/test/dir2"]
        assert ignore_list == ["node_modules", ".git"]
        # No 'last_backup' field in INI config

    def test_config_load_existing(self, temp_dir: str) -> None:
        """Test loading configuration from existing file."""
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.conf")

        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "backup_folder": "~/test_backup",
            "config_dir": "~/.config/test",
            "keep_backup": "2",
            "keep_enc_backup": "3",
            "dirs_to_backup": "~/Documents",
            "ignore_list": "node_modules",
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        # Mock the config path to use our test file
        with patch.object(BackupConfig, "config_path", Path(config_path)):
            loaded = BackupConfig.load()

        assert loaded.keep_backup == 2
        assert loaded.keep_enc_backup == 3
        assert loaded.dirs_to_backup == [os.path.expanduser("~/Documents")]
        assert "node_modules" in loaded.ignore_list

    def test_config_load_with_invalid_ini(self, temp_dir: str, caplog) -> None:
        """Test loading configuration with corrupted INI."""
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.conf")

        # Create corrupted INI file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("[DEFAULT]\nbackup_folder = /broken\n[broken")

        with patch.object(BackupConfig, "config_path", Path(config_path)):
            loaded = BackupConfig.load()

        # Should return default config and log error
        assert loaded.backup_folder.endswith("Documents/backup-for-cloud")
        assert "Error reading config file" in caplog.text

    def test_config_load_filters_unknown_fields(self, temp_dir: str) -> None:
        """Test that loading old config with unknown fields works (INI ignores unknowns)."""
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.conf")

        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "backup_folder": "~/Documents/backup-for-cloud/",
            "config_dir": "~/.config/autotarcompress",
            "keep_backup": "1",
            "keep_enc_backup": "1",
            "dirs_to_backup": "~/Documents",
            "ignore_list": "node_modules",
            # Unknown fields are simply ignored by configparser
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        with patch.object(BackupConfig, "config_path", Path(config_path)):
            loaded = BackupConfig.load()

        assert not hasattr(loaded, "last_backup")
        expected_docs_path = os.path.expanduser("~/Documents")
        assert loaded.dirs_to_backup == [expected_docs_path]

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
        with patch.object(BackupConfig, "config_path", Path("/nonexistent/config.conf")):
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
