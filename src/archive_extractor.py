import os
import sys
import tarfile
from typing import List, Callable, Optional
from .config import Config
from dataclasses import dataclass
import logging


@dataclass
class ArchiveExtractor:
    config: Config

    def list_backup_files(self, extension: str = ".tar.xz") -> List[str]:
        """List all backup files with the specified extension in the backup folder."""
        backup_folder = os.path.expanduser(self.config.backup_folder)
        files = [f for f in os.listdir(backup_folder) if f.endswith(extension)]
        if not files:
            logging.info("No backup files found.")
        return files

    def select_backup_file(self, files: List[str]) -> str:
        """Prompt the user to select a backup file to extract."""
        if not files:
            raise ValueError("No backup files available to select.")

        print("=====================================")
        print("Choose which backup file to extract:")
        for idx, file in enumerate(files, start=1):
            print(f"{idx}. {file}")

        try:
            choice = int(input("Enter your choice: "))
            if 1 <= choice <= len(files):
                return os.path.join(
                    os.path.expanduser(self.config.backup_folder), files[choice - 1]
                )
            else:
                raise ValueError("Invalid choice. Please select a valid file number.")
        except ValueError as e:
            logging.error(f"Invalid input: {e}")
            raise

    def get_extraction_path(self, file_to_extract: str) -> str:
        """Generate the extraction directory path based on the backup file name."""
        date_str = os.path.basename(file_to_extract).split(".")[0]
        extract_to = os.path.join(self.config.backup_folder, f"{date_str}-extracted")
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)
        return extract_to

    def extract_tar_file(
        self,
        file_to_extract: str,
        extract_to: str,
        filter_function: Optional[Callable[[tarfile.TarInfo], tarfile.TarInfo]] = None,
    ) -> bool:
        """Extract the specified tar file to the target directory."""
        try:
            with tarfile.open(file_to_extract, "r:xz") as tar:
                tar.extractall(path=extract_to, filter=filter_function)
            logging.info(f"Backup extracted to {extract_to}")
            return True
        except (tarfile.TarError, FileNotFoundError, PermissionError) as error:
            logging.error(f"Error extracting backup: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Extraction cancelled")
            raise

    def extract_backup(self) -> bool:
        """Main extraction workflow."""
        files = self.list_backup_files()
        if not files:
            return False

        try:
            file_to_extract = self.select_backup_file(files)
            extract_to = self.get_extraction_path(file_to_extract)
            return self.extract_tar_file(file_to_extract, extract_to)
        except Exception as e:
            logging.error(f"Extraction failed: {e}")
            return False
