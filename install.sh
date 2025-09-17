#!/usr/bin/env bash
#
# autotarcompress-installer.sh
# ------------------------------------------------
# User-level installer & updater for "autotarcompress"
# - Copies project files into XDG user data directory (~/.local/share)
# - Creates/updates a Python virtual environment
# - Installs a wrapper script in ~/.local/bin for easy command execution
# - Ensures ~/.local/bin is in PATH for both bash and zsh shells
#
# Usage:
#   ./autotarcompress-installer.sh install   # Install or reinstall
#   ./autotarcompress-installer.sh update    # Update venv without touching files
#
# Exit immediately if:
# - a command exits with a non-zero status (`-e`)
# - an unset variable is used (`-u`)
# - a pipeline fails anywhere (`-o pipefail`)
set -euo pipefail

# -- Configuration -----------------------------------------------------------

# Where user-specific data should be stored
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

# Final install location of our project
INSTALL_DIR="$XDG_DATA_HOME/autotarcompress"

# Virtual environment directory inside install dir
VENV_DIR="$INSTALL_DIR/venv"

# Virtual environment bin folder (where python/pip are located)
BIN_DIR="$VENV_DIR/bin"

# Source of our wrapper script (inside repo)
WRAPPER_SRC="$INSTALL_DIR/scripts/venv-wrapper.sh"

# Destination of wrapper script in user's PATH
WRAPPER_DST="$HOME/.local/bin/autotarcompress"

# The line to add to shell rc files to ensure ~/.local/bin is in PATH
EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'

# -- Helper functions --------------------------------------------------------

# Get absolute directory path of currently running script (resolves symlinks)
script_dir() {
  local src="${BASH_SOURCE[0]}"
  while [ -h "$src" ]; do
    src="$(readlink "$src")"
  done
  dirname "$src"
}

# Function to print colored output for autocomplete
print_status() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Detect which shell rc file to update for PATH (bash or zsh)
detect_rc_file() {
  local rc user_shell
  user_shell="$(basename "${SHELL:-}")"
  case "$user_shell" in
    zsh)
      rc="$HOME/.zshrc"
      [[ -f "$HOME/.config/zsh/.zshrc" ]] && rc="$HOME/.config/zsh/.zshrc"
      ;;
    bash)
      rc="$HOME/.bashrc"
      ;;
    *)
      rc="$HOME/.bashrc"
      ;;
  esac
  # Create the file if it doesn't exist
  [[ ! -f "$rc" ]] && touch "$rc"
  echo "$rc"
}

# Ensure PATH line is present in a given file
# $1 = rc file path
# $2 = position (optional: prepend|append, default append)
ensure_path_in_file() {
  local rc_file="$1"
  local position="${2:-append}"
  
  [[ ! -f "$rc_file" ]] && touch "$rc_file"
  
  if ! grep -Fxq "$EXPORT_LINE" "$rc_file"; then
    if [[ "$position" == "prepend" ]]; then
      # Put PATH export at the very top
      {
        echo "# Added by autotarcompress installer"
        echo "$EXPORT_LINE"
        echo
        cat "$rc_file"
      } > "$rc_file.tmp" && mv "$rc_file.tmp" "$rc_file"
      echo "Added PATH to top of $rc_file"
    else
      # Add PATH export at the bottom
      printf "\n# Added by autotarcompress installer\n$EXPORT_LINE\n" >> "$rc_file"
      echo "Added PATH to bottom of $rc_file"
    fi
  else
    echo "ℹ️ PATH already configured in $rc_file"
  fi  
}

# Ensure PATH is set for both bash and zsh shells
# - Prepend for bashrc so it’s loaded before anything else
# - Append for zshrc so it runs after bashrc in login shell chains
ensure_path_for_shells() {
  local bashrc="$HOME/.bashrc"
  local zshrc="$HOME/.zshrc"
  
  [[ -f "$HOME/.config/zsh/.zshrc" ]] && zshrc="$HOME/.config/zsh/.zshrc"
  
  ensure_path_in_file "$bashrc" prepend
  ensure_path_in_file "$zshrc" append
}

# Copy source files to install directory
copy_source_to_install_dir() {
  echo "📁 Copying source files to $INSTALL_DIR..."
  local src_dir
  src_dir="$(script_dir)"
  mkdir -p "$INSTALL_DIR"

  # Source files to copy
  for item in autotarcompress scripts autocomplete pyproject.toml "$(basename "$0")"; do
    local src_path="$src_dir/$item"
    local dst_path="$INSTALL_DIR/$item"
    if [ -e "$src_path" ]; then
      if [ -d "$src_path" ]; then
        rm -rf "$dst_path"
        cp -r "$src_path" "$dst_path"
      else
        cp "$src_path" "$dst_path"
      fi
    else
      echo "⚠️  Warning: $item not found in $src_dir"
    fi
  done
}

# Create or update virtual environment and install package in editable mode
setup_venv() {
  echo "🐍 Creating/updating virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
  source "$BIN_DIR/activate"
  python3 -m pip install --upgrade pip wheel
  echo "📦 Installing autotarcompress (editable) into venv..."
  python3 -m pip install -e "$INSTALL_DIR"
}

# Install wrapper script into ~/.local/bin so `autotarcompress` works globally
install_wrapper() {
  echo "🔧 Installing wrapper to $WRAPPER_DST..."
  mkdir -p "$(dirname "$WRAPPER_DST")"
  cp "$WRAPPER_SRC" "$WRAPPER_DST"
  chmod +x "$WRAPPER_DST"
}

# Full installation process
install_autotarcompress() {
  echo "=== Installing autotarcompress ==="
  copy_source_to_install_dir
  setup_venv
  install_wrapper
  ensure_path_for_shells
  
  local rc
  rc=$(detect_rc_file)

  echo "✅ Installation complete."
  echo "Restart your shell or run 'source $rc' to apply PATH."
  echo "Run 'autotarcompress' to get started."
}

# Update only the virtual environment, keep existing files
update_autotarcompress() {
  echo "=== Updating autotarcompress ==="
  setup_venv
  echo "✅ Update complete."
}

# -- Autocomplete functions --------------------------------------------------

# Function to install bash completion
install_bash_completion() {
    print_status "Installing Bash completion..."
    
    local bash_autocomplete_src="$INSTALL_DIR/autocomplete/bash_autocomplete"
    
    # Check if source file exists
    if [[ ! -f "$bash_autocomplete_src" ]]; then
        print_error "Bash autocomplete file not found: $bash_autocomplete_src"
        return 1
    fi

    # Add to bashrc
    if ! grep -q "source.*bash_autocomplete" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# AutoTarCompress completion" >> ~/.bashrc
        echo "source \"$bash_autocomplete_src\"" >> ~/.bashrc
        print_status "Bash completion added to ~/.bashrc"
    else
        print_warning "Bash completion already exists in ~/.bashrc"
    fi
}

# Determine if user uses .config/zsh
determine_zsh_config_dir() {
    if [[ -d "${XDG_CONFIG_HOME:-$HOME/.config}/zsh" ]]; then
        echo "${XDG_CONFIG_HOME:-$HOME/.config}/zsh"
    elif [[ -d "$HOME/.config/zsh" ]]; then
        echo "$HOME/.config/zsh"
    else
        echo "$HOME/.zsh"
    fi
}

# Function to install zsh completion
install_zsh_completion() {
    print_status "Installing Zsh completion..."

    local zsh_autocomplete_src="$INSTALL_DIR/autocomplete/zsh_autocomplete"
    
    # Check if source file exists
    if [[ ! -f "$zsh_autocomplete_src" ]]; then
        print_error "Zsh autocomplete file not found: $zsh_autocomplete_src"
        return 1
    fi

    # Determine zsh config directory
    local zsh_config_dir
    zsh_config_dir=$(determine_zsh_config_dir)
    print_status "Using zsh config directory: $zsh_config_dir"
    
    # Create user completion directory if it doesn't exist
    mkdir -p "$zsh_config_dir/completions"
    
    # Copy completion file
    cp "$zsh_autocomplete_src" "$zsh_config_dir/completions/_autotarcompress"
    print_status "Zsh completion installed to $zsh_config_dir/completions/_autotarcompress"

    # Update zshrc if needed. Ensure fpath is present BEFORE any compinit call
    local rc_file="$zsh_config_dir/.zshrc"
    # Ensure rc_file exists
    touch "$rc_file"

    local comment_line="# Added by AutoTarCompress to enable shell completion"
    local fpath_line="fpath=($zsh_config_dir/completions \$fpath)"

    # If exact fpath line already exists, do nothing. Otherwise insert it
    if grep -qF "$fpath_line" "$rc_file" 2>/dev/null; then
        print_status "fpath already configured in $rc_file"
    else
        if grep -q "compinit" "$rc_file" 2>/dev/null; then
            # Insert comment + fpath line just before the first compinit occurrence
            awk -v cl="$comment_line" -v fl="$fpath_line" 'BEGIN{printed=0} { if(!printed && $0 ~ /compinit/){ print cl; print fl; printed=1 } print } END{ if(!printed){ print cl; print fl } }' "$rc_file" > "$rc_file.tmp" && mv "$rc_file.tmp" "$rc_file"
            print_status "Inserted fpath (with comment) before compinit in $rc_file"
        else
            # Prepend comment + fpath to the top of the file
            printf "%s\n%s\n\n%s\n" "$comment_line" "$fpath_line" "$(cat "$rc_file")" > "$rc_file.tmp" && mv "$rc_file.tmp" "$rc_file"
            print_status "Prepended fpath (with comment) to $rc_file"
        fi
    fi

    # Ensure compinit is present; if it's missing, append it (after fpath)
    if ! grep -q "autoload.*compinit" "$rc_file" 2>/dev/null; then
        echo "" >> "$rc_file"
        echo "# Added by AutoTarCompress: enable shell completion" >> "$rc_file"
        echo "autoload -Uz compinit && compinit" >> "$rc_file"
        print_status "Added compinit to $rc_file"
    else
        print_status "compinit already configured in $rc_file"
    fi
}

# Function to detect shell and install appropriate completion
install_completion() {
    local shell_name
    shell_name=$(basename "$SHELL")
    
    case "$shell_name" in
        bash)
            install_bash_completion
            ;;
        zsh)
            install_zsh_completion
            ;;
        *)
            print_error "Unsupported shell: $shell_name"
            print_status "Supported shells: bash, zsh"
            print_status "You can manually install completion by following the instructions in README.md"
            exit 1
            ;;
    esac
}

# Main autocomplete installation function
install_autocomplete() {
    print_status "AutoTarCompress Autocomplete Installation"
    print_status "========================================"
    
    # Check if AutoTarCompress is installed
    if [[ ! -d "$INSTALL_DIR" ]]; then
        print_error "AutoTarCompress is not installed. Please run './install.sh install' first."
        exit 1
    fi
    
    # Check if completion files exist
    if [[ ! -f "$INSTALL_DIR/autocomplete/bash_autocomplete" ]] || [[ ! -f "$INSTALL_DIR/autocomplete/zsh_autocomplete" ]]; then
        print_error "Completion files not found in $INSTALL_DIR/autocomplete/"
        exit 1
    fi
    
    # Check if user wants to install for specific shell
    if [[ $# -eq 1 ]]; then
        case "$1" in
            bash)
                install_bash_completion
                ;;
            zsh)
                install_zsh_completion
                ;;
            both)
                install_bash_completion
                install_zsh_completion
                ;;
            *)
                print_error "Invalid option: $1"
                print_status "Usage: $0 autocomplete [bash|zsh|both]"
                exit 1
                ;;
        esac
    else
        # Auto-detect and install for current shell
        install_completion
    fi
    
    print_status ""
    print_status "Installation complete!"

    # Notify user to restart shell or source rc files
    if [[ "$(basename "$SHELL")" == "zsh" ]]; then
        local zshrc
        zshrc=$(determine_zsh_config_dir)/.zshrc
        print_status "Please restart your shell or run 'source \"$zshrc\"' to enable autocompletion."
    elif [[ "$(basename "$SHELL")" == "bash" ]]; then
        print_status "Please restart your shell or run 'source ~/.bashrc' to enable autocompletion."
    else
        print_status "Please restart your shell or source the appropriate rc file to enable autocompletion."
    fi 
    print_status ""
    print_status "Test completion by typing: autotarcompress <TAB>"
}

# -- Entry point -------------------------------------------------------------
case "${1-}" in
  install|"") install_autotarcompress ;;
  update) update_autotarcompress ;;
  autocomplete) 
    shift
    install_autocomplete "$@" 
    ;;
  *)
    cat <<EOF
Usage: $(basename "$0") [install|update|autocomplete]

Commands:
  install       Copy source, setup venv, install wrapper, configure PATH
  update        Update venv only
  autocomplete  Install shell completion [bash|zsh|both]

Examples:
  $(basename "$0") install                    # Full installation
  $(basename "$0") update                     # Update virtual environment
  $(basename "$0") autocomplete               # Auto-detect shell and install completion
  $(basename "$0") autocomplete bash          # Install bash completion only
  $(basename "$0") autocomplete zsh           # Install zsh completion only
  $(basename "$0") autocomplete both          # Install for both shells
EOF
    exit 1
    ;;
esac
