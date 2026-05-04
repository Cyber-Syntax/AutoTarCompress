---
title: "ADR-0003: Track Last Backup Date in Config or Metadata"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "metadata", "backup-tracking"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

The current `BackupConfig` dataclass in `config.py` does not track when the last backup was performed. While `metadata.json` stores `last_backup_time`, this value can be `null` and is not surfaced in the config file or used programmatically to inform the user or drive automation.

Use cases for an accessible last-backup date:

1. **User awareness** — the `info` command or startup banner could warn "Last backup was 14 days ago" to encourage regular backups.
2. **Automation** — external scripts (e.g., `auto-backup.sh`) could read the last backup date to decide whether a new backup is needed.
3. **Staleness detection** — the CLI could warn when backups are overdue based on a configurable threshold.

The question is where to store and maintain this value: in the user-facing config file (`config.conf`), in the machine-managed metadata file (`metadata.json`), or both.

## Decision

Store the `last_backup` date in **`metadata.json` only** (not in `config.conf`), and update it automatically after every successful backup. Expose the value through the `info` command and optionally through a startup warning.

Rationale for metadata-only storage:

- `config.conf` is a user-edited INI file. Automatically writing to it after each backup risks corrupting user comments or formatting.
- `metadata.json` is already machine-managed and is the canonical location for backup execution state.
- The `last_backup_time` field already exists in `BackupMetadata` — it simply needs to be reliably written and surfaced.

### Changes Required

1. Ensure `update_backup_metadata()` always writes `last_backup_time` (it already does — verify no code paths skip it).
2. Add a `last_backup` convenience property to `BackupConfig` that reads from `metadata.json` on demand.
3. Update the `info` command to display last backup date in human-readable format with relative time (e.g., "2 days ago").
4. Optionally add a startup warning when the last backup is older than a configurable threshold (default: 7 days).

## Consequences

### Positive

- **POS-001**: Users gain immediate visibility into backup recency via the `info` command.
- **POS-002**: No changes to the user-edited `config.conf` format — avoids breaking existing configs or overwriting user comments.
- **POS-003**: External scripts can parse `metadata.json` (a stable JSON format) to determine backup freshness.
- **POS-004**: Foundation for future features like scheduled backup reminders or automated staleness alerts.

### Negative

- **NEG-001**: The last backup date is not visible by simply reading `config.conf` — users must run `info` or inspect `metadata.json` directly.
- **NEG-002**: If `metadata.json` is deleted or corrupted, the last backup date is lost. Mitigated by the file being recreated on the next backup.
- **NEG-003**: Adding a startup warning introduces a minor overhead on every CLI invocation (reading `metadata.json`).

## Alternatives Considered

### Store in config.conf

- **ALT-001**: **Description**: Add a `last_backup = null` field to `config.conf` and update it after each backup.
- **ALT-002**: **Rejection Reason**: The config file uses INI format with user-written comments. Programmatically rewriting it after each backup risks losing comments and formatting. Python's `configparser` does not preserve comments reliably.

### Store in Both config.conf and metadata.json

- **ALT-003**: **Description**: Write the last backup date to both files for maximum visibility.
- **ALT-004**: **Rejection Reason**: Creates a dual-source-of-truth problem. If the two values diverge, it is unclear which is authoritative. Adds complexity for no real benefit.

### Store in a Separate File

- **ALT-005**: **Description**: Write the last backup date to a dedicated file like `last-backup.txt`.
- **ALT-006**: **Rejection Reason**: Adds yet another file to manage. `metadata.json` already serves this purpose and provides a structured format.

## Implementation Notes

- **IMP-001**: Verify that `update_backup_metadata()` in `metadata.py` is called on all successful backup paths (both encrypted and unencrypted).
- **IMP-002**: Add a `get_last_backup_age()` helper to `metadata.py` that returns a `timedelta` or `None`.
- **IMP-003**: Update the `info` command's output to include "Last backup: 2026-02-28 10:30 (2 days ago)".
- **IMP-004**: Optionally add a `--warn-stale` global option or a `backup_warn_days` config field for staleness threshold.
- **IMP-005**: Success criteria — after a successful backup, `metadata.json` contains a non-null `last_backup_time`; the `info` command displays it; existing tests pass.

## References

- **REF-001**: [autotarcompress/metadata.py](../../autotarcompress/metadata.py) — `update_backup_metadata()` already writes `last_backup_time`
- **REF-002**: [autotarcompress/config.py](../../autotarcompress/config.py) — config file format and save logic
- **REF-003**: [ADR-0002](adr-0002-multi-backup-info-config.md) — related decision on multi-backup metadata
