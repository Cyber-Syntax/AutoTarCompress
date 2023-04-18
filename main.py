import subprocess
from datetime import datetime
import os


backup_folder = os.path.expanduser('~/Documents/backup-for-cloud/')

# Timestamp
now = datetime.now()
date = now.strftime("%d-%m-%Y")

def compress_backup_dirs():
    try:          
        with open(f"{backup_folder}/ignore.txt", "r") as f:    
            print(f"Files to ignore: {f.read()}")        
        print(f"Files to compress: {dirs_to_backup}")        
        
        if input(f"Compress {dirs_to_backup} to {backup_folder}{date}.tar.xz? [y/n]: ").lower() != "y":
            return False                
        
        os_cmd = ["tar", "-cJf", f"{backup_folder}/{date}.tar.xz", "--exclude-from", f"{backup_folder}/ignore.txt", *dirs_to_backup]
        subprocess.call(" ".join(os_cmd), shell=True)
    
    except Exception as e:
        print(f"Error compressing file: {e}")
        return False

if __name__ == "__main__":
    compress_backup_dirs()
