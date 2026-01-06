# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-01-06

### Added

- Implemented progress bar for extraction process using SimpleProgressBar, calculating total archive size for accurate progress updates
- Migrated backup to tarfile library with zstd compression and built-in progress bar, supporting both .tar.zst and .tar.xz formats
- Added global --version option and improved main entry point for consistent package import context

### Changed

- Enhanced module structure by adding runner.py, removing deprecated files, and consolidating functionality
- Updated documentation including AGENTS.md guidelines, README revisions, and added exclude_patterns.md guide
- Replaced print statements with logging across modules for better traceability
- Changed backup info file path to .config directory and renamed to metadata.json
- Improved path handling in backup commands with user path expansion
- Updated logging path to align with XDG config standards
- Simplified zsh completion installation for better portability
- Added installation options for uv tool including development mode and legacy removal

### Fixed

- Fixed ignore pattern matching to properly handle absolute paths and patterns like node_modules, __pycache__, etc.

## v0.7.1-beta

## v0.7.0-beta

### BREAKING CHANGES

This release introduces a new command-line interface (CLI) for AutoTarCompress, enabling users to perform all operations via terminal commands. The previous interactive menu mode still exists but may be deprecated in future releases. Users are encouraged to transition to the CLI for better automation and scripting capabilities. For detailed usage instructions, please refer to the updated documentation in [docs/wiki.md](docs/wiki.md).

## v0.6.3-beta

## v0.6.2-beta

## v0.6.1-beta

## v0.6.0-beta

### BREAKING CHANGES

- The configuration file format has been changed from JSON to INI. Now located at `~/.config/autotarcompress/config.conf`. Please migrate your existing configuration accordingly.

#### Migration Steps

Script will create a new config file in the new format if it does not exist. Please manually transfer your settings from the old JSON file to the new INI file, following the comments provided in the new config file for guidance.

## v0.5.0-beta

### Changes

This release adds the `info` command to display details about the latest backup, including directories backed up and backup file status.

## v0.4.0-beta

## v0.3.1-beta

### Changes

### BREAKING CHANGES

Current config file location moved to `~/.config/autotarcompress/config.json`. Please review example config file and update it for your needs.

- feat!: Use XDG Base Directory specifications.
- fix: endless backup command issue
- refactor: make class for context manager
- chore: format fix
- chore: pytproject.toml and requirements.txt update
- refactor!: add command design pattern

[Unreleased]: https://github.com/Cyber-Syntax/AutoTarCompress/compare/v0.7.1-beta...HEAD
