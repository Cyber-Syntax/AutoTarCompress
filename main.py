import os
import sys
import logging
from src import (
    ArchiveExtractor,
    BackupManager,
    Config,
    EncryptionManager,
    GarbageCollector,
    SizeCalculator,
    utils,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Backup the directories listed in dirs_to_backup.txt to a compressed file"""

    # Classes
    config = Config()
    size_calculator = SizeCalculator(config=config)
    archive_extractor = ArchiveExtractor(config=config)
    backup_manager = BackupManager(config=config, size_calculator=size_calculator)
    encryption_manager = EncryptionManager(config=config)
    garbage_collector = GarbageCollector(config=config)

    if not os.path.isfile(config.config_file_path):
        logging.info("Configuration file not found. Creating a new one.")
        config.ask_inputs()
        config.save_credentials()
    else:
        config.load_credentials()
        # Check if directories to backup are configured
        if not config.dirs_to_backup:
            logging.warning("No directories found in configuration. Setting up now.")
            config.configure_directories()

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
            encryption_manager.encrypt_backup()
        elif choice == 3:
            # List all encrypted files
            print("=====================================")
            print("Choose which file to decrypt: ")
            # List only encrypted files
            files = utils.list_backup_files(extension=".enc")

            if not files:
                continue

            choice = int(input("Enter your choice: "))

            # files[choice - 1] -> get file name from list files
            file_to_decrypt = os.path.join(config.backup_folder, files[choice - 1])
            encryption_manager.decrypt(file_to_decrypt)
            encryption_manager.verify_decrypt_file(file_to_decrypt)
        elif choice == 4:
            garbage_collector.delete_old_backups()
        elif choice == 5:
            # List all tar.xz files
            print("=====================================")
            print("Choose which backup file to extract: ")
            files = utils.list_backup_files(extension=".tar.xz")

            if not files:
                continue

            choice = int(input("Enter your choice: "))

            file_to_extract = os.path.join(config.backup_folder, files[choice - 1])
            archive_extractor.extract_backup(file_to_extract)
        elif choice == 6:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")
            return


if __name__ == "__main__":
    main()
