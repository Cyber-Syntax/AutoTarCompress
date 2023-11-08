""" This script will backup with tar command and encrypt, decrypt with openssl command"""
import os
import subprocess
import hashlib
import datetime
import sys
import time
import tarfile
from tqdm import tqdm

class BackupManager:
    """ This class will backup the directories listed in dirs_to_backup.txt to a compressed file """

    def __init__(self, backup_folder):
        self.backup_folder = backup_folder
        self.dirs_file_path = 'dirs_to_backup.txt'

    # check backup already exist for today
    def check_backup_exist(self):
        """ Check if a backup file already exists for today """

        date = datetime.datetime.now().strftime("%d-%m-%Y")
        backup_file_path = os.path.expanduser(f"{self.backup_folder}/{date}.tar.xz")
        return os.path.isfile(backup_file_path)

    def verify_tar_file(self, backup_file_path):
        """ Verify that a tar file contains all expected files """

        with tarfile.open(backup_file_path, 'r') as tar:
            # Get a list of all the files in the tar file
            files_in_tar = tar.getnames()

            # Read in the directories to backup from the file
            dirs_to_backup = []
            with open(self.dirs_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    directory = line.strip()
                    if directory:
                        dirs_to_backup.append(directory)

            # Get a list of all the files in the directories to backup
            files_to_backup = []
            for directory in dirs_to_backup:
                for root, files in os.walk(directory):
                    for name in files:
                        file_path = os.path.join(root, name)
                        files_to_backup.append(file_path)

            # Sort the lists
            files_in_tar.sort()
            files_to_backup.sort()

            # Compare the lists
            for content in zip(files_in_tar, files_to_backup):
                if content[0] != content[1]:
                    print(f"File {content[0]} is missing from the backup")
                    return False

            return True

    def backup_directories(self, ignore_file_path):
        """ Backup the directories listed in dirs_to_backup.txt to a compressed file """

        # Read in the directories to backup from the file
        dirs_to_backup = []
        with open(self.dirs_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(directory)

        # The backup file will be named with the current date
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        backup_file_path = os.path.expanduser(f"{self.backup_folder}/{date}.tar.xz")

        # Exclude files and directories listed in the ignore file
        ignore = os.path.expanduser(ignore_file_path)
        exclude_option = f"--exclude-from={ignore}"
        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in dirs_to_backup]

        # Create the tar command with tqdm progress bar
        total_size = sum(os.path.getsize(os.path.join(d,f)) for d in dir_paths for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)))
        os_cmd = ["tar", "-caf", "-", filesystem_option, exclude_option] + dir_paths + ["|", "pv", "-s", str(total_size), ">", backup_file_path]

        os_cmd_str = " ".join(os_cmd)

        # Create progress bar
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="Backup") as pbar:
            def handle_output(line):
                pbar.update(len(line))

            # Run the tar command
            try:
                process = subprocess.Popen(os_cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
                                           universal_newlines=True, text=True)
                for line in iter(process.stdout.readline, ''):
                    handle_output(line)
                process.stdout.close()
                process.wait()                
            except subprocess.CalledProcessError as e:
                print(f"Error compressing file: {e}")
                return False
            except KeyboardInterrupt:
                print("Backup cancelled")
                sys.exit(0)
        
        # Verify that the tar file contains all expected files
        if not self.verify_tar_file(backup_file_path):
            print("Backup failed: tar file does not contain all expected files")
            return False

# EncryptionManager inherits from BackupManager
class EncryptionManager:
    """ This script will encrypt the backup file """
    def __init__(self, backup_folder):
        self.backup_folder = backup_folder
        self.decrypt_file_path = os.path.expanduser("~/Documents/backup-for-cloud/decrypted.tar.xz")

    # Encrypt the tar backup file
    def encrypt_backup(self, backup_file_path):
        """ Encrypt the backup file """

        # The encrypted backup file will be named with the current date
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        file_to_encrypt = os.path.join(self.backup_folder, f"{date}.tar.xz.enc")

        # Encrypt the backup file
        encrypt_cmd = ["openssl", "aes-256-cbc", "-a", "-salt", "-pbkdf2", "-in", backup_file_path, "-out",
                          file_to_encrypt]

        try:
            # ask user for password, when user enter password, encrypt file
            subprocess.run(encrypt_cmd, check=True, input="password", encoding="ascii")
        except subprocess.CalledProcessError as cp_error:
            print(f"Error encrypting file: {cp_error}")
            return False

        return True

    def decrypt(self, file_to_decrypt):
        """ Decrypt the backup file """

        decrypt_cmd = ["openssl", "aes-256-cbc", "-d", "-a", "-salt", "-pbkdf2", "-in", file_to_decrypt, "-out",
                            self.decrypt_file_path]
        try:
            # ask user for password
            subprocess.run(decrypt_cmd, check=True, input="password", encoding="ascii")
            # Wait for the file to be decrypted
            time.sleep(1)
        except subprocess.CalledProcessError as cp_error:
            print(f"Error decrypting file: {cp_error}")
            return False

        return True

    def verify_decrypt_file(self, file_to_decrypt):
        """ Verify the decrypted file same with original file """

        # remove .enc from file_to_decrypt
        original_file_path = file_to_decrypt[:-4]

        # Compute the SHA256 checksum of the decrypted file
        hasher = hashlib.sha256()
        with open(self.decrypt_file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        actual_checksum = hasher.hexdigest()

        # Compute the SHA256 checksum of the original file
        hasher_enc = hashlib.sha256()
        with open(original_file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher_enc.update(data)
        expected_checksum = hasher_enc.hexdigest()

        # Compare the checksums
        if actual_checksum == expected_checksum:
            print('File integrity verified: checksums match')
        else:
            print('File integrity check failed: checksums do not match')


def main():
    """ Backup the directories listed in dirs_to_backup.txt to a compressed file """

    # File paths
    backup_folder = os.path.expanduser("~/Documents/backup-for-cloud/")
    ignore_file_path = 'ignore.txt'
    # Classes
    backup_manager = BackupManager(backup_folder)
    encryption_manager = EncryptionManager(backup_folder)

    # Create a loop that will run until the user enters 4 to exit
    while True:
        # Display the menu
        print("1.Backup")
        print("2.Encrypt")
        print("3.Decrypt")
        print("4.Exit")
        try:
            choice = int(input("Enter your choice: "))

        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
        if choice == 1:
            # Check if a backup file already exists for today
            if backup_manager.check_backup_exist():
                print('Backup already exists for today')
                continue
            # Backup the directories listed in dirs_to_backup.txt to a compressed file
            backup_manager.backup_directories(ignore_file_path)
        elif choice == 2:
            date = datetime.datetime.now().strftime("%d-%m-%Y")
            backup_file_path = os.path.expanduser(f"~/Documents/backup-for-cloud/{date}.tar.xz")
            encryption_manager.encrypt_backup(backup_file_path)
        elif choice == 3:
            print("Choose which file to decrypt: ")
            # List only encrypted files
            files = [f for f in os.listdir(backup_folder) if f.endswith('.enc')]

            for i, file in enumerate(files, start=1):
                print(f"{i}. {file}")
            choice = int(input("Enter your choice: "))

            file_to_decrypt = os.path.join(backup_folder, files[choice])
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