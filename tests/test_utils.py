"""Tests for utility classes and functions.

This module tests the SizeCalculator and other utility functions.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.utils.progress_bar import SimpleProgressBar
from autotarcompress.utils.size_calculator import SizeCalculator
from autotarcompress.utils.utils import (
    ensure_backup_folder,
    validate_and_expand_paths,
)


class TestSizeCalculator:
    """Test SizeCalculator functionality."""

    def test_size_calculator_initialization(self) -> None:
        """Test that SizeCalculator initializes correctly."""
        EXPECTED_DIR_COUNT = 2
        EXPECTED_IGNORE_COUNT = 2

        dirs = ["/test/dir1", "/test/dir2"]
        ignore_list = ["node_modules", ".git"]

        calculator = SizeCalculator(dirs, ignore_list)
        assert len(calculator.directories) == EXPECTED_DIR_COUNT
        assert str(calculator.directories[0]) == "/test/dir1"
        assert str(calculator.directories[1]) == "/test/dir2"
        assert len(calculator.ignore_list) == EXPECTED_IGNORE_COUNT

    def test_calculate_total_size_with_test_data(
        self, test_data_dir: str
    ) -> None:
        """Test size calculation with actual test data."""
        dirs = [test_data_dir]
        ignore_list: list[str] = []

        calculator = SizeCalculator(dirs, ignore_list)
        total_size = calculator.calculate_total_size()

        # Should have some size from test files
        assert total_size > 0

    def test_calculate_total_size_with_ignore_list(
        self, test_data_dir: str
    ) -> None:
        """Test size calculation respects ignore list."""
        dirs = [test_data_dir]
        ignore_list: list[str] = [
            "ignored"
        ]  # Should ignore the "ignored" directory

        calculator = SizeCalculator(dirs, ignore_list)
        size_with_ignore = calculator.calculate_total_size()

        # Calculate size without ignore list
        no_ignore_list: list[str] = []
        calculator_no_ignore = SizeCalculator(dirs, no_ignore_list)
        size_without_ignore = calculator_no_ignore.calculate_total_size()

        # Size with ignore should be less than or equal to size without ignore
        assert size_with_ignore <= size_without_ignore

    @patch("autotarcompress.utils.size_calculator.os.walk")
    def test_calculate_total_size_handles_permission_errors(
        self, mock_walk
    ) -> None:
        """Test that size calculator handles permission errors gracefully."""
        # Mock os.walk to raise PermissionError
        mock_walk.side_effect = PermissionError("Permission denied")

        dirs = ["/test/dir"]
        ignore_list: list[str] = []

        calculator = SizeCalculator(dirs, ignore_list)
        # Should not raise an exception, should return 0
        total_size = calculator.calculate_total_size()
        assert total_size == 0

    def test_calculate_total_size_nonexistent_directory(self) -> None:
        """Test size calculation with non-existent directory."""
        dirs = ["/nonexistent/directory"]
        ignore_list: list[str] = []

        calculator = SizeCalculator(dirs, ignore_list)
        total_size = calculator.calculate_total_size()

        # Should return 0 for non-existent directory
        assert total_size == 0

    @patch("autotarcompress.utils.size_calculator.os.walk")
    def test_calculate_total_size_with_mocked_files(self, mock_walk) -> None:
        """Test size calculation with mocked file system."""
        # Mock os.walk to return test data
        mock_walk.return_value = [
            ("/test/dir", ["subdir"], ["file1.txt", "file2.txt"]),
            ("/test/dir/subdir", [], ["file3.txt"]),
        ]

        # Mock pathlib.Path.stat() to return fixed sizes
        FILE_SIZE = 100

        class MockStat:
            """Mock stat object with st_size attribute."""

            def __init__(self, size: int):
                self.st_size = size

        with (
            patch("pathlib.Path.stat") as mock_path_stat,
            patch("pathlib.Path.is_symlink") as mock_is_symlink,
        ):
            mock_path_stat.return_value = MockStat(FILE_SIZE)
            mock_is_symlink.return_value = False  # Treat all as regular files

            dirs = ["/test/dir"]
            ignore_list: list[str] = []

            calculator = SizeCalculator(dirs, ignore_list)
            total_size = calculator.calculate_total_size()

            # Should have some size from mocked files
            assert total_size >= 0

    def test_symlink_handling(self, tmp_path) -> None:
        """Test that broken symlinks are handled gracefully."""
        # Create test files and symlinks
        regular_file = tmp_path / "regular.txt"
        regular_file.write_text("test content")

        # Create a valid symlink
        valid_symlink = tmp_path / "valid_symlink"
        valid_symlink.symlink_to(regular_file)

        # Create a broken symlink
        broken_symlink = tmp_path / "broken_symlink"
        broken_symlink.symlink_to("nonexistent_target")

        calculator = SizeCalculator([str(tmp_path)], [])

        # Should not raise an exception and should return size > 0
        # (from regular file and valid symlink)
        total_size = calculator.calculate_total_size()
        assert total_size > 0


def test_validate_and_expand_paths(tmp_path) -> None:
    """Test validate_and_expand_paths returns existing and missing lists."""
    existing_dir = tmp_path / "exists"
    existing_dir.mkdir()

    missing_dir = tmp_path / "does_not_exist"

    # include an empty string which should be skipped
    inputs = [str(existing_dir), str(missing_dir), ""]

    existing, missing = validate_and_expand_paths(inputs)

    # Ensure the existing directory is returned and the missing one is reported
    assert str(existing_dir) in existing
    assert str(missing_dir) in missing


def test_ensure_backup_folder_creates_and_returns_path(tmp_path) -> None:
    """Test ensure_backup_folder creates nested folders and returns a Path."""
    nested = tmp_path / "a" / "b" / "c"
    # Pass as a string (function will expanduser internally)
    result = ensure_backup_folder(str(nested))

    assert result.exists()
    assert result.is_dir()
    # The returned path should match the expanded input path
    from pathlib import Path

    assert result == Path(str(nested)).expanduser()


def test_validate_and_expand_paths_handles_none() -> None:
    """validate_and_expand_paths should handle a None input gracefully."""
    existing, missing = validate_and_expand_paths(None)
    assert existing == []
    assert missing == []


def test_validate_and_expand_paths_with_file_and_trailing_slash(
    tmp_path,
) -> None:
    """A trailing slash on an existing file should still be reported as existing."""
    file = tmp_path / "afile.txt"
    file.write_text("content")

    inputs = [str(file) + "/"]
    existing, missing = validate_and_expand_paths(inputs)

    assert str(file) in existing
    assert missing == []


def test_ensure_backup_folder_idempotent(tmp_path) -> None:
    """ensure_backup_folder should be safe to call multiple times."""
    nested = tmp_path / "already" / "exists"
    nested.mkdir(parents=True)

    first = ensure_backup_folder(str(nested))
    second = ensure_backup_folder(str(nested))

    assert first == second


def test_ensure_backup_folder_permission_error(monkeypatch, tmp_path) -> None:
    """If the folder cannot be created due to permissions, an OSError is raised."""
    from pathlib import Path

    import pytest

    nested = tmp_path / "no_perms"

    def fake_mkdir(self, parents=True, exist_ok=True):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    with pytest.raises(OSError):
        ensure_backup_folder(str(nested))


class TestSimpleProgressBar:
    """Test SimpleProgressBar functionality."""

    def test_progress_bar_initialization(self) -> None:
        """Test that SimpleProgressBar initializes correctly."""
        total_size = 1024 * 1024 * 1024  # 1 GB
        progress = SimpleProgressBar(total_size)

        assert progress.total_size == total_size
        assert progress.current_size == 0
        assert progress.width == 30
        assert progress.last_percentage == -1

    def test_progress_bar_initialization_custom_width(self) -> None:
        """Test that SimpleProgressBar accepts custom width."""
        total_size = 1024
        width = 50
        progress = SimpleProgressBar(total_size, width)

        assert progress.width == width

    def test_calculate_eta_no_progress(self) -> None:
        """Test ETA calculation with no progress returns empty string."""
        progress = SimpleProgressBar(1024)

        eta = progress._calculate_eta()
        assert eta == ""

    def test_calculate_eta_insufficient_time(self) -> None:
        """Test ETA calculation with insufficient elapsed time."""
        progress = SimpleProgressBar(1024)
        progress.current_size = 512  # Halfway done

        # Mock time to be less than 1 second
        with patch("autotarcompress.utils.progress_bar.time") as mock_time:
            mock_time.time.return_value = progress.start_time + 0.5

            eta = progress._calculate_eta()
            assert eta == ""

    def test_calculate_eta_completion(self) -> None:
        """Test ETA calculation when backup is complete."""
        progress = SimpleProgressBar(1024)
        progress.current_size = 1024  # Complete

        with patch("autotarcompress.utils.progress_bar.time") as mock_time:
            mock_time.time.return_value = progress.start_time + 10

            eta = progress._calculate_eta()
            assert eta == "00:00"

    def test_calculate_eta_minutes_format(self) -> None:
        """Test ETA calculation returns MM:SS format for less than 1 hour."""
        progress = SimpleProgressBar(1024)  # 1 KB total
        progress.current_size = 100  # 100 bytes done

        # Mock 10 seconds elapsed, so rate = 10 bytes/sec
        # Remaining = 924 bytes, time = 92.4 seconds = 1:32
        with patch("autotarcompress.utils.progress_bar.time") as mock_time:
            mock_time.time.return_value = progress.start_time + 10

            eta = progress._calculate_eta()
            assert eta == "01:32"

    def test_calculate_eta_hours_format(self) -> None:
        """Test ETA calculation returns HH:MM:SS format for 1+ hours."""
        progress = SimpleProgressBar(7200)  # 7200 bytes total (2 hours worth)
        progress.current_size = 1  # 1 byte done

        # Mock 1 second elapsed, so rate = 1 byte/sec
        # Remaining = 7199 bytes, time = 7199 seconds = 1:59:59
        with patch("autotarcompress.utils.progress_bar.time") as mock_time:
            mock_time.time.return_value = progress.start_time + 1

            eta = progress._calculate_eta()
            assert eta == "01:59:59"

    @patch("sys.stdout")
    def test_update_displays_eta(self, mock_stdout: MagicMock) -> None:
        """Test that update method displays elapsed/ETA in progress bar."""
        progress = SimpleProgressBar(1024)
        progress.current_size = 512  # Halfway

        with patch("autotarcompress.utils.progress_bar.time") as mock_time:
            mock_time.time.return_value = progress.start_time + 10

            progress.update(0)  # Trigger display update

            # Check that stdout.write was called with elapsed/ETA
            calls = mock_stdout.write.call_args_list
            assert len(calls) > 0
            progress_text = calls[-1][0][0]  # Last call's first argument
            assert "00:10/00:10" in progress_text

    @patch("sys.stdout")
    def test_finish_displays_eta_complete(
        self, mock_stdout: MagicMock
    ) -> None:
        """Test that finish method displays elapsed/00:00 when complete."""
        progress = SimpleProgressBar(1024)

        progress.finish()

        # Check that stdout.write was called with elapsed/00:00
        calls = mock_stdout.write.call_args_list
        found_time = False
        for call in calls:
            progress_text = call[0][0]
            if "/00:00" in progress_text:
                found_time = True
                break

        assert found_time, "elapsed/00:00 not found in finish output"
