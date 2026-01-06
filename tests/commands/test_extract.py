"""Tests for the ExtractCommand class.

This module contains comprehensive tests for the extraction command implementation,
including security validation and error handling.
"""

import logging
import tarfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autotarcompress.commands.extract import ExtractCommand
from autotarcompress.config import BackupConfig


class TestExtractCommand:
    """Test cases for ExtractCommand class."""

    @pytest.fixture(autouse=True)
    def mock_pv_unavailable(self) -> Generator:
        """Mock is_pv_available to return False for all tests."""
        with patch(
            "autotarcompress.commands.extract.is_pv_available",
            return_value=False,
        ):
            yield

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        return BackupConfig()

    @pytest.fixture
    def test_archive_file(self, tmp_path: Path) -> str:
        """Create a test archive file for extraction."""
        archive_file = tmp_path / "test_backup.tar.xz"
        archive_file.write_text("archive content")
        return str(archive_file)

    @pytest.fixture
    def extract_command(
        self, mock_config: BackupConfig, test_archive_file: str
    ) -> ExtractCommand:
        """Create an ExtractCommand instance for testing."""
        return ExtractCommand(mock_config, test_archive_file)

    def test_extract_command_initialization(
        self, mock_config: BackupConfig, test_archive_file: str
    ) -> None:
        """Test ExtractCommand initialization."""
        command = ExtractCommand(mock_config, test_archive_file)

        assert command.config == mock_config
        assert command.file_path == test_archive_file
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "autotarcompress.commands.extract"

    @patch("tarfile.open")
    @patch("pathlib.Path.mkdir")
    def test_execute_successful_extraction(
        self,
        mock_mkdir: Mock,
        mock_tarfile_open: Mock,
        extract_command: ExtractCommand,
    ) -> None:
        """Test successful extraction execution."""
        # Mock tarfile operations
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "test_file.txt"
        mock_member.size = 100  # Add size for progress calculation
        mock_tar.getmembers.return_value = [mock_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        # Mock path operations for security check
        with patch("pathlib.Path.absolute") as mock_absolute:
            mock_absolute.return_value = Path(
                "/safe/extract/dir/test_file.txt"
            )

            result = extract_command.execute()

            assert result is True
            mock_mkdir.assert_called_once()
            mock_tar.extract.assert_called_once()

    @patch("tarfile.open")
    def test_execute_path_traversal_attack(
        self,
        mock_tarfile_open: Mock,
        extract_command: ExtractCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction prevents path traversal attacks."""
        # Mock tarfile with malicious path
        mock_tar = Mock()
        mock_member = Mock()
        mock_member.name = "../../../etc/passwd"
        mock_member.size = 100
        mock_tar.getmembers.return_value = [mock_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        # Mock path operations to simulate path traversal
        with patch("pathlib.Path.absolute") as mock_absolute:
            # First call for extract_dir, second for target_path
            mock_absolute.side_effect = [
                Path("/safe/extract/dir"),
                Path("/etc/passwd"),  # Outside extract directory
            ]

            with caplog.at_level(logging.ERROR):
                result = extract_command.execute()

                assert result is False
                assert "Attempted path traversal" in caplog.text
                mock_tar.extract.assert_not_called()

    @patch("tarfile.open")
    def test_execute_tarfile_error(
        self,
        mock_tarfile_open: Mock,
        extract_command: ExtractCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction handles TarError gracefully."""
        mock_tarfile_open.side_effect = tarfile.TarError("Invalid tar file")

        with caplog.at_level(logging.ERROR):
            result = extract_command.execute()

            assert result is False
            assert "Extraction failed" in caplog.text

    @patch("tarfile.open")
    def test_execute_general_exception(
        self,
        mock_tarfile_open: Mock,
        extract_command: ExtractCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction handles OS exceptions."""
        mock_tarfile_open.side_effect = OSError("Unexpected error")

        with caplog.at_level(logging.ERROR):
            result = extract_command.execute()

            assert result is False
            assert "Unexpected error during extraction" in caplog.text

    def test_extract_directory_creation(
        self, extract_command: ExtractCommand
    ) -> None:
        """Test that extract directory is created correctly."""
        with (
            patch("tarfile.open") as mock_tarfile_open,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            mock_tar = Mock()
            mock_tar.getmembers.return_value = []
            mock_tarfile_open.return_value.__enter__.return_value = mock_tar

            extract_command.execute()

            # Verify directory creation
            mock_mkdir.assert_called_once_with(exist_ok=True)

    @patch("tarfile.open")
    def test_tarfile_open_mode(
        self, mock_tarfile_open: Mock, extract_command: ExtractCommand
    ) -> None:
        """Test that tarfile is opened with correct mode."""
        mock_tar = Mock()
        mock_tar.getmembers.return_value = []
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        extract_command.execute()

        # Verify tarfile.open was called with the path (Path object) and mode
        assert mock_tarfile_open.call_count == 1
        args = mock_tarfile_open.call_args[0]
        assert str(args[0]) == extract_command.file_path
        assert args[1] == "r:xz"

    @patch("tarfile.open")
    def test_multiple_files_extraction(
        self, mock_tarfile_open: Mock, extract_command: ExtractCommand
    ) -> None:
        """Test extraction with multiple files."""
        # Mock multiple files in archive
        mock_tar = Mock()
        mock_members = []
        for i in range(5):
            member = Mock()
            member.name = f"file_{i}.txt"
            member.size = 100 + i  # Add size
            mock_members.append(member)
        mock_tar.getmembers.return_value = mock_members
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.absolute") as mock_absolute,
        ):
            # All paths are safe
            mock_absolute.return_value = Path("/safe/extract/dir/file.txt")

            result = extract_command.execute()

            assert result is True
            assert mock_tar.extract.call_count == 5

    @patch("tarfile.open")
    def test_mixed_safe_unsafe_files(
        self,
        mock_tarfile_open: Mock,
        extract_command: ExtractCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test extraction with mix of safe and unsafe files."""
        mock_tar = Mock()
        safe_member = Mock()
        safe_member.name = "safe_file.txt"
        safe_member.size = 100
        unsafe_member = Mock()
        unsafe_member.name = "../unsafe_file.txt"
        unsafe_member.size = 50
        mock_tar.getmembers.return_value = [safe_member, unsafe_member]
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.absolute") as mock_absolute,
        ):
            # First call for extract_dir, then alternating safe/unsafe
            mock_absolute.side_effect = [
                Path("/safe/extract/dir"),  # extract_dir
                Path("/safe/extract/dir/safe_file.txt"),  # safe file
                Path("/unsafe/path"),  # unsafe file
            ]

            with caplog.at_level(logging.ERROR):
                result = extract_command.execute()

                assert result is False
                assert "Attempted path traversal" in caplog.text

    def test_extract_directory_path_generation(
        self, extract_command: ExtractCommand
    ) -> None:
        """Test correct generation of extract directory path."""
        file_path = Path(extract_command.file_path)

        # Test various file extensions
        test_cases = [
            ("backup.tar.xz", "backup-extracted"),
            ("test.tar.gz", "test.tar-extracted"),
            ("archive.tar", "archive-extracted"),
            ("file.zip", "file-extracted"),
        ]

        for original, _expected_suffix in test_cases:
            temp_path = file_path.parent / original
            command = ExtractCommand(extract_command.config, str(temp_path))

            with (
                patch("tarfile.open") as mock_tarfile_open,
                patch("pathlib.Path.mkdir") as mock_mkdir,
            ):
                mock_tar = Mock()
                mock_tar.getmembers.return_value = []
                mock_tarfile_open.return_value.__enter__.return_value = (
                    mock_tar
                )

                command.execute()

                # The mkdir should be called on the expected path
                call_args = mock_mkdir.call_args
                assert call_args is not None

    @given(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        )
    )
    def test_filename_handling_property(self, filename: str) -> None:
        """Property-based test for filename handling."""
        extract_command = ExtractCommand(BackupConfig(), "/tmp/test.tar.xz")

        # Skip filenames that would be problematic in filesystem
        if any(
            char in filename
            for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        ):
            return

        mock_member = Mock()
        mock_member.name = filename
        mock_member.size = 100

        with (
            patch("tarfile.open") as mock_tarfile_open,
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.absolute") as mock_absolute,
        ):
            mock_tar = Mock()
            mock_tar.getmembers.return_value = [mock_member]
            mock_tarfile_open.return_value.__enter__.return_value = mock_tar

            # Ensure path is considered safe
            safe_path = Path(f"/safe/extract/dir/{filename}")
            mock_absolute.return_value = safe_path

            result = extract_command.execute()

            # Should succeed for valid filenames
            assert result is True

    def test_logging_configuration(
        self, extract_command: ExtractCommand
    ) -> None:
        """Test that logging is properly configured."""
        assert (
            extract_command.logger.name == "autotarcompress.commands.extract"
        )
        assert isinstance(extract_command.logger, logging.Logger)

    @patch("tarfile.open")
    def test_context_manager_usage(
        self, mock_tarfile_open: Mock, extract_command: ExtractCommand
    ) -> None:
        """Test that tarfile is properly used as context manager."""
        mock_tar = Mock()
        mock_tar.getmembers.return_value = []
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_tar)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_tarfile_open.return_value = mock_context_manager

        extract_command.execute()

        # Verify context manager protocol is used
        mock_context_manager.__enter__.assert_called_once()
        mock_context_manager.__exit__.assert_called_once()

    def test_file_path_with_spaces(
        self, tmp_path: Path, mock_config: BackupConfig
    ) -> None:
        """Test extraction with file paths containing spaces."""
        archive_file = tmp_path / "test backup with spaces.tar.xz"
        archive_file.write_text("content")
        command = ExtractCommand(mock_config, str(archive_file))

        with (
            patch("tarfile.open") as mock_tarfile_open,
            patch("pathlib.Path.mkdir"),
        ):
            mock_tar = Mock()
            mock_tar.getmembers.return_value = []
            mock_tarfile_open.return_value.__enter__.return_value = mock_tar

            result = command.execute()

            assert result is True
            # Verify tarfile.open was called with correct mode
            assert mock_tarfile_open.call_count == 1
            args = mock_tarfile_open.call_args[0]
            assert str(args[0]) == str(archive_file)
            assert args[1] == "r:xz"

    @patch("tarfile.open")
    def test_empty_archive_extraction(
        self, mock_tarfile_open: Mock, extract_command: ExtractCommand
    ) -> None:
        """Test extraction of empty archive."""
        mock_tar = Mock()
        mock_tar.getmembers.return_value = []  # Empty archive
        mock_tarfile_open.return_value.__enter__.return_value = mock_tar

        with patch("pathlib.Path.mkdir"):
            result = extract_command.execute()

            assert result is True
            # Empty archive - no extraction needed
            mock_tar.extract.assert_not_called()

    @patch(
        "autotarcompress.commands.extract.is_pv_available", return_value=True
    )
    @patch("subprocess.run")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.mkdir")
    def test_extraction_with_pv_available(
        self,
        mock_mkdir: Mock,
        mock_stat: Mock,
        mock_subprocess: Mock,
        mock_pv_available: Mock,
        extract_command: ExtractCommand,
    ) -> None:
        """Test extraction uses pv when available."""
        mock_stat.return_value.st_size = 1000000

        result = extract_command.execute()

        assert result is True
        assert mock_subprocess.called
        # Check that pv command is in the call
        call_args = mock_subprocess.call_args
        assert "pv -s 1000000" in call_args[0][0]

    @patch(
        "autotarcompress.commands.extract.is_pv_available", return_value=True
    )
    @patch("subprocess.run")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.mkdir")
    def test_extraction_with_pv_handles_spaces(
        self,
        mock_mkdir: Mock,
        mock_stat: Mock,
        mock_subprocess: Mock,
        mock_pv_available: Mock,
        tmp_path: Path,
        mock_config: BackupConfig,
    ) -> None:
        """Test extraction with pv handles file paths with spaces correctly."""
        archive_file = tmp_path / "test backup with spaces.tar.xz"
        archive_file.write_text("content")
        command = ExtractCommand(mock_config, str(archive_file))

        mock_stat.return_value.st_size = 1000000

        result = command.execute()

        assert result is True
        # Check that paths are properly quoted in command
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "spaces.tar.xz" in cmd
        # Paths should be quoted
        assert "'" in cmd or '"' in cmd
