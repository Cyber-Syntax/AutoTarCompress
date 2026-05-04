"""Tests for InfoManager — info display operations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from autotarcompress.info_manager import InfoManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_METADATA: dict = {
    "last_backup_time": "2026-05-04T08:38:13.156278+00:00",
    "last_backup_file": "/home/developer/Documents/backup-for-cloud/04-05-2026.tar.zst",
    "backup_count": 3,
    "metadata_version": "2.0",
    "file_hashes": {
        "06-01-2026.tar.zst": "a856d73a1e3484ebb2b81cc8f8466f6a37d1296b597e7abeeab6073de1bad2bd",
        "06-01-2026.tar.zst.enc": "82ea67030d886eb7321d6008acc9cc3c77b3bd33cb9e6330cba49c3cebe8139e",
        "06-01-2026.tar.zst-decrypted": "a856d73a1e3484ebb2b81cc8f8466f6a37d1296b597e7abeeab6073de1bad2bd",
        "04-05-2026.tar.zst": "5f41f93ab8746a3f02ecd57685c80d5fb0e63eab03c9dd3b8ed4f046a9c8acb3",
        "04-05-2026.tar.zst.enc": "781d842a7e61d7d99895ee716f800ed7c7ca38252b27cd0f46370eeaafcf536e",
        "04-05-2026.tar.zst-decrypted": "5f41f93ab8746a3f02ecd57685c80d5fb0e63eab03c9dd3b8ed4f046a9c8acb3",
    },
}


@pytest.fixture
def mock_config() -> MagicMock:
    cfg = MagicMock()
    cfg.config_dir = "/fake/config"
    return cfg


@pytest.fixture
def mock_logger() -> MagicMock:
    # No spec= so .info/.warning/.exception are MagicMock, not MethodType,
    # letting the type checker resolve .call_args_list / .call_count correctly.
    return MagicMock()


@pytest.fixture
def manager(mock_config: MagicMock, mock_logger: MagicMock) -> InfoManager:
    return InfoManager(config=mock_config, logger=mock_logger)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _patch_metadata(
    manager: InfoManager,
    data: dict | None,
    *,
    exists: bool = True,
    decode_error: bool = False,
    os_error: bool = False,
) -> None:
    """Patch filesystem interactions on the manager's config path."""
    metadata_path = Path(manager.config.config_dir) / "metadata.json"

    with (
        patch.object(Path, "exists", return_value=exists),
        patch.object(
            Path, "expanduser", return_value=Path(manager.config.config_dir)
        ),
    ):
        if decode_error:
            m = mock_open(read_data="not-valid-json{{{")
        elif os_error:
            m = mock_open()
            m.side_effect = OSError("disk error")
        else:
            m = mock_open(
                read_data=json.dumps(data) if data is not None else "{}"
            )

        with patch("builtins.open", m):
            yield  # tests run inside this context


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInfoManagerInit:
    def test_stores_config(self, mock_config: MagicMock) -> None:
        mgr = InfoManager(config=mock_config)
        assert mgr.config is mock_config

    def test_uses_provided_logger(
        self, mock_config: MagicMock, mock_logger: MagicMock
    ) -> None:
        mgr = InfoManager(config=mock_config, logger=mock_logger)
        assert mgr.logger is mock_logger

    def test_creates_default_logger_when_none(
        self, mock_config: MagicMock
    ) -> None:
        mgr = InfoManager(config=mock_config)
        assert isinstance(mgr.logger, logging.Logger)


# ---------------------------------------------------------------------------
# _load_backup_info
# ---------------------------------------------------------------------------


class TestLoadBackupInfo:
    def test_returns_dict_for_valid_metadata(
        self, manager: InfoManager, tmp_path: Path
    ) -> None:
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps(VALID_METADATA), encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        result = manager._load_backup_info()

        assert result == VALID_METADATA

    def test_returns_none_when_file_missing(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        manager.config.config_dir = str(
            tmp_path
        )  # directory exists, file does not

        result = manager._load_backup_info()

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_returns_none_for_invalid_json(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text("not-valid-json{{{", encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        result = manager._load_backup_info()

        assert result is None
        mock_logger.exception.assert_called_once()

    def test_returns_none_for_non_dict_json(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        result = manager._load_backup_info()

        assert result is None
        mock_logger.error.assert_called_once()

    def test_returns_none_on_permission_error(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text("{}", encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        # _load_backup_info uses Path.open(), not builtins.open
        with patch.object(
            Path, "open", side_effect=PermissionError("no access")
        ):
            result = manager._load_backup_info()

        assert result is None
        mock_logger.exception.assert_called_once()

    def test_returns_none_on_os_error(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text("{}", encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        # _load_backup_info uses Path.open(), not builtins.open
        with patch.object(Path, "open", side_effect=OSError("disk error")):
            result = manager._load_backup_info()

        assert result is None
        mock_logger.exception.assert_called_once()

    def test_expands_tilde_in_config_dir(
        self, manager: InfoManager, tmp_path: Path
    ) -> None:
        """expanduser() must be called so ~ in config_dir resolves correctly."""
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps(VALID_METADATA), encoding="utf-8")

        with patch.object(
            Path, "expanduser", return_value=tmp_path
        ) as mock_expand:
            manager._load_backup_info()

        mock_expand.assert_called_once()


# ---------------------------------------------------------------------------
# _display_backup_info
# ---------------------------------------------------------------------------


class TestDisplayBackupInfo:
    def test_logs_all_standard_fields(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        manager._display_backup_info(VALID_METADATA)

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "04-05-2026.tar.zst" in logged_messages
        assert "2026-05-04T08:38:13.156278+00:00" in logged_messages
        assert "3" in logged_messages
        assert "2.0" in logged_messages

    def test_logs_all_file_hashes(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        manager._display_backup_info(VALID_METADATA)

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        for filename, file_hash in VALID_METADATA["file_hashes"].items():
            assert filename in logged_messages
            assert file_hash in logged_messages

    def test_logs_hash_count(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        manager._display_backup_info(VALID_METADATA)

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "6" in logged_messages  # 6 entries in file_hashes

    def test_logs_none_when_no_file_hashes(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        data = {**VALID_METADATA, "file_hashes": {}}
        manager._display_backup_info(data)

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "None" in logged_messages

    def test_handles_missing_optional_fields_gracefully(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        """Fields not present should fall back to 'Unknown' without raising."""
        manager._display_backup_info({})

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert (
            logged_messages.count("Unknown") >= 4
        )  # file, date, count, version

    def test_logs_separator_lines(
        self, manager: InfoManager, mock_logger: MagicMock
    ) -> None:
        manager._display_backup_info(VALID_METADATA)

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "=====" in logged_messages


# ---------------------------------------------------------------------------
# execute_info (integration-style)
# ---------------------------------------------------------------------------


class TestExecuteInfo:
    def test_returns_true_and_displays_info_when_metadata_present(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "metadata.json").write_text(
            json.dumps(VALID_METADATA), encoding="utf-8"
        )
        manager.config.config_dir = str(tmp_path)

        result = manager.execute_info()

        assert result is True
        # _display_backup_info should have been called → many logger.info calls
        assert mock_logger.info.call_count >= 5

    def test_returns_false_when_no_metadata_file(
        self, manager: InfoManager, tmp_path: Path
    ) -> None:
        manager.config.config_dir = str(tmp_path)  # metadata.json absent

        result = manager.execute_info()

        assert result is False

    def test_returns_false_when_last_backup_file_key_missing(
        self, manager: InfoManager, tmp_path: Path
    ) -> None:
        incomplete = {
            k: v for k, v in VALID_METADATA.items() if k != "last_backup_file"
        }
        (tmp_path / "metadata.json").write_text(
            json.dumps(incomplete), encoding="utf-8"
        )
        manager.config.config_dir = str(tmp_path)

        result = manager.execute_info()

        assert result is False

    def test_logs_not_found_message_when_no_backup(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        manager.config.config_dir = str(tmp_path)

        manager.execute_info()

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "No backup information found" in logged_messages

    def test_logs_found_message_when_backup_exists(
        self, manager: InfoManager, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "metadata.json").write_text(
            json.dumps(VALID_METADATA), encoding="utf-8"
        )
        manager.config.config_dir = str(tmp_path)

        manager.execute_info()

        logged_messages = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        assert "Backup information found" in logged_messages

    def test_returns_false_on_corrupted_metadata(
        self, manager: InfoManager, tmp_path: Path
    ) -> None:
        (tmp_path / "metadata.json").write_text("{{broken", encoding="utf-8")
        manager.config.config_dir = str(tmp_path)

        result = manager.execute_info()

        assert result is False
