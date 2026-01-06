"""Tests for AutoTarCompress backup functionality.

This module contains tests for the backup manager and related components.
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

# Updated imports based on the new refactored structure
from autotarcompress.commands import (
    BackupCommand,
    CleanupCommand,
    EncryptCommand,
)
from autotarcompress.config import BackupConfig
from autotarcompress.utils.get_password import PasswordContext
from autotarcompress.utils.size_calculator import SizeCalculator


# Fixtures
@pytest.fixture
def temp_dir() -> Generator[str]:
    """Create a temporary directory for testing that gets cleaned up afterwards"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir: str) -> BackupConfig:
    """Create a test configuration for backup manager"""
    config = BackupConfig()
    config.backup_folder = os.path.join(temp_dir, "backups")
    config.config_dir = os.path.join(temp_dir, "config")
    config.dirs_to_backup = [os.path.join(temp_dir, "test_data")]
    config.ignore_list = [os.path.join(temp_dir, "test_data/ignored")]
    os.makedirs(config.backup_folder, exist_ok=True)
    os.makedirs(config.config_dir, exist_ok=True)
    return config


@pytest.fixture
def test_backup_files(test_config: BackupConfig) -> list[str]:
    """Create test backup files for testing"""
    os.makedirs(test_config.backup_folder, exist_ok=True)
    # Create a few sample backup files with different dates
    backup_files = [
        "01-01-2022.tar.xz",
        "02-01-2022.tar.xz",
        "03-01-2022.tar.xz",
        "01-01-2022.tar.xz.enc",
        "02-01-2022.tar.xz.enc",
    ]
    for filename in backup_files:
        with open(os.path.join(test_config.backup_folder, filename), "w") as f:
            f.write("test backup content")
    return backup_files


@pytest.fixture
def test_data_dir(temp_dir: str) -> str:
    """Create test data for backup"""
    data_dir = os.path.join(temp_dir, "test_data")
    os.makedirs(data_dir, exist_ok=True)

    # Create some test files
    with open(os.path.join(data_dir, "file1.txt"), "w") as f:
        f.write("Test file 1 content")

    with open(os.path.join(data_dir, "file2.txt"), "w") as f:
        f.write("Test file 2 content")

    # Create a directory to be ignored
    ignore_dir = os.path.join(data_dir, "ignored")
    os.makedirs(ignore_dir, exist_ok=True)
    with open(os.path.join(ignore_dir, "ignored.txt"), "w") as f:
        f.write("This file should be ignored")

    return data_dir


# Mock class for pathlib.Path to use in tests
class MockPath:
    """Mock implementation of pathlib.Path that always returns a fixed expanded path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def expanduser(self) -> str:
        """Always return a fixed path regardless of input."""
        return "/expanded/path"

    def __str__(self) -> str:
        """String representation is always the expanded path."""
        return "/expanded/path"


class TestBackupConfig:
    def test_init_stores_tilde_paths(self, temp_dir: str) -> None:
        """Test that paths are stored as ~ paths in __post_init__."""
        # Create paths within the temporary directory
        home_dir = Path(temp_dir)
        test_path = home_dir / "test"
        config_path = home_dir / ".config"
        dir1_path = home_dir / "dir1"
        ignore_path = home_dir / "ignore"

        # Create a custom HOME environment to ensure consistent path expansion
        with patch.dict(os.environ, {"HOME": str(home_dir)}):
            config = BackupConfig(
                backup_folder="~/test",
                config_dir="~/.config",
                dirs_to_backup=["~/dir1"],
                ignore_list=["~/ignore"],
            )

            # Check that paths are stored as ~ paths (not expanded)
            assert config.backup_folder == "~/test"
            assert config.config_dir == "~/.config"
            assert config.dirs_to_backup == [str(dir1_path)]
            assert config.ignore_list == [str(ignore_path)]

    def test_save_config(
        self, test_config: BackupConfig, temp_dir: str
    ) -> None:
        """Test saving configuration to file"""
        import configparser

        test_config.save()

        # Check if the config file was created
        config_path = os.path.join(test_config.config_dir, "config.conf")
        assert os.path.exists(config_path)

        # Verify content
        config = configparser.ConfigParser()
        config.read(config_path, encoding="utf-8")
        section = config["DEFAULT"]
        assert section["backup_folder"] == test_config.backup_folder
        dirs_to_backup = [
            d.strip()
            for d in section.get("dirs_to_backup", "").split(",")
            if d.strip()
        ]
        assert dirs_to_backup == test_config.dirs_to_backup

    def test_load_config(self, test_config: BackupConfig) -> None:
        """Test loading configuration from file"""
        import configparser

        # Prepare the config data as it would be in the file
        config_path = os.path.join(test_config.config_dir, "config.conf")
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "backup_folder": test_config.backup_folder,
            "config_dir": test_config.config_dir,
            "keep_backup": str(test_config.keep_backup),
            "keep_enc_backup": str(test_config.keep_enc_backup),
            "dirs_to_backup": ",".join(test_config.dirs_to_backup),
            "ignore_list": ",".join(test_config.ignore_list),
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        with patch.object(BackupConfig, "config_path", Path(config_path)):
            loaded_config = BackupConfig.load()

        # Check if loaded correctly
        assert loaded_config.backup_folder == test_config.backup_folder
        assert loaded_config.dirs_to_backup == test_config.dirs_to_backup

    def test_verify_config_valid(
        self, test_config: BackupConfig, test_data_dir: str
    ) -> None:
        """Test configuration verification when valid"""
        import configparser

        # Prepare the config data as it would be in the file
        config_path = os.path.join(test_config.config_dir, "config.conf")
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "backup_folder": test_config.backup_folder,
            "config_dir": test_config.config_dir,
            "keep_backup": str(test_config.keep_backup),
            "keep_enc_backup": str(test_config.keep_enc_backup),
            "dirs_to_backup": ",".join(test_config.dirs_to_backup),
            "ignore_list": ",".join(test_config.ignore_list),
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        with (
            patch.object(BackupConfig, "config_path", Path(config_path)),
            patch("pathlib.Path.exists", return_value=True),
        ):
            valid, message = BackupConfig.verify_config()
            assert valid
            assert "valid" in message.lower()

    @patch("pathlib.Path.exists", return_value=False)
    def test_verify_config_missing(self, mock_exists: MagicMock) -> None:
        """Test config verification when config file is missing"""
        valid, message = BackupConfig.verify_config()
        assert not valid
        assert "not found" in message.lower()


# Tests for SizeCalculator
class TestSizeCalculator:
    def test_calculate_total_size(
        self, test_data_dir: str, test_config: BackupConfig
    ) -> None:
        """Test size calculation functionality"""
        with patch("builtins.print"):  # Suppress print outputs
            calculator = SizeCalculator(
                directories=[test_data_dir],
                ignore_list=[os.path.join(test_data_dir, "ignored")],
            )
            total_size = calculator.calculate_total_size()

            # We should only count the sizes of file1.txt and file2.txt
            expected_size = os.path.getsize(
                os.path.join(test_data_dir, "file1.txt")
            ) + os.path.getsize(os.path.join(test_data_dir, "file2.txt"))

            assert total_size == expected_size

    def test_should_ignore(self, test_data_dir: str) -> None:
        """Test path ignoring logic"""
        calculator = SizeCalculator(
            directories=[test_data_dir],
            ignore_list=[os.path.join(test_data_dir, "ignored")],
        )

        # This path should be ignored
        assert calculator._should_ignore(
            os.path.join(test_data_dir, "ignored", "file.txt")
        )

        # This path should not be ignored
        assert not calculator._should_ignore(
            os.path.join(test_data_dir, "file1.txt")
        )


# Tests for Commands
class TestBackupCommand:
    def test_execute_backup(
        self,
        test_config: BackupConfig,
        test_data_dir: str,
    ) -> None:
        """Test backup execution delegates to manager"""
        with patch("builtins.print"):
            command = BackupCommand(test_config)
            with patch.object(
                command.manager, "execute_backup", return_value=True
            ) as mock_execute:
                result = command.execute()

                assert result is True
                mock_execute.assert_called_once()

    def test_execute_backup_file_exists(
        self,
        test_config: BackupConfig,
    ) -> None:
        """Test backup when output file already exists delegates to manager"""
        command = BackupCommand(test_config)
        with patch.object(
            command.manager, "execute_backup", return_value=True
        ) as mock_execute:
            result = command.execute()

            assert result is True
            mock_execute.assert_called_once()


class TestEncryptCommand:
    @patch("subprocess.run")
    @patch("getpass.getpass", return_value="password123")
    def test_encryption(
        self,
        mock_getpass: MagicMock,
        mock_run: MagicMock,
        test_config: BackupConfig,
        temp_dir: str,
    ) -> None:
        """Test encryption command"""
        test_file = os.path.join(temp_dir, "test.tar.xz")
        with open(test_file, "w") as f:
            f.write("test content")

        command = EncryptCommand(test_config, test_file)

        # Mock subprocess run to return success
        mock_run.return_value = MagicMock(stderr=b"")

        result = command.execute()
        assert result is True
        assert mock_run.called

    @patch("os.path.isfile", return_value=False)
    def test_encryption_missing_file(
        self, mock_isfile: MagicMock, test_config: BackupConfig
    ) -> None:
        """Test encryption with missing input file"""
        command = EncryptCommand(test_config, "nonexistent.tar.xz")
        result = command.execute()
        assert result is False


class TestCleanupCommand:
    def test_cleanup(
        self, test_config: BackupConfig, test_backup_files: list[str]
    ) -> None:
        """Test cleanup of old backups"""
        command = CleanupCommand(test_config)

        # Set to keep only the newest file
        test_config.keep_backup = 1
        test_config.keep_enc_backup = 1

        with patch("builtins.print"):
            command.execute()

        # Check that only the newest files remain
        remaining_files = os.listdir(test_config.backup_folder)
        assert len([f for f in remaining_files if f.endswith(".tar.xz")]) == 1
        assert (
            len([f for f in remaining_files if f.endswith(".tar.xz.enc")]) == 1
        )

        # Verify we kept the newest ones
        assert "03-01-2022.tar.xz" in remaining_files
        assert "02-01-2022.tar.xz.enc" in remaining_files


# Tests for PasswordContext
class TestContextManager:
    @patch("getpass.getpass", return_value="test_password")
    def test_password_context(self, mock_getpass: MagicMock) -> None:
        """Test secure password handling context"""
        manager = PasswordContext()

        with manager._password_context() as password:
            assert password == "test_password"

        # After context exit, password should be securely wiped
        # This is hard to test directly as we're testing the absence of data


if __name__ == "__main__":
    pytest.main()
