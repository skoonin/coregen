#!/bin/bash
# Script to find and clean resolved commit directories from coregen contexts

set -euo pipefail

# Function to show usage
usage() {
    echo "Usage: $0 [--dry-run|--clean] [--config|-c CONFIG_FILE]"
    echo "  --dry-run    Show what would be cleaned (default)"
    echo "  --clean      Actually remove the directories"
    echo "  --config,-c  Path to .cgconfig.yaml file (auto-detected if not provided)"
    exit 1
}

# Parse arguments
DRY_RUN=true
CONFIG_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        --clean|-c)
            DRY_RUN=false
            shift
            ;;
        --config|-cf)
            if [[ $# -lt 2 ]]; then
                echo "Error: --config requires a file path"
                usage
            fi
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

# Store original directory
ORIGINAL_DIR="$(pwd)"

# Handle config file and working directory
if [[ -n "$CONFIG_FILE" ]]; then
    # Config file provided - validate it exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "Error: Config file not found: $CONFIG_FILE"
        exit 1
    fi

    # Keep the original relative path instead of converting to absolute
    echo "Using config file: $CONFIG_FILE"
else
    # Auto-detect config file in current directory
    if [[ -f ".cgconfig.yaml" ]]; then
        CONFIG_FILE=".cgconfig.yaml"
        echo "Found config file: $CONFIG_FILE"
    elif [[ -f "test_data/.cgconfig.yaml" ]]; then
        CONFIG_FILE="test_data/.cgconfig.yaml"
        echo "Found config file: $CONFIG_FILE"
    else
        echo "Warning: No .cgconfig.yaml found in current directory or test_data/"
        echo "Proceeding without specific config file..."
    fi
fi

# Find coregen command - check installed version first, then development mode
if command -v coregen >/dev/null 2>&1; then
    echo "Using installed coregen..."
    COREGEN_CMD="coregen"
elif [[ -f "source/coregen/__main__.py" ]]; then
    echo "Using development installation..."
    COREGEN_CMD="python3 -m coregen"
else
    echo "Error: No coregen installation found. Please run 'pip install -e .' or 'make setup' first."
    exit 1
fi

# Build coregen command with config file if specified
COREGEN_CMD_WITH_CONFIG="$COREGEN_CMD"
if [[ -n "$CONFIG_FILE" ]]; then
    COREGEN_CMD_WITH_CONFIG="$COREGEN_CMD --config-file $CONFIG_FILE"
fi

# Get all contexts and their resolved commit_dir paths
echo "Getting resolved commit directories from coregen contexts..."
COMMIT_DIRS=()

# Use coregen config view enhanced to get resolved configuration with paths
if ! CONFIG_JSON=$($COREGEN_CMD_WITH_CONFIG config view enhanced -o json 2>/dev/null); then
    echo "Error: Failed to get config from coregen"
    echo "Command attempted: $COREGEN_CMD_WITH_CONFIG config view enhanced -o json"
    exit 1
fi

# Extract commit_dir values from each context in the config
# The JSON structure should have contexts with commit_dir fields
while IFS= read -r line; do
    if [[ $line =~ \"commit_dir\":[[:space:]]*\"([^\"]+)\" ]]; then
        commit_dir="${BASH_REMATCH[1]}"
        if [[ -n "$commit_dir" && "$commit_dir" != "null" ]]; then
            COMMIT_DIRS+=("$commit_dir")
        fi
    fi
done <<< "$CONFIG_JSON"

if [[ ${#COMMIT_DIRS[@]} -eq 0 ]]; then
    echo "No generated directories found in coregen contexts."
    exit 0
fi

# Remove duplicates and sort
if [[ ${#COMMIT_DIRS[@]} -gt 0 ]]; then
    # Manual approach for compatibility
    TEMP_DIRS=()
    while IFS= read -r dir; do
        TEMP_DIRS+=("$dir")
    done < <(printf '%s\n' "${COMMIT_DIRS[@]}" | sort -u)
    COMMIT_DIRS=("${TEMP_DIRS[@]}")
fi

echo "Found resolved commit directories from coregen contexts:"
EXISTING_DIRS=()
for dir in "${COMMIT_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "  EXISTS: $dir"
        EXISTING_DIRS+=("$dir")
    else
        echo "  MISSING: $dir"
    fi
done

if [[ ${#EXISTING_DIRS[@]} -eq 0 ]]; then
    echo "No existing generated directories found."
    exit 0
fi

echo

if [[ "$DRY_RUN" == true ]]; then
    echo "DRY RUN - Would remove ${#EXISTING_DIRS[@]} existing generated directories"
    echo "Run with --clean to actually remove them"
else
    echo "CLEANING - Removing ${#EXISTING_DIRS[@]} existing generated directories..."
    for dir in "${EXISTING_DIRS[@]}"; do
        echo "  Removing: $dir"
        rm -rf "$dir"
    done
    echo "✓ Cleanup complete"
fi
