"""Tests for logger module functionality.

This module tests logging setup and XDG state home functionality.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autotarcompress.logger import (
    get_logger,
    get_xdg_state_home,
    setup_application_logging,
    setup_basic_logging,
)


class TestLoggerFunctionality:
    """Test logger module functionality."""

    def test_get_xdg_state_home_with_env_var(self) -> None:
        """Test get_xdg_state_home with XDG_STATE_HOME set."""
        test_path = "/test/xdg/state"
        with patch.dict(os.environ, {"XDG_STATE_HOME": test_path}):
            result = get_xdg_state_home()
            assert result == Path(test_path)

    def test_get_xdg_state_home_fallback(self) -> None:
        """Test get_xdg_state_home fallback to default location."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_xdg_state_home()
            expected = Path.home() / ".local" / "state"
            assert result == expected

    def test_get_xdg_state_home_relative_path(self) -> None:
        """Test get_xdg_state_home with relative path falls back to default."""
        with patch.dict(os.environ, {"XDG_STATE_HOME": "relative/path"}):
            result = get_xdg_state_home()
            expected = Path.home() / ".local" / "state"
            assert result == expected

    def test_setup_application_logging_basic(self) -> None:
        """Test basic application logging setup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "autotarcompress.logger.get_xdg_state_home"
        ) as mock_xdg:
            mock_xdg.return_value = Path(temp_dir)

            # Test that logging setup doesn't raise exceptions
            setup_application_logging(logging.INFO)

            # Verify log directory was created
            log_dir = Path(temp_dir) / "autotarcompress"
            assert log_dir.exists()

            # Verify log file was created
            log_file = log_dir / "autotarcompress.log"
            assert log_file.exists()

    def test_setup_basic_logging(self) -> None:
        """Test basic logging setup."""
        # Clear any existing handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        setup_basic_logging()

        # Verify basic logging was configured
        assert logger.level == logging.INFO

    def test_get_logger(self) -> None:
        """Test get_logger function."""
        logger_name = "test_logger"
        logger = get_logger(logger_name)

        assert logger.name == logger_name
        assert isinstance(logger, logging.Logger)
