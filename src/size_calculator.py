import os
from typing import List
from tqdm import tqdm
from dataclasses import dataclass, field
from .config import Config


@dataclass
class SizeCalculator:
    config: Config

    def read_dirs_to_backup(self) -> List[str]:
        """Read the directories and files listed in dirs_to_backup.txt"""
        dirs_to_backup = []
        with open(self.config.dirs_to_backup, "r", encoding="utf-8") as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(os.path.expanduser(directory))
        return dirs_to_backup

    def read_ignore_list(self) -> List[str]:
        """Read the directories and files listed in ignore.txt"""
        ignore_list = []
        if os.path.isfile(self.config.ignore_list):
            with open(self.config.ignore_list, "r", encoding="utf-8") as file:
                for line in file:
                    ignore_path = line.strip()
                    if ignore_path:
                        ignore_list.append(os.path.expanduser(ignore_path))
        return ignore_list

    def calculate_directory_size(
        self, directory: str, ignore_paths: List[str] = []
    ) -> int:
        """Calculate the total size of a directory, excluding ignored paths"""
        total_size = 0
        ignore_paths_set = set(ignore_paths)
        for dirpath, dirnames, filenames in os.walk(directory):
            # Skip ignored directories
            dirnames[:] = [
                d
                for d in dirnames
                if not any(
                    os.path.join(dirpath, d).startswith(ignored)
                    for ignored in ignore_paths_set
                )
            ]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not any(
                    filepath.startswith(ignored) for ignored in ignore_paths_set
                ):
                    try:
                        total_size += os.path.getsize(filepath)
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        print(f"Error accessing {filepath}: {e}")
                        continue
        return total_size

    def calculate_total_size_of_dirs(self, dirs: List[str]) -> int:
        """Calculate the total size of a list of directories"""
        total_size = 0
        print("\nCalculating sizes for directories in dirs_to_backup.txt:")
        for path in tqdm(dirs, desc="Processing directories"):
            expanded_path = os.path.expanduser(path)
            if os.path.isdir(expanded_path):
                dir_size = self.calculate_directory_size(expanded_path, [])
                total_size += dir_size
                print(f"Directory: {expanded_path}, Size: {self.format_size(dir_size)}")
        return total_size

    def calculate_total_backup_size(
        self, dirs_to_backup: List[str], ignore_list: List[str]
    ) -> int:
        """Calculate the total size of directories to backup, excluding ignored paths"""
        total_backup_size = 0
        print("\nCalculating sizes for backup directories excluding ignored paths:")
        for path in tqdm(dirs_to_backup, desc="Processing backup directories"):
            expanded_path = os.path.expanduser(path)
            if os.path.isdir(expanded_path):
                dir_size = self.calculate_directory_size(expanded_path, ignore_list)
                total_backup_size += dir_size
                print(
                    f"Backup Path: {expanded_path}\n  Size: {self.format_size(dir_size)}"
                )
        return total_backup_size

    def calculate_total_ignore_size(self, ignore_list: List[str]) -> int:
        """Calculate the total size of ignored directories"""
        total_ignore_size = 0
        print("\nCalculating sizes for ignored directories:")
        for path in tqdm(ignore_list, desc="Processing ignored directories"):
            expanded_ignore_path = os.path.expanduser(path)
            if os.path.isdir(expanded_ignore_path):
                ignore_size = self.calculate_directory_size(expanded_ignore_path, [])
                total_ignore_size += ignore_size
                print(
                    f"Ignored Path: {expanded_ignore_path}, Size: {self.format_size(ignore_size)}"
                )
        return total_ignore_size

    def format_size(self, size: int) -> str:
        """Format the size to be more user-friendly"""
        size_mb = size / (1024 * 1024)
        size_gb = size / (1024 * 1024 * 1024)
        if size_gb >= 1:
            return f"{size_gb:.2f} GiB"
        else:
            return f"{size_mb:.2f} MiB"

    def calculate_and_display_sizes(self):
        """Calculate and display sizes"""
        total_size_of_dirs_to_backup = self.calculate_total_size_of_dirs(
            self.config.dirs_to_backup
        )
        total_ignore_size = self.calculate_total_ignore_size(self.config.ignore_list)
        total_backup_size_excluding_ignored = self.calculate_total_backup_size(
            self.config.dirs_to_backup, self.config.ignore_list
        )

        print("\nSummary of Sizes:")
        print(
            f"Total size of directories to backup (before excluding ignored directories): {self.format_size(total_size_of_dirs_to_backup)}"
        )
        print(
            f"Total size of ignored directories: {self.format_size(total_ignore_size)}"
        )
        print(
            f"Total size of directories to backup (after excluding ignored directories): {self.format_size(total_backup_size_excluding_ignored)}"
        )
