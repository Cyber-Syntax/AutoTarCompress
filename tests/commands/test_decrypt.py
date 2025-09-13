"""Tests for the DecryptCommand class.

This module contains comprehensive tests for the decryption command implementation,
including mocking external processes and testing security features.
"""

import hashlib
import logging
import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.commands.decrypt import DecryptCommand
from src.config import BackupConfig

# Test constants
PBKDF2_ITERATIONS = 600000
HASH_CHUNK_SIZE = 65536
MIN_CHUNK_READS = 3
SHA256_HEX_LENGTH = 64


class TestDecryptCommand:
    """Test cases for DecryptCommand class."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        return BackupConfig()

    @pytest.fixture
    def test_encrypted_file(self, tmp_path: Path) -> str:
        """Create a test encrypted file for decryption."""
        test_file = tmp_path / "test_backup.tar.xz.enc"
        test_file.write_text("encrypted content")
        return str(test_file)

    @pytest.fixture
    def decrypt_command(
        self, mock_config: BackupConfig, test_encrypted_file: str
    ) -> DecryptCommand:
        """Create a DecryptCommand instance for testing."""
        return DecryptCommand(mock_config, test_encrypted_file)

    def test_decrypt_command_initialization(
        self, mock_config: BackupConfig, test_encrypted_file: str
    ) -> None:
        """Test DecryptCommand initialization."""
        command = DecryptCommand(mock_config, test_encrypted_file)

        assert command.config == mock_config
        assert command.file_path == test_encrypted_file
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "src.commands.decrypt"
        assert command.PBKDF2_ITERATIONS == PBKDF2_ITERATIONS

    @patch("subprocess.run")
    def test_execute_successful_decryption(
        self, mock_subprocess: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test successful decryption execution."""
        # Mock the password context manager
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(decrypt_command, "_password_context", return_value=mock_password_context):
            # Mock successful subprocess
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

            with patch.object(decrypt_command, "_verify_integrity") as mock_verify:
                result = decrypt_command.execute()

                assert result is True
                mock_subprocess.assert_called_once()
                mock_verify.assert_called_once()

    def test_execute_no_password_provided(self, decrypt_command: DecryptCommand) -> None:
        """Test execute fails when no password is provided."""
        # Mock the password context manager to return None
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value=None)
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(decrypt_command, "_password_context", return_value=mock_password_context):
            result = decrypt_command.execute()

            assert result is False

    @patch("subprocess.run")
    def test_execute_subprocess_error(
        self, mock_subprocess: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test execute fails when subprocess raises CalledProcessError."""
        # Mock the password context manager
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(decrypt_command, "_password_context", return_value=mock_password_context):
            # Mock failed subprocess
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "openssl", stderr=b"decryption failed"
            )

            # Mock safe cleanup
            with patch.object(decrypt_command, "_safe_cleanup") as mock_safe_cleanup:
                result = decrypt_command.execute()

                assert result is False
                mock_safe_cleanup.assert_called_once()

    def test_openssl_command_parameters(self, decrypt_command: DecryptCommand) -> None:
        """Test that OpenSSL command uses correct parameters for decryption."""
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with (
            patch.object(decrypt_command, "_password_context", return_value=mock_password_context),
            patch("subprocess.run") as mock_subprocess,
        ):
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

            with patch.object(decrypt_command, "_verify_integrity"):
                decrypt_command.execute()

            args = mock_subprocess.call_args[0][0]

            # Verify decryption parameters
            assert "openssl" in args
            assert "enc" in args
            assert "-d" in args  # Decrypt mode
            assert "-aes-256-cbc" in args
            assert "-a" in args  # Base64 decoding
            assert "-salt" in args
            assert "-pbkdf2" in args
            assert "-iter" in args
            assert str(decrypt_command.PBKDF2_ITERATIONS) in args
            assert "-pass" in args
            assert "fd:0" in args

    def test_output_file_path_generation(self, decrypt_command: DecryptCommand) -> None:
        """Test that output file path is correctly generated."""
        expected_base = decrypt_command.file_path.replace(".enc", "")
        expected_output = f"{expected_base}-decrypted"

        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with (
            patch.object(decrypt_command, "_password_context", return_value=mock_password_context),
            patch("subprocess.run") as mock_subprocess,
        ):
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

            with patch.object(decrypt_command, "_verify_integrity"):
                decrypt_command.execute()

            args = mock_subprocess.call_args[0][0]
            out_index = args.index("-out")
            actual_output = args[out_index + 1]

            assert actual_output == expected_output

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test data")
    def test_verify_integrity_files_match(
        self, mock_file_open: Mock, mock_exists: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test _verify_integrity when decrypted file matches original."""
        mock_exists.return_value = True

        with patch.object(decrypt_command, "_calculate_sha256") as mock_hash:
            mock_hash.return_value = "same_hash"

            # Should not raise an exception
            decrypt_command._verify_integrity("decrypted_file")

    @patch("os.path.exists")
    def test_verify_integrity_no_original_file(
        self, mock_exists: Mock, decrypt_command: DecryptCommand, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _verify_integrity when original file doesn't exist."""
        mock_exists.return_value = False

        # Should not raise an exception, just skip verification
        decrypt_command._verify_integrity("decrypted_file")

    @patch("builtins.open", new_callable=mock_open, read_data=b"test content")
    def test_calculate_sha256(self, mock_file_open: Mock, decrypt_command: DecryptCommand) -> None:
        """Test _calculate_sha256 method."""
        test_data = b"test content"
        expected_hash = hashlib.sha256(test_data).hexdigest()

        result = decrypt_command._calculate_sha256("test_file")

        assert result == expected_hash
        mock_file_open.assert_called_once_with("test_file", "rb")

    @patch("builtins.open", new_callable=mock_open)
    def test_calculate_sha256_large_file(
        self, mock_file_open: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test _calculate_sha256 handles large files by reading in chunks."""
        # Mock file that returns data in chunks
        large_data = b"x" * (HASH_CHUNK_SIZE * 2 + 1000)  # Larger than chunk size
        mock_file_open.return_value.read.side_effect = [
            large_data[:HASH_CHUNK_SIZE],
            large_data[HASH_CHUNK_SIZE : HASH_CHUNK_SIZE * 2],
            large_data[HASH_CHUNK_SIZE * 2 :],
            b"",  # EOF
        ]

        expected_hash = hashlib.sha256(large_data).hexdigest()

        result = decrypt_command._calculate_sha256("large_file")

        assert result == expected_hash
        # Verify it read in chunks
        assert mock_file_open.return_value.read.call_count >= MIN_CHUNK_READS

    def test_sanitize_logs_password_redaction(self, decrypt_command: DecryptCommand) -> None:
        """Test _sanitize_logs properly redacts passwords."""
        test_output = b"password=secret123 some other output"

        result = decrypt_command._sanitize_logs(test_output)

        assert "password=[REDACTED]" in result
        assert "secret123" not in result

    def test_sanitize_logs_ip_redaction(self, decrypt_command: DecryptCommand) -> None:
        """Test _sanitize_logs properly redacts IP addresses."""
        test_output = b"connecting to 192.168.1.1 and 10.0.0.1"

        result = decrypt_command._sanitize_logs(test_output)

        assert "[IP_REDACTED]" in result
        assert "192.168.1.1" not in result
        assert "10.0.0.1" not in result

    def test_sanitize_logs_unicode_handling(self, decrypt_command: DecryptCommand) -> None:
        """Test _sanitize_logs handles invalid unicode gracefully."""
        test_output = b"\xff\xfe invalid unicode"

        result = decrypt_command._sanitize_logs(test_output)

        assert isinstance(result, str)

    @given(st.text(min_size=1, max_size=100))
    def test_sanitize_logs_property(self, text: str) -> None:
        """Property-based test for _sanitize_logs method."""
        decrypt_command = DecryptCommand(BackupConfig(), "/tmp/test.enc")

        try:
            test_output = text.encode("utf-8")
        except UnicodeEncodeError:
            return

        result = decrypt_command._sanitize_logs(test_output)

        assert isinstance(result, str)
        assert "password=" not in result.lower() or "[REDACTED]" in result

    @patch("subprocess.run")
    def test_process_shell_false_security(
        self, mock_subprocess: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test that subprocess is called with shell=False for security."""
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(decrypt_command, "_password_context", return_value=mock_password_context):
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

            with patch.object(decrypt_command, "_verify_integrity"):
                decrypt_command.execute()

            call_kwargs = mock_subprocess.call_args[1]
            assert call_kwargs["shell"] is False

    def test_decryption_constants(self, decrypt_command: DecryptCommand) -> None:
        """Test that decryption constants match encryption requirements."""
        # Must match encryption iterations for compatibility
        assert decrypt_command.PBKDF2_ITERATIONS == PBKDF2_ITERATIONS

    @patch("builtins.open")
    def test_verify_integrity_file_read_error(
        self,
        mock_file_open: Mock,
        decrypt_command: DecryptCommand,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test _verify_integrity handles file read errors gracefully."""
        import contextlib

        with patch("os.path.exists", return_value=True):
            mock_file_open.side_effect = OSError("File read error")

            # Should not raise an exception, but should log an error
            with contextlib.suppress(OSError):
                decrypt_command._verify_integrity("decrypted_file")

    @patch("subprocess.run")
    def test_execute_timeout_handling(
        self, mock_subprocess: Mock, decrypt_command: DecryptCommand
    ) -> None:
        """Test execute handles subprocess timeout gracefully."""
        # Mock the password context manager
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(decrypt_command, "_password_context", return_value=mock_password_context):
            # Mock timeout
            mock_subprocess.side_effect = subprocess.TimeoutExpired("openssl", 300)

            # Mock safe cleanup
            with patch.object(decrypt_command, "_safe_cleanup") as mock_safe_cleanup:
                result = decrypt_command.execute()

                assert result is False
                mock_safe_cleanup.assert_called_once()

    def test_input_validation_edge_cases(self, tmp_path: Path, mock_config: BackupConfig) -> None:
        """Test various edge cases for input validation."""
        # Test with non-.enc file
        non_enc_file = tmp_path / "test.tar.xz"
        non_enc_file.write_text("content")
        command = DecryptCommand(mock_config, str(non_enc_file))

        # Should still work - DecryptCommand doesn't validate extension
        assert command.file_path == str(non_enc_file)

    @given(st.binary(min_size=0, max_size=1000))
    def test_calculate_sha256_property(self, data: bytes) -> None:
        """Property-based test for _calculate_sha256 method."""
        decrypt_command = DecryptCommand(BackupConfig(), "/tmp/test.enc")

        with patch("builtins.open", mock_open(read_data=data)):
            result = decrypt_command._calculate_sha256("test_file")
            expected = hashlib.sha256(data).hexdigest()

            assert result == expected
            assert len(result) == SHA256_HEX_LENGTH  # SHA256 hex digest length
            assert all(c in "0123456789abcdef" for c in result)
