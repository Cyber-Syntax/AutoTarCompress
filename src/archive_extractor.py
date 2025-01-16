import os
import logging
import tarfile
from .config import Config
from .utils import select_file
from dataclasses import dataclass
from typing import List, Callable, Optional


@dataclass
class ArchiveExtractor:
    config: Config

    def get_extraction_path(self, file_to_extract: str) -> str:
        """Generate the extraction directory path based on the backup file name."""
        date_str = os.path.basename(file_to_extract).split(".")[0]
        extract_to = os.path.join(
            os.path.expanduser(self.config.backup_folder), f"{date_str}-extracted"
        )
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
        try:
            file_to_extract = select_file(
                extension=".tar.xz"
            )  # Call to the global select_backup_file function
            extract_to = self.get_extraction_path(file_to_extract)
            return self.extract_tar_file(file_to_extract, extract_to)
        except Exception as e:
            logging.error(f"Extraction failed: {e}")
            return False
