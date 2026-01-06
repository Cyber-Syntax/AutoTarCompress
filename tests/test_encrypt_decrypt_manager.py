"""Tests for the EncryptDecryptManager class.

This module contains comprehensive tests for the encrypt/decrypt manager
implementation, including mocking subprocess operations and testing
error conditions.
"""

import logging
import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest

from autotarcompress.config import BackupConfig
from autotarcompress.encrypt_decrypt_manager import EncryptDecryptManager


class TestEncryptDecryptManager:
    """Test cases for EncryptDecryptManager class."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        config = BackupConfig()
        config.config_dir = "~/.config/autotarcompress"
        return config

    @pytest.fixture
    def manager(self, mock_config: BackupConfig) -> EncryptDecryptManager:
        """Create an EncryptDecryptManager instance for testing."""
        return EncryptDecryptManager(mock_config)

    def test_manager_initialization(self, mock_config: BackupConfig) -> None:
        """Test EncryptDecryptManager initialization."""
        manager = EncryptDecryptManager(mock_config)

        assert manager.config == mock_config
        assert isinstance(manager.logger, logging.Logger)

    def test_validate_input_file_exists(
        self, manager: EncryptDecryptManager
    ) -> None:
        """Test _validate_input_file with existing file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()

            result = manager._validate_input_file(temp_file.name)
            assert result is True

    def test_validate_input_file_not_exists(
        self, manager: EncryptDecryptManager
    ) -> None:
        """Test _validate_input_file with non-existent file."""
        result = manager._validate_input_file("/nonexistent/file")  # type: ignore
        assert result is False

    def test_validate_input_file_empty(
        self, manager: EncryptDecryptManager
    ) -> None:
        """Test _validate_input_file with empty file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            # File is empty
            result = manager._validate_input_file(temp_file.name)
            assert result is False

    @patch("subprocess.run")
    @patch("getpass.getpass")
    def test_execute_encrypt_success(
        self, mock_getpass, mock_subprocess, manager: EncryptDecryptManager
    ) -> None:
        """Test execute_encrypt with successful encryption."""
        # Setup mocks
        mock_getpass.side_effect = [
            "test_password",
            "test_password",
        ]  # password and confirm

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b"success"
        mock_subprocess.return_value = mock_result

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()

            with patch.object(
                manager, "_validate_input_file", return_value=True
            ):
                result = manager.execute_encrypt(temp_file.name)

            assert result is True
            mock_subprocess.assert_called_once()

    @patch("getpass.getpass")
    def test_execute_encrypt_password_none(
        self, mock_getpass: MagicMock, manager: EncryptDecryptManager
    ) -> None:
        """Test execute_encrypt when password is None."""
        mock_getpass.return_value = ""  # Empty password

        result = manager.execute_encrypt("/some/file")
        assert result is False

    @patch("subprocess.run")
    @patch("getpass.getpass")
    def test_execute_decrypt_success(
        self,
        mock_getpass: MagicMock,
        mock_subprocess: MagicMock,
        manager: EncryptDecryptManager,
    ) -> None:
        """Test execute_decrypt with successful decryption."""
        # Setup mocks
        mock_getpass.side_effect = [
            "test_password",
            "test_password",
        ]  # password and confirm

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b"success"
        mock_subprocess.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix=".enc") as temp_file:
            temp_file.write(b"encrypted content")
            temp_file.flush()

            # Create a dummy original file for integrity check
            original_path = temp_file.name[:-4]  # Remove .enc
            Path(original_path).write_text(
                "original content", encoding="utf-8"
            )

            # Create the decrypted file as if openssl created it
            stem = Path(temp_file.name).stem
            decrypted_path = Path(temp_file.name).parent / f"{stem}-decrypted"
            decrypted_path.write_text("original content", encoding="utf-8")

            result = manager.execute_decrypt(temp_file.name)

            assert result is True
            mock_subprocess.assert_called_once()

    @patch("getpass.getpass")
    def test_execute_decrypt_password_none(
        self, mock_getpass: MagicMock, manager: EncryptDecryptManager
    ) -> None:
        """Test execute_decrypt when password is None."""
        mock_getpass.return_value = ""  # Empty password

        result = manager.execute_decrypt("/some/file.enc")
        assert result is False

    def test_calculate_sha256(self, manager: EncryptDecryptManager) -> None:
        """Test _calculate_sha256 calculates correct hash."""
        test_content = b"Hello, World!"
        expected_hash = (
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_content)
            temp_file.flush()

            result = manager._calculate_sha256(temp_file.name)  # type: ignore
            assert result == expected_hash

    def test_verify_integrity_match(
        self, manager: EncryptDecryptManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _verify_integrity when hashes match."""
        test_content = b"test content"

        with (
            tempfile.NamedTemporaryFile() as decrypted_file,
            tempfile.NamedTemporaryFile() as original_file,
        ):
            decrypted_file.write(test_content)
            decrypted_file.flush()
            original_file.write(test_content)
            original_file.flush()

            with caplog.at_level(logging.INFO):
                manager._verify_integrity(
                    decrypted_file.name, original_file.name
                )

            assert "Integrity verified:" in caplog.text

    def test_verify_integrity_no_match(
        self, manager: EncryptDecryptManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _verify_integrity when hashes don't match."""
        with (
            tempfile.NamedTemporaryFile() as decrypted_file,
            tempfile.NamedTemporaryFile() as original_file,
        ):
            decrypted_file.write(b"different content")
            decrypted_file.flush()
            original_file.write(b"original content")
            original_file.flush()

            with caplog.at_level(logging.ERROR):
                manager._verify_integrity(
                    decrypted_file.name, original_file.name
                )

            assert "Integrity check failed" in caplog.text

    def test_verify_integrity_no_original_file(
        self, manager: EncryptDecryptManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _verify_integrity when original file doesn't exist."""
        with tempfile.NamedTemporaryFile() as decrypted_file:
            decrypted_file.write(b"content")
            decrypted_file.flush()

            with caplog.at_level(logging.INFO):
                manager._verify_integrity(decrypted_file.name, "/nonexistent")  # type: ignore

            # Should not log anything since original doesn't exist
            assert "Integrity verified" not in caplog.text
            assert "Integrity check failed" not in caplog.text

    def test_sanitize_logs(self, manager: EncryptDecryptManager) -> None:
        """Test _sanitize_logs redacts sensitive information."""
        input_bytes = b"password=secret123 ip=192.168.1.1 error"
        expected = "password=[REDACTED] ip=[IP_REDACTED] error"

        result = manager._sanitize_logs(input_bytes)  # type: ignore
        assert result == expected

    @patch("subprocess.run")
    def test_run_encryption_process_success(
        self, mock_subprocess: MagicMock, manager: EncryptDecryptManager
    ) -> None:
        """Test _run_encryption_process succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b"success"
        mock_subprocess.return_value = mock_result

        result = manager._run_encryption_process("/input/file", "password")  # type: ignore
        assert result is True
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_run_encryption_process_failure(
        self, mock_subprocess: MagicMock, manager: EncryptDecryptManager
    ) -> None:
        """Test _run_encryption_process fails."""
        mock_subprocess.side_effect = CalledProcessError(
            1, "openssl", stderr=b"error"
        )

        result = manager._run_encryption_process("/input/file", "password")  # type: ignore
        assert result is False
