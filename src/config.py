"""Configuration management for backup system.

This module handles loading, saving, and validation of backup configuration.
"""

import datetime
import json
import logging
import os
from dataclasses import dataclass, field
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

    def __post_init__(self):
        """Expand all paths after initialization."""
        self.backup_folder = os.path.expanduser(self.backup_folder)
        self.ignore_list = [os.path.expanduser(p) for p in self.ignore_list]
        self.dirs_to_backup = [os.path.expanduser(d) for d in self.dirs_to_backup]
        self.config_dir = os.path.expanduser(self.config_dir)

    @property
    def current_date(self) -> str:
        """Get current date formatted as string."""
        return datetime.datetime.now().strftime("%d-%m-%Y")

    @property
    def config_path(self) -> str:
        """Get the full path to the config file."""
        return os.path.join(self.config_dir, "config.json")

    @property
    def backup_path(self) -> str:
        """Get the full path to the backup file."""
        return os.path.expanduser(f"{self.backup_folder}/{self.current_date}.tar.xz")

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
        os.makedirs(self.config_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=4)

        logging.info(f"Configuration saved to {self.config_path}")

    @classmethod
    def load(cls) -> "BackupConfig":
        """Load configuration from file or create with defaults if not exists."""
        default_config = cls()
        config_path = default_config.config_path

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
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
        if not os.path.exists(config_path):
            return False, f"Configuration file not found at {config_path}"

        try:
            # Try to load the configuration
            with open(config_path, "r") as f:
                config_data = json.load(f)

            config = cls(**config_data)

            # Validate essential configuration
            if not config.dirs_to_backup:
                return False, "No backup directories configured"

            # Check if backup folder exists or can be created
            backup_folder = os.path.expanduser(config.backup_folder)
            if not os.path.exists(backup_folder):
                try:
                    os.makedirs(backup_folder, exist_ok=True)
                except OSError:
                    return False, f"Cannot create backup folder at {backup_folder}"

            # All checks passed
            return True, "Configuration is valid"

        except json.JSONDecodeError:
            return False, "Configuration file is corrupt or invalid JSON"
        except KeyError as e:
            return False, f"Missing required configuration key: {e}"
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
