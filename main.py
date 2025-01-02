import os
import subprocess
import datetime
from dataclasses import dataclass, field
from typing import List
from tqdm import tqdm
import sys
import time
from src.size_calculator import SizeCalculator
from src.old_delete import BackupDeletionManager


@dataclass
class BackupManager:
    backup_folder: str = os.path.expanduser("~/Documents/backup-for-cloud/")
    dirs_file_path: str = "dirs_to_backup.txt"
    current_date: str = datetime.datetime.now().strftime("%d-%m-%Y")
    backup_file_path: str = field(init=False)
    ignore_file_path: str = os.path.expanduser("ignore.txt")

    def __post_init__(self):
        self.backup_file_path = os.path.expanduser(
            f"{self.backup_folder}/{self.current_date}.tar.xz"
        )

    def check_backup_exist(self) -> bool:
        """Check if a backup file already exists for today"""
        return os.path.isfile(self.backup_file_path)

    def backup_directories(self) -> bool:
        """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

        # Read in the directories to backup from the file
        dirs_to_backup: List[str] = []
        with open(self.dirs_file_path, "r", encoding="utf-8") as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(directory)

        # Read and expand paths in the ignore file
        ignore_paths = []
        if os.path.isfile(self.ignore_file_path):
            with open(self.ignore_file_path, "r", encoding="utf-8") as file:
                for line in file:
                    ignore_path = line.strip()
                    if ignore_path:
                        ignore_paths.append(os.path.expanduser(ignore_path))

        # Generate the exclude options for the tar command
        exclude_options = " ".join([f"--exclude={path}" for path in ignore_paths])

        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in dirs_to_backup]

        # Calculate the total size using SizeCalculator
        size_calculator = SizeCalculator(self.dirs_file_path, self.ignore_file_path)
        total_size_bytes = size_calculator.calculate_total_backup_size(
            dirs_to_backup, size_calculator.ignore_list
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


@dataclass
class EncryptionManager(BackupManager):
    decrypt_file_path: str = os.path.expanduser(
        "~/Documents/backup-for-cloud/decrypted.tar.xz"
    )

    def encrypt_backup(self) -> bool:
        """Encrypt the backup file with openssl command"""

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
        ]

        try:
            # ask user for password, when user enter password, encrypt file
            subprocess.run(encrypt_cmd, check=True, input="password", encoding="ascii")
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            PermissionError,
            OSError,
            subprocess.TimeoutExpired,
            ValueError,
        ) as error:
            print(f"Error encrypting file: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Encryption cancelled")
            sys.exit(0)
        else:
            print("Encryption completed successfully")

    def decrypt(self, file_to_decrypt: str) -> bool:
        """Decrypt the backup file"""

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
        ]

        try:
            # ask user for password
            subprocess.run(decrypt_cmd, check=True, input="password", encoding="ascii")
            # Wait for the file to be decrypted
            time.sleep(1)
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            PermissionError,
            OSError,
            subprocess.TimeoutExpired,
            ValueError,
        ) as error:
            print(f"Error decrypting file: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Decryption cancelled")
            sys.exit(0)

    def verify_decrypt_file(self, file_to_decrypt: str):
        """Verify the decrypted file is the same as the original file"""

        # remove .enc from file_to_decrypt
        original_file_path = file_to_decrypt[:-4]

        # Compute the SHA256 checksum of the *decrypted file*
        hasher = hashlib.sha256()
        with open(self.decrypt_file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        actual_checksum = hasher.hexdigest()

        # Compute the SHA256 checksum of the *original file*
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
            print("File integrity verified: checksums match")
        else:
            print("File integrity check failed: checksums do not match")


def main():
    """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

    # Classes
    backup_manager = BackupManager()
    encryption_manager = EncryptionManager()
    deletion_manager = BackupDeletionManager()

    # Create a loop that will run until the user enters 4 to exit
    while True:
        # Display the menu
        print("=====================================")
        print("Select an option:")
        print("1.Backup")
        print("2.Encrypt")
        print("3.Decrypt")
        print("4.Delete Old Backups")
        print("5.Exit")
        print("=====================================")
        try:
            choice = int(input("Enter your choice: "))
        except (ValueError, TypeError, NameError, AttributeError, IndexError) as error:
            print(f"Error: {type(error).__name__} - {error}")
            print("Please enter a number between 1 and 5.")
            continue
        except KeyboardInterrupt:
            print("Exiting...")
            sys.exit(0)

        if choice == 1:
            # Check if a backup file already exists for today
            if backup_manager.check_backup_exist():
                print("Backup already exists for today")
                continue
            # Backup the directories listed in dirs_to_backup.txt to a compressed file
            success = backup_manager.backup_directories()
            if success:
                print("Backup was successful.")
            else:
                print("Backup failed.")
        elif choice == 2:
            encryption_manager.encrypt_backup()
        elif choice == 3:
            # List all encrypted files
            print("=====================================")
            print("Choose which file to decrypt: ")
            # List only encrypted files
            files = [
                f
                for f in os.listdir(backup_manager.backup_folder)
                if f.endswith(".enc")
            ]

            for i, file in enumerate(files, start=1):
                print(f"{i}. {file}")
            print("=====================================")
            choice = int(input("Enter your choice: "))

            # files[choice - 1] -> get file name from list files
            file_to_decrypt = os.path.join(
                backup_manager.backup_folder, files[choice - 1]
            )
            encryption_manager.decrypt(file_to_decrypt)
            encryption_manager.verify_decrypt_file(file_to_decrypt)
        elif choice == 4:
            deletion_manager.delete_old_backups()
        elif choice == 5:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")
            return


if __name__ == "__main__":
    main()
