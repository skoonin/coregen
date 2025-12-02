#!/bin/bash
# Simple Python detection script - finds Python 3.11+ on Mac/Linux

check_version() {
    local python="$1"
    if command -v "$python" >/dev/null 2>&1; then
        local python_path=$(command -v "$python")
        # Validate it's actually a file and executable
        if [ -f "$python_path" ] && [ -x "$python_path" ]; then
            version=$("$python_path" -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)' 2>/dev/null)
            # Validate version is numeric before comparison
            if [[ "$version" =~ ^[0-9]+$ ]] && [ "$version" -ge 311 ]; then
                echo "$python_path"
                exit 0
            fi
        fi
    fi
}

# Check in priority order - prefer Python 3.11 for consistency with Docker builds
[ -x ".venv/bin/python" ] && check_version ".venv/bin/python"
check_version "python3.11"
check_version "python3.12"
check_version "python3.13"
check_version "python3"
[ "$(uname)" = "Darwin" ] && check_version "/opt/homebrew/bin/python3"
[ "$(uname)" = "Darwin" ] && check_version "/usr/local/bin/python3"

echo "Error: Python 3.11+ not found. Please install Python 3.11 or later." >&2
exit 1
