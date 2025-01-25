import os
import subprocess
import datetime
import sys
import time
import json
import gettext
from typing import List
from dataclasses import dataclass, field
from tqdm import tqdm

# TODO: get, set, setup to send backup_folder to utils.py or ...?


@dataclass
class Config:

    backup_folder: str = field(default_factory=lambda: "~/Documents/backup-for-cloud/")
    dirs_to_backup: List[str] = field(default_factory=list)
    keep_backup: int = field(default_factory=lambda: 1)
    keep_enc_backup: int = field(default_factory=lambda: 1)
    ignore_list: List[str] = field(default_factory=list)
    config_file_path: str = field(init=False)
    backup_file_path: str = field(init=False)
    current_date: str = datetime.datetime.now().strftime("%d-%m-%Y")

    def __post_init__(self):
        self.backup_file_path = os.path.expanduser(
            f"{self.backup_folder}/{self.current_date}.tar.xz"
        )
        self.config_file_path = os.path.join(
            os.path.expanduser(self.backup_folder), "config_files", "config.json"
        )

    def ask_inputs(self):
        while True:
            print("=================================================")
            self.backup_folder = (
                input(
                    _(
                        "Which directory to save backups \n(Default: '~/Documents/backup-for-cloud/' if you leave it blank):"
                    )
                ).strip()
                or self.backup_folder
            )

            # Handling default values when input is left blank
            try:
                self.keep_backup = int(
                    input("Enter the number of backups to keep: ") or self.keep_backup
                )
                self.keep_enc_backup = int(
                    input("Enter the number of .enc backups to keep: ")
                    or self.keep_enc_backup
                )
                break  # Exiting the loop after collecting input
            except ValueError:
                print("Invalid input, please enter a valid integer.")

        print("\nNow let's configure the directories for backup.")
        self.configure_directories()

    def save_credentials(self):
        """Save the credentials to a file in json format from response"""

        # Ensure the directory for the config file exists
        config_dir = os.path.dirname(self.config_file_path)
        os.makedirs(config_dir, exist_ok=True)

        config = {
            "backup_folder": self.backup_folder,
            "keep_backup": self.keep_backup,
            "keep_enc_backup": self.keep_enc_backup,
            "dirs_to_backup": self.dirs_to_backup,
            "ignore_list": self.ignore_list,
        }

        with open(self.config_file_path, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)

        print(f"Configuration file created at {self.config_file_path}")
        print(f"Updated number of backups to keep to {self.keep_backup}")
        print(f"Updated number of .enc backups to keep to {self.keep_enc_backup}")
        self.load_credentials()

    def load_credentials(self):
        """Load the credentials from a file and update the class attributes"""
        config_path = os.path.expanduser(self.config_file_path)

        if os.path.exists(config_path):
            with open(self.config_file_path, "r") as config_file:
                config = json.load(config_file)

            self.backup_folder = config.get("backup_folder", self.backup_folder)
            self.keep_backup = config.get("keep_backup", self.keep_backup)
            self.keep_enc_backup = config.get("keep_enc_backup", self.keep_enc_backup)
            self.dirs_to_backup = config.get("dirs_to_backup", self.dirs_to_backup)
            self.ignore_list = config.get("ignore_list", self.ignore_list)

            print(f"Configuration loaded from {self.config_file_path}")
            print(f"Backup folder set to {self.backup_folder}")
            print(f"Keep backup: {self.keep_backup}")
            print(f"Keep encrypted backup: {self.keep_enc_backup}")
            print(f"Directories to backup: {self.dirs_to_backup}")
            print(f"Ignore list: {self.ignore_list}")
        else:
            print(f"Configuration file {self.config_file_path} not found.")

    def configure_directories(self):
        """Interactive method to add directories to backup and ignore lists."""
        print("=== Configure Directories to Backup ===")
        while True:
            print("\nCurrent directories to backup:")
            for idx, directory in enumerate(self.dirs_to_backup, start=1):
                print(f"{idx}. {directory}")
            print("\nOptions:")
            print("1. Add directories (separate multiple entries with commas)")
            print("2. Remove a directory")
            print("3. View ignore list")
            print("4. Modify ignore list")
            print("5. Finish and save")

            choice = input("Choose an option (1-5): ").strip()
            if choice == "1":
                dirs_input = input(
                    "Enter directories to add (separate multiple entries with commas): "
                ).strip()
                new_dirs = [d.strip() for d in dirs_input.split(",") if d.strip()]
                # Avoid duplicates and invalid entries
                added_dirs = [d for d in new_dirs if d not in self.dirs_to_backup]
                self.dirs_to_backup.extend(added_dirs)
                print(f"Added directories: {', '.join(added_dirs)}")
            elif choice == "2":
                print("Select a directory to remove:")
                for idx, directory in enumerate(self.dirs_to_backup, start=1):
                    print(f"{idx}. {directory}")
                try:
                    idx_to_remove = int(input("Enter the number to remove: ").strip())
                    if 0 < idx_to_remove <= len(self.dirs_to_backup):
                        removed_dir = self.dirs_to_backup.pop(idx_to_remove - 1)
                        print(f"Removed: {removed_dir}")
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
            elif choice == "3":
                print("Current ignore list:")
                for idx, path in enumerate(self.ignore_list, start=1):
                    print(f"{idx}. {path}")
            elif choice == "4":
                self.modify_ignore_list()
            elif choice == "5":
                self.save_credentials()
                print("Configuration saved.")
                break
            else:
                print("Invalid choice. Please try again.")

    def modify_ignore_list(self):
        """Interactive method to add or remove paths from the ignore list."""
        print("=== Modify Ignore List ===")
        while True:
            print("\nCurrent ignore list:")
            for idx, path in enumerate(self.ignore_list, start=1):
                print(f"{idx}. {path}")

            print("\nOptions:")
            print("1. Add ignore paths (separate multiple entries with commas)")
            print("2. Remove an ignore path")
            print("3. Finish and save")

            choice = input("Choose an option (1-3): ").strip()
            if choice == "1":
                ignore_input = input(
                    "Enter paths to ignore (separate multiple entries with commas): "
                ).strip()
                new_ignores = [p.strip() for p in ignore_input.split(",") if p.strip()]
                # Avoid duplicates and invalid entries
                added_ignores = [p for p in new_ignores if p not in self.ignore_list]
                self.ignore_list.extend(added_ignores)
                print(f"Added ignore paths: {', '.join(added_ignores)}")
            elif choice == "2":
                print("Select an ignore path to remove:")
                for idx, path in enumerate(self.ignore_list, start=1):
                    print(f"{idx}. {path}")
                try:
                    idx_to_remove = int(input("Enter the number to remove: ").strip())
                    if 0 < idx_to_remove <= len(self.ignore_list):
                        removed_path = self.ignore_list.pop(idx_to_remove - 1)
                        print(f"Removed from ignore list: {removed_path}")
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
            elif choice == "3":
                self.save_credentials()
                print("Ignore list updated and saved.")
                break
            else:
                print("Invalid choice. Please try again.")
