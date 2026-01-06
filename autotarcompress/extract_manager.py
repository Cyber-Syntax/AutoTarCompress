"""Extract manager for handling archive extraction operations.

This module contains the ExtractManager class that encapsulates
the core extraction logic extracted from ExtractCommand.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

from autotarcompress.utils.progress_bar import SimpleProgressBar
from autotarcompress.utils.utils import is_pv_available

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class ExtractManager:
    """Manager class for extraction operations.

    Handles the core extraction logic including compression detection,
    tarfile operations, progress tracking, and security checks.
    """

    def __init__(
        self, config: BackupConfig, logger: logging.Logger | None = None
    ) -> None:
        """Initialize ExtractManager.

        Args:
            config: Backup configuration
            logger: Logger instance (optional, creates default if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def execute_extract(self, file_path: str) -> bool:
        """Execute the complete extraction process.

        Args:
            file_path: Path to the archive file to extract

        Returns:
            True if extraction succeeded, False otherwise
        """
        file_path_obj = Path(file_path)
        extract_dir = Path(f"{file_path_obj.with_suffix('')}-extracted")

        # Create extraction directory
        try:
            extract_dir.mkdir(exist_ok=True)
            self.logger.info("Created extraction directory: %s", extract_dir)
        except (OSError, PermissionError):
            self.logger.exception("Failed to create extraction directory")
            return False

        # Determine compression format from file extension
        # Support both .tar.zst (new) and .tar.xz (legacy)
        compression = self._detect_compression(file_path_obj)
        if not compression:
            self.logger.error(
                "Unsupported file format: %s (expected .tar.zst or .tar.xz)",
                file_path_obj.suffix,
            )
            return False

        # Use pv for progress if available (only for xz, tarfile for zst)
        if is_pv_available() and compression == "xz":
            return self._extract_with_pv(file_path_obj, extract_dir)

        return self._extract_without_pv(
            file_path_obj, extract_dir, compression
        )

    def _detect_compression(self, file_path: Path) -> str | None:
        """Detect compression format from file extension.

        Args:
            file_path: Path to the archive file

        Returns:
            Compression format ('xz' or 'zst'), or None if unsupported
        """
        suffix = file_path.suffix.lower()
        if suffix == ".zst":
            return "zst"
        if suffix == ".xz":
            return "xz"
        return None

    def _extract_with_pv(self, file_path: Path, extract_dir: Path) -> bool:
        """Extract archive using pv to show progress.

        Args:
            file_path: Path to the archive file
            extract_dir: Directory to extract to

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            file_size = file_path.stat().st_size
            cmd = (
                f"pv -s {file_size} {shlex.quote(str(file_path))} | "
                f"tar -xJ -C {shlex.quote(str(extract_dir))}"
            )
            subprocess.run(cmd, shell=True, check=True)  # noqa: S602
        except subprocess.CalledProcessError:
            self.logger.exception("Extraction with pv failed")
            return False
        except (OSError, PermissionError):
            self.logger.exception("Error during extraction")
            return False
        else:
            self.logger.info("Successfully extracted to %s", extract_dir)
            return True

    def _extract_without_pv(
        self, file_path: Path, extract_dir: Path, compression: str
    ) -> bool:
        """Extract archive without pv (fallback method).

        Args:
            file_path: Path to the archive file
            extract_dir: Directory to extract to
            compression: Compression format ('xz' or 'zst')

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            with tarfile.open(str(file_path), f"r:{compression}") as tar:  # type: ignore[call-overload]
                # Calculate total size for progress bar
                total_size = sum(member.size for member in tar.getmembers())
                progress = SimpleProgressBar(total_size)

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

                # Extract each member with progress tracking
                for member in tar.getmembers():
                    tar.extract(member, path=extract_dir)
                    progress.update(member.size)

                progress.finish()
                self.logger.info("Successfully extracted to %s", extract_dir)
                return True
        except tarfile.TarError:
            self.logger.exception("Extraction failed")
            return False
        except (OSError, PermissionError):
            self.logger.exception("Unexpected error during extraction")
            return False
