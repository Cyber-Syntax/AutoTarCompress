"""Extract command implementation for backup archives.

This module contains the ExtractCommand class that handles the extraction
of compressed backup archives.
"""

import logging
import tarfile
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig


class ExtractCommand(Command):
    """Concrete command to perform extraction of tar.xz archives"""

    def __init__(self, config: BackupConfig, file_path: str):
        self.config = config
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Extract the specified archive to a directory"""
        file_path = Path(self.file_path)
        extract_dir = Path(f"{file_path.with_suffix('')}-extracted")
        extract_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(self.file_path, "r:xz") as tar:
                # Ensure we're not extracting files outside of the target directory
                for member in tar.getmembers():
                    target_path = extract_dir / member.name
                    if not str(target_path.absolute()).startswith(str(extract_dir.absolute())):
                        self.logger.error(f"Attempted path traversal: {member.name}")
                        return False

                # Safe to extract
                tar.extractall(path=extract_dir)

            self.logger.info(f"Successfully extracted to {extract_dir}")
            return True
        except tarfile.TarError as e:
            self.logger.error(f"Extraction failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during extraction: {e}")
            return False
