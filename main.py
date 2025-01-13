import os
import sys
import logging
from src.backup_manager import BackupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

    # Classes
    backup_manager = BackupManager()

    if not os.path.isfile(backup_manager.config_file_path):
        logging.info("Configuration file not found. Creating a new one.")
        backup_manager.ask_inputs()
        backup_manager.save_credentials()
    else:
        backup_manager.load_credentials()
        # Check if directories to backup are configured
        if not backup_manager.dirs_to_backup:
            logging.warning("No directories found in configuration. Setting up now.")
            backup_manager.configure_directories()

    # Create a loop that will run until the user enters 6 to exit
    while True:
        # Display the menu
        print("=====================================")
        print("Select an option:")
        print("1.Backup")
        print("2.Encrypt")
        print("3.Decrypt")
        print("4.Delete Old Backups")
        print("5.Extract Backup Files")
        print("6.Exit")
        print("=====================================")
        try:
            choice = int(input("Enter your choice: "))
        except (ValueError, TypeError, NameError, AttributeError, IndexError) as error:
            print(f"Error: {type(error).__name__} - {error}")
            print("Please enter a number between 1 and 6.")
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
            backup_manager.encrypt_backup()
        elif choice == 3:
            # List all encrypted files
            print("=====================================")
            print("Choose which file to decrypt: ")
            # List only encrypted files
            files = backup_manager.list_backup_files(extension=".enc")

            if not files:
                continue

            choice = int(input("Enter your choice: "))

            # files[choice - 1] -> get file name from list files
            file_to_decrypt = os.path.join(
                backup_manager.backup_folder, files[choice - 1]
            )
            backup_manager.decrypt(file_to_decrypt)
            backup_manager.verify_decrypt_file(file_to_decrypt)
        elif choice == 4:
            backup_manager.delete_old_backups()
        elif choice == 5:
            # List all tar.xz files
            print("=====================================")
            print("Choose which backup file to extract: ")
            files = backup_manager.list_backup_files(extension=".tar.xz")

            if not files:
                continue

            choice = int(input("Enter your choice: "))

            file_to_extract = os.path.join(
                backup_manager.backup_folder, files[choice - 1]
            )
            backup_manager.extract_backup(file_to_extract)
        elif choice == 6:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")
            return


if __name__ == "__main__":
    main()
