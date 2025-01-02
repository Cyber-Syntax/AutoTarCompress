import os
import json
import datetime
import re
import sys
from dataclasses import dataclass


def ask_and_save_preferences(config_file_path: str):
    """Ask the user for preferences and save them to the config file."""
    try:
        keep_count = int(input("Enter the number of backups to keep: "))
        keep_enc_count = int(input("Enter the number of .enc backups to keep: "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        sys.exit(1)

    config = {"keep_count": keep_count, "keep_enc_count": keep_enc_count}
    with open(config_file_path, "w") as config_file:
        json.dump(config, config_file, indent=4)
    print(f"Updated number of backups to keep to {keep_count}")
    print(f"Updated number of .enc backups to keep to {keep_enc_count}")


@dataclass
class BackupDeletionManager:
    backup_folder: str = os.path.expanduser("~/Documents/backup-for-cloud/")
    config_file_path: str = "config_files/backup_config.json"
    keep_count: int = 3  # Default value
    keep_enc_count: int = 0  # Default value

    def __post_init__(self):
        # Ensure the config_files directory exists
        os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
        self.load_config_or_ask_preferences()

    def load_config_or_ask_preferences(self):
        """Load configuration from the config file or ask for user input if the file doesn't exist."""
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, "r") as config_file:
                    config = json.load(config_file)
                    self.keep_count = config.get("keep_count", 3)
                    self.keep_enc_count = config.get("keep_enc_count", 0)
            except FileNotFoundError:
                self.save_config()  # Save default config if file not found
        else:
            ask_and_save_preferences(self.config_file_path)
            self.load_config()  # Load the newly created config

    def load_config(self):
        """Load configuration from the config file."""
        try:
            with open(self.config_file_path, "r") as config_file:
                config = json.load(config_file)
                self.keep_count = config.get("keep_count", 3)
                self.keep_enc_count = config.get("keep_enc_count", 0)
        except FileNotFoundError:
            self.save_config()  # Save default config if file not found

    def save_config(self):
        """Save the current configuration to the config file."""
        config = {"keep_count": self.keep_count, "keep_enc_count": self.keep_enc_count}
        with open(self.config_file_path, "w") as config_file:
            json.dump(config, config_file, indent=4)

    def delete_old_backups(self):
        """Delete old backup files if there are more than 'keep_count' files"""
        # List all backup files in the backup folder
        backup_files = [
            f
            for f in os.listdir(self.backup_folder)
            if re.match(r"\d{2}-\d{2}-\d{4}\.tar\.xz", f)
            or re.match(r"\d{2}-\d{2}-\d{4}\.tar\.xz\.enc", f)
        ]

        # Sort the backup files by date
        backup_files.sort(
            key=lambda x: datetime.datetime.strptime(x.split(".")[0], "%d-%m-%Y")
        )

        # Separate .xz and .xz.enc files
        xz_files = [f for f in backup_files if f.endswith(".tar.xz")]
        enc_files = [f for f in backup_files if f.endswith(".tar.xz.enc")]

        # Track deleted files to avoid duplicate deletions
        deleted_files = set()

        # Delete old backups if there are more than 'keep_count'
        while len(xz_files) > self.keep_count:
            old_backup = xz_files.pop(0)
            old_backup_path = os.path.join(self.backup_folder, old_backup)
            print(f"Attempting to delete: {old_backup_path}")
            try:
                os.remove(old_backup_path)
                deleted_files.add(old_backup)
                print(f"Deleted old backup: {old_backup}")
            except Exception as e:
                print(f"Failed to delete {old_backup_path}: {e}")

        # Delete old .enc files if there are more than 'keep_enc_count'
        while len(enc_files) > self.keep_enc_count:
            old_enc_backup = enc_files.pop(0)
            old_enc_backup_path = os.path.join(self.backup_folder, old_enc_backup)
            print(f"Attempting to delete: {old_enc_backup_path}")
            try:
                os.remove(old_enc_backup_path)
                deleted_files.add(old_enc_backup)
                print(f"Deleted old encrypted backup: {old_enc_backup}")
            except Exception as e:
                print(f"Failed to delete {old_enc_backup_path}: {e}")
