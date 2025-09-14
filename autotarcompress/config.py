"""Configuration management for backup system.

Handles loading, saving, and validation of backup configuration using INI (.conf) files.
Comments are supported in the config file.
"""

import configparser
import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass
class BackupConfig:
    """Configuration data for backup manager (paths, retention, targets).

    Uses INI (.conf) file for configuration, allowing comments.
    Default values provide practical examples for common backup and ignore
    paths.
    """

    backup_folder: str = "~/Documents/backup-for-cloud/"
    config_dir: str = "~/.config/autotarcompress"
    keep_backup: int = 0
    keep_enc_backup: int = 1
    log_level: str = "INFO"
    # List of directories to include in the backup.
    # These are typically user data, browser profiles, documents, photos,
    # application configs, and dotfiles. Adjust this list to match the
    # important data you want to preserve. Each path is expanded to an
    # absolute path at runtime.
    dirs_to_backup: list[str] = field(
        default_factory=lambda: [
            "~/.zen/qknutvmw.Default Profile/",
            "~/.config/BraveSoftware/Brave-Browser/Default",
            "~/Photos",
            "~/Pictures",
            "~/Documents",
            "~/.config/syncthing",
            "~/.config/my-unicorn/",
            "~/.config/FreeTube",
            "~/dotfiles",
        ]
    )

    # List of directories or patterns to exclude from the backup.
    # These are typically large, redundant, or auto-generated folders
    # such as build artifacts, caches, version control folders, and
    # backup destinations themselves. Adjust this list to avoid backing
    # up unnecessary or volatile data.
    ignore_list: list[str] = field(
        default_factory=lambda: [
            "~/Documents/global-repos",
            "~/Documents/backup-for-cloud",
            "~/Documents/.stversions",
            "node_modules",
            ".venv",
            "__pycache__",
            ".ruff_cache",
            "~/Documents/my-repos/rust-unicorn/target",
            "lock",
            "chrome",
            ".bin",
        ]
    )

    def __post_init__(self) -> None:
        """Expand all configured paths after initialization."""
        self.backup_folder = str(Path(self.backup_folder).expanduser())
        self.ignore_list = [str(Path(p).expanduser()) for p in self.ignore_list]
        self.dirs_to_backup = [str(Path(d).expanduser()) for d in self.dirs_to_backup]
        self.config_dir = str(Path(self.config_dir).expanduser())
        # Validate and normalize log level
        self.log_level = self._validate_log_level(self.log_level)

    def _validate_log_level(self, level: str) -> str:
        """Validate and normalize the log level string.

        Args:
            level (str): The log level string to validate.

        Returns:
            str: A valid log level string (uppercase).

        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level_upper = level.upper()
        if level_upper not in valid_levels:
            logging.warning("Invalid log level '%s', defaulting to INFO", level)
            return "INFO"
        return level_upper

    def get_log_level(self) -> int:
        """Convert the string log level to logging module constant.

        Returns:
            int: The logging level constant.

        """
        return getattr(logging, self.log_level, logging.INFO)

    @property
    def current_date(self) -> str:
        """Return current date as string (dd-mm-YYYY)."""
        return datetime.datetime.now().strftime("%d-%m-%Y")

    @property
    def config_path(self) -> Path:
        """Return the full path to the config file (INI format)."""
        return Path(self.config_dir) / "config.conf"

    @property
    def backup_path(self) -> Path:
        """Return the full path to the backup file."""
        return Path(self.backup_folder) / f"{self.current_date}.tar.xz"

    def save(self) -> None:
        """Save current configuration to the config file in INI format.

        Comments are supported in the config file.
        Lists are saved as INI multi-line values for user-friendly editing.
        Explanatory comments are written to the config file for user guidance.
        """
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        # Write config with inline comments for each setting
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("[DEFAULT]\n")

            # log_level
            f.write("# Logging level for the application.\n")
            f.write("#   Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL\n")
            f.write("#   DEBUG: Detailed information for debugging purposes\n")
            f.write("#   INFO: General information about application flow\n")
            f.write("#   WARNING: Warning messages for unusual conditions\n")
            f.write("#   ERROR: Error messages for failure conditions\n")
            f.write("#   CRITICAL: Critical error messages\n")
            f.write(f"log_level = {self.log_level}\n\n")

            # backup_folder
            f.write("# Directory where backup archives will be stored.\n")
            f.write("#   Default: ~/Documents/backup-for-cloud/\n")
            f.write(f"backup_folder = {self.backup_folder}\n\n")

            # config_dir
            f.write("# Directory where this config file is saved.\n")
            f.write("#   Default: ~/.config/autotarcompress\n")
            f.write(f"config_dir = {self.config_dir}\n\n")

            # keep_backup
            f.write("# Number of unencrypted backups to keep (0 = unlimited).\n")
            f.write("#   Useful for retention policy and disk space management.\n")
            f.write(f"keep_backup = {self.keep_backup}\n\n")

            # keep_enc_backup
            f.write("# Number of encrypted backups to keep (0 = unlimited).\n")
            f.write("#   Applies to encrypted backup retention.\n")
            f.write(f"keep_enc_backup = {self.keep_enc_backup}\n\n")

            # dirs_to_backup
            f.write("# List of directories to include in the backup.\n")
            f.write("#   Typically user data, browser profiles, documents, photos,\n")
            f.write("#   application configs, and dotfiles. Adjust this list to match\n")
            f.write("#   the important data you want to preserve. Each path is expanded\n")
            f.write("#   to an absolute path at runtime.\n")
            f.write("dirs_to_backup =\n")
            for dir_path in self.dirs_to_backup:
                f.write(f"\t{dir_path}\n")
            f.write("\n")

            # ignore_list
            f.write("# List of directories or patterns to exclude from the backup.\n")
            f.write("#   Typically large, redundant, or auto-generated folders such as build\n")
            f.write("#   artifacts, caches, version control folders, and backup destinations\n")
            f.write("#   themselves. Adjust this list to avoid backing up unnecessary or\n")
            f.write("#   volatile data.\n")
            f.write("ignore_list =\n")
            for ignore_path in self.ignore_list:
                f.write(f"\t{ignore_path}\n")

        logging.info("Configuration saved to %s", self.config_path)

    @classmethod
    def load(cls) -> "BackupConfig":
        """Load config from INI file or create with defaults if missing.

        Lists are loaded as INI multi-line values for user-friendly editing.
        """
        default_config = cls()
        config_path = default_config.config_path

        if config_path.exists():
            config = configparser.ConfigParser()
            try:
                config.read(config_path, encoding="utf-8")
                section = config["DEFAULT"]
                # Parse fields
                backup_folder = section.get("backup_folder", default_config.backup_folder)
                config_dir = section.get("config_dir", default_config.config_dir)
                keep_backup = int(section.get("keep_backup", default_config.keep_backup))
                keep_enc_backup = int(
                    section.get("keep_enc_backup", default_config.keep_enc_backup)
                )
                log_level = section.get("log_level", default_config.log_level).upper()
                # Parse multi-line lists

                def parse_multiline_list(val: str) -> list[str]:
                    if not val:
                        return []
                    return [line.strip() for line in val.strip().splitlines() if line.strip()]

                dirs_to_backup = parse_multiline_list(section.get("dirs_to_backup", ""))
                ignore_list = parse_multiline_list(section.get("ignore_list", ""))

                return cls(
                    backup_folder=backup_folder,
                    config_dir=config_dir,
                    keep_backup=keep_backup,
                    keep_enc_backup=keep_enc_backup,
                    log_level=log_level,
                    dirs_to_backup=dirs_to_backup,
                    ignore_list=ignore_list,
                )
            except Exception as e:
                logging.error("Error reading config file: %s", e)
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
            config = configparser.ConfigParser()
            config.read(config_path, encoding="utf-8")
            section = config["DEFAULT"]
            dirs_to_backup = [
                d.strip() for d in section.get("dirs_to_backup", "").split(",") if d.strip()
            ]
            backup_folder = section.get("backup_folder", default_config.backup_folder)

            if not dirs_to_backup:
                return False, "No backup directories configured"

            backup_folder_path = Path(backup_folder).expanduser()
            if not backup_folder_path.exists():
                try:
                    backup_folder_path.mkdir(parents=True, exist_ok=True)
                except OSError:
                    return (False, f"Cannot create backup folder at {backup_folder_path}")

            return True, "Configuration is valid"

        except Exception as e:
            return False, f"Configuration validation error: {e!s}"
