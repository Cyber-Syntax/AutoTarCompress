"""Facade pattern implementation for backup system.

This module provides a simplified interface to the backup system components.
"""

from pathlib import Path
from typing import Any, Dict, List

from src.commands import BackupCommand, CleanupCommand, Command
from src.config import BackupConfig


class BackupFacade:
    """Facade to manage backup manager operations"""

    def __init__(self):
        self.config = BackupConfig.load()
        self.commands: Dict[str, Command] = {
            "backup": BackupCommand(self.config),
            "cleanup": CleanupCommand(self.config),
        }

    def configure(self) -> None:
        """Interactive configuration wizard"""
        print("\n=== Backup Manager Configuration ===")
        self._setup_paths()
        self._setup_retention()
        self._setup_directories()
        self.config.save()
        print("\nConfiguration saved successfully!")

    def execute_command(self, command_name: str) -> Any:
        """Execute a predefined command"""
        if command_name in self.commands:
            return self.commands[command_name].execute()
        else:
            raise ValueError(f"Unknown command: {command_name}")

    def _setup_paths(self) -> None:
        """Configure backup storage location"""
        print("\n=== Backup Storage Location ===")
        new_path = input(
            "Enter backup directory (default: ~/Documents/backup-for-cloud/): "
        ).strip()
        if new_path:
            self.config.backup_folder = str(Path(new_path).expanduser())
        print(f"Using backup directory: {Path(self.config.backup_folder).expanduser()}")

    def _setup_retention(self) -> None:
        """Configure backup retention policies"""
        print("\n=== Backup Retention Settings ===")
        try:
            self.config.keep_backup = int(
                input("Number of regular backups to keep (default 1): ") or self.config.keep_backup
            )
            self.config.keep_enc_backup = int(
                input("Number of encrypted backups to keep (default 1): ")
                or self.config.keep_enc_backup
            )
        except ValueError:
            print("Invalid number format. Using existing values.")

    def _setup_directories(self) -> None:
        """Interactive directory configuration"""
        print("\n=== Directory Configuration ===")
        self._manage_path_list(
            "Backup Directories",
            self.config.dirs_to_backup,
            "Enter directories to add (comma-separated): ",
            "Current backup directories:",
        )
        self._manage_path_list(
            "Ignored Paths",
            self.config.ignore_list,
            "Enter paths to ignore (comma-separated): ",
            "Current ignored paths:",
        )

    def _manage_path_list(
        self, title: str, target_list: list, add_prompt: str, list_header: str
    ) -> None:
        """Generic interactive list manager"""
        while True:
            print(f"\n{list_header}")
            if not target_list:
                print("  None configured")
            else:
                for i, path in enumerate(target_list, 1):
                    expanded = Path(path).expanduser()
                    status = "(exists)" if expanded.exists() else "(not found)"
                    print(f"  {i}. {path} {status}")

            print("\nOptions:")
            print("1. Add paths")
            print("2. Remove path")
            print("3. Finish configuration")

            try:
                choice = int(input("Choose an option (1-3): "))
            except ValueError:
                print("Please enter a valid number")
                continue

            if choice == 1:
                new_items = input(add_prompt).split(",")
                cleaned_paths = self._validate_paths([p.strip() for p in new_items])
                target_list.extend(p for p in cleaned_paths if p not in target_list)
            elif choice == 2:
                self._remove_path(target_list)
            elif choice == 3:
                break
            else:
                print("Invalid choice. Please try again.")

    def _validate_paths(self, paths: List[str]) -> List[str]:
        """Validate and normalize paths with user confirmation"""
        valid_paths = []
        for path in paths:
            if not path:
                continue

            expanded = Path(path).expanduser()
            if not expanded.exists():
                print(f"Warning: Path does not exist - {expanded}")
                if input("Add anyway? (y/N): ").lower() != "y":
                    continue

            # Store original path with ~ if provided
            valid_paths.append(path)
        return valid_paths

    def _remove_path(self, target_list: list) -> None:
        """Safely remove items from list"""
        if not target_list:
            print("List is empty")
            return

        try:
            index = int(input(f"Enter number to remove (1-{len(target_list)}): ")) - 1
            if 0 <= index < len(target_list):
                removed = target_list.pop(index)
                print(f"Removed: {removed}")
            else:
                print("Invalid index number")
        except ValueError:
            print("Please enter a valid number")
