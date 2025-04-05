# json_backup.py

from typing import Union
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)


class FileBackupManager:
    def __init__(self, file_path: Union[str, Path], max_backups: int = 3):
        self.file_path = Path(file_path)
        self.max_backups = max_backups

    def _get_backup_name(self, index: int) -> Path:
        """Return the backup path using prompts_json.bak1 format."""
        if index == 0:
            return self.file_path
        stem = self.file_path.stem.replace('.', '_')
        return self.file_path.with_name(f"{stem}.bak{index}")

    def rotate_backups(self):
        """Rotate .bak1 → .bak2, ..., .bak{n-1} → .bak{n}"""
        for i in range(self.max_backups, 1, -1):  # e.g. 3 → 2, 2 → 1
            src = self._get_backup_name(i - 1)
            dst = self._get_backup_name(i)
            if src.exists():
                logger.debug(f"Rotating backup: {src} -> {dst}")
                src.replace(dst)  # .replace() handles overwrites safely

    def backup_current_file(self):
        """Copy the current JSON file to .bak1 if it exists."""
        if not self.file_path.exists():
            logger.info(f"🔸 No file to back up: {self.file_path}")
            return

        self.rotate_backups()  # Rotate .bak1 → .bak2, etc.
        shutil.copy2(self.file_path, self._get_backup_name(1))  # Only copy original, don't rename it
        logger.info(f"📁 Backed up {self.file_path} to {self._get_backup_name(1)}")
