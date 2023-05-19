import os
import subprocess
import hashlib
import datetime

""" This script will backup the directories listed in dirs_to_backup.txt to a compressed file """
class BackupManager:
    def __init__(self, backup_folder):
        self.backup_folder = backup_folder

    def calculate_checksum(self, file_path):                
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(65536)  # read in 64KB blocks
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error calculating checksum for {file_path}: {e}")
            return None

    def backup_directories(self, dirs_to_backup, ignore_file_path):        
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

def main():
    # Backup folder is the folder where the compressed backup files will be stored
    backup_folder = '~/Documents/backup-for-cloud'
    dirs_file_path = 'dirs_to_backup.txt'
    ignore_file_path = 'ignore.txt'

    backup_manager = BackupManager(backup_folder)

    # Read in the directories to backup from the file
    dirs_to_backup = []
    with open(dirs_file_path, 'r') as file:
        for line in file:
            directory = line.strip()
            if directory:  # Skip empty lines
                dirs_to_backup.append(directory)
    
    backup_manager.backup_directories(dirs_to_backup, ignore_file_path)

if __name__ == "__main__":
    main()
