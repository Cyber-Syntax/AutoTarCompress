# AutoTarCompress CLI Reference & Guide

AutoTarCompress is a backup and archive management tool for Linux, offering both CLI and interactive menu modes.
It supports compressed backups, encryption, extraction, cleanup, and more.

---

## CLI Command Reference

### `backup`

Create a backup archive of configured directories.

**Usage:**

```bash
autotarcompress backup
```

---

### `encrypt`

Encrypt a backup file. Requires exactly one option:

- `--latest` — Encrypt the latest backup
- `--date DD-MM-YYYY` — Encrypt backup from a specific date
- `filename` — Encrypt a specific file

**Examples:**

```bash
autotarcompress encrypt --latest
autotarcompress encrypt --date 15-01-2024
autotarcompress encrypt backup_15-01-2024_10-30-45.tar.xz
```

---

### `decrypt`

Decrypt an encrypted backup file (same options as encrypt).

**Examples:**

```bash
autotarcompress decrypt --latest
autotarcompress decrypt --date 15-01-2024
autotarcompress decrypt backup_15-01-2024_10-30-45.tar.xz
```

---

### `extract`

Extract a backup archive (same options as encrypt).

**Examples:**

```bash
autotarcompress extract --latest
autotarcompress extract --date 15-01-2024
autotarcompress extract backup_15-01-2024_10-30-45.tar.xz
```

---

### `cleanup`

Clean up old backup files.

**Options:**

- No options: Use configuration defaults
- `--all` — Remove all old backups
- `--older-than N` — Remove backups older than N days
- `--keep N` — Keep only N most recent backups

**Examples:**

```bash
autotarcompress cleanup
autotarcompress cleanup --all
autotarcompress cleanup --older-than 30
autotarcompress cleanup --keep 5
```

---

### `info`

Show information about the last backup.

**Usage:**

```bash
autotarcompress info
```

---

### `interactive`

Launch the interactive menu (legacy mode).

**Usage:**

```bash
autotarcompress interactive
```

---

## Example Scripts

### Daily Backup Script

```bash
#!/bin/bash
# Daily backup with cleanup
autotarcompress backup
autotarcompress encrypt --latest
autotarcompress cleanup --keep 7
autotarcompress info
```

### Restore from Specific Date

```bash
# Extract backup from January 15, 2024
autotarcompress extract --date 15-01-2024
```

---

## Configuration

On first run, AutoTarCompress will guide you through initial configuration:

1. **Backup storage location** — Where to store backup files
2. **Directories to backup** — Which directories to include
3. **Ignore patterns** — Files/directories to exclude
4. **Retention policy** — How many backups to keep
