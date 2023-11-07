import os
import subprocess
import hashlib
import datetime
import sys
import time
from tqdm import tqdm

class BackupManager:
    """ This script will backup the directories listed in dirs_to_backup.txt to a compressed file """

    def __init__(self, backup_folder):
        self.backup_folder = backup_folder

    def calculate_checksum(self, file_path):
        """ Calculate the checksum of a file """
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(65536)  # read in 64KB blocks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except (IOError, OSError) as e:
            print(f"Error calculating checksum: {e}")
            return None

    # check backup already exist for today
    def check_backup_exist(self):
        """ Check if a backup file already exists for today """

        date = datetime.datetime.now().strftime("%d-%m-%Y")
        backup_file_path = os.path.expanduser(f"{self.backup_folder}/{date}.tar.xz")
        return os.path.isfile(backup_file_path)
        
    def backup_directories(self, dirs_to_backup, ignore_file_path):
        """ Backup the directories listed in dirs_to_backup.txt to a compressed file """

        # Read in the directories to backup from the file
        dirs_to_backup = []
        with open(dirs_file_path, 'r') as file:
            for line in file:
                directory = line.strip()
                if directory:
                    dirs_to_backup.append(directory)

        # The backup file will be named with the current date
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        backup_file_path = os.path.expanduser(f"{self.backup_folder}/{date}.tar.xz")
        ignore = os.path.expanduser(ignore_file_path)

        # Exclude files and directories listed in the ignore file
        exclude_option = f"--exclude-from={ignore}"

        # Only backup files on the same filesystem as the backup folder
        filesystem_option = "--one-file-system"

        # Expand the user's home directory for each directory to backup
        dir_paths = [os.path.expanduser(path) for path in dirs_to_backup]

        # Create the tar command
        os_cmd = ["tar", "-cJf", backup_file_path, exclude_option, filesystem_option] + dir_paths

        # Run the tar command
        try:
            subprocess.run(os_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error compressing file: {e}")
        else:
            # Calculate the checksums of the backup file
            expected_checksum = self.calculate_checksum(backup_file_path)
            actual_checksum = self.calculate_checksum(backup_file_path)

            if expected_checksum is not None and actual_checksum is not None:
                if actual_checksum == expected_checksum:
                    print('File integrity verified: checksums match')
                else:
                    print('File integrity check failed: checksums do not match')
            else:
                print('File integrity check failed: could not calculate checksums')

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
        print(backup_file_path)
        print(file_to_encrypt)

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

        # Decrypt the backup file
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
    dirs_file_path = 'dirs_to_backup.txt'
    ignore_file_path = 'ignore.txt'
    # Classes
    backup_manager = BackupManager(backup_folder)
    encryption_manager = EncryptionManager(backup_folder)

    # Display the menu
    print("1.Backup")
    print("2.Encrypt")
    print("3.Decrypt")
    print("4.Exit")

    choice = int(input("Enter your choice: "))
    if choice == 1:
        # Check if a backup file already exists for today
        if backup_manager.check_backup_exist():
            print('Backup already exists for today')
            return
        # Backup the directories listed in dirs_to_backup.txt to a compressed file
        backup_manager.backup_directories(dirs_file_path, ignore_file_path)
    elif choice == 2:
        date = datetime.datetime.now().strftime("%d-%m-%Y")
        backup_file_path = os.path.expanduser(f"~/Documents/backup-for-cloud/{date}.tar.xz")
        encryption_manager.encrypt_backup(backup_file_path)
    elif choice == 3:
        print("Choose which file to decrypt: ")
        # List only encrypted files
        files = [f for f in os.listdir(backup_folder) if f.endswith('.enc')]

        for i in enumerate(files):
            print(i)
        choice = int(input("Enter your choice: "))

        file_to_decrypt = os.path.join(backup_folder, files[choice])
        encryption_manager.decrypt(file_to_decrypt)
        encryption_manager.verify_decrypt_file(file_to_decrypt)
    elif choice == 4:
        sys.exit()
    else:
        print("Invalid choice")
        return

if __name__ == "__main__":
    main()
