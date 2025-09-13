"""Command pattern implementations for backup operations.

This module aggregates all command classes for easy importing.
"""

from autotarcompress.commands.command import Command
from autotarcompress.commands.backup import BackupCommand
from autotarcompress.commands.cleanup import CleanupCommand
from autotarcompress.commands.decrypt import DecryptCommand
from autotarcompress.commands.encrypt import EncryptCommand
from autotarcompress.commands.extract import ExtractCommand
from autotarcompress.commands.info import InfoCommand

__all__ = [
    "Command",
    "BackupCommand",
    "CleanupCommand",
    "DecryptCommand",
    "EncryptCommand",
    "ExtractCommand",
    "InfoCommand",
]