"""Command interface for backup operations.

This module contains the abstract Command class that defines the command pattern interface.
"""

from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract command interface for backup manager operations."""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command operation.

        Returns:
            bool: True if command succeeded, False otherwise.

        """
