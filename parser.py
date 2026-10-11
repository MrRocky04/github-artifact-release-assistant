"""Local artifact discovery helpers."""

import os
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "$Recycle.Bin",
    "System Volume Information",
    "Windows",
    "Program Files",
    "Program Files (x86)",
}


def find_artifact(artifact_name: str):
    """Search common locations and drives for an exact artifact filename."""
    artifact_name = artifact_name.strip()
    if not artifact_name:
        return None

    current_directory = Path.cwd()
    home_directory = Path.home()

    search_roots = [
        current_directory,
        home_directory / "Desktop",
        home_directory / "Downloads",
        home_directory / "Documents",
        home_directory,
    ]

    seen = set()
    for root in search_roots:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        if resolved in seen or not root.exists():
            continue
        seen.add(resolved)

        result = search_directory(root, artifact_name)
        if result:
            return result

    if os.name == "nt":
        import string

        for drive_letter in string.ascii_uppercase:
            drive = Path(f"{drive_letter}:\\")
            if not drive.exists() or drive.drive == home_directory.drive:
                continue
            print(f"\nSearching drive: {drive}")
            result = search_directory(drive, artifact_name)
            if result:
                return result
    else:
        result = search_directory(Path("/"), artifact_name)
        if result:
            return result

    return None


def search_directory(directory: Path, artifact_name: str):
    """Recursively search a directory for an exact artifact filename."""
    target_name = artifact_name.lower()

    try:
        for root, dirs, files in os.walk(directory, topdown=True):
            dirs[:] = [
                name for name in dirs
                if name not in IGNORED_DIRECTORIES
            ]

            for file_name in files:
                if file_name.lower() == target_name:
                    return Path(root) / file_name
    except (PermissionError, OSError):
        pass

    return None
