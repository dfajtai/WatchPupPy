import os
import time
import shutil
from threading import Lock
from typing import Optional, List, Callable

from .pattern_matcher import PatternMatcher
from .utils import current_time_str, md5_for_file


class BackupManager:
    def __init__(self, backup_folder: str, max_versions: Optional[int] = None) -> None:
        self.backup_folder = backup_folder
        self.max_versions = max_versions
        self.lock = Lock()

    def backup_file(self, filepath: str) -> None:
        with self.lock:
            try:
                os.makedirs(self.backup_folder, exist_ok=True)
                timestamp = current_time_str()
                dest_dir = os.path.join(self.backup_folder, timestamp)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(filepath, os.path.join(dest_dir, os.path.basename(filepath)))
                self._prune_old_backups()
            except Exception as e:
                print(f"Backup failed for {filepath}: {e}")

    def _prune_old_backups(self) -> None:
        if self.max_versions is None:
            return
        try:
            backups = sorted(os.listdir(self.backup_folder))
            while len(backups) > self.max_versions:
                oldest = backups.pop(0)
                shutil.rmtree(os.path.join(self.backup_folder, oldest))
        except Exception as e:
            print(f"Backup pruning failed: {e}")


class FolderWatcher:
    def __init__(
        self,
        watch_folder: str,
        backup_manager: BackupManager,
        interval_seconds: int = 60,
        filename_patterns: Optional[List[str]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        self.watch_folder = watch_folder
        self.backup_manager = backup_manager
        self.interval_seconds = interval_seconds
        self.pattern_matcher = PatternMatcher(filename_patterns)
        self._running = False
        self._last_mtimes = {}
        self._log_callback = log_callback

    def _log(self, message: str) -> None:
        if self._log_callback:
            self._log_callback(message)
        else:
            print(message)

    def _matches(self, filename: str) -> bool:
        return self.pattern_matcher.matches(filename)

    def _get_latest_backup_dir(self) -> Optional[str]:
        try:
            dirs = [d for d in os.listdir(self.backup_manager.backup_folder)
                    if os.path.isdir(os.path.join(self.backup_manager.backup_folder, d))]
            if not dirs:
                return None
            latest_dir = sorted(dirs)[-1]
            return os.path.join(self.backup_manager.backup_folder, latest_dir)
        except Exception:
            return None

    def _initialize_backup_state(self) -> None:
        """
        Initializes the backup state by synchronizing the current watched folder files
        with the latest backup. For each matched file in the watch folder, computes the MD5
        hash and compares it with the corresponding file's hash in the latest backup directory.
        If no previous backup exists or the file is missing/different in the backup, it copies
        the file to the backup folder. Updates the internal last modified times map accordingly.
        """
        latest_backup_dir = self._get_latest_backup_dir()
        if latest_backup_dir is None:
            self._log("Initial synchronization: no previous backup found.")
        else:
            self._log(f"Initial synchronization: latest backup directory is {latest_backup_dir}")

        current_files = {}
        # Compute MD5 hashes for matched files in the watch directory
        for root, _, files in os.walk(self.watch_folder):
            for fname in files:
                if not self._matches(fname):
                    continue
                fpath = os.path.join(root, fname)
                md5_current = md5_for_file(fpath)
                current_files[fpath] = md5_current

        # If no backups exist, back up all current files
        if latest_backup_dir is None:
            for fpath, md5_cur in current_files.items():
                self._log(f"Backup (no previous): {fpath}")
                self.backup_manager.backup_file(fpath)
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
            return

        # Check each current file against the latest backup and back up if missing or changed
        for fpath, md5_cur in current_files.items():
            target_dir = latest_backup_dir
            target_path = os.path.join(target_dir, os.path.basename(fpath))
            if not os.path.exists(target_path):
                self._log(f"Missing backup file -> Copying: {fpath} -> {target_dir}")
                self.backup_manager.backup_file(fpath)
            else:
                md5_target = md5_for_file(target_path)
                if md5_target != md5_cur:
                    self._log(f"Difference detected -> Updating: {fpath} (MD5: {md5_target} -> {md5_cur})")
                    self.backup_manager.backup_file(fpath)
                else:
                    self._log(f"File matches backup: {fpath}")
            self._last_mtimes[fpath] = os.path.getmtime(fpath)
            
    
    def start(self) -> None:
        self._initialize_backup_state()
        self._running = True
        self._log("WatchPuppPy started watching.")

        sync_interval = self.interval_seconds
        control_interval = 1

        elapsed = 0
        while self._running:
            if elapsed >= sync_interval:
                try:
                    for root, dirs, files in os.walk(self.watch_folder):
                        for fname in files:
                            if not self._matches(fname):
                                continue
                            fpath = os.path.join(root, fname)
                            try:
                                mtime = os.path.getmtime(fpath)
                            except OSError:
                                continue
                            last_mtime = self._last_mtimes.get(fpath)
                            if last_mtime is None or mtime > last_mtime:
                                md5_current = md5_for_file(fpath)
                                latest_backup_dir = self._get_latest_backup_dir()
                                backup_file_path = None
                                md5_backup = None
                                if latest_backup_dir is not None:
                                    backup_file_path = os.path.join(latest_backup_dir, os.path.basename(fpath))
                                    if os.path.exists(backup_file_path):
                                        md5_backup = md5_for_file(backup_file_path)

                                if md5_backup != md5_current:
                                    self._log(f"Backing up updated file: {fpath}")
                                    self.backup_manager.backup_file(fpath)
                                    self._last_mtimes[fpath] = mtime
                except Exception as e:
                    self._log(f"Watcher error: {e}")
                elapsed = 0
            time.sleep(control_interval)
            elapsed += control_interval

        self._log("WatchPuppPy stopped watching.")

    def stop(self) -> None:
        self._running = False
