from typing import List
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLineEdit, QLabel, QMessageBox, QFileDialog
)
from src.watchpuppy.pattern_matcher import PatternMatcher
from src.watchpuppy.pattern_builder import simple_pattern_builder

class PatternManagerGUI(QDialog):
    """
    A dialog window for managing filename patterns.

    Provides functionality to view, add, edit, delete, and test regex patterns
    against filenames in a selected folder. Supports pattern creation based on
    example filenames from the filesystem.
    """

    def __init__(self, parent=None):
        """
        Initializes the Pattern Manager dialog UI components and connects signals.

        Args:
            parent (QWidget, optional): Parent widget of the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("Pattern Manager")
        self.patterns: List[str] = []

        # Widgets
        self.pattern_list = QListWidget()
        self.clear_selection_button = QPushButton("Clear Selection")
        
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setReadOnly(False)

        self.add_button = QPushButton("Add")
        
        self.add_from_file_button = QPushButton("Add Pattern from File")
        
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.test_button = QPushButton("Test Selected")
        self.test_all_button = QPushButton("Test All")

        self.edit_ok_button = QPushButton("OK")
        self.edit_cancel_button = QPushButton("Cancel")
        self.edit_ok_button.hide()
        self.edit_cancel_button.hide()

        self.browse_button = QPushButton("Browse Folder")
        self.test_folder_edit = QLineEdit()

        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        # Layouts
        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Patterns:"))
        main_layout.addWidget(self.pattern_list)

        clear_select_row = QHBoxLayout()
        clear_select_row.addWidget(self.clear_selection_button)
        main_layout.addLayout(clear_select_row)
        
        # Pattern edit and add
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Pattern:"))
        add_row.addWidget(self.pattern_edit)
        add_row.addWidget(self.add_button)
        main_layout.addLayout(add_row)

        # add from file
        add_from_file_row = QHBoxLayout()
        add_from_file_row.addWidget(self.add_from_file_button)
        main_layout.addLayout(add_from_file_row)
        
        # Edit/Delete/Test buttons row
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.edit_button)
        btn_row.addWidget(self.delete_button)
        btn_row.addWidget(self.test_button)
        main_layout.addLayout(btn_row)

        # Edit confirm/cancel buttons row (hidden initially)
        edit_confirm_row = QHBoxLayout()
        edit_confirm_row.addWidget(self.edit_ok_button)
        edit_confirm_row.addWidget(self.edit_cancel_button)
        main_layout.addLayout(edit_confirm_row)

        # Folder selection for testing
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Test Folder:"))
        folder_layout.addWidget(self.test_folder_edit)
        folder_layout.addWidget(self.browse_button)
        main_layout.addLayout(folder_layout)

        # Test all button
        main_layout.addWidget(self.test_all_button)

        # Dialog OK/Cancel buttons
        ok_cancel_row = QHBoxLayout()
        ok_cancel_row.addStretch()
        ok_cancel_row.addWidget(self.ok_button)
        ok_cancel_row.addWidget(self.cancel_button)
        main_layout.addLayout(ok_cancel_row)

        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.test_button.setEnabled(False)
        
        self.setLayout(main_layout)

        # Connect signals to slots
        self.clear_selection_button.clicked.connect(self.clear_selection)
        self.add_button.clicked.connect(self.add_pattern)
        self.add_from_file_button.clicked.connect(self.add_pattern_from_file)
        self.edit_button.clicked.connect(self.start_editing)
        self.delete_button.clicked.connect(self.delete_pattern)
        self.test_button.clicked.connect(self.test_selected_pattern)
        self.test_all_button.clicked.connect(self.test_all_patterns)
        self.pattern_list.itemSelectionChanged.connect(self.pattern_selected)
        self.edit_ok_button.clicked.connect(self.finish_editing)
        self.edit_cancel_button.clicked.connect(self.cancel_editing)
        self.browse_button.clicked.connect(self.browse_folder)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def add_pattern(self) -> None:
        """
        Adds a new pattern from the pattern edit box to the list.
        """
        pattern = self.pattern_edit.text().strip()
        if pattern:
            self.patterns.append(pattern)
            self.pattern_list.addItem(pattern)
            self.pattern_edit.clear()

    def start_editing(self) -> None:
        """
        Enables editing mode for the selected pattern,
        locks other controls to prevent conflicts.
        """
        selected_items = self.pattern_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a pattern to edit.")
            return
        self.pattern_edit.setReadOnly(False)
        self.pattern_edit.setFocus()
        self.pattern_list.setDisabled(True)
        self.add_button.setDisabled(True)
        self.edit_button.setDisabled(True)
        self.delete_button.setDisabled(True)
        self.test_button.setDisabled(True)
        self.test_all_button.setDisabled(True)
        self.ok_button.setDisabled(True)
        self.cancel_button.setDisabled(True)
        self.edit_ok_button.show()
        self.edit_cancel_button.show()

    def finish_editing(self) -> None:
        """
        Accepts the edited pattern and updates the list.
        """
        new_pattern = self.pattern_edit.text().strip()
        if not new_pattern:
            QMessageBox.warning(self, "Empty Pattern", "Pattern cannot be empty.")
            return
        selected_items = self.pattern_list.selectedItems()
        if selected_items:
            index = self.pattern_list.row(selected_items[0])
            self.patterns[index] = new_pattern
            self.pattern_list.item(index).setText(new_pattern)
        self.stop_editing()

    def cancel_editing(self) -> None:
        """
        Cancels editing and reverts the pattern edit box to the selected pattern.
        """
        selected_items = self.pattern_list.selectedItems()
        if selected_items:
            self.pattern_edit.setText(selected_items[0].text())
        else:
            self.pattern_edit.clear()
        self.stop_editing()

    def stop_editing(self) -> None:
        """
        Disables editing mode, re-enables other controls.
        """
        self.pattern_edit.setReadOnly(False)
        self.pattern_list.setDisabled(False)
        self.add_button.setDisabled(False)
        self.edit_button.setDisabled(False)
        self.delete_button.setDisabled(False)
        self.test_button.setDisabled(False)
        self.test_all_button.setDisabled(False)
        self.ok_button.setDisabled(False)
        self.cancel_button.setDisabled(False)
        self.edit_ok_button.hide()
        self.edit_cancel_button.hide()

    def delete_pattern(self) -> None:
        """
        Deletes the selected pattern from the list.
        """
        selected_items = self.pattern_list.selectedItems()
        if not selected_items:
            return
        index = self.pattern_list.row(selected_items[0])
        self.pattern_list.takeItem(index)
        del self.patterns[index]
        self.pattern_edit.clear()

    def pattern_selected(self) -> None:
        """
        Updates the pattern edit box to show the selected pattern
        and enables or disables buttons depending on selection.
        """
        selected_items = self.pattern_list.selectedItems()
        has_selection = bool(selected_items)
        if has_selection:
            self.pattern_edit.setText(selected_items[0].text())
        else:
            self.pattern_edit.clear()
        # Enable or disable Edit, Delete, Test button based on selection
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.test_button.setEnabled(has_selection)
        
        
    def clear_selection(self) -> None:
        """
        Clears the current selection in the pattern list.
        """
        self.pattern_list.clearSelection()
        self.pattern_edit.clear()

        # Kapcsold ki az Edit/Delete/Test gombokat is, mert nincs kijelölés
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.test_button.setEnabled(False)
        
    
    def add_pattern_from_file(self) -> None:
        """
        Opens a file dialog to select a file and
        generates a filename pattern from the selected filename.
        Adds the generated pattern to the pattern list.
        """
        
        default_folder = None
        if os.path.exists(str(self.test_folder_edit.text()).strip()):
            default_folder = str(self.test_folder_edit.text()).strip()
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a File to Create Pattern From",default_folder)
        if file_path:
            filename = os.path.basename(file_path)
            pattern = simple_pattern_builder(filename)
            if pattern:
                self.patterns.append(pattern)
                self.pattern_list.addItem(pattern)
                QMessageBox.information(self, "Pattern Created", f"Pattern created from file:\n{filename}\n\n{pattern}")
            else:
                QMessageBox.warning(self, "Pattern Not Created", "Failed to create a pattern from the selected file.")



    def browse_folder(self) -> None:
        """
        Opens a directory selector dialog and sets the test folder input.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Testing")
        if folder:
            self.test_folder_edit.setText(folder)

    def test_selected_pattern(self) -> None:
        """
        Tests the selected pattern against files in the test folder,
        shows message with matched filenames.
        """
        folder = self.test_folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid test folder.")
            return
        selected_items = self.pattern_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Pattern Selected", "Please select a pattern to test.")
            return
        pattern = selected_items[0].text()
        self.show_matching_files(folder, [pattern])

    def test_all_patterns(self) -> None:
        """
        Tests all stored patterns against files in the test folder,
        shows message with matched filenames.
        """
        folder = self.test_folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid test folder.")
            return
        if not self.patterns:
            QMessageBox.information(self, "No Patterns", "No patterns to test.")
            return
        self.show_matching_files(folder, self.patterns)

    def show_matching_files(self, folder: str, patterns: List[str]) -> None:
        """
        Filters and displays matching files in a message box.

        Args:
            folder (str): Path of the folder to search.
            patterns (List[str]): List of regex patterns to match.
        """
        matcher = PatternMatcher(patterns)
        matched_files = matcher.filter_files(folder)
        if matched_files:
            QMessageBox.information(
                self,
                "Matched Files",
                "Found matching files:\n" + "\n".join(matched_files)
            )
        else:
            QMessageBox.information(self, "No Matches", "No files matched the selected pattern(s).")

    def accept(self) -> None:
        """
        Stores current pattern list and closes dialog with acceptance.
        """
        self.patterns = [self.pattern_list.item(i).text() for i in range(self.pattern_list.count())]
        super().accept()
