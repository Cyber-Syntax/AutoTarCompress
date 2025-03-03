[![en](https://img.shields.io/badge/lang-en-green.svg)](https://github.com/Cyber-Syntax/AutoTarCompress/blob/main/README.md)
[![tr](https://img.shields.io/badge/lang-tr-blue.svg)](https://github.com/Cyber-Syntax/AutoTarCompress/blob/main/README.tr.md)

---

# **⚠️ Attention**

- **This project is in a beta phase** due to limited testing at this time.. Although primarily developed for learning purposes, it effectively addresses my specific needs.
- **Important:** Follow the instructions in the **Releases section** when updating the script. Updates may include new features or changes that could require different steps. I’ll strive to keep the instructions as simple as possible.
- **Currently supported:** Linux only. While it might work on macOS, it has not been tested yet.

---

## **About AutoTarCompress**

- The script compresses specific directories into tar files (e.g., 01-01-2025.tar.xz) and is able to encrypt them using the OpenSSL Python library.
- It also allows for decryption and extraction of the created files.

---

## **💡 How to Use**

1. Open a terminal and clone this repo (make sure you have git installed):

   ```bash
   cd ~/Downloads &
   git clone https://github.com/Cyber-Syntax/AutoTarCompress.git
   ```

2. Navigate to the project directory:

   ```bash
   cd ~/Downloads/Cyber-Syntax/AutoTarCompress
   ```

3. **Optional: Create a virtual environment (Recommended)**

   - Create a virtual environment:
     - `python3 -m venv .venv`
   - Activate the virtual environment:
     - `source .venv/bin/activate`
   - Install dependencies using `pip`:
     - `pip install -r requirements.txt`
   - If this doesn't work, install manually (some of them may already be installed; exclude those if you encounter an error again).
     - `pip3 install tqdm`

4. Activate the virtual environment (if applicable):

   ```bash
   source .venv/bin/activate
   ```

5. Config File Handling:

   - To customize your backup settings, you need to use a `config.json` file. This file allows you to specify:
     - Backup folder location, Directories to back up, Directories to ignore, Number of tar.xz and tar.xz.enc files to keep
   - **Creating a Config File:**
     - You have two options:
       1. **Use an example config file (Recommended)**:
          - Copy the example configuration from `config_files_example/config.json`
          - Paste it into your `backup_folder/config_files/config.json` location (e.g `~/Documents/backup-for-cloud/config_files/config.json`)
          - Modify it as needed
       2. **Run the script and follow the on-screen instructions**.
          - This will guide you through creating a `config.json` file.

6. Start the script:

   ```bash
   python3 main.py
   ```

7. Follow the on-screen instructions.

---

## **🙏 Support This Project**

If this script has been helpful:

- **Consider giving it a star ⭐** on GitHub to show your support and keep me motivated on my coding journey!
- **💖 Support This Project:** If you'd like to support my work and help me continue learning and building projects, consider sponsoring me:
  - [![Sponsor Me](https://img.shields.io/badge/Sponsor-💖-brightgreen)](https://github.com/sponsors/Cyber-Syntax)

### **🤝 Contributing**

- This project is primarily a learning resource for me, but I appreciate any feedback or suggestions! While I can't promise to incorporate all contributions or maintain active involvement, I’m open to improvements and ideas that align with the project’s goals.
- Anyway, please refer to the [CONTRIBUTING.md](.github/CONTRIBUTING.md) file for more detailed explanation.

---

## **📝 License**

This script is licensed under the [GPL 3.0 License]. You can find a copy of the license in the [LICENSE](https://github.com/Cyber-Syntax/my-unicorn/blob/main/LICENSE) file or at [www.gnu.org](https://www.gnu.org/licenses/gpl-3.0.en.html).

---
