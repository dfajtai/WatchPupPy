import sys
from typing import Optional
import threading
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QMessageBox
)
from PySide6.QtCore import Signal

from src.gui.watcher_config_gui import WatcherConfigGUI
from src.gui.pattern_manager_gui import PatternManagerGUI
from src.watchpuppy.watcher import FolderWatcher, BackupManager
from src.watchpuppy.utils import log_timestamp
from src.watchpuppy.logger import *

class MainGUI(QWidget):
    watcherStopped = Signal()
    # newLogMessage = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        
        # control
        self.watcher: FolderWatcher = None
        self.watcher_thread: threading.Thread = None
        self.watcher_running = False

        self.state = "stopped"  # stopped, starting, running, stopping
        
        # logging
        
        self.qt_logger = QtLogger()
        self.qt_logger.newLogMessage.connect(self._append_log_slot)

        # GUI def
        self.setWindowTitle("WatchPupPy")

        self.config_gui = WatcherConfigGUI()

        self.start_btn = QPushButton("Start Watching")
        self.stop_btn = QPushButton("Stop Watching")
        self.merge_final_btn = QPushButton("Merge to FINAL")
        self.stop_btn.setEnabled(False)

        self.status_lbl = QLabel("Status: Stopped")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        self.edit_patterns_btn = self.config_gui.edit_patterns_btn

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.edit_patterns_btn)

        
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.config_gui)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.status_lbl)
        main_layout.addWidget(self.merge_final_btn)
        main_layout.addWidget(QLabel("Log:"))
        main_layout.addWidget(self.log_text)

        self.setLayout(main_layout)


        self.start_btn.clicked.connect(self.start_watching)
        self.stop_btn.clicked.connect(self.stop_watching)
        self.merge_final_btn.clicked.connect(self.merge_to_final)
        
        self.edit_patterns_btn.clicked.connect(self.open_pattern_manager)

        self.watcherStopped.connect(self.on_watcher_stopped)
        # self.newLogMessage.connect(self._append_log_slot)

    def set_state(self, new_state: str) -> None:
        print(f"Switching states: {self.state} -> {new_state}")
        self.state = new_state
        if new_state == "stopped":
            self.status_lbl.setText("Status: Stopped")
            self.set_controls_enabled(True)
        elif new_state == "starting":
            self.status_lbl.setText("Status: Starting...")
            self.set_controls_enabled(False)
        elif new_state == "running":
            self.status_lbl.setText("Status: Running")
            self.set_controls_enabled(False)
        elif new_state == "stopping":
            self.status_lbl.setText("Status: Stopping...")
            self.set_controls_enabled(False)

    def set_controls_enabled(self, enabled: bool) -> None:
        # print(f"Set controls enabled called with {enabled}")
        self.config_gui.setEnabled(enabled)
        self.start_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)
        self.edit_patterns_btn.setEnabled(enabled)
        self.merge_final_btn.setEnabled(enabled) 

    def _append_log_slot(self, message: str) -> None:
        self.log_text.append(message)

    def append_log(self, message: str) -> None:
        # self.newLogMessage.emit(f"{log_timestamp()}: {message}")
        # print(f"{log_timestamp()}: {message}")
        self.qt_logger.info(message)

    def open_pattern_manager(self) -> None:
        patterns = [
            self.config_gui.pattern_list.item(i).text()
            for i in range(self.config_gui.pattern_list.count())
        ]
        dialog = PatternManagerGUI(self)
        dialog.patterns = patterns
        if str(self.config_gui.folder_edit.text()).strip() != "":
            dialog.test_folder_edit.setText(self.config_gui.folder_edit.text())
        dialog.pattern_list.clear()
        dialog.pattern_list.addItems(patterns)

        if dialog.exec():
            new_patterns = dialog.patterns
            self.config_gui.set_patterns(new_patterns)
            
    
    def get_backup_manager(self) -> Optional[BackupManager]:
        """
        Return existing BackupManager or create one from current config.
        Returns None if creation fails.
        """
        if self.watcher and self.watcher.backup_manager:
            return self.watcher.backup_manager

        cfg = self.config_gui.get_config()
        backup_folder = cfg.get("backup_folder")
        max_versions = cfg.get("max_versions", 5)

        if not backup_folder:
            self.append_log("Backup folder not set, cannot create BackupManager.")
            return None

        try:
            return BackupManager(backup_folder, max_versions)
        except Exception as e:
            self.append_log(f"Failed to create BackupManager: {e}")
        return None
    

    def merge_to_final(self) -> None:
        """
        Merge backups into FINAL folder on demand.
        """
        if self.watcher_running:
            QMessageBox.information(self, "Info", "Cannot merge while watcher is running.")
            return

        backup_mgr = self.get_backup_manager()
        if not backup_mgr:
            QMessageBox.warning(self, "Warning", "No backup manager available.")
            return

        self.append_log("Merging backups to FINAL folder...")
        try:
            backup_mgr.merge_final_on_demand()
            self.append_log("Merge completed successfully.")
            QMessageBox.information(self, "Success", "Merge to FINAL completed.")
        except Exception as e:
            self.append_log(f"Merge failed: {e}")
            QMessageBox.critical(self, "Error", f"Merge failed:\n{e}")
    

    def start_watching(self) -> None:
        if self.state != "stopped":
            QMessageBox.information(self, "Info", "Watcher is already running or starting.")
            return

        cfg = self.config_gui.get_config()
        if not cfg["watch_folder"] or not cfg["backup_folder"]:
            QMessageBox.warning(self, "Invalid Config", "Watch folder and backup folder cannot be empty.")
            return

        backup_mgr = BackupManager(cfg["backup_folder"], cfg["max_versions"])
        self.watcher = FolderWatcher(
            watch_folder=cfg["watch_folder"],
            backup_manager=backup_mgr,
            interval_seconds=cfg["interval"],
            filename_patterns=cfg["patterns"],
            use_final_as_initial=cfg["use_final_as_initial"],
            watch_new_files=cfg["watch_new_files"],
            log_callback=self.append_log
        )

        self.set_state("starting")
        self.watcher_thread = threading.Thread(target=self._run_watcher, daemon=True)
        self.watcher_running = True
        self.watcher_thread.start()
        self.append_log(f"Watcher thread started.")

    def _run_watcher(self) -> None:
        try:
            self.set_state("running")
            self.watcher.start()  # Blocking threading, the watcher is running
        except Exception as e:
            self.append_log(f"Watcher error: {e}")
        finally:
            self.watcher_running = False
            self.watcherStopped.emit()

    def stop_watching(self) -> None:
        if self.state != "running":
            QMessageBox.information(self, "Info", "Watcher is not running.")
            return

        self.set_state("stopping")
        self.watcher.stop()  # Stopps the watcher loop
        self.append_log(f"Watcher stopping requested.")

    def on_watcher_stopped(self) -> None:
        # At this stage the bachground thread should stopped
        self.set_state("stopped")
        self.append_log(f"Watcher thread finished.")
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.join()


    def closeEvent(self, event):
        if self.state == "running":
            self.append_log("Main window closing: stopping watcher first...")
            self.stop_watching()
            if self.watcher_thread and self.watcher_thread.is_alive():
                self.watcher_thread.join(timeout=5)
                if self.watcher_thread.is_alive():
                    self.append_log("Watcher thread did not finish in time.")
            self.append_log("Watcher stopped, closing application.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainGUI()
    main_win.resize(800, 600)
    main_win.show()
    sys.exit(app.exec())
