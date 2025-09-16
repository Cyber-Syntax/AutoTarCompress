"""Comprehensive tests for CleanupCommand.

This module provides extensive test coverage for the CleanupCommand class,
including old backup file cleanup, retention policies, date parsing,
error handling, and file system operations.
"""

import datetime
import logging
from pathlib import Path
from typing import List
from unittest.mock import Mock, call, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autotarcompress.commands.cleanup import CleanupCommand
from autotarcompress.config import BackupConfig

# Constants for test magic numbers
EXPECTED_DELETED_COUNT_REGULAR = 4
EXPECTED_DELETED_COUNT_ENCRYPTED = 3
DATE_COMPONENTS_COUNT = 3


def _is_valid_date_filename(x: str) -> bool:
    """Check if filename has valid date format and extension.

    Args:
        x (str): Filename to validate.

    Returns:
        bool: True if filename is valid.

    """
    return (
        len(x.split("-")) == DATE_COMPONENTS_COUNT
        and x.endswith(".tar.xz")
        and all(part.isdigit() for part in x.replace(".tar.xz", "").split("-"))
    )


class TestCleanupCommand:
    """Test suite for CleanupCommand functionality."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock configuration for testing.

        Returns:
            BackupConfig: Mock configuration with test backup settings.

        """
        config = Mock(spec=BackupConfig)
        config.backup_folder = "/test/backup/folder"
        config.keep_backup = 5
        config.keep_enc_backup = 3
        return config

    @pytest.fixture
    def cleanup_command(self, mock_config: BackupConfig) -> CleanupCommand:
        """Create a CleanupCommand instance for testing.

        Args:
            mock_config: Mock backup configuration.

        Returns:
            CleanupCommand: Instance for testing.

        """
        return CleanupCommand(mock_config)

    @pytest.fixture
    def sample_backup_files(self) -> List[str]:
        """Create sample backup filenames for testing.

        Returns:
            List of sample backup filenames with dates.

        """
        return [
            "15-12-2024.tar.xz",
            "14-12-2024.tar.xz",
            "13-12-2024.tar.xz",
            "12-12-2024.tar.xz",
            "11-12-2024.tar.xz",
            "10-12-2024.tar.xz",
            "09-12-2024.tar.xz",
        ]

    @pytest.fixture
    def sample_encrypted_files(self) -> List[str]:
        """Create sample encrypted backup filenames for testing.

        Returns:
            List of sample encrypted backup filenames.

        """
        return [
            "15-12-2024.tar.xz.enc",
            "14-12-2024.tar.xz.enc",
            "13-12-2024.tar.xz.enc",
            "12-12-2024.tar.xz.enc",
            "11-12-2024.tar.xz.enc",
        ]

    def test_initialization(self, mock_config: BackupConfig) -> None:
        """Test CleanupCommand initialization.

        Args:
            mock_config: Mock backup configuration.

        """
        command = CleanupCommand(mock_config)

        assert command.config is mock_config
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "autotarcompress.commands.cleanup"

    def test_initialization_with_cleanup_all(self, mock_config: BackupConfig) -> None:
        """Test CleanupCommand initialization with cleanup_all parameter.

        Args:
            mock_config: Mock backup configuration.

        """
        command = CleanupCommand(mock_config, cleanup_all=True)

        assert command.config is mock_config
        assert command.cleanup_all is True
        assert isinstance(command.logger, logging.Logger)

        # Test default value
        command_default = CleanupCommand(mock_config)
        assert command_default.cleanup_all is False

    @patch.object(CleanupCommand, "_cleanup_files")
    def test_execute_calls_cleanup_methods(
        self, mock_cleanup: Mock, cleanup_command: CleanupCommand
    ) -> None:
        """Test that execute calls cleanup for all file types.

        Args:
            mock_cleanup: Mock cleanup method.
            cleanup_command: CleanupCommand instance.

        """
        result = cleanup_command.execute()

        assert result is True
        expected_calls = [
            call(".tar.xz", 5),
            call(".tar.xz-decrypted", 5),
            call(".tar-extracted", 5),
            call(".tar.xz.enc", 3),
        ]
        mock_cleanup.assert_has_calls(expected_calls)

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_keeps_recent_backups(
        self,
        mock_unlink: Mock,
        mock_listdir: Mock,
        cleanup_command: CleanupCommand,
        sample_backup_files: List[str],
    ) -> None:
        """Test that cleanup keeps the specified number of recent files.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            sample_backup_files: Sample backup filenames.

        """
        mock_listdir.return_value = sample_backup_files
        keep_count = 3

        cleanup_command._cleanup_files(".tar.xz", keep_count)

        # Should delete 4 files (7 total - 3 to keep)
        assert mock_unlink.call_count == EXPECTED_DELETED_COUNT_REGULAR

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_with_fewer_than_keep_count(
        self, mock_unlink: Mock, mock_listdir: Mock, cleanup_command: CleanupCommand
    ) -> None:
        """Test cleanup when there are fewer files than keep count.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.

        """
        # Only 2 files, but want to keep 5
        mock_listdir.return_value = ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]

        cleanup_command._cleanup_files(".tar.xz", 5)

        # Should not delete any files
        mock_unlink.assert_not_called()

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_no_matching_files(
        self, mock_unlink: Mock, mock_listdir: Mock, cleanup_command: CleanupCommand
    ) -> None:
        """Test cleanup when no files match the extension.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.

        """
        # Directory has files but none with target extension
        mock_listdir.return_value = ["file1.txt", "file2.log", "file3.zip"]

        cleanup_command._cleanup_files(".tar.xz", 3)

        # Should not delete any files
        mock_unlink.assert_not_called()

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_encrypted_backups(
        self,
        mock_unlink: Mock,
        mock_listdir: Mock,
        cleanup_command: CleanupCommand,
        sample_encrypted_files: List[str],
    ) -> None:
        """Test cleanup of encrypted backup files.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            sample_encrypted_files: Sample encrypted filenames.

        """
        mock_listdir.return_value = sample_encrypted_files

        cleanup_command._cleanup_files(".tar.xz.enc", 2)

        # Should delete 3 files (5 total - 2 to keep)
        assert mock_unlink.call_count == EXPECTED_DELETED_COUNT_ENCRYPTED

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_deletion_error_handling(
        self,
        mock_unlink: Mock,
        mock_listdir: Mock,
        cleanup_command: CleanupCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test error handling during file deletion.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            caplog: Pytest log capture fixture.

        """
        mock_listdir.return_value = ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]
        mock_unlink.side_effect = PermissionError("Access denied")

        with caplog.at_level(logging.ERROR):
            cleanup_command._cleanup_files(".tar.xz", 1)

        # Should attempt to delete one file and log error
        assert mock_unlink.call_count == 1
        assert "Failed to delete" in caplog.text
        assert "Access denied" in caplog.text

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_successful_deletion_logging(
        self,
        mock_unlink: Mock,
        mock_listdir: Mock,
        cleanup_command: CleanupCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test logging of successful file deletions.

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            caplog: Pytest log capture fixture.

        """
        mock_listdir.return_value = ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]

        with caplog.at_level(logging.INFO):
            cleanup_command._cleanup_files(".tar.xz", 1)

        assert mock_unlink.call_count == 1
        assert "Deleted old backup:" in caplog.text
        assert "14-12-2024.tar.xz" in caplog.text

    def test_date_parsing_validation(self, cleanup_command: CleanupCommand) -> None:
        """Test that date parsing works correctly for filename sorting.

        Args:
            cleanup_command: CleanupCommand instance.

        """
        # Test the date parsing logic used in the sorting
        test_filename = "15-12-2024.tar.xz"
        date_part = test_filename.split(".")[0]
        parsed_date = datetime.datetime.strptime(date_part, "%d-%m-%Y")

        expected_date = datetime.datetime(2024, 12, 15)
        assert parsed_date == expected_date

    @patch("os.listdir")
    def test_cleanup_files_sorting_by_date(
        self, mock_listdir: Mock, cleanup_command: CleanupCommand
    ) -> None:
        """Test that files are sorted correctly by date.

        Args:
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.

        """
        # Files in random order
        unsorted_files = [
            "13-12-2024.tar.xz",
            "15-12-2024.tar.xz",
            "11-12-2024.tar.xz",
            "14-12-2024.tar.xz",
            "12-12-2024.tar.xz",
        ]
        mock_listdir.return_value = unsorted_files

        with patch("pathlib.Path.unlink") as mock_unlink:
            cleanup_command._cleanup_files(".tar.xz", 2)

            # Should delete the 3 oldest files
            assert mock_unlink.call_count == 3

    @patch("os.listdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_with_zero_keep_count(
        self,
        mock_unlink: Mock,
        mock_listdir: Mock,
        cleanup_command: CleanupCommand,
        sample_backup_files: List[str],
    ) -> None:
        """Test cleanup when keep count is zero (delete all files).

        Args:
            mock_unlink: Mock file deletion method.
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            sample_backup_files: Sample backup filenames.

        """
        mock_listdir.return_value = sample_backup_files

        cleanup_command._cleanup_files(".tar.xz", 0)

        # Should delete all files
        assert mock_unlink.call_count == len(sample_backup_files)

    @given(st.integers(min_value=0, max_value=20))
    def test_cleanup_files_keep_count_property(self, keep_count: int) -> None:
        """Property-based test for various keep counts.

        Args:
            keep_count: Random keep count value.

        """
        cleanup_command = CleanupCommand(BackupConfig())
        sample_files = [f"{i:02d}-12-2024.tar.xz" for i in range(1, 16)]  # 15 files

        with patch("os.listdir", return_value=sample_files), patch(
            "pathlib.Path.unlink"
        ) as mock_unlink:
            cleanup_command._cleanup_files(".tar.xz", keep_count)

            if keep_count >= len(sample_files):
                # Should not delete any files
                assert mock_unlink.call_count == 0
            else:
                # Should delete the appropriate number of files
                expected_deletions = len(sample_files) - keep_count
                assert mock_unlink.call_count == expected_deletions

    @given(
        st.lists(
            st.text(min_size=10, max_size=15).filter(_is_valid_date_filename),
            min_size=0,
            max_size=10,
            unique=True,
        )
    )
    def test_cleanup_files_various_filenames_property(self, filenames: List[str]) -> None:
        """Property-based test for various filename patterns.

        Args:
            filenames: Random list of date-formatted filenames.

        """
        cleanup_command = CleanupCommand(BackupConfig())
        # Filter out invalid dates to avoid datetime parsing errors
        valid_filenames = []
        for filename in filenames:
            try:
                date_part = filename.split(".")[0]
                datetime.datetime.strptime(date_part, "%d-%m-%Y")
                valid_filenames.append(filename)
            except ValueError:
                continue

        with patch("os.listdir", return_value=valid_filenames), patch(
            "pathlib.Path.unlink"
        ) as mock_unlink:
            keep_count = 3
            cleanup_command._cleanup_files(".tar.xz", keep_count)

            if len(valid_filenames) <= keep_count:
                assert mock_unlink.call_count == 0
            else:
                expected_deletions = len(valid_filenames) - keep_count
                assert mock_unlink.call_count == expected_deletions

    def test_backup_folder_path_construction(self, cleanup_command: CleanupCommand) -> None:
        """Test that backup folder path is constructed correctly.

        Args:
            cleanup_command: CleanupCommand instance.

        """
        with patch("os.listdir") as mock_listdir, patch("pathlib.Path.unlink") as mock_unlink:
            mock_listdir.return_value = ["15-12-2024.tar.xz"]
            cleanup_command._cleanup_files(".tar.xz", 0)

            # Verify the correct path was used for listing
            mock_listdir.assert_called_once_with(Path("/test/backup/folder"))

            # Verify unlink was called (since keep_count is 0, file should be deleted)
            assert mock_unlink.call_count == 1

    @patch("os.listdir")
    def test_cleanup_files_handles_os_error(
        self, mock_listdir: Mock, cleanup_command: CleanupCommand, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test handling of OS errors during directory listing.

        Args:
            mock_listdir: Mock directory listing.
            cleanup_command: CleanupCommand instance.
            caplog: Pytest log capture fixture.

        """
        mock_listdir.side_effect = OSError("Directory not found")

        # Should not raise exception
        with pytest.raises(OSError):
            cleanup_command._cleanup_files(".tar.xz", 5)

    def test_file_extension_filtering(self, cleanup_command: CleanupCommand) -> None:
        """Test that only files with correct extension are processed.

        Args:
            cleanup_command: CleanupCommand instance.

        """
        mixed_files = [
            "15-12-2024.tar.xz",  # Should match
            "14-12-2024.tar.gz",  # Should not match
            "13-12-2024.tar.xz.enc",  # Should not match for .tar.xz
            "12-12-2024.zip",  # Should not match
            "11-12-2024.tar.xz",  # Should match
        ]

        with patch("os.listdir", return_value=mixed_files), patch(
            "pathlib.Path.unlink"
        ) as mock_unlink:
            cleanup_command._cleanup_files(".tar.xz", 1)

            # Should only process the 2 .tar.xz files and delete 1 (oldest)
            assert mock_unlink.call_count == 1

    def test_cleanup_all_files_functionality(self, mock_config: BackupConfig) -> None:
        """Test that cleanup_all deletes all files regardless of retention policy.

        Args:
            mock_config: Mock backup configuration.

        """
        command = CleanupCommand(mock_config, cleanup_all=True)

        # Mock files for different extensions
        test_files = [
            "15-12-2024.tar.xz",
            "14-12-2024.tar.xz",
            "13-12-2024.tar.xz-decrypted",
            "12-12-2024.tar-extracted",
            "11-12-2024.tar.xz.enc",
        ]

        with patch("os.listdir", return_value=test_files), patch(
            "pathlib.Path.unlink"
        ) as mock_unlink, patch("pathlib.Path.is_dir", return_value=False):
            command._cleanup_all_files()

            # Should delete all files (4 calls for 4 different extensions)
            # Each extension will be processed, but only matching files deleted
            assert mock_unlink.call_count == len(test_files)

    def test_execute_with_cleanup_all_calls_cleanup_all_files(
        self, mock_config: BackupConfig
    ) -> None:
        """Test that execute() calls _cleanup_all_files when cleanup_all is True.

        Args:
            mock_config: Mock backup configuration.

        """
        command = CleanupCommand(mock_config, cleanup_all=True)

        with patch.object(command, "_cleanup_all_files") as mock_cleanup_all:
            result = command.execute()

            assert result is True
            mock_cleanup_all.assert_called_once()

    def test_execute_without_cleanup_all_calls_regular_cleanup(
        self, mock_config: BackupConfig
    ) -> None:
        """Test that execute() calls regular cleanup when cleanup_all is False.

        Args:
            mock_config: Mock backup configuration.

        """
        command = CleanupCommand(mock_config, cleanup_all=False)

        with patch.object(command, "_cleanup_files") as mock_cleanup_files:
            result = command.execute()

            assert result is True
            # Should be called 4 times for different file extensions
            assert mock_cleanup_files.call_count == 4
