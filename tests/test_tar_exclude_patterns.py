# ruff: noqa: SLF001
"""Comprehensive tests for tar exclude patterns functionality.

This module tests that ignore patterns are properly applied during backup
operations, ensuring files and directories matching ignore patterns are
excluded from both size calculation and tar archive creation.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autotarcompress.commands.backup import BackupCommand
from autotarcompress.config import BackupConfig
from autotarcompress.utils.size_calculator import SizeCalculator


class TestIgnorePatternMatching:
    """Test ignore pattern matching with size calculator."""

    @pytest.fixture
    def ignore_list(self) -> list[str]:
        """Common ignore list matching user's configuration."""
        return [
            "~/Documents/global-repos",
            "~/Documents/backup-for-cloud",
            ".stversions",
            "node_modules",
            ".venv",
            "__pycache__",
            ".ruff_cache",
            ".mypy_cache",
            ".pytest_cache",
            "*.egg-info",
            "*target",
            "lock",
            "chrome",
            ".bin",
        ]

    @pytest.fixture
    def temp_dir_structure(self, tmp_path: Path) -> Path:
        """Create a temporary directory structure for testing."""
        # Create directory structure with ignored and non-ignored paths
        (tmp_path / "project1" / "node_modules" / "package1").mkdir(
            parents=True
        )
        (tmp_path / "project1" / "src").mkdir(parents=True)
        (tmp_path / "project2" / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / "project2" / "tests").mkdir(parents=True)
        (tmp_path / "project3" / "__pycache__").mkdir(parents=True)
        (tmp_path / ".stversions" / "old_files").mkdir(parents=True)
        (tmp_path / "rust_project" / "target" / "debug").mkdir(parents=True)
        (tmp_path / "rust_project" / "src").mkdir(parents=True)
        (tmp_path / "python_project" / "my_package.egg-info").mkdir(
            parents=True
        )
        (tmp_path / ".ruff_cache" / "cache").mkdir(parents=True)
        (tmp_path / ".mypy_cache" / "cache").mkdir(parents=True)
        (tmp_path / ".pytest_cache" / "cache").mkdir(parents=True)
        (tmp_path / "chrome").mkdir(parents=True)
        (tmp_path / ".bin").mkdir(parents=True)

        # Create files to track size
        (tmp_path / "project1" / "src" / "main.py").write_text("x" * 1000)
        (
            tmp_path / "project1" / "node_modules" / "package1" / "index.js"
        ).write_text("x" * 5000)
        (tmp_path / "project2" / "tests" / "test.py").write_text("x" * 800)
        (tmp_path / "project2" / ".venv" / "lib" / "module.py").write_text(
            "x" * 3000
        )
        (
            tmp_path / "project3" / "__pycache__" / "main.cpython-312.pyc"
        ).write_text("x" * 2000)
        (tmp_path / ".stversions" / "old_files" / "data.txt").write_text(
            "x" * 10000
        )
        (tmp_path / "rust_project" / "target" / "debug" / "binary").write_text(
            "x" * 20000
        )
        (tmp_path / "rust_project" / "src" / "main.rs").write_text("x" * 500)
        (
            tmp_path / "python_project" / "my_package.egg-info" / "PKG-INFO"
        ).write_text("x" * 1500)
        (tmp_path / ".ruff_cache" / "cache" / "data").write_text("x" * 4000)
        (tmp_path / ".mypy_cache" / "cache" / "data").write_text("x" * 4500)
        (tmp_path / ".pytest_cache" / "cache" / "data").write_text("x" * 3500)
        (tmp_path / "chrome" / "data").write_text("x" * 6000)
        (tmp_path / ".bin" / "binary").write_text("x" * 2500)

        return tmp_path

    def test_pattern_matching_node_modules(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test node_modules pattern excludes directories correctly."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        total_size = calculator.calculate_total_size()

        # Only non-ignored files: main.py(1000) + test.py(800) + main.rs(500)
        expected_files_size = 2300
        assert total_size == expected_files_size

    def test_pattern_matching_pycache(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test __pycache__ pattern excludes directories."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        pycache_path = temp_dir_structure / "project3" / "__pycache__"
        assert calculator._should_ignore(pycache_path) is True

    def test_pattern_matching_venv(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test .venv pattern excludes directories."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        venv_path = temp_dir_structure / "project2" / ".venv"
        assert calculator._should_ignore(venv_path) is True

    def test_pattern_matching_egg_info(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test *.egg-info pattern excludes directories."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        egg_info_path = (
            temp_dir_structure / "python_project" / "my_package.egg-info"
        )
        assert calculator._should_ignore(egg_info_path) is True

    def test_pattern_matching_target(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test *target pattern excludes target directories."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        target_path = temp_dir_structure / "rust_project" / "target"
        assert calculator._should_ignore(target_path) is True

    def test_pattern_matching_cache_dirs(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test cache directory patterns are excluded."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        ruff_cache = temp_dir_structure / ".ruff_cache"
        mypy_cache = temp_dir_structure / ".mypy_cache"
        pytest_cache = temp_dir_structure / ".pytest_cache"

        assert calculator._should_ignore(ruff_cache) is True
        assert calculator._should_ignore(mypy_cache) is True
        assert calculator._should_ignore(pytest_cache) is True

    def test_pattern_matching_stversions(
        self, temp_dir_structure: Path, ignore_list: list[str]
    ) -> None:
        """Test .stversions pattern excludes directories."""
        calculator = SizeCalculator([str(temp_dir_structure)], ignore_list)
        stversions_path = temp_dir_structure / ".stversions"
        assert calculator._should_ignore(stversions_path) is True

    def test_absolute_path_ignores(self) -> None:
        """Test absolute paths in ignore list work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            global_repos = tmp_path / "global-repos"
            global_repos.mkdir()
            (global_repos / "file.txt").write_text("x" * 1000)

            backup_cloud = tmp_path / "backup-for-cloud"
            backup_cloud.mkdir()
            (backup_cloud / "data.txt").write_text("x" * 2000)

            normal_dir = tmp_path / "normal"
            normal_dir.mkdir()
            (normal_dir / "file.txt").write_text("x" * 500)

            ignore_list = [str(global_repos), str(backup_cloud)]
            calculator = SizeCalculator([str(tmp_path)], ignore_list)
            total_size = calculator.calculate_total_size()

            assert total_size == 500


class TestBackupCommandIgnorePatterns:
    """Test BackupCommand properly passes ignore patterns to tar."""

    @pytest.fixture
    def backup_config(self, tmp_path: Path) -> BackupConfig:
        """Create BackupConfig with common ignore patterns."""
        config = BackupConfig()
        config.backup_folder = str(tmp_path / "backups")
        config.config_dir = str(tmp_path / "config")
        config.dirs_to_backup = [str(tmp_path / "source")]
        config.ignore_list = [
            ".stversions",
            "node_modules",
            ".venv",
            "__pycache__",
            ".ruff_cache",
            ".mypy_cache",
            ".pytest_cache",
            "*.egg-info",
            "*target",
            "lock",
            "chrome",
            ".bin",
        ]

        Path(config.backup_folder).mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        (tmp_path / "source").mkdir(parents=True, exist_ok=True)

        return config

    def test_tar_command_includes_exclude_flags(
        self, backup_config: BackupConfig
    ) -> None:
        """Test _should_exclude includes patterns correctly."""
        command = BackupCommand(backup_config)

        # Test that patterns are properly handled
        for pattern in backup_config.ignore_list:
            # Test directory name matching
            if not pattern.startswith(("*", "/")):
                test_path = Path(f"/some/path/{pattern}/file.txt")
                assert command._should_exclude(test_path) is True

    def test_should_exclude_glob_patterns(
        self, backup_config: BackupConfig
    ) -> None:
        """Test _should_exclude handles glob patterns."""
        command = BackupCommand(backup_config)

        # Test glob pattern matching
        assert command._should_exclude(Path("/path/package.egg-info"))
        assert command._should_exclude(Path("/path/mytarget"))

    def test_should_exclude_structure(
        self, backup_config: BackupConfig
    ) -> None:
        """Test _should_exclude method handles different pattern types."""
        command = BackupCommand(backup_config)

        # Test directory names
        assert command._should_exclude(Path("/path/node_modules/file.txt"))
        assert command._should_exclude(Path("/path/.venv/file.txt"))
        assert command._should_exclude(Path("/path/__pycache__/file.pyc"))


class TestIntegrationBackupWithIgnores:
    """Integration tests for backup command with ignore patterns."""

    @pytest.fixture
    def integration_setup(
        self, tmp_path: Path
    ) -> tuple[Path, Path, BackupConfig]:
        """Set up realistic directory structure."""
        source_dir = tmp_path / "source"
        backup_dir = tmp_path / "backups"

        # Create realistic project structure
        (source_dir / "project1" / "node_modules" / "lodash").mkdir(
            parents=True
        )
        (source_dir / "project1" / "src").mkdir(parents=True)
        (source_dir / "project2" / ".venv" / "lib" / "python3.12").mkdir(
            parents=True
        )
        (source_dir / "project2" / "app").mkdir(parents=True)
        (source_dir / "project3" / "__pycache__").mkdir(parents=True)
        (source_dir / ".stversions").mkdir(parents=True)

        # Create files
        (source_dir / "project1" / "src" / "index.js").write_text(
            "// Main app\n" * 100
        )
        (
            source_dir / "project1" / "node_modules" / "lodash" / "index.js"
        ).write_text("// Library\n" * 1000)
        (source_dir / "project2" / "app" / "main.py").write_text(
            "# Main app\n" * 100
        )
        (
            source_dir
            / "project2"
            / ".venv"
            / "lib"
            / "python3.12"
            / "site.py"
        ).write_text("# Venv\n" * 500)
        (source_dir / "project3" / "script.py").write_text("# Script\n" * 50)
        (
            source_dir / "project3" / "__pycache__" / "script.cpython-312.pyc"
        ).write_text("binary" * 200)
        (source_dir / ".stversions" / "old_version.txt").write_text(
            "old data\n" * 500
        )

        backup_dir.mkdir(parents=True)

        config = BackupConfig()
        config.backup_folder = str(backup_dir)
        config.dirs_to_backup = [str(source_dir)]
        config.ignore_list = [
            ".stversions",
            "node_modules",
            ".venv",
            "__pycache__",
        ]

        return source_dir, backup_dir, config

    def test_backup_excludes_ignored_directories(
        self, integration_setup: tuple[Path, Path, BackupConfig]
    ) -> None:
        """Test backup excludes ignored directories."""
        source_dir, _backup_dir, config = integration_setup

        command = BackupCommand(config)

        expected_files = [
            source_dir / "project1" / "src" / "index.js",
            source_dir / "project2" / "app" / "main.py",
            source_dir / "project3" / "script.py",
        ]
        expected_size = sum(f.stat().st_size for f in expected_files)

        calculated_size = command._calculate_total_size()

        assert calculated_size == expected_size

    @patch("tarfile.open")
    @patch("pathlib.Path.exists")
    @patch("autotarcompress.commands.backup.validate_and_expand_paths")
    def test_full_backup_execution_with_ignores(
        self,
        mock_validate: Mock,
        mock_exists: Mock,
        mock_tarfile: Mock,
        integration_setup: tuple[Path, Path, BackupConfig],
    ) -> None:
        """Integration test: full backup with ignore patterns."""
        source_dir, _backup_dir, config = integration_setup

        mock_validate.return_value = (config.dirs_to_backup, [])
        mock_exists.return_value = False

        # Mock tarfile context manager
        mock_tar = Mock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        command = BackupCommand(config)

        # Mock _save_backup_info to prevent writing metadata with temp paths
        with patch.object(command, "_save_backup_info"):
            result = command.execute()

        assert result is True
        assert mock_tarfile.called

        # Verify tarfile.open was called with zst compression
        call_args = mock_tarfile.call_args
        assert "w:zst" in call_args[0]  # Check for zst compression mode

    def test_size_calculator_respects_nested_ignores(
        self, tmp_path: Path
    ) -> None:
        """Test deeply nested ignored dirs are excluded."""
        deep_path = tmp_path / "a" / "b" / "c" / "node_modules" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "file.js").write_text("x" * 5000)

        normal_path = tmp_path / "a" / "b" / "c" / "src"
        normal_path.mkdir(parents=True)
        (normal_path / "main.js").write_text("x" * 1000)

        calculator = SizeCalculator([str(tmp_path)], ["node_modules"])
        total_size = calculator.calculate_total_size()

        assert total_size == 1000

    def test_multiple_patterns_same_directory(self, tmp_path: Path) -> None:
        """Test directory matching multiple patterns is excluded."""
        multi_match = tmp_path / "project" / "__pycache__"
        multi_match.mkdir(parents=True)
        (multi_match / "cache.pyc").write_text("x" * 2000)

        normal = tmp_path / "project" / "src"
        normal.mkdir(parents=True)
        (normal / "main.py").write_text("x" * 500)

        ignore_list = ["__pycache__", "*.pyc", "*cache*"]
        calculator = SizeCalculator([str(tmp_path)], ignore_list)
        total_size = calculator.calculate_total_size()

        assert total_size == 500


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_ignore_list(self, tmp_path: Path) -> None:
        """Test backup works with empty ignore list."""
        (tmp_path / "file.txt").write_text("x" * 1000)
        calculator = SizeCalculator([str(tmp_path)], [])
        total_size = calculator.calculate_total_size()
        assert total_size == 1000

    def test_symlink_in_ignored_directory(self, tmp_path: Path) -> None:
        """Test symlinks in ignored dirs don't cause issues."""
        ignored = tmp_path / "node_modules"
        ignored.mkdir()

        target = tmp_path / "target.txt"
        target.write_text("x" * 1000)

        link = ignored / "link.txt"
        link.symlink_to(target)

        calculator = SizeCalculator([str(tmp_path)], ["node_modules"])
        total_size = calculator.calculate_total_size()

        assert total_size == 1000
