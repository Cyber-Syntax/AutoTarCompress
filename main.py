import os
import sys
import logging
from src.backup_manager import BackupFacade, DecryptCommand, ExtractCommand, EncryptCommand

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def select_file(files: list, backup_folder: str) -> str:
    """Helper function to select a file from a list"""
    for idx, file in enumerate(files, start=1):
        print(f"{idx}. {file}")
    choice = int(input("Enter your choice: ")) - 1
    return os.path.join(backup_folder, files[choice])


def main():
    """Main application entry point"""
    facade = BackupFacade()
    
    # Initial configuration check
    if not os.path.exists(facade.config.config_path):
        logging.info("No configuration found. Starting initial setup.")
        facade.configure()
    else:
        logging.info("Loading existing configuration")
        facade.config = facade.config.load()

    while True:
        print("\n===== Backup Manager =====")
        print("1. Perform Backup")
        print("2. Encrypt Backup File")
        print("3. Decrypt Backup")
        print("4. Cleanup Old Backups")
        print("5. Extract Backup")
        print("6. Exit")
        
        try:
            choice = input("Enter your choice (1-6): ").strip()
            if choice == "6":
                print("Exiting...")
                sys.exit(0)

            choice = int(choice)
            if choice < 1 or choice > 6:
                raise ValueError
                
        except ValueError:
            print("Invalid input. Please enter a number between 1-6.")
            continue

        try:
            if choice == 1:
                facade.execute_command('backup')
            elif choice == 2:
                # List available backup files
                backup_files = [
                    f for f in os.listdir(facade.config.backup_folder)
                    if f.endswith('.tar.xz') and not f.endswith('.enc')
                ]
                if not backup_files:
                    print("No backup files available for encryption")
                    continue
                selected = select_file(backup_files, facade.config.backup_folder)
                EncryptCommand(facade.config, selected).execute()
            elif choice == 3:
                enc_files = [
                    f for f in os.listdir(facade.config.backup_folder) 
                    if f.endswith('.enc')
                ]
                if not enc_files:
                    print("No encrypted backups found")
                    continue
                selected = select_file(enc_files, facade.config.backup_folder)
                DecryptCommand(facade.config, selected).execute()
            elif choice == 4:
                facade.execute_command('cleanup')
            elif choice == 5:
                backup_files = [
                    f for f in os.listdir(facade.config.backup_folder)
                    if f.endswith('.tar.xz') and not f.endswith('.enc')
                ]
                if not backup_files:
                    print("No backup files found")
                    continue
                selected = select_file(backup_files, facade.config.backup_folder)
                ExtractCommand(facade.config, selected).execute()
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logging.error(f"Operation failed: {str(e)}")


if __name__ == "__main__":
    main()
