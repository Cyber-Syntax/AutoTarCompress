"""Tests for the Command abstract base class.

This module contains tests for the abstract Command interface that all
command implementations must follow.
"""

from abc import ABC
from typing import Any

import pytest

from autotarcompress.commands.command import Command


class ConcreteCommand(Command):
    """Concrete implementation of Command for testing purposes."""

    def __init__(self, should_succeed: bool = True) -> None:
        """Initialize with success/failure control for testing."""
        self.should_succeed = should_succeed
        self.executed = False

    def execute(self) -> bool:
        """Execute the command and return success status."""
        self.executed = True
        return self.should_succeed


class TestCommand:
    """Test cases for the Command abstract base class."""

    def test_command_is_abstract_base_class(self) -> None:
        """Test that Command is properly defined as an ABC."""
        assert issubclass(Command, ABC)
        assert hasattr(Command, "__abstractmethods__")
        assert "execute" in Command.__abstractmethods__

    def test_cannot_instantiate_abstract_command(self) -> None:
        """Test that Command cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Command()  # type: ignore[abstract]

    def test_concrete_command_can_be_instantiated(self) -> None:
        """Test that concrete implementations can be instantiated."""
        command = ConcreteCommand()
        assert isinstance(command, Command)
        assert hasattr(command, "execute")

    def test_concrete_command_execute_success(self) -> None:
        """Test successful execution of concrete command."""
        command = ConcreteCommand(should_succeed=True)
        result = command.execute()

        assert result is True
        assert command.executed is True

    def test_concrete_command_execute_failure(self) -> None:
        """Test failed execution of concrete command."""
        command = ConcreteCommand(should_succeed=False)
        result = command.execute()

        assert result is False
        assert command.executed is True

    def test_execute_method_signature(self) -> None:
        """Test that execute method has correct signature."""
        command = ConcreteCommand()

        # Test that execute method exists and is callable
        assert callable(command.execute)

        # Test return type annotation (if available)
        annotations = getattr(command.execute, "__annotations__", {})
        if "return" in annotations:
            # This is flexible since return type may vary in implementations
            assert annotations["return"] in [bool, Any, None]
