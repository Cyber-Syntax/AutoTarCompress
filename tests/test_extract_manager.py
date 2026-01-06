"""Tests for the ExtractManager class.

This module contains comprehensive tests for the extract manager
implementation, including mocking external processes and testing
error conditions.
"""

import logging
import subprocess
import tarfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autotarcompress.config import BackupConfig
from autotarcompress.extract_manager import ExtractManager


class TestExtractManager:
    """Test cases for ExtractManager class."""

    @pytest.fixture(autouse=True)
    def mock_pv_unavailable(self) -> Generator:
        """Mock is_pv_available to return False for all tests."""
        with patch(
            "autotarcompress.extract_manager.is_pv_available",
            return_value=False,
        ):
            yield

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        return BackupConfig()

    @pytest.fixture
    def extract_manager(self, mock_config: BackupConfig) -> ExtractManager:
        """Create an ExtractManager instance for testing."""
        return ExtractManager(mock_config)

    def test_extract_manager_initialization(
        self, mock_config: BackupConfig
    ) -> None:
        """Test ExtractManager initialization."""
        manager = ExtractManager(mock_config)

        assert manager.config == mock_config
        assert isinstance(manager.logger, logging.Logger)
        assert manager.logger.name == "autotarcompress.extract_manager"

    @patch("pathlib.Path.mkdir")
    @patch("tarfile.open")
    def test_execute_extract_successful_zst(
        self,
        mock_tarfile_open: Mock,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
    ) -> None:
        """Test successful extraction of zst archive."""
        archive_file = tmp_path / "test.tar.zst"
        archive_file.write_text("dummy")

        # Mock tarfile operations
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "test_file.txt"
        mock_member.size = 100
        mock_tar.getmembers.return_value = [mock_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        result = extract_manager.execute_extract(str(archive_file))

        assert result is True
        mock_mkdir.assert_called_once()
        mock_tarfile_open.assert_called_once_with(str(archive_file), "r:zst")
        mock_tar.extract.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("tarfile.open")
    def test_execute_extract_successful_xz(
        self,
        mock_tarfile_open: Mock,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
    ) -> None:
        """Test successful extraction of xz archive."""
        archive_file = tmp_path / "test.tar.xz"
        archive_file.write_text("dummy")

        # Mock tarfile operations
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "test_file.txt"
        mock_member.size = 100
        mock_tar.getmembers.return_value = [mock_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        result = extract_manager.execute_extract(str(archive_file))

        assert result is True
        mock_mkdir.assert_called_once()
        mock_tarfile_open.assert_called_once_with(str(archive_file), "r:xz")
        mock_tar.extract.assert_called_once()

    @patch(
        "autotarcompress.extract_manager.is_pv_available",
        return_value=True,
    )
    @patch("pathlib.Path.mkdir")
    @patch("subprocess.run")
    @patch("pathlib.Path.stat")
    def test_execute_extract_with_pv_xz(
        self,
        mock_stat: Mock,
        mock_subprocess: Mock,
        mock_mkdir: Mock,
        mock_pv_available: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
    ) -> None:
        """Test extraction uses pv for xz archives when available."""
        archive_file = tmp_path / "test.tar.xz"
        archive_file.write_text("dummy")
        mock_stat.return_value.st_size = 1000000

        result = extract_manager.execute_extract(str(archive_file))

        assert result is True
        mock_subprocess.assert_called_once()
        # Check that pv command is used
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "pv -s 1000000" in cmd
        assert "tar -xJ" in cmd

    @patch("pathlib.Path.mkdir")
    @patch("tarfile.open")
    def test_execute_extract_path_traversal_attack(
        self,
        mock_tarfile_open: Mock,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction prevents path traversal attacks."""
        archive_file = tmp_path / "test.tar.zst"
        archive_file.write_text("dummy")

        # Mock tarfile with malicious path
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "../../../etc/passwd"
        mock_member.size = 100
        mock_tar.getmembers.return_value = [mock_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        # Mock path operations to simulate path traversal
        with patch("pathlib.Path.absolute") as mock_absolute:
            mock_absolute.side_effect = [
                Path("/safe/extract/dir"),
                Path("/etc/passwd"),  # Outside extract directory
            ]

            with caplog.at_level(logging.ERROR):
                result = extract_manager.execute_extract(str(archive_file))

                assert result is False
                assert "Attempted path traversal" in caplog.text
                mock_tar.extract.assert_not_called()

    @patch("pathlib.Path.mkdir")
    def test_execute_extract_tarfile_error(
        self,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction handles TarError gracefully."""
        archive_file = tmp_path / "test.tar.zst"
        archive_file.write_text("dummy")

        with patch(
            "tarfile.open", side_effect=tarfile.TarError("Invalid tar file")
        ):
            with caplog.at_level(logging.ERROR):
                result = extract_manager.execute_extract(str(archive_file))

                assert result is False
                assert "Extraction failed" in caplog.text

    @patch("pathlib.Path.mkdir")
    def test_execute_extract_general_exception(
        self,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction handles OS exceptions."""
        archive_file = tmp_path / "test.tar.zst"
        archive_file.write_text("dummy")

        with patch("tarfile.open", side_effect=OSError("Unexpected error")):
            with caplog.at_level(logging.ERROR):
                result = extract_manager.execute_extract(str(archive_file))

                assert result is False
                assert "Unexpected error during extraction" in caplog.text

    def test_execute_extract_unsupported_format(
        self,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction fails for unsupported file formats."""
        archive_file = tmp_path / "test.zip"
        archive_file.write_text("dummy")

        with caplog.at_level(logging.ERROR):
            result = extract_manager.execute_extract(str(archive_file))

            assert result is False
            assert "Unsupported file format" in caplog.text

    @patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied"))
    def test_execute_extract_directory_creation_fails(
        self,
        mock_mkdir: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction fails when directory creation fails."""
        archive_file = tmp_path / "test.tar.zst"
        archive_file.write_text("dummy")

        with caplog.at_level(logging.ERROR):
            result = extract_manager.execute_extract(str(archive_file))

            assert result is False
            assert "Failed to create extraction directory" in caplog.text

    @patch(
        "autotarcompress.extract_manager.is_pv_available", return_value=True
    )
    @patch("pathlib.Path.mkdir")
    @patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "tar")
    )
    @patch("pathlib.Path.stat")
    def test_execute_extract_pv_fails(
        self,
        mock_stat: Mock,
        mock_subprocess: Mock,
        mock_mkdir: Mock,
        mock_pv_available: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction fails gracefully when pv subprocess fails."""
        archive_file = tmp_path / "test.tar.xz"
        archive_file.write_text("dummy")
        mock_stat.return_value.st_size = 1000000

        with caplog.at_level(logging.ERROR):
            result = extract_manager.execute_extract(str(archive_file))

            assert result is False
            assert "Extraction with pv failed" in caplog.text

    @patch(
        "autotarcompress.extract_manager.is_pv_available", return_value=True
    )
    @patch("pathlib.Path.mkdir")
    @patch("subprocess.run", side_effect=OSError("Permission denied"))
    @patch("pathlib.Path.stat")
    def test_execute_extract_pv_os_error(
        self,
        mock_stat: Mock,
        mock_subprocess: Mock,
        mock_mkdir: Mock,
        mock_pv_available: Mock,
        extract_manager: ExtractManager,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction fails gracefully when pv encounters OS error."""
        archive_file = tmp_path / "test.tar.xz"
        archive_file.write_text("dummy")
        mock_stat.return_value.st_size = 1000000

        with caplog.at_level(logging.ERROR):
            result = extract_manager.execute_extract(str(archive_file))

            assert result is False
            assert "Error during extraction" in caplog.text
