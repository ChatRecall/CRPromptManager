# dialog_placeholder.py

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QDialog,
    QFileDialog, QDialogButtonBox
)
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

from WrapSideSix.widgets.line_edit_widget import WSLineButtonFile

import WrapSideSix.icons.icons_mat_des
WrapSideSix.icons.icons_mat_des.qInitResources()

class PlaceholderDialog(QDialog):
    def __init__(self, placeholders=None, file_placeholders=None, parent=None):
        """
        :param placeholders: A list of placeholder strings found with << var >>
        :param file_placeholders: A list of placeholder strings found with %% var %%
        """
        super().__init__(parent)
        self.setWindowTitle("Fill in Placeholders")

        # Default to empty lists
        self.placeholders = placeholders or []
        self.file_placeholders = file_placeholders or []

        self.values = {}       # final text or file paths for all placeholders
        self.input_fields = {} # maps placeholder name -> input widget (QLineEdit / WSLineButton)

        # Build the UI in a dedicated method
        self._build_ui()

    def _build_ui(self):
        """Constructs the dialog’s layout with placeholders and OK/Cancel buttons."""
        main_layout = QVBoxLayout(self)

        # 1. Add normal placeholders (<< var >>)
        self._add_normal_placeholders(main_layout, self.placeholders)

        # 2. Add file placeholders (%% var %%)
        self._add_file_placeholders(main_layout, self.file_placeholders)

        # 3. OK/Cancel buttons
        self._add_dialog_buttons(main_layout)

        self.setLayout(main_layout)

    def _add_normal_placeholders(self, parent_layout, placeholders):
        """Creates labeled QLineEdit fields for each normal (text) placeholder."""
        for placeholder in placeholders:
            label = QLabel(f"Value for {placeholder} ", self)
            line_edit = QLineEdit(self)

            parent_layout.addWidget(label)
            parent_layout.addWidget(line_edit)

            # Store reference so we can retrieve later in self.accept()
            self.input_fields[placeholder] = line_edit

    def _add_file_placeholders(self, parent_layout, file_placeholders):
        """Creates labeled WSLineButton fields for each file placeholder."""
        for file_placeholder in file_placeholders:
            label = QLabel(f"File for {file_placeholder} ", self)
            h_layout = QHBoxLayout()

            # 1) Create your WSLineButton with no action
            line_edit = WSLineButtonFile(
                button_icon=":/icons/mat_des/folder_24dp.png",
                parent=self
            )

            # Build layout
            h_layout.addWidget(line_edit)
            parent_layout.addWidget(label)
            parent_layout.addLayout(h_layout)

            # Store reference for retrieving its text in self.accept()
            self.input_fields[file_placeholder] = line_edit

    def _add_dialog_buttons(self, parent_layout):
        """Adds the standard OK/Cancel button box."""
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, parent=self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        parent_layout.addWidget(button_box)

    def accept(self):
        """
        Gather all user-entered text (and/or file paths), store them in self.values.
        Then call super().accept() to close the dialog normally.
        """
        for key, widget in self.input_fields.items():
            self.values[key] = widget.text().strip()

        super().accept()
