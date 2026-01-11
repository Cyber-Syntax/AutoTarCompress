# **AutoTarCompress**

> [!CAUTION]
>
> - This project is in a **beta phase** due to limited testing at this time.
> - **Important:** Follow the instructions in the **Releases section** when updating the script.
> - **Supported OS:** Currently, only Linux is supported.
>

## **📖 Overview**

> [!NOTE]
>
> AutoTarCompress is a robust backup and archive management tool that provides both command-line interface (CLI) and interactive menu functionality for creating, encrypting, and managing backup archives.
>
> - Detailed information: [wiki.md](docs/wiki.md)

Turkish: [README.tr.md](README.tr.md)

## **✨ Features**

- **Create compressed backups** using tar and zstd compression
- **Encrypt/decrypt backups** with AES-256-GCM authenticated encryption
- **Extract backup archives** to restore files
- **Clean up old backups** with configurable retention policies
- **Backup information display** showing file details and metadata
- **🆕 Command-line interface** for scriptable automation
- **Interactive menu** for user-friendly operation
- **Configurable backup directories** and ignore patterns
- **Progress bar with ETA** for backup and extraction operations
- **Logging and error handling** for reliable operation

---

## **💡 Installation**

1. Open a terminal and clone this repo (make sure you have git installed):

```bash
git clone https://github.com/Cyber-Syntax/AutoTarCompress.git
```

1. Navigate to the project directory:

```bash
cd AutoTarCompress
```

1. Make executable and run the install script:

```bash
chmod +x install.sh

# for production use
./install.sh uv-prod
# for development use
./install.sh uv-dev
```

1. After installation, restart your shell or run:

```bash
source ~/.bashrc   # or ~/.zshrc
```

1. Go to configuration file and set your preferences:

```bash
vim ~/.config/autotarcompress/config.conf
```

1. (Optional) Enable shell autocompletion for bash or zsh:

```bash
# Auto detect your shell and install autocomplete
sh install.sh autocomplete

# Or manually install for bash/zsh
sh install.sh autocomplete bash
sh install.sh autocomplete zsh
```

---

## **🚀 Usage**

AutoTarCompress now offers two ways to use it:

### **🔥 New: Command-Line Interface (Recommended for automation)**

The CLI provides scriptable access to all backup operations:

```bash
# Show all available commands
autotarcompress --help

# Create a backup
autotarcompress backup

# Encrypt the latest backup
autotarcompress encrypt --latest

# Encrypt a backup from a specific date
autotarcompress encrypt --date 15-01-2024

# Encrypt a specific backup file
autotarcompress encrypt backup_15-01-2024_10-30-45.tar.xz

# Decrypt the latest encrypted backup
autotarcompress decrypt --latest

# Extract the latest backup
autotarcompress extract --latest

# Clean up old backups (uses config defaults)
autotarcompress cleanup

# Clean up keeping only 5 most recent backups
autotarcompress cleanup --keep 5

# Show last backup information
autotarcompress info
```

### **📋 Interactive Menu (Original experience)**

For users who prefer an interactive experience:

```bash
autotarcompress interactive
```

Or simply run without arguments (default behavior):

```bash
autotarcompress
```

---

## **📚 CLI Commands Overview**

AutoTarCompress provides the following commands:

- `backup` — Create a backup archive
- `encrypt` — Encrypt a backup file
- `decrypt` — Decrypt an encrypted backup file
- `extract` — Extract a backup archive
- `cleanup` — Remove old backups
- `info` — Show information about the last backup
- `interactive` — Launch the interactive menu (legacy mode)

For detailed options, usage examples, configuration, and migration notes, see [docs/wiki.md](docs/wiki.md).

### Quick Example

```bash
autotarcompress backup
autotarcompress encrypt --latest
autotarcompress cleanup --keep 7
autotarcompress info
```

See the [wiki](docs/wiki.md) for advanced usage and full documentation.

## **🙏 Support This Project**

If this script has been helpful:

- **Consider giving it a star ⭐** on GitHub to show your support and keep me motivated on my coding journey!
- **💖 Support This Project:** If you'd like to support my work and help me continue learning and building projects, consider sponsoring me:
    - [![Sponsor Me](https://img.shields.io/badge/Sponsor-💖-brightgreen)](https://github.com/sponsors/Cyber-Syntax)
