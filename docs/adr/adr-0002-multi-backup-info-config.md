---
title: "ADR-0002: Keep Multiple Backup Records in Config (Current and Previous)"
status: "Proposed"
date: "2026-02-28"
authors: "Cyber-Syntax"
tags: ["architecture", "decision", "metadata", "backup-history"]
supersedes: ""
superseded_by: ""
---

## Status

**Proposed**

## Context

Currently, the `BackupMetadata` dataclass in `autotarcompress/metadata.py` stores only a single snapshot of backup information:

- `last_backup_time` — timestamp of the most recent backup
- `last_backup_file` — path to the most recent backup archive
- `backup_count` — total number of backups ever created
- `file_hashes` — SHA256 hashes keyed by filename

When a new backup is created, the previous record is overwritten completely. This means:

1. If the latest backup is corrupted or incomplete, the user has no record of the previous good backup.
2. The `info` command can only display the current backup's details, providing no historical comparison.
3. There is no way to quickly identify what changed between two consecutive backups without inspecting the filesystem directly.

Users need visibility into at least the current and previous backup to make informed decisions about retention, restoration, and integrity verification.

## Decision

Extend the metadata schema to maintain an ordered list of the **N most recent backup records** (default N=2: current and previous), stored in `metadata.json`. Each record will be a self-contained object with the same fields currently tracked for a single backup.

### Schema Change (metadata.json v3.0)

```json
{
  "metadata_version": "3.0",
  "backup_count": 5,
  "backups": [
    {
      "backup_time": "2026-02-28T10:30:00+00:00",
      "backup_file": "/home/user/backups/28-02-2026.tar.zst",
      "file_hashes": {
        "28-02-2026.tar.zst": "sha256:abc..."
      }
    },
    {
      "backup_time": "2026-02-27T09:15:00+00:00",
      "backup_file": "/home/user/backups/27-02-2026.tar.zst",
      "file_hashes": {
        "27-02-2026.tar.zst": "sha256:def..."
      }
    }
  ]
}
```

Key design decisions:

- **Fixed-size list** (configurable, default 2) — oldest entries are evicted when the list is full.
- **Backward-compatible migration** — `from_dict` will detect v2.0 format and automatically migrate to v3.0 by wrapping the existing single record into a one-element list.
- **`BackupMetadata`** will retain convenience properties (`last_backup_time`, `last_backup_file`) that delegate to `backups[0]`.

## Consequences

### Positive

- **POS-001**: Users can view and compare the current and previous backup via the `info` command.
- **POS-002**: If the latest backup is corrupted, the previous backup's path and hash are readily available for recovery.
- **POS-003**: The schema is forward-compatible — increasing `N` later requires no structural change.
- **POS-004**: Minimal storage overhead — each additional record is a few hundred bytes of JSON.

### Negative

- **NEG-001**: Schema migration logic adds complexity to `BackupMetadata.from_dict` (must handle v1.0, v2.0, and v3.0).
- **NEG-002**: Code that currently accesses `metadata.last_backup_file` directly will need to be updated or use the convenience properties.
- **NEG-003**: Tests covering metadata loading/saving will need to be updated for the new schema.

## Alternatives Considered

### Store Full Unlimited History

- **ALT-001**: **Description**: Keep every backup record ever created in `metadata.json` without a cap.
- **ALT-002**: **Rejection Reason**: The file would grow unboundedly over time. For a daily backup over years this becomes unwieldy. A fixed window (default 2) keeps the file small and focused.

### Use a Separate History File

- **ALT-003**: **Description**: Keep `metadata.json` as-is for the current backup, and write a separate `history.json` or append-only log.
- **ALT-004**: **Rejection Reason**: Splits related data across two files, increasing complexity for both code and users. A single file with an ordered list is simpler.

### Store in the Config File (config.conf)

- **ALT-005**: **Description**: Add backup history fields directly to the INI config file.
- **ALT-006**: **Rejection Reason**: The config file is user-edited and INI format is poorly suited for structured lists of records. Metadata belongs in `metadata.json`.

## Implementation Notes

- **IMP-001**: Add a `BackupRecord` dataclass to represent a single backup entry (time, file, hashes).
- **IMP-002**: Refactor `BackupMetadata` to contain a `backups: list[BackupRecord]` field with a max length parameter.
- **IMP-003**: Update `update_backup_metadata()` to prepend the new record and trim the list to max length.
- **IMP-004**: Update `info` command to display both current and previous backup details.
- **IMP-005**: Write migration logic in `from_dict` that detects `metadata_version` and upgrades v1.0/v2.0 to v3.0.
- **IMP-006**: Success criteria — `uv run pytest` passes, `info` command shows both records, and v2.0 metadata files are auto-migrated on first load.

## References

- **REF-001**: [autotarcompress/metadata.py](../../autotarcompress/metadata.py) — current metadata implementation
- **REF-002**: [autotarcompress/config.py](../../autotarcompress/config.py) — config management
- **REF-003**: [tests/test_metadata.py](../../tests/test_metadata.py) — existing metadata tests
