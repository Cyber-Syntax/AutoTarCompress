"""Shared pytest fixtures for AutoTarCompress tests.

This module contains common fixtures used across multiple test modules.
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Generator

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.config import BackupConfig


@pytest.fixture
def temp_dir() -> Generator[str]:
    """Create a temporary directory for testing that gets cleaned up afterwards."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir: str) -> BackupConfig:
    """Create a test configuration for backup manager.

    Uses a temporary directory to ensure tests don't pollute
    the real user configuration directory.
    """
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
    """Create test backup files for testing."""
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
    """Create test data for backup."""
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


@pytest.fixture
def mock_backup_info() -> dict[str, str | int | list[str]]:
    """Create mock backup info data."""
    return {
        "backup_file": "13-09-2025.tar.xz",
        "backup_path": "/tmp/test_backups/13-09-2025.tar.xz",
        "backup_date": "2025-09-13T10:30:45.123456",
        "backup_size_bytes": 1073741824,  # 1 GB
        "backup_size_human": "1.00 GB",
        "directories_backed_up": [
            "/home/user/Documents",
            "/home/user/Pictures",
        ],
    }
