import os
import subprocess
import datetime
import sys
import time
import json
import gettext
from typing import List
from dataclasses import dataclass, field
from tqdm import tqdm
from .size_calculator import SizeCalculator
from .config import Config

_ = gettext.gettext


@dataclass
class BackupManager:
    config: Config
    size_calculator: SizeCalculator

    def check_backup_exist(self) -> bool:
        """Check if a backup file already exists for today"""
        return os.path.isfile(self.config.backup_file_path)

    def backup_directories(self) -> bool:
        """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

        if not self.config.dirs_to_backup:
            print(
                "No directories to backup. Create directories on the config.json. Look example config.json."
            )
            sys.exit()

        ignore_paths = [os.path.expanduser(path) for path in self.config.ignore_list]

        # Generate the exclude options for the tar command
        exclude_options = " ".join([f"--exclude={path}" for path in ignore_paths])

        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in self.config.dirs_to_backup]

        # Calculate the total size using SizeCalculator
        # size_calculator = BackupManager(self.config.dirs_to_backup, self.config.ignore_list)
        total_size_bytes = self.size_calculator.calculate_total_backup_size(
            dir_paths, ignore_paths
        )

        # Convert the total size to MB and GiB
        total_size_mb = total_size_bytes / (1024 * 1024)
        total_size_gib = total_size_bytes / (1024 * 1024 * 1024)

        print(f"Total size: {total_size_mb:.2f} MB / {total_size_gib:.2f} GiB")

        # Get the number of CPU threads for xz compression
        cpu_threads = os.cpu_count() - 1
        print(f"CPU threads - 1: {cpu_threads}")

        # Create the tar command
        os_cmd = (
            f"tar -cf - {filesystem_option} {exclude_options} {' '.join(dir_paths)} | "
            f"xz --threads={cpu_threads} > {self.config.backup_file_path}"
        )

        # Run the tar command and update the progress bar
        try:
            proc = subprocess.Popen(
                os_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            pbar = tqdm(
                total=total_size_bytes,
                unit="B",
                unit_scale=True,
                desc="Processing",
                dynamic_ncols=True,
            )

            while proc.poll() is None:
                if os.path.exists(self.config.backup_file_path):
                    current_size = os.path.getsize(self.config.backup_file_path)
                    pbar.update(
                        current_size - pbar.n
                    )  # Update the progress bar with the difference
                time.sleep(0.1)  # Sleep briefly to avoid too frequent polling

            proc.wait()
            pbar.close()

            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, os_cmd)

            print("Backup completed successfully")
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
        ) as error:
            print(f"Error backing up files: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Backup cancelled")
            sys.exit(0)
