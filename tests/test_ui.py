"""Tests for UI module functionality.

This module tests user interface utilities and input validation.
Tests follow modern Python 3.12+ practices with full type annotations.
"""

import os
import sys
from unittest.mock import patch

import pytest

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

        with pytest.raises(ValueError, match="No files available for selection"):
            select_file(files, backup_folder)

    def test_select_file_invalid_input_then_valid(self) -> None:
        """Test select_file with invalid input followed by valid input."""
        files = ["backup1.tar.xz", "backup2.tar.xz"]
        backup_folder = "/tmp/backups"

        # Mock input to return invalid input first, then valid
        with patch("builtins.input", side_effect=["invalid", "1"]):
            with patch("builtins.print") as mock_print:
                result = select_file(files, backup_folder)
                expected = os.path.join(backup_folder, "backup1.tar.xz")
                assert result == expected
                # Verify error message was printed
                mock_print.assert_any_call("Invalid input. Please enter a number.")

    def test_get_menu_choice_valid(self) -> None:
        """Test get_menu_choice with valid input."""
        with patch("builtins.input", return_value="3"):
            result = get_menu_choice()
            assert result == 3

    def test_get_menu_choice_invalid_then_valid(self) -> None:
        """Test get_menu_choice with invalid input followed by valid."""
        with patch("builtins.input", side_effect=["invalid", "8", "5"]):
            with patch("builtins.print") as mock_print:
                result = get_menu_choice()
                assert result == 5
                # Verify error messages were printed
                mock_print.assert_any_call("Invalid input. Please enter a number between 1-7.")

    def test_display_main_menu(self) -> None:
        """Test display_main_menu prints expected content."""
        with patch("builtins.print") as mock_print:
            display_main_menu()
            # Verify the menu was printed
            mock_print.assert_any_call("\n===== Backup Manager =====")
            mock_print.assert_any_call("1. Perform Backup")
            mock_print.assert_any_call("7. Exit")

    def test_exit_application(self) -> None:
        """Test exit_application calls sys.exit."""
        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                exit_application()
                mock_exit.assert_called_once_with(0)
                mock_print.assert_called_with("Exiting...")

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
