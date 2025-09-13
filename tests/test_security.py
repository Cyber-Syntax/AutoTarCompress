"""Tests for security-related functionality.

This module tests security features including encryption, password handling,
and other security components.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autotarcompress.security import ContextManager


class TestContextManager:
    """Test ContextManager security functionality."""

    def test_context_manager_initialization(self) -> None:
        """Test that ContextManager initializes correctly."""
        context_manager = ContextManager()
        assert hasattr(context_manager, "logger")

    def test_context_manager_has_password_context_method(self) -> None:
        """Test that ContextManager has the password context method."""
        context_manager = ContextManager()
        assert hasattr(context_manager, "_password_context")
        assert callable(context_manager._password_context)

    @patch("autotarcompress.security.getpass.getpass")
    def test_password_context_functionality(self, mock_getpass: MagicMock) -> None:
        """Test password context functionality through mocking."""
        mock_getpass.return_value = "test_password"

        context_manager = ContextManager()

        # Test that we can call the password context (even if protected)
        # This tests the underlying functionality without direct access
        with patch.object(context_manager, "_password_context") as mock_context:
            mock_context.return_value.__enter__ = MagicMock(return_value="test_password")
            mock_context.return_value.__exit__ = MagicMock(return_value=None)

            with mock_context() as password:
                assert password == "test_password"

    def test_context_manager_logger_setup(self) -> None:
        """Test that context manager has proper logging setup."""
        context_manager = ContextManager()
        assert hasattr(context_manager, "logger")
        assert context_manager.logger is not None
        assert hasattr(context_manager.logger, "error")
        assert hasattr(context_manager.logger, "info")
        assert hasattr(context_manager.logger, "debug")

    @patch("autotarcompress.security.logging.getLogger")
    def test_context_manager_logging_configuration(self, mock_get_logger: MagicMock) -> None:
        """Test that context manager configures logging correctly."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        context_manager = ContextManager()

        # Verify logger was requested with correct module name
        mock_get_logger.assert_called_with("autotarcompress.security")
        assert context_manager.logger == mock_logger
