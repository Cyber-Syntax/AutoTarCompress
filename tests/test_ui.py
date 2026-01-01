"""Tests for UI module functionality.

This module tests user interface utilities and input validation.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import os
import sys
from typing import Any
from unittest.mock import patch

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from autotarcompress.ui import (
    display_main_menu,
    exit_application,
    get_menu_choice,
    select_file,
)


class TestUIFunctionality:
    """Test UI module functionality."""

    def test_select_file_valid_choice(self) -> None:
        """Test select_file with valid user input."""
        files = ["backup1.tar.xz", "backup2.tar.xz", "backup3.tar.xz"]
        backup_folder = "/tmp/backups"

        with patch("builtins.input", return_value="2"):
            result = select_file(files, backup_folder)
            expected = os.path.join(backup_folder, "backup2.tar.xz")
            assert result == expected

    def test_select_file_empty_list(self) -> None:
        """Test select_file with empty file list."""
        files: list[str] = []
        backup_folder = "/tmp/backups"

        with pytest.raises(
            ValueError, match="No files available for selection"
        ):
            select_file(files, backup_folder)

    def test_select_file_invalid_input_then_valid(self, capsys: Any) -> None:
        """Test select_file with invalid input followed by valid input."""
        from autotarcompress.logger import setup_application_logging

        files = ["backup1.tar.xz", "backup2.tar.xz"]
        backup_folder = "/tmp/backups"

        setup_application_logging()
        # Mock input to return invalid input first, then valid
        with patch("builtins.input", side_effect=["invalid", "1"]):
            result = select_file(files, backup_folder)
            expected = os.path.join(backup_folder, "backup1.tar.xz")
            assert result == expected

        captured = capsys.readouterr()
        assert "Invalid input. Please enter a number." in captured.out

    def test_get_menu_choice_valid(self) -> None:
        """Test get_menu_choice with valid input."""
        with patch("builtins.input", return_value="3"):
            result = get_menu_choice()
            assert result == 3

    def test_get_menu_choice_invalid_then_valid(self, capsys: Any) -> None:
        """Test get_menu_choice with invalid input followed by valid."""
        from autotarcompress.logger import setup_application_logging

        setup_application_logging()
        with patch("builtins.input", side_effect=["invalid", "8", "5"]):
            result = get_menu_choice()
            assert result == 5

        captured = capsys.readouterr()
        assert (
            "Invalid input. Please enter a number between 1-7." in captured.out
        )

    def test_display_main_menu(self, capsys: Any) -> None:
        """Test display_main_menu prints expected content."""
        from autotarcompress.logger import setup_application_logging

        setup_application_logging()
        display_main_menu()

        captured = capsys.readouterr()
        output = captured.out
        assert "===== Backup Manager =====" in output
        assert "1. Perform Backup" in output
        assert "7. Exit" in output

    def test_exit_application(self, capsys: Any) -> None:
        """Test exit_application calls sys.exit."""
        from autotarcompress.logger import setup_application_logging

        setup_application_logging()
        with patch("sys.exit") as mock_exit:
            exit_application()
            mock_exit.assert_called_once_with(0)

        captured = capsys.readouterr()
        assert "Exiting..." in captured.out

    def test_select_file_keyboard_interrupt(self) -> None:
        """Test select_file handles KeyboardInterrupt properly."""
        files = ["backup1.tar.xz"]
        backup_folder = "/tmp/backups"

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                select_file(files, backup_folder)

    def test_get_menu_choice_keyboard_interrupt(self) -> None:
        """Test get_menu_choice handles KeyboardInterrupt properly."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                get_menu_choice()
