#  dialog_settings.py

from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QDialogButtonBox, QLineEdit, QLabel, QMessageBox,
                               QComboBox, QFileDialog)
from PySide6.QtCore import Qt, QDir
# from pathlib import Path

import logging

# Logger Configuration
logger = logging.getLogger(__name__)

from WrapSideSix.layouts.grid_layout import (WSGridRecord, WSGridLayoutHandler, WSGridPosition)
from WrapSideSix.io.ws_io import WSGuiIO
from WrapSideSix.widgets.line_edit_widget import WSLineButton
from WrapConfig import INIHandler, RuntimeConfig, SecretsManager

from WrapAIVenice.info.models import VeniceModels

import WrapSideSix.icons.icons_mat_des
WrapSideSix.icons.icons_mat_des.qInitResources()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(700)
        self.run_time = RuntimeConfig()
        self.ini_handler = INIHandler(self.run_time.ini_file_name)
        self.settings_io = None
        self.secrets = SecretsManager(".env")

        self.venice_ai_api = QLineEdit()
        self.default_model_combobox = QComboBox()
        self.default_prompt_file = WSLineButton(button_icon=":/icons/mat_des/file_open_24dp.png", button_action=self.select_default_prompt_file, use_custom_menu=True)
        self.project_dir = QDir.homePath()


        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                           QDialogButtonBox.StandardButton.Cancel)
        self.layout = QVBoxLayout()

        self.init_ui()
        self.connect_signals()
        self.set_fields()

    def init_ui(self):
        grid_layout_handler = WSGridLayoutHandler()

        main_grid_widgets = [
            WSGridRecord(widget=QLabel("Required fields"), position=WSGridPosition(row=0, column=0), alignment=Qt.AlignmentFlag.AlignRight),
            WSGridRecord(widget=QLabel("Venice API Key"), position=WSGridPosition(row=1, column=0)),
            WSGridRecord(widget=self.venice_ai_api, position=WSGridPosition(row=1, column=1)),
            WSGridRecord(widget=QLabel("Default Model"), position=WSGridPosition(row=2, column=0)),
            WSGridRecord(widget=self.default_model_combobox, position=WSGridPosition(row=2, column=1)),

            WSGridRecord(widget=QLabel(""), position=WSGridPosition(row=3, column=0), col_span=2),

            WSGridRecord(widget=QLabel("Optional fields"), position=WSGridPosition(row=4, column=0), alignment=Qt.AlignmentFlag.AlignRight),
            WSGridRecord(widget=QLabel("Default Prompt File"), position=WSGridPosition(row=5, column=0)),
            WSGridRecord(widget=self.default_prompt_file, position=WSGridPosition(row=5, column=1)),

            WSGridRecord(widget=QLabel(""), position=WSGridPosition(row=6, column=0), col_span=2),

            WSGridRecord(widget=self.button_box, position=WSGridPosition(row=7, column=0), col_span=2),
            ]

        grid_layout_handler.add_widget_records(main_grid_widgets)
        self.layout.addWidget(grid_layout_handler.as_widget())
        self.setLayout(self.layout)

    def connect_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.venice_ai_api.editingFinished.connect(self.fetch_models_if_valid)

    def fetch_models_if_valid(self):
        """Fetch models only if a valid API key is entered."""
        api_key = self.venice_ai_api.text().strip()
        if api_key:
            models_list, models_dict = self.get_available_models(api_key)

            # Clear and repopulate the comboboxes
            self.default_model_combobox.clear()
            for model in models_list:
                tokens = models_dict.get(model, "N/A")
                display_text = f"{model} (Tokens: {tokens})"
                self.default_model_combobox.addItem(display_text, model)

            # Set the previously saved selection, if available
            default_model = self.ini_handler.read_value('CRPromptManager', 'default_model')

                # Set current text if saved value is available
            if default_model in models_list:
                index = models_list.index(default_model)
                self.default_model_combobox.setCurrentIndex(index)

    def get_available_models(self, api_key):
        """
        Fetch available models using VeniceModels and return a tuple:
        (sorted list of model names, tokens dictionary).
        """
        # api_key = self.venice_ai_api.text()

        venice_models = VeniceModels(api_key)
        venice_models.fetch_models()
        models_dict = venice_models.get_model_tokens_dict()
        models_list = sorted(models_dict.keys())
        return models_list, models_dict

    def select_default_prompt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a file",
            self.project_dir,
            "All Files (*)"  # Filter; you can change this if needed
        )
        if file_path:
            self.default_prompt_file.setText(file_path)

    def set_fields(self):
        try:
            # key = self.ini_handler.read_value('API-Keys', 'venice')
            key = self.secrets.get_secret("Venice_API_KEY")
            default_model = self.ini_handler.read_value('CRPromptManager', 'default_model')
            default_prompt_file = self.ini_handler.read_value('CRPromptManager', 'default_prompt_file')

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read settings: {e}")
            return

        # Set the API key field so that get_available_models() uses the correct key.
        self.venice_ai_api.setText(key)

        # Only fetch models if there is a valid API key
        if key:
            self.fetch_models_if_valid()

        # Set other fields.
        widget_mapping = {
            'api_key': self.venice_ai_api,
            'default_model': self.default_model_combobox,
            'default_prompt_file': self.default_prompt_file,
        }
        dialog_values = {
            'api_key': key,
            'default_model': default_model,
            'default_prompt_file': default_prompt_file,
        }
        self.settings_io = WSGuiIO(widget_mapping, dialog_values)
        self.settings_io.set_gui()

    def get_fields(self):
        try:
            updated_settings = self.settings_io.get_gui()
            # Retrieve the model name from the combo box's item data.
            updated_settings['default_model'] = self.default_model_combobox.currentData()



            # self.ini_handler.create_or_update_option('API-Keys', 'venice', updated_settings['api_key'])
            self.secrets.set_secret("Venice_API_KEY", updated_settings['api_key'])
            self.ini_handler.create_or_update_option('CRPromptManager', 'default_model', updated_settings['default_model'])
            self.ini_handler.create_or_update_option('CRPromptManager', 'default_prompt_file', updated_settings['default_prompt_file'])

            self.ini_handler.save_changes()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            return False

    def accept(self):
        # Validate mandatory fields
        if not self.validate_mandatory_fields():
            QMessageBox.warning(self, "Missing Information", "Please fill in all required fields before saving.")
            return  # Stop the dialog from closing

        if self.get_fields():  # Save the fields if valid
            super().accept()  # Only accept the dialog if saving succeeded
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")

    def validate_mandatory_fields(self):
        """
        Check if mandatory fields are filled.
        Returns True if all fields are valid, False otherwise.
        """
        if not self.venice_ai_api.text().strip():
            return False
        if self.default_model_combobox.currentIndex() == -1:  # No item selected
            return False

        return True  # All fields are valid

if __name__ == "__main__":
    app = QApplication([])
    dialog = SettingsDialog()
    if dialog.exec():
        print(dialog.get_fields())
    else:
        print("Dialog canceled")
