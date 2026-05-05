"""Command pattern implementations for backup operations.

This module aggregates all command classes for easy importing.
"""

from autotarcompress.cli.commands.backup import BackupCommand
from autotarcompress.cli.commands.cleanup import CleanupCommand
from autotarcompress.cli.commands.command import Command
from autotarcompress.cli.commands.decrypt import DecryptCommand
from autotarcompress.cli.commands.encrypt import EncryptCommand
from autotarcompress.cli.commands.extract import ExtractCommand
from autotarcompress.cli.commands.info import InfoCommand

__all__ = [
    "BackupCommand",
    "CleanupCommand",
    "Command",
    "DecryptCommand",
    "EncryptCommand",
    "ExtractCommand",
    "InfoCommand",
]
