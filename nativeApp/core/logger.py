# core/logger.py
# ===========================================================================
# TerraSimLogger — Persistent Session Logging & Journaling
# ===========================================================================
# Manages real-time log rotation and persistent storage in AppData.
# Ensures that console output and state changes are durable.
# ===========================================================================

import os
import sys
import glob
from datetime import datetime
from PySide6.QtCore import QStandardPaths, QDir

class TerraSimLogger:
    _instance = None

    @classmethod
    def instance(cls, max_files: int = 5):
        if cls._instance is None:
            cls._instance = cls(max_files)
        return cls._instance

    def __init__(self, max_files: int = 5):
        self.max_files = max_files
        # 1. Resolve AppData/Local path
        # Typically: C:/Users/<user>/AppData/Local/DaharEngineer/TerraSim/logs
        self.base_dir = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        self.log_dir = os.path.join(self.base_dir, "logs")
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

        # 2. Rotate existing logs (Keep max_files-1 to make room for current session)
        self._rotate_logs("console", self.max_files)
        self._rotate_logs("journal", self.max_files)

        # 3. Create NEW files for this session
        self.console_file_path = self._get_next_filename("console")
        self.journal_file_path = self._get_next_filename("journal")

        # Open handles with line buffering (buffering=1) for real-time safety
        self.console_handle = open(self.console_file_path, "a", encoding="utf-8", buffering=1)
        self.journal_handle = open(self.journal_file_path, "a", encoding="utf-8", buffering=1)

        self.log_console(f"--- Session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        self.log_journal(f"--- Session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    def _rotate_logs(self, prefix: str, max_files: int):
        """Removes the oldest files if more than (max_files-1) exist."""
        pattern = os.path.join(self.log_dir, f"{prefix}_*.txt")
        files = glob.glob(pattern)
        if len(files) >= max_files:
            # Sort by name (sequential naming 00001, 00002 makes this easy)
            files.sort()
            # Delete until we have (max_files - 1) left
            to_delete = files[:len(files) - (max_files - 1)]
            for f in to_delete:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"[Logger] Failed to rotate {f}: {e}")

    def _get_next_filename(self, prefix: str) -> str:
        """Finds the highest existing index and returns the next one."""
        pattern = os.path.join(self.log_dir, f"{prefix}_*.txt")
        files = glob.glob(pattern)
        max_idx = 0
        for f in files:
            try:
                # Extract XXXXX from prefix_XXXXX.txt
                basename = os.path.basename(f)
                idx_str = basename.replace(f"{prefix}_", "").replace(".txt", "")
                max_idx = max(max_idx, int(idx_str))
            except:
                continue
        
        next_idx = max_idx + 1
        return os.path.join(self.log_dir, f"{prefix}_{next_idx:05d}.txt")

    def log_console(self, message: str):
        """Append a message to the console session log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.console_handle.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"[Logger] Console Write Error: {e}")

    def log_journal(self, action: str):
        """Append a state-change action to the journal session log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.journal_handle.write(f"[{timestamp}] ACTION: {action}\n")
        except Exception as e:
            print(f"[Logger] Journal Write Error: {e}")

    def close(self):
        """Clean up handles."""
        if hasattr(self, "console_handle"): self.console_handle.close()
        if hasattr(self, "journal_handle"): self.journal_handle.close()
