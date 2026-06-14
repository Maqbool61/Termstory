import os
import shutil
from datetime import datetime
from termstory.config import get_db_path


def _get_backup_dir() -> str:
    """Return the directory where backups are stored. Creates it if missing."""
    db_path = get_db_path()
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def backup_db() -> str:
    """Create a timestamped backup of the TermStory database.

    Returns:
        The absolute path to the created backup file.
    """
    db_path = get_db_path()
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"TermStory database not found at {db_path}")
    backup_dir = _get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"termstory_backup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def restore_db(backup_path: str) -> None:
    """Restore the TermStory database from a backup file.

    Args:
        backup_path: Absolute path to the backup .db file.
    """
    if not os.path.isfile(backup_path):
        raise FileNotFoundError(f"Backup file not found at {backup_path}")
    db_path = get_db_path()
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # Replace the current database with the backup (atomic replace)
    shutil.copy2(backup_path, db_path)
