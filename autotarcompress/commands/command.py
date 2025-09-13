"""Command interface for backup operations.

This module contains the abstract Command class that defines the command pattern interface.
"""

from abc import ABC, abstractmethod


class Command(ABC):
    """Command interface for backup manager"""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command operation"""
