"""Logging configuration and setup for AutoTarCompress.

This module provides centralized logging configuration following the Single
Responsibility Principle. It handles file rotation, console output, and
formatting consistently across the application.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_xdg_config_home() -> Path:
    """Return the XDG config home directory path.

    Returns:
        Path: XDG config home directory or fallback to ~/.config

    """
    xdg_config_home: str | None = os.getenv("XDG_CONFIG_HOME")
    if not xdg_config_home or not Path(xdg_config_home).is_absolute():
        return Path.home() / ".config"
    return Path(xdg_config_home)


def setup_application_logging(log_level: int = logging.INFO) -> None:
    """Configure comprehensive logging for the AutoTarCompress application.

    Sets up both file and console logging with appropriate formatters and
    rotation. File logs are stored in XDG-compliant state directory.

    Args:
        log_level (int): The logging level to use. Defaults to INFO.

    """
    # Create log directory
    config_home: Path = get_xdg_config_home()
    log_dir: Path = config_home / "autotarcompress" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure file handler with rotation
    log_file_path: Path = log_dir / "autotarcompress.log"
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3,
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)

    # Configure console handler (errors only)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add our handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    level_name = logging.getLevelName(log_level)
    logger = logging.getLogger(__name__)
    logger.info("Logging configured with %s level", level_name)


def setup_basic_logging() -> None:
    """Configure basic logging for initial application setup.

    Used when config is not yet available or during initial setup phase.

    """
    logging.basicConfig(level=logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name (str): Usually __name__ of the calling module.

    Returns:
        logging.Logger: Configured logger instance.

    """
    return logging.getLogger(name)
