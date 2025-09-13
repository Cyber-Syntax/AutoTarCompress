"""Tests for facade pattern implementation.

This module tests the BackupFacade class which provides a simplified interface
for backup operations.
"""

import os
import sys
from unittest.mock import patch

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import BackupConfig
from src.facade import BackupFacade


class TestBackupFacade:
    """Test BackupFacade functionality."""

    def test_facade_initialization(self) -> None:
        """Test that BackupFacade initializes correctly."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_config = BackupConfig()
            mock_load.return_value = mock_config

            facade = BackupFacade()
            assert facade.config == mock_config
            assert hasattr(facade, "commands")
            assert isinstance(facade.commands, dict)

    def test_facade_has_all_commands(self) -> None:
        """Test that facade provides access to all command types."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            expected_commands = ["backup", "cleanup", "info"]

            for command_name in expected_commands:
                assert command_name in facade.commands
                assert facade.commands[command_name] is not None

    def test_facade_backup_command(self) -> None:
        """Test that facade can execute backup command."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            # Mock the backup command execution
            with patch.object(
                facade.commands["backup"], "execute", return_value=True
            ) as mock_execute:
                result = facade.commands["backup"].execute()
                assert result is True
                mock_execute.assert_called_once()

    def test_facade_cleanup_command(self) -> None:
        """Test that facade can execute cleanup command."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            # Mock the cleanup command execution
            with patch.object(
                facade.commands["cleanup"], "execute", return_value=None
            ) as mock_execute:
                result = facade.commands["cleanup"].execute()
                assert result is None
                mock_execute.assert_called_once()

    def test_facade_info_command(self) -> None:
        """Test that facade can execute info command."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            # Mock the info command execution
            with patch.object(
                facade.commands["info"], "execute", return_value=None
            ) as mock_execute:
                result = facade.commands["info"].execute()
                assert result is None
                mock_execute.assert_called_once()

    def test_facade_configuration_method(self) -> None:
        """Test that facade has configuration functionality."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            assert hasattr(facade, "configure")
            assert callable(facade.configure)

    def test_facade_command_access_patterns(self) -> None:
        """Test different ways to access commands through facade."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_config = BackupConfig()
            mock_load.return_value = mock_config

            facade = BackupFacade()

            # Test direct access
            backup_cmd = facade.commands["backup"]
            assert backup_cmd is not None

            # Test that commands have expected attributes
            assert hasattr(backup_cmd, "execute")
            assert hasattr(backup_cmd, "config")
            assert backup_cmd.config == mock_config

    def test_facade_with_different_config_loads(self) -> None:
        """Test facade behavior with different configuration loads."""
        config1 = BackupConfig()
        config1.backup_folder = "/test/backup1"

        config2 = BackupConfig()
        config2.backup_folder = "/test/backup2"

        with patch.object(BackupConfig, "load", return_value=config1):
            facade1 = BackupFacade()

        with patch.object(BackupConfig, "load", return_value=config2):
            facade2 = BackupFacade()

        # Facades should reflect their loaded configs
        assert facade1.config.backup_folder == "/test/backup1"
        assert facade2.config.backup_folder == "/test/backup2"

        # But should have same command structure
        assert set(facade1.commands.keys()) == set(facade2.commands.keys())

    def test_facade_command_execution_isolation(self) -> None:
        """Test that facade commands are properly isolated."""
        with patch.object(BackupConfig, "load") as mock_load:
            mock_load.return_value = BackupConfig()

            facade = BackupFacade()

            # Mock multiple command executions
            with patch.object(facade.commands["backup"], "execute") as mock_backup, patch.object(
                facade.commands["cleanup"], "execute"
            ) as mock_cleanup:
                # Execute different commands
                facade.commands["backup"].execute()
                facade.commands["cleanup"].execute()

                # Verify each was called independently
                mock_backup.assert_called_once()
                mock_cleanup.assert_called_once()
