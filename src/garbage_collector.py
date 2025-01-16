import os
import datetime
import re
from dataclasses import dataclass, field
from .config import Config


@dataclass
class GarbageCollector:
    config: Config

    def delete_old_backups(self):
        """Delete old backup files if there are more than 'keep_backup' files"""
        # List all backup files in the backup folder
        backup_files = [
            f
            for f in os.listdir(os.path.expanduser(self.config.backup_folder))
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

        # Delete old backups if there are more than 'keep_backup'
        while len(xz_files) > self.config.keep_backup:
            old_backup = xz_files.pop(0)
            old_backup_path = os.path.join(self.config.backup_folder, old_backup)
            print(f"Attempting to delete: {old_backup_path}")
            try:
                os.remove(old_backup_path)
                deleted_files.add(old_backup)
                print(f"Deleted old backup: {old_backup}")
            except Exception as e:
                print(f"Failed to delete {old_backup_path}: {e}")

        # Delete old .enc files if there are more than 'keep_enc_backup'
        while len(enc_files) > self.config.keep_enc_backup:
            old_enc_backup = enc_files.pop(0)
            old_enc_backup_path = os.path.join(
                self.config.backup_folder, old_enc_backup
            )
            print(f"Attempting to delete: {old_enc_backup_path}")
            try:
                os.remove(old_enc_backup_path)
                deleted_files.add(old_enc_backup)
                print(f"Deleted old encrypted backup: {old_enc_backup}")
            except Exception as e:
                print(f"Failed to delete {old_enc_backup_path}: {e}")

        print("Old backup deletion process completed.")
