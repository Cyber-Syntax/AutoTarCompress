"""Tests for the EncryptCommand class.

This module contains comprehensive tests for the encryption command implementation,
including mocking external processes and testing security features.
"""

import logging
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.commands.encrypt import EncryptCommand
from src.config import BackupConfig

# Test constants
PBKDF2_ITERATIONS = 600000
OPENSSL_VERSION = (3, 0, 0)


class TestEncryptCommand:
    """Test cases for EncryptCommand class."""

    @pytest.fixture
    def mock_config(self) -> BackupConfig:
        """Create a mock BackupConfig for testing."""
        return BackupConfig()

    @pytest.fixture
    def test_file(self, tmp_path: Path) -> str:
        """Create a test file for encryption."""
        test_file = tmp_path / "test_backup.tar.xz"
        test_file.write_text("test content for encryption")
        return str(test_file)

    @pytest.fixture
    def encrypt_command(self, mock_config: BackupConfig, test_file: str) -> EncryptCommand:
        """Create an EncryptCommand instance for testing."""
        return EncryptCommand(mock_config, test_file)

    def test_encrypt_command_initialization(
        self, mock_config: BackupConfig, test_file: str
    ) -> None:
        """Test EncryptCommand initialization."""
        command = EncryptCommand(mock_config, test_file)

        assert command.file_to_encrypt == test_file
        assert isinstance(command.logger, logging.Logger)
        assert command.logger.name == "src.commands.encrypt"
        assert command.PBKDF2_ITERATIONS == PBKDF2_ITERATIONS

    def test_execute_file_not_found(self, encrypt_command: EncryptCommand) -> None:
        """Test execute fails when file does not exist."""
        encrypt_command.file_to_encrypt = "/nonexistent/file.tar.xz"

        result = encrypt_command.execute()

        assert result is False

    def test_execute_empty_file(self, tmp_path: Path, mock_config: BackupConfig) -> None:
        """Test execute fails when file is empty (security measure)."""
        empty_file = tmp_path / "empty.tar.xz"
        empty_file.touch()
        command = EncryptCommand(mock_config, str(empty_file))

        result = command.execute()

        assert result is False

    @patch("subprocess.run")
    def test_execute_successful_encryption(
        self, mock_subprocess: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test successful encryption execution."""
        # Mock the password context manager
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(encrypt_command, "_password_context", return_value=mock_password_context):
            # Mock successful subprocess
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

            result = encrypt_command.execute()

            assert result is True
            mock_subprocess.assert_called_once()

            # Verify OpenSSL command parameters
            call_args = mock_subprocess.call_args
            cmd = call_args[1]["input"]  # The command input
            assert cmd == b"test_password\n"

            # Verify command arguments
            args = call_args[0][0]
            assert "openssl" in args
        assert "enc" in args
        assert "-aes-256-cbc" in args
        assert "-pbkdf2" in args
        assert "-iter" in args
        assert "600000" in args

    def test_execute_no_password_provided(self, encrypt_command: EncryptCommand) -> None:
        """Test execute fails when no password is provided."""
        # Mock the password context manager to return None
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value=None)
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(encrypt_command, "_password_context", return_value=mock_password_context):
            result = encrypt_command.execute()

            assert result is False

    @patch("subprocess.run")
    def test_execute_subprocess_error(
        self, mock_subprocess: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test execute fails when subprocess raises CalledProcessError."""
        # Mock the password context manager
        mock_password_context = Mock()
        mock_password_context.__enter__ = Mock(return_value="test_password")
        mock_password_context.__exit__ = Mock(return_value=None)

        with patch.object(encrypt_command, "_password_context", return_value=mock_password_context):
            # Mock failed subprocess
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "openssl", stderr=b"encryption failed"
            )

            # Mock safe cleanup
            with patch.object(encrypt_command, "_safe_cleanup") as mock_safe_cleanup:
                result = encrypt_command.execute()

                assert result is False
                mock_safe_cleanup.assert_called_once()

    def test_validate_input_file_not_exists(self, encrypt_command: EncryptCommand) -> None:
        """Test _validate_input_file with non-existent file."""
        encrypt_command.file_to_encrypt = "/nonexistent/file.tar.xz"

        result = encrypt_command._validate_input_file()

        assert result is False

    def test_validate_input_file_empty(self, tmp_path: Path, mock_config: BackupConfig) -> None:
        """Test _validate_input_file with empty file."""
        empty_file = tmp_path / "empty.tar.xz"
        empty_file.touch()
        command = EncryptCommand(mock_config, str(empty_file))

        result = command._validate_input_file()

        assert result is False

    def test_validate_input_file_valid(self, encrypt_command: EncryptCommand) -> None:
        """Test _validate_input_file with valid file."""
        result = encrypt_command._validate_input_file()

        assert result is True

    @patch("subprocess.run")
    def test_run_encryption_process_success(
        self, mock_subprocess: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test _run_encryption_process with successful encryption."""
        mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")

        result = encrypt_command._run_encryption_process("test_password")

        assert result is True
        mock_subprocess.assert_called_once()

        # Verify command structure
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "openssl"
        assert "-aes-256-cbc" in args
        assert "-pbkdf2" in args
        assert str(encrypt_command.PBKDF2_ITERATIONS) in args

    @patch("subprocess.run")
    def test_run_encryption_process_timeout(
        self, mock_subprocess: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test _run_encryption_process handles timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("openssl", 300)

        with patch.object(encrypt_command, "_safe_cleanup") as mock_cleanup:
            result = encrypt_command._run_encryption_process("test_password")

            assert result is False
            mock_cleanup.assert_called_once()

    def test_sanitize_logs_password_redaction(self, encrypt_command: EncryptCommand) -> None:
        """Test _sanitize_logs properly redacts passwords."""
        test_output = b"password=secret123 some other output"

        result = encrypt_command._sanitize_logs(test_output)

        assert "password=[REDACTED]" in result
        assert "secret123" not in result

    def test_sanitize_logs_ip_redaction(self, encrypt_command: EncryptCommand) -> None:
        """Test _sanitize_logs properly redacts IP addresses."""
        test_output = b"connecting to 192.168.1.1 and 10.0.0.1"

        result = encrypt_command._sanitize_logs(test_output)

        assert "[IP_REDACTED]" in result
        assert "192.168.1.1" not in result
        assert "10.0.0.1" not in result

    def test_sanitize_logs_unicode_handling(self, encrypt_command: EncryptCommand) -> None:
        """Test _sanitize_logs handles invalid unicode gracefully."""
        test_output = b"\xff\xfe invalid unicode"

        result = encrypt_command._sanitize_logs(test_output)

        assert isinstance(result, str)
        # Should not raise an exception

    @given(st.text(min_size=1, max_size=100))
    def test_sanitize_logs_property(self, text: str) -> None:
        """Property-based test for _sanitize_logs method."""
        encrypt_command = EncryptCommand(BackupConfig(), "/tmp/test.tar.xz")

        # Convert to bytes and back to ensure we can handle various inputs
        try:
            test_output = text.encode("utf-8")
        except UnicodeEncodeError:
            # Skip invalid unicode test cases
            return

        result = encrypt_command._sanitize_logs(test_output)

        assert isinstance(result, str)
        # Should not contain sensitive patterns in output
        assert "password=" not in result.lower() or "[REDACTED]" in result

    def test_openssl_command_security_parameters(self, encrypt_command: EncryptCommand) -> None:
        """Test that OpenSSL command uses secure parameters."""
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")
            encrypt_command._run_encryption_process("test_password")

            args = mock_subprocess.call_args[0][0]

            # Verify security parameters
            assert "-aes-256-cbc" in args  # Strong encryption
            assert "-a" in args  # Base64 encoding
            assert "-salt" in args  # Salt for key derivation
            assert "-pbkdf2" in args  # PBKDF2 key derivation
            assert str(encrypt_command.PBKDF2_ITERATIONS) in args  # Sufficient iterations
            assert "-pass" in args
            assert "fd:0" in args  # Secure password passing

    def test_output_file_path_generation(self, encrypt_command: EncryptCommand) -> None:
        """Test that output file path is correctly generated."""
        expected_output = f"{encrypt_command.file_to_encrypt}.enc"

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")
            encrypt_command._run_encryption_process("test_password")

            args = mock_subprocess.call_args[0][0]
            out_index = args.index("-out")
            actual_output = args[out_index + 1]

            assert actual_output == expected_output

    @patch("subprocess.run")
    def test_process_shell_false_security(
        self, mock_subprocess: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test that subprocess is called with shell=False for security."""
        mock_subprocess.return_value = Mock(returncode=0, stderr=b"success")
        encrypt_command._run_encryption_process("test_password")

        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["shell"] is False

    def test_encryption_constants(self, encrypt_command: EncryptCommand) -> None:
        """Test that encryption constants meet security requirements."""
        # OWASP recommended minimum iterations
        assert encrypt_command.PBKDF2_ITERATIONS >= PBKDF2_ITERATIONS

        # Required OpenSSL version for strong crypto
        assert encrypt_command.required_openssl_version == OPENSSL_VERSION

    @patch("os.path.isfile")
    @patch("os.path.getsize")
    def test_edge_case_file_permissions(
        self, mock_getsize: Mock, mock_isfile: Mock, encrypt_command: EncryptCommand
    ) -> None:
        """Test edge case where file exists but can't be read."""
        mock_isfile.return_value = True
        mock_getsize.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            encrypt_command._validate_input_file()
