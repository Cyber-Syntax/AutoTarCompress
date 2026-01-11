# Configuring Ignore Patterns in AutoTarCompress

**Last Updated:** January 1, 2026

## Overview

AutoTarCompress allows you to exclude specific directories and files from your backups using the `ignore_list` configuration. This feature helps reduce backup size by skipping unnecessary or temporary files like cache directories, build artifacts, and large data folders.

## How Ignore Patterns Work

The `ignore_list` in your configuration file (`~/.config/autotarcompress/config.conf`) specifies patterns and paths to exclude during backup creation. The system supports two types of exclusions:

### 1. Pattern-Based Exclusions

- **Relative patterns** like `node_modules`, `__pycache__`, `*.pyc`
- These match any directory or file with that name anywhere in the backup tree
- Use wildcards (`*`) for flexible matching

### 2. Absolute Path Exclusions

- **Full paths** starting with `~` (home directory) or `/` (root)
- These exclude specific directories regardless of location
- Useful for excluding specific folders like backup destinations or large data directories

## Configuration Syntax

Add the `ignore_list` setting to your `[DEFAULT]` section:

```ini
[DEFAULT]
ignore_list =
    # Absolute paths (exclude specific directories)
    ~/Documents/global-repos
    ~/Documents/backup-for-cloud
    ~/.stversions

    # Patterns (exclude matching names anywhere)
    node_modules
    .venv
    __pycache__
    .ruff_cache
    .mypy_cache
    .pytest_cache
    *.egg-info
    *target
    lock
    chrome
    .bin
```

## Examples

### Common Development Exclusions

```ini
ignore_list =
    # Node.js dependencies
    node_modules

    # Python virtual environments and cache
    .venv
    __pycache__
    *.pyc

    # Development tool caches
    .ruff_cache
    .mypy_cache
    .pytest_cache

    # Build artifacts
    *.egg-info
    *target
    dist
    build
```

### System and Application Exclusions

```ini
ignore_list =
    # Browser cache and data
    chrome
    .cache

    # Temporary files
    *.tmp
    *.temp
    .DS_Store

    # Lock files
    lock
    *.lock
```

### Absolute Path Exclusions

```ini
ignore_list =
    # Exclude backup destination itself
    ~/Documents/backup-for-cloud

    # Exclude large data directories
    ~/Documents/large-datasets
    ~/Videos
```

## Developer Current Configuration

Based on my working config, here's how your `ignore_list` is processed:

```ini
[DEFAULT]
ignore_list =
    ~/Documents/global-repos      # → /home/user/Documents/global-repos (absolute path)
    ~/Documents/backup-for-cloud  # → /home/user/Documents/backup-for-cloud (absolute path)
    .stversions                   # → .stversions (pattern)
    node_modules                  # → node_modules (pattern)
    .venv                         # → .venv (pattern)
    __pycache__                   # → __pycache__ (pattern)
    .ruff_cache                   # → .ruff_cache (pattern)
    .mypy_cache                   # → .mypy_cache (pattern)
    .pytest_cache                 # → .pytest_cache (pattern)
    *.egg-info                    # → *.egg-info (pattern)
    *target                       # → *target (pattern)
    lock                          # → lock (pattern)
    chrome                        # → chrome (pattern)
    .bin                          # → .bin (pattern)
```

## How It Works Internally

1. **Configuration Processing**: Patterns starting with `~` or `/` are expanded to absolute paths. Others remain as patterns.

2. **Backup Creation**: The tar command includes `--exclude` flags for each item:

   ```bash
   tar --exclude='/home/user/Documents/global-repos' \
       --exclude='.stversions' \
       --exclude='node_modules' \
       --exclude='__pycache__' \
       --exclude='*.egg-info' ...
   ```

3. **Size Calculation**: The size calculator respects the same exclusions to show accurate backup sizes.

4. **Pattern Matching**: Uses shell-style wildcards (`*`, `?`, `[...]`) for flexible matching.

## Tips and Best Practices

- **Test Your Exclusions**: Use `autotarcompress info --latest` to verify backup contents
- **Monitor Backup Size**: Compare sizes before and after adding exclusions
- **Use Absolute Paths**: For directories you always want excluded, regardless of location
- **Use Patterns**: For common directories that appear in multiple projects
- **Wildcard Power**: `*.log` excludes all `.log` files, `*cache*` matches any cache-related directory
- **Case Sensitivity**: Patterns are case-sensitive (`.Cache` ≠ `.cache`)

## Troubleshooting

### Exclusions Not Working

- **Check Syntax**: Ensure each pattern is on a new line in the config
- **Absolute vs Relative**: Remember that absolute paths exclude specific locations, patterns exclude by name
- **Verify Config**: Run the app with debug logging to see processed patterns

### Unexpected Exclusions

- **Overly Broad Patterns**: `cache` will exclude any directory named `cache`, not just `.cache`
- **Absolute Path Issues**: `~/Documents` excludes the entire Documents directory
