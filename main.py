""" This script will backup with tar command and encrypt, decrypt with openssl command"""
import os
import subprocess
import hashlib
import datetime
import sys
import time

class BackupManager:
    """ This class will backup the directories listed in dirs_to_backup.txt to a compressed file """

    def __init__(self):
        self.backup_folder = os.path.expanduser("~/Documents/backup-for-cloud/")
        self.dirs_file_path = 'dirs_to_backup.txt'
        self.current_date = datetime.datetime.now().strftime("%d-%m-%Y")
        self.backup_file_path = os.path.expanduser(
                                f"{self.backup_folder}/{self.current_date}.tar.xz")
        self.ignore_file_path = os.path.expanduser('ignore.txt')

    # check backup already exist for today
    def check_backup_exist(self):
        """ Check if a backup file already exists for today """
        return os.path.isfile(self.backup_file_path)

    def backup_directories(self):
        """ Backup the directories listed in dirs_to_backup.txt to a compressed file """

        # Read in the directories to backup from the file
        dirs_to_backup = []
        with open(self.dirs_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(directory)

        # Exclude files and directories listed in the ignore file
        exclude_option = (f"--exclude-from={self.ignore_file_path}"
                            if os.path.isfile(self.ignore_file_path)
                            else f"--exclude={self.ignore_file_path}")

        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in dirs_to_backup]

        # Create the tar command with tqdm progress bar
        total_size = sum(entry.stat().st_size
                        for path in dir_paths
                        for entry in os.scandir(path)
                        if entry.is_file()
        )

        print(f"Total size: {total_size} bytes")

        # Get the number of CPU threads for xz compression
        cpu_threads = os.cpu_count() - 1
        print(f"CPU threads - 1: {cpu_threads}")

        # Create the tar command with tqdm progress bar
        os_cmd = (
            f"tar -cf - {filesystem_option} {exclude_option} {' '.join(dir_paths)} | "
            f"xz --threads={cpu_threads} | "
            f"tqdm --bytes --total {total_size} --desc Processing | gzip | "
            f"tqdm --bytes --total {total_size} "
            f"--desc Compressing > {self.backup_file_path}"
        )

        # Run the tar command
        try:
            subprocess.run(os_cmd, check=True, shell=True)
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError, OSError,
                ValueError) as error:
            print(f"Error backing up files: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Backup cancelled")
            sys.exit(0)
        else:
            print("Backup completed successfully")
            return True

# EncryptionManager inherits from BackupManager
class EncryptionManager(BackupManager):
    """ This script will encrypt the backup file with openssl command"""
    def __init__(self):
        # Call the __init__() method of the parent class
        super().__init__()
        self.decrypt_file_path = os.path.expanduser("~/Documents/backup-for-cloud/decrypted.tar.xz")

    def encrypt_backup(self):
        """ Encrypt the backup file with openssl command"""

        # The encrypted backup file will be named with the current date
        file_to_encrypt = os.path.join(self.backup_folder, f"{self.current_date}.tar.xz.enc")

        # Encrypt the backed up file with openssl command
        encrypt_cmd = ["openssl", "aes-256-cbc", "-a", "-salt", "-pbkdf2", "-in",
                        self.backup_file_path, "-out", file_to_encrypt]

        try:
            # ask user for password, when user enter password, encrypt file
            subprocess.run(encrypt_cmd, check=True, input="password", encoding="ascii")
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError,
                OSError, subprocess.TimeoutExpired, ValueError) as error:
            print(f"Error encrypting file: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Encryption cancelled")
            sys.exit(0)
        else:
            print("Encryption completed successfully")

        return True

    def decrypt(self, file_to_decrypt):
        """ Decrypt the backup file """

        # Decrypt the backup file with openssl command
        decrypt_cmd = ["openssl", "aes-256-cbc", "-d", "-a", "-salt",
                        "-pbkdf2", "-in", file_to_decrypt, "-out", self.decrypt_file_path]

        try:
            # ask user for password
            subprocess.run(decrypt_cmd, check=True, input="password", encoding="ascii")
            # Wait for the file to be decrypted
            time.sleep(1)
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError, OSError,
                subprocess.TimeoutExpired,ValueError) as error:
            print(f"Error decrypting file: {type(error).__name__} - {error}")
            return False
        except KeyboardInterrupt:
            print("Decryption cancelled")
            sys.exit(0)
        else:
            print("Decryption completed successfully")

        return True

    def verify_decrypt_file(self, file_to_decrypt):
        """ Verify the decrypted file same with original file """

        # remove .enc from file_to_decrypt
        original_file_path = file_to_decrypt[:-4]

        # Compute the SHA256 checksum of the *decrypted file*
        hasher = hashlib.sha256()
        with open(self.decrypt_file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        actual_checksum = hasher.hexdigest()

        # Compute the SHA256 checksum of the *original file*
        hasher_orginal = hashlib.sha256()
        with open(original_file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher_orginal.update(data)
        expected_checksum = hasher_orginal.hexdigest()

        # Compare the checksums
        if actual_checksum == expected_checksum:
            print('File integrity verified: checksums match')
        else:
            print('File integrity check failed: checksums do not match')

def main():
    """ Backup the directories listed in dirs_to_backup.txt to a compressed file """

    # Classes
    backup_manager = BackupManager()
    encryption_manager = EncryptionManager()

    # Create a loop that will run until the user enters 4 to exit
    while True:
        # Display the menu
        print("=====================================")
        print("Select an option:")
        print("1.Backup")
        print("2.Encrypt")
        print("3.Decrypt")
        print("4.Exit")
        print("=====================================")
        try:
            choice = int(input("Enter your choice: "))
        except (ValueError, TypeError, NameError, AttributeError,
                IndexError) as error:
            print(f"Error: {type(error).__name__} - {error}")
            print("Please enter a number between 1 and 4.")
            continue
        except KeyboardInterrupt:
            print("Exiting...")
            sys.exit(0)

        if choice == 1:
            # Check if a backup file already exists for today
            if backup_manager.check_backup_exist():
                print('Backup already exists for today')
                continue
            # Backup the directories listed in dirs_to_backup.txt to a compressed file
            backup_manager.backup_directories()
        elif choice == 2:
            encryption_manager.encrypt_backup()

        elif choice == 3:
            # List all encrypted files
            print("=====================================")
            print("Choose which file to decrypt: ")
                    # List only encrypted files
            files = [f for f in os.listdir(backup_manager.backup_folder) if f.endswith('.enc')]

            for i, file in enumerate(files, start=1):
                print(f"{i}. {file}")
            print("=====================================")
            choice = int(input("Enter your choice: "))

            # files[choice - 1] -> get file name from list files
            file_to_decrypt = os.path.join(backup_manager.backup_folder, files[choice - 1])
            encryption_manager.decrypt(file_to_decrypt)
            encryption_manager.verify_decrypt_file(file_to_decrypt)
        elif choice == 4:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")
            return

if __name__ == "__main__":
    main()
