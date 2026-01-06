"""Tests for hash utilities."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from autotarcompress.utils.hash_utils import calculate_sha256, verify_hash

if TYPE_CHECKING:
    from pathlib import Path


class TestCalculateSHA256:
    """Tests for calculate_sha256 function."""

    def test_calculate_hash_for_file(self, tmp_path: Path) -> None:
        """Test calculating SHA256 hash for a file."""
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Calculate hash using function
        actual_hash = calculate_sha256(test_file)

        assert actual_hash == expected_hash

    def test_calculate_hash_for_large_file(self, tmp_path: Path) -> None:
        """Test calculating SHA256 hash for a large file."""
        test_file = tmp_path / "large.bin"

        # Create a large file (1MB)
        large_content = b"x" * (1024 * 1024)
        test_file.write_bytes(large_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(large_content).hexdigest()

        # Calculate hash using function
        actual_hash = calculate_sha256(test_file)

        assert actual_hash == expected_hash

    def test_calculate_hash_for_empty_file(self, tmp_path: Path) -> None:
        """Test calculating SHA256 hash for an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        # Calculate expected hash for empty file
        expected_hash = hashlib.sha256(b"").hexdigest()

        actual_hash = calculate_sha256(test_file)

        assert actual_hash == expected_hash

    def test_calculate_hash_nonexistent_file(self, tmp_path: Path) -> None:
        """Test calculating hash for nonexistent file raises error."""
        nonexistent_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            calculate_sha256(nonexistent_file)

    def test_calculate_hash_for_directory(self, tmp_path: Path) -> None:
        """Test calculating hash for a directory raises error."""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        with pytest.raises(ValueError, match="Path is not a file"):
            calculate_sha256(test_dir)

    def test_calculate_hash_with_string_path(self, tmp_path: Path) -> None:
        """Test that function works with string paths."""
        test_file = tmp_path / "test.txt"
        test_content = b"Test content"
        test_file.write_bytes(test_content)

        # Calculate using Path
        hash_from_path = calculate_sha256(test_file)

        # Calculate using string
        hash_from_string = calculate_sha256(str(test_file))

        assert hash_from_path == hash_from_string


class TestVerifyHash:
    """Tests for verify_hash function."""

    def test_verify_correct_hash(self, tmp_path: Path) -> None:
        """Test verifying correct hash returns True."""
        test_file = tmp_path / "test.txt"
        test_content = b"Test content"
        test_file.write_bytes(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()

        result = verify_hash(test_file, expected_hash)

        assert result is True

    def test_verify_incorrect_hash(self, tmp_path: Path) -> None:
        """Test verifying incorrect hash returns False."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Test content")

        wrong_hash = "0" * 64  # Definitely wrong hash

        result = verify_hash(test_file, wrong_hash)

        assert result is False

    def test_verify_hash_nonexistent_file(self, tmp_path: Path) -> None:
        """Test verifying hash for nonexistent file returns False."""
        nonexistent_file = tmp_path / "nonexistent.txt"
        some_hash = "a" * 64

        result = verify_hash(nonexistent_file, some_hash)

        assert result is False

    def test_verify_hash_with_string_path(self, tmp_path: Path) -> None:
        """Test that verify_hash works with string paths."""
        test_file = tmp_path / "test.txt"
        test_content = b"Test content"
        test_file.write_bytes(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Test with Path
        result_path = verify_hash(test_file, expected_hash)

        # Test with string
        result_string = verify_hash(str(test_file), expected_hash)

        assert result_path is True
        assert result_string is True
        assert result_path == result_string
