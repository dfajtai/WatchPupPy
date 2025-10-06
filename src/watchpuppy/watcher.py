"""
Module for file backup and folder watching with version control and secure preservation.

This module provides two main classes:

- BackupManager: Manages file backups into timestamped folders with rolling version control.
  It preserves files that would otherwise be deleted by maintaining a special 'FINAL' folder
  containing secured backups and a JSON log with file metadata (timestamp and MD5 checksums).

- FolderWatcher: Monitors a specified folder for file changes and new files matching given 
  patterns. It performs periodic scans to detect updates or new files and triggers backups 
  accordingly. Supports initialization based on the latest backup or the FINAL snapshot, and 
  optionally watches for new files created during runtime.

Features:
- Thread-safe backup operations with lock protection.
- Rolling backups with configurable max versions; older backups are pruned safely.
- FINAL folder snapshot with detailed JSON logging to avoid data loss.
- MD5-based file integrity checks minimize redundant backups.
- Modular, extensible design for easy maintenance and feature enhancements.
- Configurable log callbacks for integration with UI or logging frameworks.

Usage:
- Instantiate BackupManager with backup folder and max_versions.
- Instantiate FolderWatcher with watch folder, BackupManager, and other options.
- Start the FolderWatcher to begin monitoring and automatic backup.

This module is suitable for applications that require reliable file change monitoring 
and versioned backup management with data preservation guarantees.
"""

import os
import time
import shutil
import datetime
import json
from threading import Lock
from typing import Optional, List, Callable

from .pattern_matcher import PatternMatcher
from .utils import current_time_str, md5_for_file


class BackupManager:
    """
    Manages file backups with version control and a special FINAL folder for data preservation.

    This class handles the creation of timestamped backup folders, enforces a maximum number
    of backup versions with safe pruning, and ensures that files potentially deleted due to
    rolling backup limits are preserved in a dedicated FINAL folder. It maintains a JSON log
    containing metadata (timestamp and MD5 hash) of all files stored in the FINAL folder to
    verify file integrity and support incremental updates.

    Attributes:
        backup_folder (str): Base directory path for storing backups.
        max_versions (Optional[int]): Maximum number of backup versions to keep; if exceeded,
                                      oldest backups are pruned after preservation.
        final_folder (str): Path to the FINAL subfolder within backup_folder for preserving
                            files that would be removed by pruning.
        final_log_file (str): Path to a JSON file tracking metadata of files in the FINAL folder.
        lock (Lock): Thread-safe lock to serialize access to backup operations.

    Methods:
        backup_file(filepath): Backs up a given file to a new timestamped folder.
        backup_file_to_final(filepath): Backs up a file directly into the FINAL folder and updates the log.
        _prune_old_backups(): Enforces max_versions limit by deleting old backups after preserving files.
        _preserve_files_in_final(backup_path): Copies files from a backup folder into FINAL with logging.
        _load_final_log(): Loads the JSON metadata log for FINAL files.
        _save_final_log(data): Saves the JSON metadata log for FINAL files.
        merge_final_on_demand(): Consolidates all backup folders into FINAL, refreshing the log.

    This class is designed for use alongside FolderWatcher to reliably monitor and back up
    file changes while protecting data from loss due to rotation of backup versions.
    """

    def __init__(self, backup_folder: str, max_versions: Optional[int] = None) -> None:
        """
        Initialize the BackupManager with backup folder and optional version limit.

        Args:
            backup_folder (str): Path to the backup directory.
            max_versions (Optional[int]): Maximum backup versions to retain. Pass None for unlimited.
        """
        self.backup_folder = backup_folder
        self.max_versions = max_versions
        self.final_folder = os.path.join(self.backup_folder, "FINAL")
        self.final_log_file = os.path.join(self.backup_folder, "final_info.json")
        self.lock = Lock()

        # Ensure the FINAL folder exists
        os.makedirs(self.final_folder, exist_ok=True)

    def backup_file(self, filepath: str) -> None:
        """
        Back up a given file by copying it into a new timestamped folder inside the backup folder.
        After backup, prune old backups exceeding maximum version count.

        Args:
            filepath (str): The full path of the file to back up.
        """
        with self.lock:
            try:
                os.makedirs(self.backup_folder, exist_ok=True)
                timestamp = current_time_str()
                dest_dir = os.path.join(self.backup_folder, timestamp)
                os.makedirs(dest_dir, exist_ok=True)

                shutil.copy2(filepath, os.path.join(dest_dir, os.path.basename(filepath)))

                # Remove old backups if exceeding max_versions
                self._prune_old_backups()
            except Exception as e:
                print(f"Backup failed for {filepath}: {e}")

    def _prune_old_backups(self) -> None:
        """
        Delete the oldest backup folders if the number of backups exceeds max_versions.
        Before deletion, preserve files from the backup in the FINAL folder to avoid data loss.
        The FINAL folder is excluded from pruning to prevent accidental deletion.
        """
        if self.max_versions is None:
            return
        try:
            # List backup folders excluding the FINAL folder
            backups = sorted(d for d in os.listdir(self.backup_folder) if d != "FINAL")
            while len(backups) > self.max_versions:
                oldest = backups.pop(0)
                oldest_path = os.path.join(self.backup_folder, oldest)

                # Preserve files from the oldest backup before deletion
                self._preserve_files_in_final(oldest_path)

                # Remove the oldest backup folder
                shutil.rmtree(oldest_path)
        except Exception as e:
            print(f"Backup pruning failed: {e}")

    def _preserve_files_in_final(self, backup_path: str) -> None:
        """
        Copy files from backup_path to FINAL folder and log files with timestamp and md5.
        """
        try:
            folder_name = os.path.basename(backup_path)
            final_subfolder = os.path.join(self.final_folder, folder_name)
            os.makedirs(final_subfolder, exist_ok=True)

            log_data = self._load_final_log()

            for fname in os.listdir(backup_path):
                src_file = os.path.join(backup_path, fname)
                dest_file = os.path.join(final_subfolder, fname)

                if not os.path.exists(dest_file):
                    shutil.copy2(src_file, dest_file)
                    mtime = os.path.getmtime(src_file)
                    md5_hash = md5_for_file(src_file)

                    # Log the file with its timestamp and md5
                    relative_path = os.path.relpath(dest_file, self.final_folder)
                    log_data[relative_path] = {
                        "timestamp": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "md5": md5_hash
                    }

            self._save_final_log(log_data)
        except Exception as e:
            print(f"Error preserving files to FINAL folder: {e}")

    def _load_final_log(self) -> dict:
        """
        Load the JSON log file that tracks final folder files.
        Returns an empty dict if file doesn't exist or can't be loaded.
        """
        try:
            if os.path.exists(self.final_log_file):
                with open(self.final_log_file, "r") as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"Error loading final log JSON: {e}")
            return {}

    def _save_final_log(self, data: dict) -> None:
        """
        Save the file tracking JSON log into final_log_file.
        """
        try:
            with open(self.final_log_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving final log JSON: {e}")

    
    def backup_file_to_final(self, filepath: str) -> None:
        """
        Backup a given file directly into the FINAL folder, without timestamp subfolder.
        Updates the FINAL folder JSON log with the file's timestamp and MD5 hash.

        Args:
            filepath (str): The full path of the file to back up.
        """
        with self.lock:
            try:
                os.makedirs(self.final_folder, exist_ok=True)
                dest_path = os.path.join(self.final_folder, os.path.basename(filepath))
                shutil.copy2(filepath, dest_path)

                # Load existing final log data
                log_data = self._load_final_log()

                # Get file modification time and md5 hash
                mtime = os.path.getmtime(filepath)
                md5_hash = md5_for_file(filepath)

                # Relative path as key in log data
                relative_path = os.path.relpath(dest_path, self.final_folder)
                log_data[relative_path] = {
                    "timestamp": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "md5": md5_hash
                }

                # Save updated log
                self._save_final_log(log_data)

            except Exception as e:
                print(f"Backup to FINAL failed for {filepath}: {e}")
    
    
    def merge_final_on_demand(self) -> None:
        """
        Merge all backup subfolders recursively.
        For each unique relative file path across all backups,
        keep the most recent version only, and copy it into the FINAL folder,
        preserving the directory structure under FINAL.
        Updates the FINAL folder JSON log with human-readable timestamps and md5.
        """
        try:
            latest_files = {}  # Dict[str, Tuple[float, str]] mapping relative path -> (mtime, full_path)

            backup_root = self.backup_folder
            backup_subfolders = [
                d for d in os.listdir(backup_root)
                if d != "FINAL" and os.path.isdir(os.path.join(backup_root, d))
            ]

            # Walk all backups; collect latest mtime file for each relative path
            for backup_subfolder in backup_subfolders:
                base_path = os.path.join(backup_root, backup_subfolder)
                for root, _, files in os.walk(base_path):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, base_path)
                        mtime = os.path.getmtime(full_path)
                        if rel_path not in latest_files or mtime > latest_files[rel_path][0]:
                            latest_files[rel_path] = (mtime, full_path)

            os.makedirs(self.final_folder, exist_ok=True)
            log_data = {}

            # Copy latest file versions into FINAL folder, preserving subfolders
            for rel_path, (mtime, src_path) in latest_files.items():
                dest_path = os.path.join(self.final_folder, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)

                human_mtime = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                md5_hash = md5_for_file(dest_path)

                log_data[rel_path] = {
                    "timestamp": human_mtime,
                    "md5": md5_hash
                }

            self._save_final_log(log_data)
            print("Final folder merged and updated successfully.")

        except Exception as e:
            print(f"Error during final merge: {e}")
        
        
        
class FolderWatcher:
    """
    Monitors a specified folder for file changes and new file creation according to 
    provided filename patterns. Automatically performs versioned backups via the provided
    BackupManager instance.

    Attributes:
        watch_folder (str): Path to the directory to monitor.
        backup_manager (BackupManager): Instance responsible for managing backups.
        interval_seconds (int): Time interval in seconds between scans.
        pattern_matcher (PatternMatcher): Instance to match filenames against specified patterns.
        _running (bool): Flag controlling the watch loop state.
        _last_mtimes (dict): Mapping of file paths to last modification timestamps.
        _log_callback (Callable[[str], None], optional): Optional callback for log messages.
        use_final_as_initial (bool): If True, initialize backup state from FINAL snapshot.
        watch_new_files (bool): If True, detect and back up files created during runtime.

    Methods:
        start(): Begin watching the folder, performing periodic scans and backups.
        stop(): Stop the watcher loop.
        _initialize_backup_state(): Initialize internal state from latest backup or FINAL folder.
        _perform_periodic_scan(): Scan watch folder and back up needed files.
        _check_and_backup_file(fpath): Check a single file for new or modified content and back up.
        _matches(filename): Check if filename matches any of the configured patterns.
        _get_latest_backup_dir(): Determine the most recent backup directory to compare against.
        _log(message): Emit log messages using callback or standard output.
    """
    
    def __init__(
        self,
        watch_folder: str,
        backup_manager: BackupManager,
        interval_seconds: int = 60,
        filename_patterns: Optional[List[str]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        use_final_as_initial: bool = False,
        watch_new_files: bool = False
        
    ) -> None:
        self.watch_folder = watch_folder
        self.backup_manager = backup_manager
        self.interval_seconds = interval_seconds
        self.pattern_matcher = PatternMatcher(filename_patterns)
        self._running = False
        self._last_mtimes = {}
        self._log_callback = log_callback
        self.use_final_as_initial = use_final_as_initial
        self.watch_new_files = watch_new_files

    def _log(self, message: str) -> None:
        if self._log_callback:
            self._log_callback(message)
        else:
            print(message)

    def _matches(self, filename: str) -> bool:
        return self.pattern_matcher.matches(filename)

    def _get_latest_backup_dir(self) -> Optional[str]:
        """
        Returns the path to the latest backup directory.
        If use_final_as_initial is True, considers FINAL folder as well.
        """
        try:
            backup_dirs = []
            base_folder = self.backup_manager.backup_folder

            # List all backup subdirectories except FINAL
            dirs = [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]
            
            # Build a list of (dir_path, modification_time) tuples excluding FINAL
            for d in dirs:
                if d == "FINAL":
                    continue
                dir_path = os.path.join(base_folder, d)
                mod_time = os.path.getmtime(dir_path)
                backup_dirs.append((dir_path, mod_time))

            # If FINAL should be considered, add it with its mod time
            if self.use_final_as_initial and "FINAL" in dirs:
                final_path = os.path.join(base_folder, "FINAL")
                final_mod_time = os.path.getmtime(final_path)
                backup_dirs.append((final_path, final_mod_time))

            if not backup_dirs:
                return None

            # Sort by modification time ascending, latest last
            backup_dirs.sort(key=lambda x: x[1])
            latest_dir = backup_dirs[-1][0]
            return latest_dir

        except Exception:
            return None

    def _initialize_backup_state(self) -> None:
        """
        Initializes the backup state by synchronizing the current watched folder files
        with the latest backup or FINAL folder (if use_final_as_initial is True).
        For each matched file in the watch folder, computes the MD5 hash and compares it with
        the corresponding file's hash in the base snapshot (backup or FINAL).
        If no previous backup exists or the file is missing/different in the base snapshot,
        it copies the file to the appropriate backup folder.
        Updates the internal last modified times map accordingly.
        """
        base_snapshot = {}

        if self.use_final_as_initial:
            self._log("Initial synchronization: using FINAL folder as base.")
            base_snapshot = self.backup_manager.get_final_snapshot()
        else:
            latest_backup_dir = self._get_latest_backup_dir()
            if latest_backup_dir is None:
                self._log("Initial synchronization: no previous backup found.")
            else:
                self._log(f"Initial synchronization: latest backup directory is {latest_backup_dir}")
                base_snapshot = self.backup_manager.get_backup_snapshot(latest_backup_dir)

        current_files = {}
        # Compute MD5 hashes for matched files in the watch directory
        for root, _, files in os.walk(self.watch_folder):
            for fname in files:
                if not self._matches(fname):
                    continue
                fpath = os.path.join(root, fname)
                md5_current = md5_for_file(fpath)
                current_files[fpath] = md5_current

        # If no backups exist and using FINAL as initial, back up all current files to FINAL
        if not base_snapshot:
            for fpath, md5_cur in current_files.items():
                self._log(f"Backup (no previous): {fpath}")
                if self.use_final_as_initial:
                    self.backup_manager.backup_file_to_final(fpath)
                else:
                    self.backup_manager.backup_file(fpath)
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
            return

        # Compare current files with base snapshot and back up if new or changed
        for fpath, md5_cur in current_files.items():
            rel_path = os.path.relpath(fpath, self.watch_folder)
            base_md5 = base_snapshot.get(rel_path)

            if base_md5 is None:
                self._log(f"Backup (no previous): {fpath}")
                self.backup_manager.backup_file(fpath)
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
            elif base_md5 != md5_cur:
                self._log(f"Difference detected -> Updating: {fpath} (MD5: {base_md5} -> {md5_cur})")
                self.backup_manager.backup_file(fpath)
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
            else:
                self._log(f"File matches backup: {fpath}")
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
            
    
    def start(self) -> None:
        """
        Starts the watcher, initializes state, and enters the main loop.
        Handles periodic scanning and backups, including detection of new files if enabled.
        """
        self._initialize_backup_state()
        self._running = True
        self._log("WatchPuppPy started watching.")
        
        sync_interval = self.interval_seconds
        control_interval = 1  # seconds

        elapsed = 0
        while self._running:
            if elapsed >= sync_interval:
                self._perform_periodic_scan()
                elapsed = 0
            time.sleep(control_interval)
            elapsed += control_interval

        self._log("WatchPuppPy stopped watching.")


    def _perform_periodic_scan(self) -> None:
        """
        Performs a full scan of the watch folder.
        Checks each file against the last modification time and MD5 hash.
        Handles new files if the watch_new_files option is enabled.
        """
        try:
            for root, dirs, files in os.walk(self.watch_folder):
                for fname in files:
                    if not self._matches(fname):
                        continue
                    fpath = os.path.join(root, fname)
                    self._check_and_backup_file(fpath)
        except Exception as e:
            self._log(f"Watcher error during scan: {e}")

    def _check_and_backup_file(self, fpath: str) -> None:
        """
        Checks a single file for modification or newness.
        Handles new files if watch_new_files is enabled.
        Backs up modified or new files and updates last modified times.
        """
        try:
            mtime = os.path.getmtime(fpath)
        except OSError:
            return

        last_mtime = self._last_mtimes.get(fpath)

        # Handle new files explicitly if watch_new_files is enabled
        if last_mtime is None:
            if self.watch_new_files:
                self._log(f"New file detected: {fpath}")
                self.backup_manager.backup_file(fpath)
                self._last_mtimes[fpath] = mtime
            # If not watching new files, do not backup new files yet
            return

        # Handle modifications for known files
        if mtime > last_mtime:
            md5_current = md5_for_file(fpath)
            latest_backup_dir = self._get_latest_backup_dir()
            md5_backup = None
            if latest_backup_dir:
                backup_file_path = os.path.join(latest_backup_dir, os.path.basename(fpath))
                if os.path.exists(backup_file_path):
                    md5_backup = md5_for_file(backup_file_path)

            if md5_backup != md5_current:
                self._log(f"Backing up updated file: {fpath}")
                self.backup_manager.backup_file(fpath)
            self._last_mtimes[fpath] = mtime

    def stop(self) -> None:
        self._running = False
