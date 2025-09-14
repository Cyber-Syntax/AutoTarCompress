"""Command pattern implementations for backup operations.

This module re-exports command classes from the commands package
for backward compatibility.
"""

# Re-export command classes for backward compatibility
from autotarcompress.commands.backup import BackupCommand
from autotarcompress.commands.cleanup import CleanupCommand
from autotarcompress.commands.command import Command
from autotarcompress.commands.decrypt import DecryptCommand
from autotarcompress.commands.encrypt import EncryptCommand
from autotarcompress.commands.extract import ExtractCommand
from autotarcompress.commands.info import InfoCommand

__all__ = [
    "BackupCommand",
    "CleanupCommand",
    "Command",
    "DecryptCommand",
    "EncryptCommand",
    "ExtractCommand",
    "InfoCommand",
]
