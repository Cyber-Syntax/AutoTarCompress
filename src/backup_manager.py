import os
import subprocess
import datetime
import sys
import time
import tarfile
import json
import gettext
import getpass
import logging
import hashlib
import re
from typing import List
from dataclasses import dataclass, field
from tqdm import tqdm

_ = gettext.gettext


@dataclass
class BackupManager:

    backup_folder: str = field(default_factory=lambda: "~/Documents/backup-for-cloud/")
    keep_backup: int = field(default_factory=lambda: 1)
    keep_enc_backup: int = field(default_factory=lambda: 1)
    dirs_to_backup: List[str] = field(default_factory=list)
    ignore_list: List[str] = field(default_factory=list)
    config_file_path: str = field(init=False)
    backup_file_path: str = field(init=False)
    decrypt_file_path: str = field(init=False)
    current_date: str = datetime.datetime.now().strftime("%d-%m-%Y")

    def __post_init__(self):
        self.backup_file_path = os.path.expanduser(
            f"{self.backup_folder}/{self.current_date}.tar.xz"
        )
        self.config_file_path = os.path.join(
            os.path.expanduser(self.backup_folder), "config_files", "config.json"
        )
        # encryption
        self.decrypt_file_path = os.path.join(self.backup_folder, "decrypted.tar.xz")
        # # size calculator
        # self.dirs_to_backup = []
        # self.ignore_list = []

    def ask_inputs(self):
        while True:
            print("=================================================")
            self.backup_folder = (
                input(
                    _(
                        "Which directory to save backups \n(Default: '~/Documents/backup-for-cloud/' if you leave it blank):"
                    )
                ).strip()
                or self.backup_folder
            )

            # Handling default values when input is left blank
            try:
                self.keep_backup = int(
                    input("Enter the number of backups to keep: ") or self.keep_backup
                )
                self.keep_enc_backup = int(
                    input("Enter the number of .enc backups to keep: ")
                    or self.keep_enc_backup
                )
                break  # Exiting the loop after collecting input
            except ValueError:
                print("Invalid input, please enter a valid integer.")

        print("\nNow let's configure the directories for backup.")
        self.configure_directories()

    def configure_directories(self):
        """Interactive method to add directories to backup and ignore lists."""
        print("=== Configure Directories to Backup ===")
        while True:
            print("\nCurrent directories to backup:")
            for idx, directory in enumerate(self.dirs_to_backup, start=1):
                print(f"{idx}. {directory}")
            print("\nOptions:")
            print("1. Add directories (separate multiple entries with commas)")
            print("2. Remove a directory")
            print("3. View ignore list")
            print("4. Modify ignore list")
            print("5. Finish and save")

            choice = input("Choose an option (1-5): ").strip()
            if choice == "1":
                dirs_input = input(
                    "Enter directories to add (separate multiple entries with commas): "
                ).strip()
                new_dirs = [d.strip() for d in dirs_input.split(",") if d.strip()]
                # Avoid duplicates and invalid entries
                added_dirs = [d for d in new_dirs if d not in self.dirs_to_backup]
                self.dirs_to_backup.extend(added_dirs)
                print(f"Added directories: {', '.join(added_dirs)}")
            elif choice == "2":
                print("Select a directory to remove:")
                for idx, directory in enumerate(self.dirs_to_backup, start=1):
                    print(f"{idx}. {directory}")
                try:
                    idx_to_remove = int(input("Enter the number to remove: ").strip())
                    if 0 < idx_to_remove <= len(self.dirs_to_backup):
                        removed_dir = self.dirs_to_backup.pop(idx_to_remove - 1)
                        print(f"Removed: {removed_dir}")
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
            elif choice == "3":
                print("Current ignore list:")
                for idx, path in enumerate(self.ignore_list, start=1):
                    print(f"{idx}. {path}")
            elif choice == "4":
                self.modify_ignore_list()
            elif choice == "5":
                self.save_credentials()
                print("Configuration saved.")
                break
            else:
                print("Invalid choice. Please try again.")

    def modify_ignore_list(self):
        """Interactive method to add or remove paths from the ignore list."""
        print("=== Modify Ignore List ===")
        while True:
            print("\nCurrent ignore list:")
            for idx, path in enumerate(self.ignore_list, start=1):
                print(f"{idx}. {path}")

            print("\nOptions:")
            print("1. Add ignore paths (separate multiple entries with commas)")
            print("2. Remove an ignore path")
            print("3. Finish and save")

            choice = input("Choose an option (1-3): ").strip()
            if choice == "1":
                ignore_input = input(
                    "Enter paths to ignore (separate multiple entries with commas): "
                ).strip()
                new_ignores = [p.strip() for p in ignore_input.split(",") if p.strip()]
                # Avoid duplicates and invalid entries
                added_ignores = [p for p in new_ignores if p not in self.ignore_list]
                self.ignore_list.extend(added_ignores)
                print(f"Added ignore paths: {', '.join(added_ignores)}")
            elif choice == "2":
                print("Select an ignore path to remove:")
                for idx, path in enumerate(self.ignore_list, start=1):
                    print(f"{idx}. {path}")
                try:
                    idx_to_remove = int(input("Enter the number to remove: ").strip())
                    if 0 < idx_to_remove <= len(self.ignore_list):
                        removed_path = self.ignore_list.pop(idx_to_remove - 1)
                        print(f"Removed from ignore list: {removed_path}")
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
            elif choice == "3":
                self.save_credentials()
                print("Ignore list updated and saved.")
                break
            else:
                print("Invalid choice. Please try again.")

    def save_credentials(self):
        """Save the credentials to a file in json format from response"""

        # Ensure the directory for the config file exists
        config_dir = os.path.dirname(self.config_file_path)
        os.makedirs(config_dir, exist_ok=True)

        config = {
            "backup_folder": self.backup_folder,
            "keep_backup": self.keep_backup,
            "keep_enc_backup": self.keep_enc_backup,
            "dirs_to_backup": self.dirs_to_backup,
            "ignore_list": self.ignore_list,
        }

        with open(self.config_file_path, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)

        print(f"Configuration file created at {self.config_file_path}")
        print(f"Updated number of backups to keep to {self.keep_backup}")
        print(f"Updated number of .enc backups to keep to {self.keep_enc_backup}")
        self.load_credentials()

    def load_credentials(self):
        """Load the credentials from a file and update the class attributes"""
        config_path = os.path.expanduser(self.config_file_path)

        if os.path.exists(config_path):
            with open(self.config_file_path, "r") as config_file:
                config = json.load(config_file)

            self.backup_folder = config.get("backup_folder", self.backup_folder)
            self.keep_backup = config.get("keep_backup", self.keep_backup)
            self.keep_enc_backup = config.get("keep_enc_backup", self.keep_enc_backup)
            self.dirs_to_backup = config.get("dirs_to_backup", self.dirs_to_backup)
            self.ignore_list = config.get("ignore_list", self.ignore_list)

            print(f"Configuration loaded from {self.config_file_path}")
            print(f"Backup folder set to {self.backup_folder}")
            print(f"Keep backup: {self.keep_backup}")
            print(f"Keep encrypted backup: {self.keep_enc_backup}")
            print(f"Directories to backup: {self.dirs_to_backup}")
            print(f"Ignore list: {self.ignore_list}")
        else:
            print(f"Configuration file {self.config_file_path} not found.")

    def check_backup_exist(self) -> bool:
        """Check if a backup file already exists for today"""
        return os.path.isfile(self.backup_file_path)

    def backup_directories(self) -> bool:
        """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

        if not self.dirs_to_backup:
            print(
                "No directories to backup. Create directories on the config.json. Look example config.json."
            )
            sys.exit()

        ignore_paths = [os.path.expanduser(path) for path in self.ignore_list]

        # Generate the exclude options for the tar command
        exclude_options = " ".join([f"--exclude={path}" for path in ignore_paths])

        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in self.dirs_to_backup]

        # Calculate the total size using SizeCalculator
        # size_calculator = BackupManager(self.dirs_to_backup, self.ignore_list)
        total_size_bytes = self.calculate_total_backup_size(dir_paths, ignore_paths)

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
            f"xz --threads={cpu_threads} > {self.backup_file_path}"
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
                if os.path.exists(self.backup_file_path):
                    current_size = os.path.getsize(self.backup_file_path)
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

    def list_backup_files(self, extension: str = ".tar.xz") -> List[str]:
        """List all backup files with the specified extension in the backup directory"""
        try:
            files = [f for f in os.listdir(self.backup_folder) if f.endswith(extension)]
            if not files:
                print("No backup files found.")
                return []
            for i, file in enumerate(files, start=1):
                print(f"{i}. {file}")
            return files
        except Exception as error:
            print(f"Error listing backup files: {type(error).__name__} - {error}")
            return []

    def extract_backup(self, file_to_extract: str) -> bool:
        """Extract the backup file to the specified directory"""
        date_str = os.path.basename(file_to_extract).split(".")[0]
        extract_to = os.path.join(self.backup_folder, f"{date_str}-extracted")
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)

        def filter_function(tarinfo, path):
            # Customize the tarinfo object here if needed
            return tarinfo

        try:
            with tarfile.open(file_to_extract, "r:xz") as tar:
                tar.extractall(path=extract_to, filter=filter_function)
            print(f"Backup extracted to {extract_to}")
            return True
        except (tarfile.TarError, FileNotFoundError, PermissionError) as error:
            print(f"Error extracting backup: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Extraction cancelled")
            sys.exit(0)

    ### EncryptionManager

    def encrypt_backup(self) -> bool:
        """Encrypt the backup file with openssl command"""
        password = getpass.getpass(prompt="Enter encryption password: ")

        # The encrypted backup file will be named with the current date
        file_to_encrypt = os.path.join(
            self.backup_folder, f"{self.current_date}.tar.xz.enc"
        )

        # Encrypt the backed up file with openssl command
        encrypt_cmd = [
            "openssl",
            "aes-256-cbc",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            self.backup_file_path,
            "-out",
            file_to_encrypt,
            "-pass",
            f"pass:{password}",
        ]

        try:
            subprocess.run(encrypt_cmd, check=True)
            logging.info("Encryption completed successfully")
            return True
        except subprocess.CalledProcessError as error:
            logging.error(f"Error encrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Encryption cancelled")
            sys.exit(0)

    def decrypt(self, file_to_decrypt: str) -> bool:
        """Decrypt the backup file"""
        password = getpass.getpass(prompt="Enter decryption password: ")

        # Decrypt the backup file with openssl command
        decrypt_cmd = [
            "openssl",
            "aes-256-cbc",
            "-d",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            file_to_decrypt,
            "-out",
            self.decrypt_file_path,
            "-pass",
            f"pass:{password}",
        ]

        try:
            subprocess.run(decrypt_cmd, check=True)
            time.sleep(1)
            logging.info("Decryption completed successfully")
            return True
        except subprocess.CalledProcessError as error:
            logging.error(f"Error decrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Decryption cancelled")
            sys.exit(0)

    def verify_decrypt_file(self, file_to_decrypt: str):
        """Verify the decrypted file is the same as the original file"""
        original_file_path = file_to_decrypt[:-4]

        # Compute the SHA256 checksum of the decrypted file
        hasher = hashlib.sha256()
        with open(self.decrypt_file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        actual_checksum = hasher.hexdigest()

        # Compute the SHA256 checksum of the original file
        hasher_original = hashlib.sha256()
        with open(original_file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher_original.update(data)
        expected_checksum = hasher_original.hexdigest()

        # Compare the checksums
        if actual_checksum == expected_checksum:
            logging.info("File integrity verified: checksums match")
        else:
            logging.error("File integrity check failed: checksums do not match")

    ### OLD DELETE

    def delete_old_backups(self):
        """Delete old backup files if there are more than 'keep_backup' files"""
        # List all backup files in the backup folder
        backup_files = [
            f
            for f in os.listdir(self.backup_folder)
            if re.match(r"\d{2}-\d{2}-\d{4}\.tar\.xz", f)
            or re.match(r"\d{2}-\d{2}-\d{4}\.tar\.xz\.enc", f)
        ]

        # Sort the backup files by date
        backup_files.sort(
            key=lambda x: datetime.datetime.strptime(x.split(".")[0], "%d-%m-%Y")
        )

        # Separate .xz and .xz.enc files
        xz_files = [f for f in backup_files if f.endswith(".tar.xz")]
        enc_files = [f for f in backup_files if f.endswith(".tar.xz.enc")]

        # Track deleted files to avoid duplicate deletions
        deleted_files = set()

        # Delete old backups if there are more than 'keep_backup'
        while len(xz_files) > self.keep_backup:
            old_backup = xz_files.pop(0)
            old_backup_path = os.path.join(self.backup_folder, old_backup)
            print(f"Attempting to delete: {old_backup_path}")
            try:
                os.remove(old_backup_path)
                deleted_files.add(old_backup)
                print(f"Deleted old backup: {old_backup}")
            except Exception as e:
                print(f"Failed to delete {old_backup_path}: {e}")

        # Delete old .enc files if there are more than 'keep_enc_backup'
        while len(enc_files) > self.keep_enc_backup:
            old_enc_backup = enc_files.pop(0)
            old_enc_backup_path = os.path.join(self.backup_folder, old_enc_backup)
            print(f"Attempting to delete: {old_enc_backup_path}")
            try:
                os.remove(old_enc_backup_path)
                deleted_files.add(old_enc_backup)
                print(f"Deleted old encrypted backup: {old_enc_backup}")
            except Exception as e:
                print(f"Failed to delete {old_enc_backup_path}: {e}")

        print("Old backup deletion process completed.")

    ### SIZE CALCULATOR

    def read_dirs_to_backup(self) -> List[str]:
        """Read the directories and files listed in dirs_to_backup.txt"""
        dirs_to_backup = []
        with open(self.dirs_to_backup, "r", encoding="utf-8") as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(os.path.expanduser(directory))
        return dirs_to_backup

    def read_ignore_list(self) -> List[str]:
        """Read the directories and files listed in ignore.txt"""
        ignore_list = []
        if os.path.isfile(self.ignore_list):
            with open(self.ignore_list, "r", encoding="utf-8") as file:
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
            self.dirs_to_backup
        )
        total_ignore_size = self.calculate_total_ignore_size(self.ignore_list)
        total_backup_size_excluding_ignored = self.calculate_total_backup_size(
            self.dirs_to_backup, self.ignore_list
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
