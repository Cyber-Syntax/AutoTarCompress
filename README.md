Turkish: [README.tr.md](https://github.com/Cyber-Syntax/AutoTarCompress/blob/main/README.tr.md)

---

> [!CAUTION]
>
> - This project is in a **beta phase** due to limited testing at this time.
> - **Important:** Follow the instructions in the **Releases section** when updating the script.
> - **Supported OS:** Currently, only Linux is supported.

---

# **About AutoTarCompress**

> [!NOTE]
> AutoTarCompress is a command-line tool for Linux that simplifies the process of creating and managing compressed backups of your important directories. It offers features like compressing, encryption, decryption.
>
> - Detailed information: [wiki.md](docs/wiki.md)

---

## **💡 How to Use**

1. Open a terminal and clone this repo (make sure you have git installed):

```bash
git clone https://github.com/Cyber-Syntax/AutoTarCompress.git
```

2. Navigate to the project directory:

```bash
cd AutoTarCompress
```

cd AutoTarCompress
chmod +x install.sh
./install.sh

3. Make executable and run the install script:

```bash
chmod +x install.sh && ./install.sh
```

4. After installation, restart your shell or run:

```bash
source ~/.bashrc   # or ~/.zshrc
```

5. Configure

Copy the example config and edit as needed:

```bash
mkdir -p ~/.config/autotarcompress
cp config_files_example/config.json ~/.config/autotarcompress/config.json
# Edit ~/.config/autotarcompress/config.json to match your needs
```

Or, just run the tool and follow the prompts to generate a config interactively.

## Run the script

```bash
autotarcompress
```

Follow the on-screen instructions to create, encrypt, or extract backups.

---

## **🙏 Support This Project**

If this script has been helpful:

- **Consider giving it a star ⭐** on GitHub to show your support and keep me motivated on my coding journey!
- **💖 Support This Project:** If you'd like to support my work and help me continue learning and building projects, consider sponsoring me:
    - [![Sponsor Me](https://img.shields.io/badge/Sponsor-💖-brightgreen)](https://github.com/sponsors/Cyber-Syntax)
