"""Platform detection and normalization utilities."""

import platform
import sys


class Platform:
    """Unified platform detection and normalization."""

    @staticmethod
    def get_os() -> str:
        """Get normalized OS name.

        Returns:
            'darwin' for macOS, 'linux' for Linux, 'windows' for Windows
        """
        system = platform.system().lower()
        return system

    @staticmethod
    def get_arch() -> str:
        """Get normalized architecture name.

        Returns:
            'amd64' for x86_64, 'arm64' for ARM64/aarch64
        """
        machine = platform.machine().lower()

        # Normalize architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }

        return arch_map.get(machine, machine)

    @staticmethod
    def get_platform() -> str:
        """Get full platform string.

        Returns:
            Platform string in format 'os_arch' (e.g., 'darwin_arm64')
        """
        return f"{Platform.get_os()}_{Platform.get_arch()}"

    @staticmethod
    def is_darwin() -> bool:
        """Check if running on macOS."""
        return sys.platform == "darwin"

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return sys.platform.startswith("linux")

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return sys.platform == "win32"

    @staticmethod
    def get_python_version() -> tuple[int, int, int]:
        """Get Python version as tuple."""
        return sys.version_info[:3]

    @staticmethod
    def has_python_min_version(major: int = 3, minor: int = 11) -> bool:
        """Check if Python meets minimum version requirement."""
        current = Platform.get_python_version()
        return current[0] > major or (current[0] == major and current[1] >= minor)
