## AutoTarCompress - Improvement Plan

### 1. Architecture

**1.1 Eliminate the Dual Command + Manager Layer**

Every operation follows a rigid pattern: `Command` -> `Manager` -> actual logic. For example, `BackupCommand.execute()` just calls `self.manager.execute_backup()`. The Command classes in backup.py, extract.py, encrypt.py, and decrypt.py are pure pass-through wrappers that add no value - they just forward to the Manager. The `Command` ABC in command.py defines a single `execute() -> bool` method but provides no shared behavior.

**Recommendation:** Collapse Commands into Managers. The CLI parser in parser.py can directly instantiate and call Manager classes. This removes 7 files and an entire indirection layer. If you want a uniform `execute()` interface, add it as a Protocol or ABC on the Manager classes themselves.

**1.2 Stale Docstrings Referencing OpenSSL**

`EncryptCommand` docstring says *"Using OpenSSL with secure PBKDF2 implementation. fd:0 is used to pass password securely"* and `DecryptCommand` says *"securely decrypt backup archives using OpenSSL with PBKDF2"*. But the actual implementation now uses the `cryptography` library with AES-256-GCM (migrated in v0.8.0-alpha). These misleading docstrings in encrypt.py and decrypt.py should be updated.

Additionally, `EncryptCommand` has a class attribute `PBKDF2_ITERATIONS = 600000` that is completely unused - the actual iteration count lives in `BaseCryptoManager`. Same for `DecryptCommand`.

**1.3 Config Format Inconsistency in `verify_config()`**

`BackupConfig.save()` writes `dirs_to_backup` as INI multi-line values (one per line), but `verify_config()` in config.py parses them with `.split(",")` (comma-separated). This means verification will always find zero directories when reading a config saved by the current `save()` method. The `load()` method correctly uses `parse_multiline_list()`. `verify_config()` should use the same parsing logic.

**1.4 Default Configuration Contains Developer-Specific Paths**

`_default_dirs_to_backup()` in config.py includes `~/.zen/qknutvmw.Default Profile`, `~/dotfiles`, `~/.config/syncthing`, `~/.config/FreeTube` - these are developer-specific and not universal defaults. New users will get broken config out of the box.

**Recommendation:** Ship an empty or minimal default (e.g., `["~/Documents"]`) and guide users through interactive setup on first run. The current defaults cause warning noise on every first backup.

---

### 2. Code Quality

**2.1 `sys.path` Hacking in Tests**

Every test file contains:

```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

This is unnecessary when using `uv run pytest` or editable installs (`pip install -e .`). Since the project uses pyproject.toml with uv, this manual sys.path manipulation should be removed from all test files. It can also mask import errors.

**2.2 Inconsistent Error Handling Patterns**

- `BackupManager.execute_backup()` catches specific exceptions and returns `bool`
- `EncryptManager._run_encryption_process()` catches bare `Exception`
- `DecryptManager` has proper retry logic with typed exceptions (`InvalidTag`)
- `ExtractManager` catches both `subprocess.CalledProcessError` and `OSError`

**Recommendation:** Define a custom exception hierarchy (e.g., `BackupError`, `EncryptionError`, `DecryptionError`) and use those instead of returning booleans. Let the CLI layer translate exceptions to exit codes. This would make error reporting more informative and testable.

**2.3 Password Handling Could Use `SecretStr` or Explicit Zeroing**

The `EncryptCommand` docstring mentions *"the password is deleted from memory"* but the actual code just uses plain Python strings. Python strings are immutable and cannot be reliably zeroed. Consider using `bytearray` for password storage (which can be zeroed) or at minimum remove the misleading security claims.

**2.4 Large File Encryption Reads Entire File into Memory**

Both `EncryptManager._run_encryption_process()` and `DecryptManager._run_decryption_process()` read the entire file into memory with `f.read()`. For multi-GB backup archives, this will exhaust memory.

**Recommendation:** Implement streaming encryption/decryption. AES-GCM can be used in a chunked mode, or consider switching to a streaming AEAD construction like AES-GCM-SIV with chunked processing, or use a tool-level approach with `cryptography`'s `CipherContext`.

**2.5 Double Slash Bug in Backup Path**

The todo.md already documents this: paths like `/home/developer/Documents/backup-for-cloud//13-04-2025.tar.xz` are generated because `backup_folder` has a trailing slash and the filename is joined naively. Use `Path` joining consistently instead of string concatenation.

**2.6 `format_size` Duplicates Exist**

The function `format_size` in format.py and the inline GB calculation in `SimpleProgressBar.update()` both format byte sizes but using different logic. Consolidate to a single utility.

---

### 3. CLI Tool

**3.1 No `--dry-run` Flag for Destructive Operations**

`backup`, `cleanup`, `encrypt`, and `decrypt` all perform irreversible operations. There's no `--dry-run` or `--verbose` flag to preview what would happen.

**Recommendation:** Add `--dry-run` to `backup` (show what would be backed up and estimated size), `cleanup` (show which files would be deleted), and `encrypt`/`decrypt` (show source and target paths).

**3.2 No `--config` Override**

The config path is hardcoded to `~/.config/autotarcompress/config.conf`. Users cannot specify an alternative config file. This limits multi-profile usage and makes testing harder.

**Recommendation:** Add a global `--config PATH` option to the Typer app callback.

**3.3 No `--output` / `-o` for Operations**

`backup`, `encrypt`, `decrypt`, and `extract` all determine output paths internally. Users cannot specify where to write output files.

**3.4 Cleanup UX Could Be Better**

Running `autotarcompress cleanup` with no options silently uses the `keep_backup` config value. This is documented but can be surprising. Consider printing what retention policy is being applied.

**3.5 `interactive` Command is Undocumented in Code**

The autocomplete scripts and wiki reference an `interactive` command, but I don't see it defined in parser.py. If it was removed, clean up references. If it exists elsewhere, ensure it's registered.

**3.6 No `--quiet` / `-q` Flag**

There's no way to suppress non-error output, which matters for cron/automation use cases listed in the examples.

**3.7 Typer Completion Disabled**

In parser.py, `add_completion=False` is set on the Typer app. This disables Typer's built-in completion in favor of the custom bash/zsh scripts in autocomplete. Consider leveraging Typer's native completion instead, which auto-updates as commands change.

---

### 4. Testing

**4.1 Duplicate Fixtures Across Test Files**

`temp_dir`, `test_config`, and `mock_backup_info` fixtures are defined identically in conftest.py, test_backup_manager.py, test_backup_info.py, and others. Use only the shared conftest.py fixtures.

**4.2 No Integration Tests for the Full CLI Pipeline**

Tests mock heavily. There's no test that runs `backup` -> `encrypt` -> `decrypt` -> `extract` end-to-end with real files. The existing `TestIntegration` class only tests encrypt/decrypt.

**Recommendation:** Add an integration test that creates real temp files, backs them up, encrypts, decrypts, extracts, and verifies file contents match.

**4.3 No Test Coverage Reporting in CI**

The AGENTS.md mentions `--cov` but with incorrect module paths (`aps.<folder>.<module>`, `my_unicorn.cli.parser`). Fix these examples and add coverage reporting to the test workflow.

**4.4 Missing Edge Case Tests**

- No test for what happens when disk is full during backup
- No test for concurrent backup operations
- No test for symlink handling in backup directories
- No test for very large file paths (near OS limit)
- No test for Unicode/special characters in directory names

---

### 5. Security

**5.1 PBKDF2 Iteration Count Should Be Configurable**

The iteration count (600,000) is hardcoded in `BaseCryptoManager`. As hardware improves, this should be user-configurable or at least easily bumped.

**5.2 No File Permissions Hardening**

Created backup files, encrypted files, and config files don't have explicit permissions set. Backup archives containing sensitive data should be created with `0o600` permissions. The config file (which doesn't contain secrets) is fine, but encrypted output files should be restricted.

**5.3 No Encrypted File Header/Version**

The encrypted file format `[salt(16)][nonce(12)][ciphertext][tag(16)]` has no version header. If you later change the encryption scheme, there's no way to detect which version was used. Add a magic byte + version prefix.

---

### 6. Performance

**6.1 `SizeCalculator` Walks the Entire Tree Twice**

The backup process first calculates total size (for the progress bar) by walking all directories, then the actual `tarfile` backup walks them again. For large backup sets, this doubles the I/O.

**Recommendation:** Either cache the file list from the size calculation pass and reuse it for tar creation, or estimate size from a previous backup's metadata.

**6.2 No Parallel Compression**

The backup uses Python's `tarfile` with zstd compression in a single thread. The `zstandard` library supports multi-threaded compression via the `threads` parameter. For multi-GB backups, this could significantly speed up the process.

---

### 7. Operational Improvements

**7.1 No Backup Verification Command**

After creating a backup, there's no way to verify its integrity without extracting it. Add a `verify` command that checks the tar archive integrity and optionally verifies against stored hashes.

**7.2 No Restore Command**

`extract` dumps files into a `*-extracted` directory. A proper `restore` command could extract directly to the original paths (with confirmation), making disaster recovery easier.

**7.3 Metadata Version Should Auto-Migrate**

The metadata system has a `metadata_version` field (currently "2.0") but no migration logic for older formats. If the format changes, old metadata files will fail silently.

**7.4 Logging Could Support Structured Output**

For automation, structured JSON logging would make it easier to parse backup results programmatically. Add a `--json` output flag or a `--log-format json` config option.

---

### Priority Summary

| Priority | Item | Impact |
|----------|------|--------|
| **P0 - Bugs** | Fix `verify_config()` parsing (comma vs multiline) | Config validation is broken |
| **P0 - Bugs** | Fix double-slash in backup paths | Cosmetic but confusing |
| **P1 - High** | Memory-safe large file encryption (streaming) | OOM on large backups |
| **P1 - High** | Remove stale OpenSSL references/unused constants | Misleading docs |
| **P1 - High** | Add `--dry-run` to destructive operations | Safety |
| **P2 - Medium** | Collapse Command -> Manager layer | Simplify architecture |
| **P2 - Medium** | Remove `sys.path` hacking from tests | Code hygiene |
| **P2 - Medium** | Deduplicate test fixtures | DRY |
| **P2 - Medium** | Add `--config` global option | Usability |
| **P2 - Medium** | Fix default config paths | New user experience |
| **P3 - Low** | Add encrypted file version header | Future-proofing |
| **P3 - Low** | Multi-threaded zstd compression | Performance |
| **P3 - Low** | Add `verify` command | Reliability |
| **P3 - Low** | Structured JSON logging | Automation |
