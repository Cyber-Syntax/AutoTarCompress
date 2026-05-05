"""Simple ASCII progress bar for backup operations.

Provides a pure-Python progress bar without external dependencies.
"""

import sys
import time

# Constants for time formatting
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60


class SimpleProgressBar:
    """Simple ASCII progress bar [====     ] 45% 1.2GB/2.5GB ETA: 2m 30s."""

    def __init__(self, total_size: int, width: int = 30) -> None:
        """Initialize progress bar.

        Args:
            total_size: Total size in bytes for progress calculation
            width: Width of the progress bar in characters (default: 30)

        """
        self.total_size: int = total_size
        self.current_size: int = 0
        self.width: int = width
        self.last_percentage: int = -1
        self.start_time: float = time.time()
        self.last_update_time: float = self.start_time

    def _calculate_eta(self) -> str:
        """Calculate estimated time remaining.

        Returns:
            Formatted ETA string or empty string if unable to calculate
        """
        current_time = time.time()
        elapsed = current_time - self.start_time

        # Need at least 1 second and some progress to calculate meaningful ETA
        if elapsed < 1.0 or self.current_size == 0:
            return ""

        # Calculate bytes per second
        rate = self.current_size / elapsed

        # Calculate remaining bytes and time
        remaining_bytes = self.total_size - self.current_size
        if remaining_bytes <= 0:
            return "00:00"

        remaining_seconds = remaining_bytes / rate

        # Format as MM:SS or HH:MM:SS
        if remaining_seconds < SECONDS_PER_HOUR:  # Less than 1 hour
            minutes = int(remaining_seconds // SECONDS_PER_MINUTE)
            seconds = int(remaining_seconds % SECONDS_PER_MINUTE)
            return f"{minutes:02d}:{seconds:02d}"

        # 1 hour or more
        hours = int(remaining_seconds // SECONDS_PER_HOUR)
        minutes = int(
            (remaining_seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        )
        seconds = int(remaining_seconds % SECONDS_PER_MINUTE)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _calculate_elapsed(self) -> str:
        """Calculate elapsed time.

        Returns:
            Formatted elapsed time string
        """
        current_time = time.time()
        elapsed_seconds = current_time - self.start_time

        # Format as MM:SS or HH:MM:SS
        if elapsed_seconds < SECONDS_PER_HOUR:  # Less than 1 hour
            minutes = int(elapsed_seconds // SECONDS_PER_MINUTE)
            seconds = int(elapsed_seconds % SECONDS_PER_MINUTE)
            return f"{minutes:02d}:{seconds:02d}"

        # 1 hour or more
        hours = int(elapsed_seconds // SECONDS_PER_HOUR)
        minutes = int(
            (elapsed_seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        )
        seconds = int(elapsed_seconds % SECONDS_PER_MINUTE)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def update(self, bytes_added: int) -> None:
        """Update progress and redraw bar.

        Args:
            bytes_added: Number of bytes to add to current progress

        """
        self.current_size += bytes_added

        # Avoid division by zero
        if self.total_size == 0:
            return

        percentage = int((self.current_size / self.total_size) * 100)

        # Only update display if percentage changed (reduce flicker)
        if percentage == self.last_percentage:
            return

        self.last_percentage = percentage

        # Calculate filled portion of bar
        filled = int(self.width * self.current_size / self.total_size)
        filled = min(filled, self.width)  # Cap at width

        bar = "=" * filled + " " * (self.width - filled)

        # Format sizes in GB
        current_gb = self.current_size / (1024**3)
        total_gb = self.total_size / (1024**3)

        # Calculate ETA and elapsed
        eta = self._calculate_eta()
        elapsed = self._calculate_elapsed()

        time_display = f" {elapsed}/{eta}" if eta else f" {elapsed}"

        # Print with carriage return (overwrite same line)
        # Use \r to return to start of line
        base_text = (
            f"\r[{bar}] {percentage:3d}% {current_gb:6.2f}GB/{total_gb:.2f}GB"
        )
        progress_text = f"{base_text}{time_display}"
        sys.stdout.write(progress_text)
        sys.stdout.flush()

    def finish(self) -> None:
        """Complete the progress bar and move to new line."""
        # Ensure we show 100%
        if self.total_size > 0:
            self.current_size = self.total_size
            percentage = 100
            bar = "=" * self.width

            current_gb = self.current_size / (1024**3)
            total_gb = self.total_size / (1024**3)

            elapsed = self._calculate_elapsed()
            progress_text = (
                f"\r[{bar}] {percentage:3d}% "
                f"{current_gb:6.2f}GB/{total_gb:.2f}GB {elapsed}/00:00"
            )
            sys.stdout.write(progress_text)
            sys.stdout.flush()

        # Move to new line
        sys.stdout.write("\n")
        sys.stdout.flush()
