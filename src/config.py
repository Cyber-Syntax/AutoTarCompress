"""Configuration management for backup system.

This module handles loading, saving, and validation of backup configuration.
"""

import datetime
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class BackupConfig:
    """Configuration data for backup manager.

    This class handles configuration properties for the backup system including
    file paths, retention policies, and backup targets.
    """

    backup_folder: str = "~/Documents/backup-for-cloud/"
    config_dir: str = "~/.config/autotarcompress"
    keep_backup: int = 1
    keep_enc_backup: int = 1
    dirs_to_backup: List[str] = field(default_factory=list)
    ignore_list: List[str] = field(default_factory=list)
    last_backup: Optional[str] = None

    def __post_init__(self) -> None:
        """Expand all paths after initialization."""
        self.backup_folder = str(Path(self.backup_folder).expanduser())
        self.ignore_list = [str(Path(p).expanduser()) for p in self.ignore_list]
        self.dirs_to_backup = [str(Path(d).expanduser()) for d in self.dirs_to_backup]
        self.config_dir = str(Path(self.config_dir).expanduser())

    @property
    def current_date(self) -> str:
        """Get current date formatted as string."""
        return datetime.datetime.now().strftime("%d-%m-%Y")

    @property
    def config_path(self) -> Path:
        """Get the full path to the config file."""
        return Path(self.config_dir) / "config.json"

    @property
    def backup_path(self) -> Path:
        """Get the full path to the backup file."""
        return Path(self.backup_folder) / f"{self.current_date}.tar.xz"

    def save(self) -> None:
        """Save current configuration to the config file."""
        config_data = {
            "backup_folder": self.backup_folder,
            "config_dir": self.config_dir,
            "keep_backup": self.keep_backup,
            "keep_enc_backup": self.keep_enc_backup,
            "dirs_to_backup": self.dirs_to_backup,
            "ignore_list": self.ignore_list,
            "last_backup": self.last_backup,
        }

        # Ensure the config directory exists
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        logging.info(f"Configuration saved to {self.config_path}")

    @classmethod
    def load(cls) -> "BackupConfig":
        """Load configuration from file or create with defaults if not exists."""
        default_config = cls()
        config_path = default_config.config_path

        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config_data = json.load(f)
                return cls(**config_data)
            except json.JSONDecodeError as e:
                logging.error(f"Error reading config file: {e}")
                logging.warning("Using default configuration")
                return default_config
        return default_config

    @classmethod
    def verify_config(cls) -> Tuple[bool, str]:
        """Verify if the configuration file exists and is properly set up.

        Returns:
            Tuple containing:
            - bool: True if configuration is valid, False otherwise
            - str: Message describing the verification result

        """
        default_config = cls()
        config_path = default_config.config_path

        # Check if config file exists
        if not config_path.exists():
            return False, f"Configuration file not found at {config_path}"

        try:
            # Try to load the configuration
            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)

            config = cls(**config_data)

            # Validate essential configuration
            if not config.dirs_to_backup:
                return False, "No backup directories configured"

            # Check if backup folder exists or can be created
            backup_folder = Path(config.backup_folder)
            if not backup_folder.exists():
                try:
                    backup_folder.mkdir(parents=True, exist_ok=True)
                except OSError:
                    return False, f"Cannot create backup folder at {backup_folder}"

            # All checks passed
            return True, "Configuration is valid"

        except json.JSONDecodeError:
            return False, "Configuration file is corrupt or invalid JSON"
        except KeyError as e:
            return False, f"Missing required configuration key: {e}"
        except Exception as e:
            return False, f"Configuration validation error: {e!s}"
