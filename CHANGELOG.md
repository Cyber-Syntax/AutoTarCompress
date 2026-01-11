# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0-alpha] - 2026-01-10

### BREAKING CHANGES

- **Metadata Schema Update:** Upgraded metadata.json from v1.0 to v2.0 to support integrity verification hashes. Backward compatible - existing v1.0 metadata will be migrated automatically.
- **Encryption Migration:** Migrated from OpenSSL subprocess calls to the `cryptography` library with AES-256-GCM authenticated encryption. This is a breaking change - **old .enc files encrypted with OpenSSL will not be decryptable** with the new version. Users should decrypt any existing encrypted backups before upgrading or keep the old version to decrypt legacy files.

### Added

- **SHA256 Integrity Verification:** Added comprehensive file integrity verification system
    - Calculate and store SHA256 hash of backup archives (.tar.zst)
    - Calculate and store SHA256 hash of encrypted files (.enc)
    - Calculate and store SHA256 hash of decrypted files
    - Verify decrypted file integrity against original backup archive hash
    - All hashes stored in metadata.json v2.0 with appropriate naming
    - Added 28 new tests for hash utilities and metadata v2.0
- Pure Python encryption using the `cryptography` library - no more external OpenSSL binary dependency
- AES-256-GCM authenticated encryption provides both confidentiality and integrity verification
- PBKDF2-HMAC-SHA256 key derivation with 600,000 iterations (OWASP recommended)
- Built-in tamper detection - decryption automatically fails if encrypted file has been modified
- Improved error handling with Python exceptions instead of subprocess stderr parsing
- Added comprehensive encryption/decryption tests including tamper detection and round-trip validation
- Implemented progress bar for extraction process using SimpleProgressBar, calculating total archive size for accurate progress updates
- Migrated backup to tarfile library with zstd compression and built-in progress bar, supporting both .tar.zst and .tar.xz formats
- Added global --version option and improved main entry point for consistent package import context

### Changed

- Updated BackupMetadata dataclass to version 2.0 with file_hashes field
- BackupManager now calculates SHA256 hash after backup creation and stores in metadata
- EncryptManager calculates SHA256 hash after encryption and stores in metadata
- DecryptManager calculates SHA256 hash after decryption and verifies against backup hash
- Encryption file format changed from base64-encoded OpenSSL output to binary format: `[salt(16)][nonce(12)][ciphertext][tag(16)]`
- Removed hash embedding - GCM mode provides built-in authentication via authentication tag
- Simplified encryption/decryption managers - removed subprocess complexity
- Enhanced module structure by adding runner.py, removing deprecated files, and consolidating functionality
- Updated documentation including AGENTS.md guidelines, README revisions, and added exclude_patterns.md guide
- Replaced print statements with logging across modules for better traceability
- Changed backup info file path to .config directory and renamed to metadata.json
- Improved path handling in backup commands with user path expansion
- Updated logging path to align with XDG config standards
- Simplified zsh completion installation for better portability
- Added installation options for uv tool including development mode and legacy removal

### Removed

- Removed old `save_backup_info()` method in favor of `save_backup_metadata_with_hash()`
- Removed OpenSSL system dependency (previously required `openssl` command)
- Removed `_sanitize_logs()` method (no longer needed without subprocess)
- Removed `_verify_integrity_mandatory()` method (GCM provides automatic integrity verification)

### Fixed

- Fixed ignore pattern matching to properly handle absolute paths and patterns like node_modules, **pycache**, etc.

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
