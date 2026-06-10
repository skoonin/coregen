# Troubleshooting Dependency Issues

## Pydantic Import Error

### Symptom

If you see this error:

```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

### Solution

This is typically caused by a mismatch between `pydantic` and `pydantic-core` versions. Fix it with:

```bash
# Reinstall both packages
pip install --force-reinstall pydantic pydantic-core

# Reinstall the package in development mode
pip install -e .
```

## Virtual Environment Issues

If you experience problems with the virtual environment during `make setup`, you can manually execute these steps instead:

```bash
# Create and configure virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .
pip install -e .[dev]
pip install -e .

# Create symlink
ln -sf "$(pwd)/source/coregen/__main__.py" "$(pwd)/cg"
chmod +x "$(pwd)/cg"
```

## Other Common Issues

### Package Conflicts

If you're seeing unexplained import errors or version conflicts, try:

```bash
pip freeze > requirements.backup.txt  # Backup your current environment
pip uninstall -y -r <(pip freeze)     # Remove all packages
pip install -e .       # Reinstall required packages
pip install -e .[dev]   # Reinstall dev packages
pip install -e .                      # Reinstall package in dev mode
```
