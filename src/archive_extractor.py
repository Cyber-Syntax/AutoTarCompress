import os
import sys
import tarfile
from typing import List
from dataclasses import dataclass, field
from .config import Config


@dataclass
class ArchiveExtractor:
    config: Config

    def extract_backup(self, file_to_extract: str) -> bool:
        """Extract the backup file to the specified directory"""
        date_str = os.path.basename(file_to_extract).split(".")[0]
        extract_to = os.path.join(self.config.backup_folder, f"{date_str}-extracted")
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)

        def filter_function(tarinfo, path):
            # Customize the tarinfo object here if needed
            return tarinfo

        try:
            with tarfile.open(file_to_extract, "r:xz") as tar:
                tar.extractall(path=extract_to, filter=filter_function)
            print(f"Backup extracted to {extract_to}")
            return True
        except (tarfile.TarError, FileNotFoundError, PermissionError) as error:
            print(f"Error extracting backup: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Extraction cancelled")
            sys.exit(0)
