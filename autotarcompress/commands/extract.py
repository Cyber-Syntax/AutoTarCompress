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
    """Command to extract tar.xz backup archives securely."""

    def __init__(self, config: BackupConfig, file_path: str) -> None:
        """Initialize ExtractCommand.

        Args:
            config (BackupConfig): Backup configuration object.
            file_path (str): Path to the archive to extract.

        """
        self.config: BackupConfig = config
        self.file_path: str = file_path
        self.logger: logging.Logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Extract the specified archive to a directory.

        Returns:
            bool: True if extraction succeeded, False otherwise.

        """
        file_path: Path = Path(self.file_path)
        extract_dir: Path = Path(f"{file_path.with_suffix('')}-extracted")
        extract_dir.mkdir(exist_ok=True)
        try:
            with tarfile.open(self.file_path, "r:xz") as tar:
                # Prevent path traversal attacks by checking extraction target
                for member in tar.getmembers():
                    target_path = extract_dir / member.name
                    if not str(target_path.absolute()).startswith(str(extract_dir.absolute())):
                        self.logger.error("Attempted path traversal: %s", member.name)
                        return False
                tar.extractall(path=extract_dir)
            self.logger.info("Successfully extracted to %s", extract_dir)
            return True
        except tarfile.TarError as e:
            self.logger.error("Extraction failed: %s", e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during extraction: %s", e)
            return False
