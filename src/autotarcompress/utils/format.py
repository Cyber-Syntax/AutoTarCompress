"""Utilities for formatting data."""

BYTES_IN_KB = 1024.0


def format_size(size_in_bytes: int) -> str:
    """Convert a size in bytes to a human-readable format (KB, MB, GB).

    Args:
        size_in_bytes: The size in bytes.

    Returns:
        The formatted size string.

    """
    size = float(size_in_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < BYTES_IN_KB:
            return f"{size:.2f} {unit}"
        size /= BYTES_IN_KB
    return f"{size:.2f} PB"
