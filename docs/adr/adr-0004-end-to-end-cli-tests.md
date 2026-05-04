---
title: "ADR-0004: Add End-to-End CLI Tests with Temporary Fixtures"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "testing", "e2e", "cli"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The existing test suite for AutoTarCompress consists of unit tests that exercise individual modules (`config.py`, `metadata.py`, `backup_manager.py`, etc.) in isolation using mocks and temporary directories. While these tests provide good coverage of internal logic, they do not verify the complete user workflow:

1. **No CLI invocation tests** — the Typer CLI commands (`backup`, `encrypt`, `decrypt`, `extract`, `info`, `cleanup`) are never exercised as a user would invoke them.
2. **No integration of config → backup → metadata flow** — the chain of loading config, running a backup, writing metadata, and verifying output is not tested end-to-end.
3. **No verification of actual archive contents** — unit tests mock the tarfile operations, so archive integrity is never validated.
4. **No testing of CLI exit codes and output** — error handling paths that produce specific exit codes or user-facing messages are untested at the CLI level.

The project uses `pytest` with `conftest.py` fixtures (temporary directories, test configs, test data) that provide a foundation for E2E tests, but these fixtures are currently only used by unit tests.

## Decision

Add a dedicated E2E test module (`tests/test_e2e.py`) that tests the full CLI workflow by:

1. **Using `typer.testing.CliRunner`** to invoke CLI commands programmatically within pytest.
2. **Creating temporary config files** (`config.conf`) in `tmp_path` fixtures, pointing to temporary source and destination directories.
3. **Creating real test data** (files and directories) in temporary locations.
4. **Executing the full backup → info → encrypt → decrypt → extract → cleanup pipeline** and asserting on:
   - Exit codes (0 for success, non-zero for expected failures)
   - Output messages (confirmation text, file paths)
   - Filesystem state (archive exists, extracted files match originals, metadata written)
   - Metadata accuracy (timestamps, file hashes, backup count)

### Test Scenarios

| Test | Description |
|------|-------------|
| `test_backup_creates_archive` | Run `backup` command, verify `.tar.zst` archive exists |
| `test_backup_with_ignore_patterns` | Verify excluded directories are not in the archive |
| `test_info_shows_backup_details` | Run `info` after backup, verify output contains expected fields |
| `test_encrypt_decrypt_roundtrip` | Encrypt a backup, decrypt it, verify content matches |
| `test_extract_restores_files` | Extract a backup, verify file contents match originals |
| `test_cleanup_removes_old_backups` | Create multiple backups, run cleanup, verify retention policy |
| `test_full_pipeline` | Run the complete workflow end-to-end in sequence |

## Consequences

### Positive

- **POS-001**: Catches integration bugs that unit tests miss — e.g., incorrect argument passing between CLI layer and manager classes.
- **POS-002**: Validates the real user experience — commands produce expected output and exit codes.
- **POS-003**: Verifies archive integrity — real `.tar.zst` files are created and their contents validated.
- **POS-004**: Serves as living documentation of supported workflows.
- **POS-005**: Existing `conftest.py` fixtures (`temp_dir`, `test_config`, `test_data_dir`) can be extended and reused.

### Negative

- **NEG-001**: E2E tests are slower than unit tests due to real filesystem I/O and archive creation. Mitigated by using small test data and marking tests with `@pytest.mark.slow` or `@pytest.mark.integration`.
- **NEG-002**: Tests that invoke the full CLI may be more brittle to output format changes. Mitigated by asserting on key substrings rather than exact output.
- **NEG-003**: Password-dependent commands (`encrypt`, `decrypt`) require careful fixture design to provide passwords non-interactively.

## Alternatives Considered

### Shell-Based E2E Tests

- **ALT-001**: **Description**: Write E2E tests as shell scripts that invoke the installed `autotarcompress` binary and use standard UNIX tools (`grep`, `tar`, `diff`) to validate output.
- **ALT-002**: **Rejection Reason**: Shell tests are harder to maintain, lack pytest's assertion introspection and fixture management, and would not integrate with the existing test infrastructure or CI coverage reports.

### Subprocess-Based Python Tests

- **ALT-003**: **Description**: Use `subprocess.run()` in pytest to invoke `autotarcompress` as an external process.
- **ALT-004**: **Rejection Reason**: Requires the package to be installed first, adds process overhead, and makes it harder to inject test configuration. `typer.testing.CliRunner` provides the same coverage with simpler setup and faster execution.

### Expand Unit Tests Only

- **ALT-005**: **Description**: Instead of E2E tests, add more granular unit tests with fewer mocks to cover integration gaps.
- **ALT-006**: **Rejection Reason**: Unit tests with reduced mocking still don't exercise the CLI argument parsing, Typer command registration, and output formatting layers. E2E tests fill a fundamentally different gap.

## Implementation Notes

- **IMP-001**: Create `tests/test_e2e.py` with a dedicated fixture (`e2e_env`) that sets up a complete temporary environment: config file, source directories with test data, and an empty backup destination.
- **IMP-002**: Use `typer.testing.CliRunner` to invoke commands. Example:

  ```python
  from typer.testing import CliRunner
  from autotarcompress.cli import app

  runner = CliRunner()
  result = runner.invoke(app, ["backup"])
  assert result.exit_code == 0
  ```

- **IMP-003**: For password-dependent commands, use `CliRunner.invoke(input=...)` to provide stdin input, or monkeypatch the password prompt.
- **IMP-004**: Mark E2E tests with `@pytest.mark.integration` so they can be run separately: `uv run pytest -m integration`.
- **IMP-005**: Add the `integration` marker to `pyproject.toml` markers list (already partially configured).
- **IMP-006**: Keep test data small (a few KB) to ensure fast execution even on CI.
- **IMP-007**: Success criteria — all E2E tests pass with `uv run pytest -m integration`, and they cover the backup → info → encrypt → decrypt → extract → cleanup pipeline.

## References

- **REF-001**: [Typer testing documentation](https://typer.tiangolo.com/tutorial/testing/)
- **REF-002**: [tests/conftest.py](../../tests/conftest.py) — existing test fixtures
- **REF-003**: [autotarcompress/cli/parser.py](../../autotarcompress/cli/parser.py) — CLI command definitions
- **REF-004**: [pyproject.toml](../../pyproject.toml) — pytest configuration and markers
