"""Tests for the EncryptManager and DecryptManager classes.

This module contains comprehensive tests for the encrypt/decrypt managers
using AES-256-GCM authenticated encryption with the cryptography library.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autotarcompress.config import BackupConfig
from autotarcompress.decrypt_manager import DecryptManager
from autotarcompress.encrypt_manager import EncryptManager


class TestEncryptManager:
    """Test cases for EncryptManager class."""

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> BackupConfig:
        """Create a mock BackupConfig for testing.

        Uses a temporary directory to ensure tests don't pollute
        the real user configuration directory.
        """
        config = BackupConfig()
        config.config_dir = str(tmp_path / "config")
        return config

    @pytest.fixture
    def manager(self, mock_config: BackupConfig) -> EncryptManager:
        """Create an EncryptManager instance for testing."""
        return EncryptManager(mock_config)

    def test_manager_initialization(self, mock_config: BackupConfig) -> None:
        """Test EncryptManager initialization."""
        manager = EncryptManager(mock_config)

        assert manager.config == mock_config
        assert isinstance(manager.logger, logging.Logger)
        assert manager.PBKDF2_ITERATIONS == 600000
        assert manager.SALT_SIZE == 16
        assert manager.NONCE_SIZE == 12
        assert manager.KEY_SIZE == 32

    def test_validate_input_file_exists(self, manager: EncryptManager) -> None:
        """Test _validate_input_file with existing file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()

            result = manager._validate_input_file(temp_file.name)
            assert result is True

    def test_validate_input_file_not_exists(
        self, manager: EncryptManager
    ) -> None:
        """Test _validate_input_file with non-existent file."""
        result = manager._validate_input_file("/nonexistent/file")
        assert result is False

    def test_validate_input_file_empty(self, manager: EncryptManager) -> None:
        """Test _validate_input_file with empty file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            result = manager._validate_input_file(temp_file.name)
            assert result is False

    def test_calculate_sha256(self, manager: EncryptManager) -> None:
        """Test _calculate_sha256 calculates correct hash."""
        test_content = b"Hello, World!"
        expected_hash = (
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_content)
            temp_file.flush()

            result = manager._calculate_sha256(temp_file.name)
            assert result == expected_hash

    def test_derive_key_deterministic(self, manager: EncryptManager) -> None:
        """Test _derive_key produces same key with same password and salt."""
        password = "test_password"
        salt = b"sixteen_bytes123"

        key1 = manager._derive_key(password, salt)
        key2 = manager._derive_key(password, salt)

        assert key1 == key2
        assert len(key1) == 32  # 256 bits

    def test_derive_key_different_salts(self, manager: EncryptManager) -> None:
        """Test _derive_key produces different keys with different salts."""
        password = "test_password"
        salt1 = b"sixteen_bytes123"
        salt2 = b"sixteen_bytes456"

        key1 = manager._derive_key(password, salt1)
        key2 = manager._derive_key(password, salt2)

        assert key1 != key2

    def test_generate_salt(self, manager: EncryptManager) -> None:
        """Test _generate_salt creates random salt of correct size."""
        salt1 = manager._generate_salt()
        salt2 = manager._generate_salt()

        assert len(salt1) == 16
        assert len(salt2) == 16
        assert salt1 != salt2  # Should be random

    def test_generate_nonce(self, manager: EncryptManager) -> None:
        """Test _generate_nonce creates random nonce of correct size."""
        nonce1 = manager._generate_nonce()
        nonce2 = manager._generate_nonce()

        assert len(nonce1) == 12
        assert len(nonce2) == 12
        assert nonce1 != nonce2  # Should be random

    @patch("getpass.getpass")
    def test_execute_encrypt_success(
        self, mock_getpass: MagicMock, manager: EncryptManager
    ) -> None:
        """Test execute_encrypt with successful encryption."""
        mock_getpass.side_effect = ["test_password", "test_password"]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content for encryption")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            result = manager.execute_encrypt(temp_path)
            assert result is True

            # Verify .enc file was created
            enc_path = f"{temp_path}.enc"
            assert Path(enc_path).exists()

            # Verify file structure: salt(16) + nonce(12) + ciphertext + tag
            encrypted_data = Path(enc_path).read_bytes()
            assert len(encrypted_data) >= 44  # Minimum size

            # Clean up
            Path(enc_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("getpass.getpass")
    def test_execute_encrypt_password_none(
        self, mock_getpass: MagicMock, manager: EncryptManager
    ) -> None:
        """Test execute_encrypt when password is empty."""
        mock_getpass.return_value = ""

        result = manager.execute_encrypt("/some/file")
        assert result is False

    def test_execute_encrypt_invalid_file(
        self, manager: EncryptManager
    ) -> None:
        """Test execute_encrypt with invalid file."""
        result = manager.execute_encrypt("/nonexistent/file")
        assert result is False


class TestDecryptManager:
    """Test cases for DecryptManager class."""

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> BackupConfig:
        """Create a mock BackupConfig for testing.

        Uses a temporary directory to ensure tests don't pollute
        the real user configuration directory.
        """
        config = BackupConfig()
        config.config_dir = str(tmp_path / "config")
        return config

    @pytest.fixture
    def manager(self, mock_config: BackupConfig) -> DecryptManager:
        """Create a DecryptManager instance for testing."""
        return DecryptManager(mock_config)

    def test_manager_initialization(self, mock_config: BackupConfig) -> None:
        """Test DecryptManager initialization."""
        manager = DecryptManager(mock_config)

        assert manager.config == mock_config
        assert isinstance(manager.logger, logging.Logger)
        assert manager.MAX_PASSWORD_ATTEMPTS == 3
        assert manager.BASE_BACKOFF_DELAY == 1.0

    @patch("getpass.getpass")
    def test_execute_decrypt_success(
        self, mock_getpass: MagicMock, manager: DecryptManager
    ) -> None:
        """Test execute_decrypt with successful decryption."""
        # First encrypt a file
        encrypt_manager = EncryptManager(manager.config)
        mock_getpass.side_effect = ["test_password", "test_password"]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content for decryption")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # Encrypt
            result = encrypt_manager.execute_encrypt(temp_path)
            assert result is True

            enc_path = f"{temp_path}.enc"
            assert Path(enc_path).exists()

            # Decrypt
            mock_getpass.side_effect = ["test_password", "test_password"]
            result = manager.execute_decrypt(enc_path)
            assert result is True

            # Verify decrypted file
            decrypted_path = f"{temp_path}-decrypted"
            assert Path(decrypted_path).exists()

            decrypted_content = Path(decrypted_path).read_bytes()
            assert decrypted_content == b"test content for decryption"

            # Clean up
            Path(decrypted_path).unlink(missing_ok=True)
            Path(enc_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("getpass.getpass")
    def test_execute_decrypt_wrong_password(
        self, mock_getpass: MagicMock, manager: DecryptManager
    ) -> None:
        """Test execute_decrypt with wrong password."""
        # First encrypt a file
        encrypt_manager = EncryptManager(manager.config)
        mock_getpass.side_effect = [
            "correct_password",
            "correct_password",
        ]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # Encrypt
            result = encrypt_manager.execute_encrypt(temp_path)
            assert result is True

            enc_path = f"{temp_path}.enc"

            # Try to decrypt with wrong password (3 attempts)
            mock_getpass.side_effect = [
                "wrong_password",
                "wrong_password",
                "wrong_password",
            ]

            # Speed up test by mocking time.sleep
            with patch("time.sleep"):
                result = manager.execute_decrypt(enc_path)

            assert result is False

            # Clean up
            Path(enc_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("getpass.getpass")
    def test_execute_decrypt_password_none(
        self, mock_getpass: MagicMock, manager: DecryptManager
    ) -> None:
        """Test execute_decrypt when password is empty."""
        mock_getpass.return_value = ""

        result = manager.execute_decrypt("/some/file.enc")
        assert result is False

    def test_execute_decrypt_invalid_file(
        self, manager: DecryptManager
    ) -> None:
        """Test execute_decrypt with invalid file."""
        result = manager.execute_decrypt("/nonexistent/file.enc")
        assert result is False

    @patch("getpass.getpass")
    def test_decrypt_tampered_file(
        self, mock_getpass: MagicMock, manager: DecryptManager
    ) -> None:
        """Test decryption fails when file is tampered."""
        # First encrypt a file
        encrypt_manager = EncryptManager(manager.config)
        mock_getpass.side_effect = ["test_password", "test_password"]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # Encrypt
            result = encrypt_manager.execute_encrypt(temp_path)
            assert result is True

            enc_path = f"{temp_path}.enc"

            # Tamper with encrypted file
            encrypted_data = Path(enc_path).read_bytes()
            # Modify a byte in the ciphertext
            tampered_data = bytearray(encrypted_data)
            tampered_data[30] ^= 0xFF  # Flip bits
            Path(enc_path).write_bytes(bytes(tampered_data))

            # Try to decrypt tampered file
            mock_getpass.side_effect = ["test_password"]

            with patch("time.sleep"):
                result = manager.execute_decrypt(enc_path)

            assert result is False

            # Clean up
            Path(enc_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_decrypt_file_too_small(self, manager: DecryptManager) -> None:
        """Test decryption fails with file smaller than minimum size."""
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".enc"
        ) as temp_file:
            # Write less than 44 bytes (min size)
            temp_file.write(b"too small")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            with patch("getpass.getpass", return_value="password"):
                result = manager.execute_decrypt(temp_path)

            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestIntegration:
    """Integration tests for encrypt and decrypt workflow."""

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> BackupConfig:
        """Create a mock BackupConfig for testing.

        Uses a temporary directory to ensure tests don't pollute
        the real user configuration directory.
        """
        config = BackupConfig()
        config.config_dir = str(tmp_path / "config")
        return config

    @patch("getpass.getpass")
    def test_encrypt_decrypt_round_trip(
        self, mock_getpass: MagicMock, mock_config: BackupConfig
    ) -> None:
        """Test complete encrypt-decrypt round trip."""
        encrypt_manager = EncryptManager(mock_config)
        decrypt_manager = DecryptManager(mock_config)

        test_content = b"This is a test content for round trip encryption!"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # Encrypt
            mock_getpass.side_effect = ["mypassword", "mypassword"]
            result = encrypt_manager.execute_encrypt(temp_path)
            assert result is True

            enc_path = f"{temp_path}.enc"
            assert Path(enc_path).exists()

            # Decrypt
            mock_getpass.side_effect = ["mypassword", "mypassword"]
            result = decrypt_manager.execute_decrypt(enc_path)
            assert result is True

            # Verify content matches
            decrypted_path = f"{temp_path}-decrypted"
            decrypted_content = Path(decrypted_path).read_bytes()
            assert decrypted_content == test_content

            # Clean up
            Path(decrypted_path).unlink(missing_ok=True)
            Path(enc_path).unlink(missing_ok=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("getpass.getpass")
    def test_encrypt_with_different_nonce_produces_different_ciphertext(
        self, mock_getpass: MagicMock, mock_config: BackupConfig
    ) -> None:
        """Test that encrypting same data twice produces different output."""
        encrypt_manager = EncryptManager(mock_config)
        test_content = b"Same content encrypted twice"

        with (
            tempfile.NamedTemporaryFile(delete=False) as temp1,
            tempfile.NamedTemporaryFile(delete=False) as temp2,
        ):
            temp1.write(test_content)
            temp1.flush()
            temp2.write(test_content)
            temp2.flush()
            temp_path1 = temp1.name
            temp_path2 = temp2.name

        try:
            # Encrypt first file
            mock_getpass.side_effect = ["password", "password"]
            encrypt_manager.execute_encrypt(temp_path1)

            # Encrypt second file with same password
            mock_getpass.side_effect = ["password", "password"]
            encrypt_manager.execute_encrypt(temp_path2)

            enc1 = Path(f"{temp_path1}.enc").read_bytes()
            enc2 = Path(f"{temp_path2}.enc").read_bytes()

            # Encrypted files should be different due to random nonce
            assert enc1 != enc2

            # But both should decrypt to same content
            decrypt_manager = DecryptManager(mock_config)

            mock_getpass.side_effect = ["password", "password"]
            decrypt_manager.execute_decrypt(f"{temp_path1}.enc")
            mock_getpass.side_effect = ["password", "password"]
            decrypt_manager.execute_decrypt(f"{temp_path2}.enc")

            dec1 = Path(f"{temp_path1}-decrypted").read_bytes()
            dec2 = Path(f"{temp_path2}-decrypted").read_bytes()

            assert dec1 == dec2 == test_content

            # Clean up
            for path in [temp_path1, temp_path2]:
                Path(f"{path}.enc").unlink(missing_ok=True)
                Path(f"{path}-decrypted").unlink(missing_ok=True)
                Path(path).unlink(missing_ok=True)
        except Exception:
            # Clean up on error
            for path in [temp_path1, temp_path2]:
                Path(path).unlink(missing_ok=True)
                Path(f"{path}.enc").unlink(missing_ok=True)
                Path(f"{path}-decrypted").unlink(missing_ok=True)
            raise
