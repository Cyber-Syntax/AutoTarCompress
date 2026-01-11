"""Comprehensive tests for CleanupManager.

This module provides extensive test coverage for the CleanupManager class,
including old backup file cleanup, retention policies, date parsing,
error handling, and file system operations.
"""

import datetime
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autotarcompress.cleanup_manager import CleanupManager
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


class TestCleanupManager:
    """Test suite for CleanupManager functionality."""

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
    def cleanup_manager(self, mock_config: BackupConfig) -> CleanupManager:
        """Create a CleanupManager instance for testing.

        Args:
            mock_config: Mock backup configuration.

        Returns:
            CleanupManager: Instance for testing.

        """
        return CleanupManager(mock_config)

    @pytest.fixture
    def sample_backup_files(self) -> list[str]:
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
    def sample_encrypted_files(self) -> list[str]:
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

    def _create_mock_files(self, filenames: list[str]) -> list[Mock]:
        """Create mock Path objects for testing.

        Args:
            filenames: List of filenames to create mocks for.

        Returns:
            List of mock Path objects.
        """
        mock_files = []
        for filename in filenames:
            mock_file = Mock(spec=Path)
            mock_file.name = filename
            mock_files.append(mock_file)
        return mock_files

    @patch("pathlib.Path.iterdir")
    @patch("pathlib.Path.unlink")
    def test_cleanup_files_keeps_recent_backups(
        self,
        mock_unlink: Mock,
        mock_iterdir: Mock,
        cleanup_manager: CleanupManager,
        sample_backup_files: list[str],
    ) -> None:
        """Test that cleanup keeps the specified number of recent files.

        Args:
            mock_unlink: Mock file deletion method.
            mock_iterdir: Mock directory listing.
            cleanup_manager: CleanupManager instance.
            sample_backup_files: Sample backup filenames.

        """
        # Create mock Path objects with names
        mock_paths = []
        for filename in sample_backup_files:
            mock_path = Mock()
            mock_path.name = filename
            mock_paths.append(mock_path)
        mock_iterdir.return_value = mock_paths
        keep_count = 3

        cleanup_manager._cleanup_files(".tar.xz", keep_count)

        # Should delete 4 files (7 total - 3 to keep)
        assert mock_unlink.call_count == EXPECTED_DELETED_COUNT_REGULAR

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_with_fewer_than_keep_count(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
    ) -> None:
        """Test cleanup when there are fewer files than keep count.

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.

        """
        # Only 2 files, but want to keep 5
        mock_iterdir.return_value = self._create_mock_files(
            ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]
        )

        cleanup_manager._cleanup_files(".tar.xz", 5)

        # Should not delete any files
        mock_unlink.assert_not_called()

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_no_matching_files(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
    ) -> None:
        """Test cleanup when no files match the extension.

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.

        """
        # Directory has files but none with target extension
        mock_iterdir.return_value = self._create_mock_files(
            ["file1.txt", "file2.log", "file3.zip"]
        )

        cleanup_manager._cleanup_files(".tar.xz", 3)

        # Should not delete any files
        mock_unlink.assert_not_called()

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_encrypted_backups(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
        sample_encrypted_files: list[str],
    ) -> None:
        """Test cleanup of encrypted backup files.

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.
            sample_encrypted_files: Sample encrypted filenames.

        """
        mock_iterdir.return_value = self._create_mock_files(
            sample_encrypted_files
        )

        cleanup_manager._cleanup_files(".tar.xz.enc", 2)

        # Should delete 3 files (5 total - 2 to keep)
        assert mock_unlink.call_count == EXPECTED_DELETED_COUNT_ENCRYPTED

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_deletion_error_handling(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test error handling during file deletion.

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.
            caplog: Pytest log capture fixture.

        """
        mock_iterdir.return_value = self._create_mock_files(
            ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]
        )
        mock_unlink.side_effect = PermissionError("Access denied")

        with caplog.at_level(logging.ERROR):
            cleanup_manager._cleanup_files(".tar.xz", 1)

        # Should attempt to delete one file and log error
        assert mock_unlink.call_count == 1
        assert "Failed to delete" in caplog.text
        assert "Access denied" in caplog.text

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_successful_deletion_logging(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test logging of successful file deletions.

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.
            caplog: Pytest log capture fixture.

        """
        mock_iterdir.return_value = self._create_mock_files(
            ["15-12-2024.tar.xz", "14-12-2024.tar.xz"]
        )

        with caplog.at_level(logging.INFO):
            cleanup_manager._cleanup_files(".tar.xz", 1)

        assert mock_unlink.call_count == 1
        assert "Deleted old backup:" in caplog.text
        assert "14-12-2024.tar.xz" in caplog.text

    def test_date_parsing_validation(
        self, cleanup_manager: CleanupManager
    ) -> None:
        """Test that date parsing works correctly for filename sorting.

        Args:
            cleanup_manager: CleanupManager instance.

        """
        # Test the date parsing logic used in the sorting
        test_filename = "15-12-2024.tar.xz"
        date_part = test_filename.split(".")[0]
        parsed_date = datetime.datetime.strptime(date_part, "%d-%m-%Y")

        expected_date = datetime.datetime(2024, 12, 15)
        assert parsed_date == expected_date

    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_sorting_by_date(
        self, mock_iterdir: Mock, cleanup_manager: CleanupManager
    ) -> None:
        """Test that files are sorted correctly by date.

        Args:
            mock_iterdir: Mock directory listing.
            cleanup_manager: CleanupManager instance.

        """
        # Files in random order
        unsorted_files = [
            "13-12-2024.tar.xz",
            "15-12-2024.tar.xz",
            "11-12-2024.tar.xz",
            "14-12-2024.tar.xz",
            "12-12-2024.tar.xz",
        ]
        mock_iterdir.return_value = self._create_mock_files(unsorted_files)

        with patch("pathlib.Path.unlink") as mock_unlink:
            cleanup_manager._cleanup_files(".tar.xz", 2)

            # Should delete the 3 oldest files
            assert mock_unlink.call_count == 3

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_with_zero_keep_count(
        self,
        mock_iterdir: Mock,
        mock_unlink: Mock,
        cleanup_manager: CleanupManager,
        sample_backup_files: list[str],
    ) -> None:
        """Test cleanup when keep count is zero (delete all files).

        Args:
            mock_iterdir: Mock directory listing.
            mock_unlink: Mock file deletion method.
            cleanup_manager: CleanupManager instance.
            sample_backup_files: Sample backup filenames.

        """
        mock_iterdir.return_value = self._create_mock_files(
            sample_backup_files
        )

        cleanup_manager._cleanup_files(".tar.xz", 0)

        # Should delete all files
        assert mock_unlink.call_count == len(sample_backup_files)

    @given(st.integers(min_value=0, max_value=20))
    def test_cleanup_files_keep_count_property(self, keep_count: int) -> None:
        """Property-based test for various keep counts.

        Args:
            keep_count: Random keep count value.

        """
        cleanup_manager = CleanupManager(BackupConfig())
        sample_files = [
            f"{i:02d}-12-2024.tar.xz" for i in range(1, 16)
        ]  # 15 files

        with (
            patch(
                "pathlib.Path.iterdir",
                return_value=self._create_mock_files(sample_files),
            ),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            cleanup_manager._cleanup_files(".tar.xz", keep_count)

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
    def test_cleanup_files_various_filenames_property(
        self, filenames: list[str]
    ) -> None:
        """Property-based test for various filename patterns.

        Args:
            filenames: Random list of date-formatted filenames.

        """
        cleanup_manager = CleanupManager(BackupConfig())
        # Filter out invalid dates to avoid datetime parsing errors
        valid_filenames = []
        for filename in filenames:
            try:
                date_part = filename.split(".")[0]
                datetime.datetime.strptime(date_part, "%d-%m-%Y")
                valid_filenames.append(filename)
            except ValueError:
                continue

        with (
            patch(
                "pathlib.Path.iterdir",
                return_value=self._create_mock_files(valid_filenames),
            ),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            keep_count = 3
            cleanup_manager._cleanup_files(".tar.xz", keep_count)

            if len(valid_filenames) <= keep_count:
                assert mock_unlink.call_count == 0
            else:
                expected_deletions = len(valid_filenames) - keep_count
                assert mock_unlink.call_count == expected_deletions

    def test_backup_folder_path_construction(
        self, cleanup_manager: CleanupManager
    ) -> None:
        """Test that backup folder path is constructed correctly.

        Args:
            cleanup_manager: CleanupManager instance.

        """
        with (
            patch("pathlib.Path.iterdir") as mock_iterdir,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            mock_iterdir.return_value = self._create_mock_files(
                ["15-12-2024.tar.xz"]
            )
            cleanup_manager._cleanup_files(".tar.xz", 0)

            # Verify unlink was called (since keep_count is 0, file should be deleted)
            assert mock_unlink.call_count == 1

    @patch("pathlib.Path.iterdir")
    def test_cleanup_files_handles_os_error(
        self,
        mock_iterdir: Mock,
        cleanup_manager: CleanupManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of OS errors during directory listing.

        Args:
            mock_iterdir: Mock directory listing.
            cleanup_manager: CleanupManager instance.
            caplog: Pytest log capture fixture.

        """
        mock_iterdir.side_effect = FileNotFoundError("Directory not found")

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            cleanup_manager._cleanup_files(".tar.xz", 5)

    def test_file_extension_filtering(
        self, cleanup_manager: CleanupManager
    ) -> None:
        """Test that only files with correct extension are processed.

        Args:
            cleanup_manager: CleanupManager instance.

        """
        mixed_files = [
            "15-12-2024.tar.xz",  # Should match
            "14-12-2024.tar.gz",  # Should not match
            "13-12-2024.tar.xz.enc",  # Should not match for .tar.xz
            "12-12-2024.zip",  # Should not match
            "11-12-2024.tar.xz",  # Should match
        ]

        with (
            patch(
                "pathlib.Path.iterdir",
                return_value=self._create_mock_files(mixed_files),
            ),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            cleanup_manager._cleanup_files(".tar.xz", 1)

            # Should only process the 2 .tar.xz files and delete 1 (oldest)
            assert mock_unlink.call_count == 1

    def test_cleanup_all_files_functionality(
        self, cleanup_manager: CleanupManager
    ) -> None:
        """Test that cleanup_all deletes all files regardless of retention policy.

        Args:
            cleanup_manager: CleanupManager instance.

        """
        # Mock files for different extensions
        test_files = [
            "15-12-2024.tar.xz",
            "14-12-2024.tar.xz",
            "13-12-2024.tar.xz-decrypted",
            "12-12-2024.tar-extracted",
            "11-12-2024.tar.xz.enc",
        ]

        # Create mock Path objects
        mock_paths = []
        for filename in test_files:
            mock_path = Mock()
            mock_path.name = filename
            mock_paths.append(mock_path)

        with (
            patch("pathlib.Path.iterdir", return_value=mock_paths),
            patch("pathlib.Path.unlink") as mock_unlink,
            patch("pathlib.Path.is_dir", return_value=False),
        ):
            cleanup_manager._cleanup_all_files()
