from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox, QLabel,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QCheckBox
)

from src.watchpuppy.config import ConfigManager


class WatcherConfigGUI(QWidget):
    """
    GUI component for configuring folder watcher settings.

    Provides input fields for watch folder, backup folder, checking interval,
    maximum number of backup versions, and a list of filename patterns.
    Includes buttons to open pattern editor, and to save/load configuration
    in JSON or YAML formats depending on file extension, handled via ConfigManager.
    """

    def __init__(self) -> None:
        """
        Initializes the GUI elements and layout.

        Sets up input widgets for user configuration, pattern display, and 
        buttons for editing patterns and saving/loading configuration files.
        Connects button click events to their respective handler methods.
        """
        super().__init__()

        # Input widgets
        self.folder_edit = QLineEdit()
        self.backup_edit = QLineEdit()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 9999)
        self.interval_spin.setValue(60)
        self.max_versions_spin = QSpinBox()
        self.max_versions_spin.setRange(1, 1000)
        self.max_versions_spin.setValue(5)

        self.pattern_list = QListWidget()
        self.edit_patterns_btn = QPushButton("Edit Patterns")
        self.save_config_btn = QPushButton("Save Config")
        self.load_config_btn = QPushButton("Load Config")

        # Browse buttons for folders
        self.watch_folder_browse_btn = QPushButton("Browse...")
        self.backup_folder_browse_btn = QPushButton("Browse...")

        self.use_final_check = QCheckBox("Initialize from FINAL snapshot")
        self.watch_new_files_check = QCheckBox("Watch new files created during runtime")
        self.use_final_check.setChecked(True)
        self.watch_new_files_check.setChecked(False)
        
        
        # Layout setup
        layout = QVBoxLayout()

        def add_row(label: str, edit_widget, browse_button=None) -> None:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(edit_widget)
            if browse_button is not None:
                row.addWidget(browse_button)
            layout.addLayout(row)

        add_row("Watch Folder:", self.folder_edit, self.watch_folder_browse_btn)
        add_row("Backup Folder:", self.backup_edit, self.backup_folder_browse_btn)
        add_row("Interval (sec):", self.interval_spin)
        add_row("Max Versions:", self.max_versions_spin)

        layout.addWidget(self.use_final_check)
        layout.addWidget(self.watch_new_files_check)
                
        layout.addWidget(QLabel("Patterns:"))
        layout.addWidget(self.pattern_list)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.edit_patterns_btn)
        btn_layout.addWidget(self.save_config_btn)
        btn_layout.addWidget(self.load_config_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect buttons to their slots
        self.save_config_btn.clicked.connect(self.save_config_dialog)
        self.load_config_btn.clicked.connect(self.load_config_dialog)

        self.watch_folder_browse_btn.clicked.connect(self.browse_watch_folder)
        self.backup_folder_browse_btn.clicked.connect(self.browse_backup_folder)

    def browse_watch_folder(self) -> None:
        """
        Opens a directory picker dialog to select the watch folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Watch Folder")
        if folder:
            self.folder_edit.setText(folder)

    def browse_backup_folder(self) -> None:
        """
        Opens a directory picker dialog to select the backup folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.backup_edit.setText(folder)

    def get_config(self) -> Dict[str, Any]:
        """
        Retrieves the current watcher configuration from the GUI inputs.

        Returns:
            dict: A dictionary containing the current watcher configuration parameters:
                - watch_folder (str): Path of the folder to watch.
                - backup_folder (str): Path to the backup folder.
                - interval (int): Watching interval in seconds.
                - max_versions (int): Maximum number of backup versions to keep.
                - patterns (List[str]): List of filename pattern strings.
        """
        return dict(
            watch_folder=self.folder_edit.text(),
            backup_folder=self.backup_edit.text(),
            interval=self.interval_spin.value(),
            max_versions=self.max_versions_spin.value(),
            patterns=[self.pattern_list.item(i).text() for i in range(self.pattern_list.count())],
            use_final_as_initial = self.use_final_check.isChecked(),
            watch_new_files = self.watch_new_files_check.isChecked()
        )

    def set_patterns(self, patterns: List[str]) -> None:
        """
        Sets the pattern list displayed in the GUI.

        Args:
            patterns (List[str]): List of filename patterns to display.
        """
        self.pattern_list.clear()
        self.pattern_list.addItems(patterns)

    def set_parameters(self, config: Dict[str, Any]) -> None:
        """
        Sets the GUI input fields to match the provided configuration dictionary.

        Args:
            config (dict): Configuration dictionary containing keys corresponding to:
                - watch_folder (str)
                - backup_folder (str)
                - interval (int)
                - max_versions (int)
                - patterns (List[str])
        """
        self.folder_edit.setText(config.get("watch_folder", ""))
        self.backup_edit.setText(config.get("backup_folder", ""))
        self.interval_spin.setValue(config.get("interval", 60))
        self.max_versions_spin.setValue(config.get("max_versions", 5))
        self.set_patterns(config.get("patterns", []))
        self.use_final_check.setChecked(config.get("use_final_as_initial", False))
        self.watch_new_files_check.setChecked(config.get("watch_new_files", False))

    def save_config(self, filepath: str) -> None:
        """
        Saves the current configuration to a file in JSON or YAML format,
        depending on the file extension.

        Utilizes the ConfigManager class to handle the file operations.

        Args:
            filepath (str): The file path where the configuration will be saved.

        Raises:
            Exception: Propagates exceptions encountered during saving,
                       such as file write issues or format errors.
        """
        try:
            config = self.get_config()
            cm = ConfigManager(filepath)
            cm.save(config)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save config:\n{str(e)}")

    def load_config(self, filepath: str) -> None:
        """
        Loads the configuration from a JSON or YAML file and applies it to the GUI inputs.

        Utilizes the ConfigManager class to handle reading and parsing the configuration.

        Args:
            filepath (str): The file path from which the configuration is loaded.

        Raises:
            Exception: Propagates exceptions encountered during loading,
                       such as file read issues or parse errors.
        """
        try:
            cm = ConfigManager(filepath)
            config = cm.load()
            if config is not None:
                self.set_parameters(config)
            else:
                QMessageBox.information(self, "Load Config", "Config file is empty or missing.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load config:\n{str(e)}")

    def save_config_dialog(self) -> None:
        """
        Opens a save file dialog to select location to save configuration,
        allowing JSON or YAML file types.
        """
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            filter="JSON/YAML Files (*.json *.yaml *.yml)"
        )
        if filepath:
            self.save_config(filepath)

    def load_config_dialog(self) -> None:
        """
        Opens an open file dialog to select a configuration file to load,
        accepting JSON or YAML files.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            filter="JSON/YAML Files (*.json *.yaml *.yml)"
        )
        if filepath:
            self.load_config(filepath)
