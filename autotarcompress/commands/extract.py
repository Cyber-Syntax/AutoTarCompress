"""Extract command implementation for backup archives.

This module contains the ExtractCommand class that handles the extraction
of compressed backup archives.
"""

import logging
import shlex
import subprocess
import tarfile
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.utils.utils import is_pv_available


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

        # Use pv for progress if available
        if is_pv_available() and file_path.suffix == ".xz":
            return self._extract_with_pv(file_path, extract_dir)

        return self._extract_without_pv(file_path, extract_dir)

    def _extract_with_pv(self, file_path: Path, extract_dir: Path) -> bool:
        """Extract archive using pv to show progress.

        Args:
            file_path (Path): Path to the archive file.
            extract_dir (Path): Directory to extract to.

        Returns:
            bool: True if extraction succeeded, False otherwise.

        """
        try:
            file_size = file_path.stat().st_size
            cmd = (
                f"pv -s {file_size} {shlex.quote(str(file_path))} | "
                f"tar -xJ -C {shlex.quote(str(extract_dir))}"
            )
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Successfully extracted to %s", extract_dir)
            return True
        except subprocess.CalledProcessError:
            self.logger.exception("Extraction with pv failed")
            return False
        except (OSError, PermissionError):
            self.logger.exception("Error during extraction")
            return False

    def _extract_without_pv(self, file_path: Path, extract_dir: Path) -> bool:
        """Extract archive without pv (fallback method).

        Args:
            file_path (Path): Path to the archive file.
            extract_dir (Path): Directory to extract to.

        Returns:
            bool: True if extraction succeeded, False otherwise.

        """
        try:
            with tarfile.open(file_path, "r:xz") as tar:
                # Prevent path traversal attacks by checking extraction target
                for member in tar.getmembers():
                    target_path = extract_dir / member.name
                    if not str(target_path.absolute()).startswith(
                        str(extract_dir.absolute())
                    ):
                        self.logger.error(
                            "Attempted path traversal: %s", member.name
                        )
                        return False
                tar.extractall(path=extract_dir)
            self.logger.info("Successfully extracted to %s", extract_dir)
            return True
        except tarfile.TarError:
            self.logger.exception("Extraction failed")
            return False
        except (OSError, PermissionError):
            self.logger.exception("Unexpected error during extraction")
            return False
