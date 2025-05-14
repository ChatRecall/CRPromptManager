# dialog_settings2.py

from dataclasses import dataclass
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QDialogButtonBox,
    QLineEdit, QLabel, QMessageBox, QComboBox, QFileDialog
)
from PySide6.QtCore import Qt, QDir

from WrapSideSix.layouts.grid_layout import (
    WSGridRecord, WSGridLayoutHandler, WSGridPosition
)
from WrapSideSix.io.gui_binder import WSGuiBinder
from WrapSideSix.widgets.line_edit_widget import WSLineButton
from WrapConfig import INIHandler, RuntimeConfig, SecretsManager
from WrapAI.info.models import VeniceModels

import WrapSideSix.icons.icons_mat_des
WrapSideSix.icons.icons_mat_des.qInitResources()


@dataclass
class DialogSettings:
    api_key: str = ""
    default_model: str = ""
    default_prompt_file: str = ""
    app_name: str = ""
    data_version: str = ""
    file_name: str = ""


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Manager Settings")
        self.setMinimumWidth(700)

        self.run_time = RuntimeConfig()
        self.ini_handler = INIHandler(self.run_time.ini_file_name)
        self.secrets = SecretsManager(".env")
        self.header_data_ref = None

        # Widgets
        self.venice_ai_api = QLineEdit()
        self.default_model_combobox = QComboBox()
        self.default_prompt_file = WSLineButton(button_icon=":/icons/mat_des/file_open_24dp.png", button_action=self.select_default_prompt_file, use_custom_menu=True)
        self.app_name = QLineEdit()
        self.data_version = QLineEdit()
        self.file_type = QLineEdit()
        self.project_dir = QDir.homePath()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        self.binder = None
        self.init_ui()
        self.connect_signals()
        self.set_fields()

    def init_ui(self):
        grid = WSGridLayoutHandler()

        grid.add_widget_records([
            WSGridRecord(QLabel("Required fields"), WSGridPosition(0, 0), alignment=Qt.AlignRight),
            WSGridRecord(QLabel("Venice API Key"), WSGridPosition(1, 0)),
            WSGridRecord(self.venice_ai_api, WSGridPosition(1, 1)),
            WSGridRecord(QLabel("Default Model"), WSGridPosition(2, 0)),
            WSGridRecord(self.default_model_combobox, WSGridPosition(2, 1)),

            WSGridRecord(QLabel(""), WSGridPosition(3, 0), col_span=2),
            WSGridRecord(QLabel("Optional fields"), WSGridPosition(4, 0), alignment=Qt.AlignRight),
            WSGridRecord(QLabel("Default Prompt File"), WSGridPosition(5, 0)),
            WSGridRecord(self.default_prompt_file, WSGridPosition(5, 1)),

            WSGridRecord(QLabel(""), WSGridPosition(6, 0), col_span=2),
            WSGridRecord(QLabel("Prompt File Header Information"), WSGridPosition(7, 0), col_span=2),
            WSGridRecord(QLabel("Application Name"), WSGridPosition(8, 0)),
            WSGridRecord(self.app_name, WSGridPosition(8, 1)),
            WSGridRecord(QLabel("Data Version"), WSGridPosition(9, 0)),
            WSGridRecord(self.data_version, WSGridPosition(9, 1)),
            WSGridRecord(QLabel("File Type"), WSGridPosition(10, 0)),
            WSGridRecord(self.file_type, WSGridPosition(10, 1)),

            WSGridRecord(QLabel(""), WSGridPosition(11, 0), col_span=2),
            WSGridRecord(self.button_box, WSGridPosition(12, 0), col_span=2),
        ])

        layout = QVBoxLayout()
        layout.addWidget(grid.as_widget())
        self.setLayout(layout)

        # Bind fields
        self.binder = WSGuiBinder(DialogSettings, {
            'api_key': self.venice_ai_api,
            'default_model': self.default_model_combobox,
            'default_prompt_file': self.default_prompt_file,
            'app_name': self.app_name,
            'data_version': self.data_version,
            'file_name': self.file_type,
        })

    def connect_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.venice_ai_api.editingFinished.connect(self.fetch_models_if_valid)

    def set_fields(self, header_data=None):
        settings = DialogSettings(
            api_key=self.secrets.get_secret("Venice_API_KEY"),
            default_model=self.ini_handler.read_value("CRPromptManager", "default_model"),
            default_prompt_file=self.ini_handler.read_value("CRPromptManager", "default_prompt_file"),
        )

        self.binder.instance = settings
        self.binder.to_gui()

        if header_data is None:
            self.app_name.setEnabled(False)
            self.data_version.setEnabled(False)
            self.file_type.setEnabled(False)
            self.header_data_ref = None
        else:
            self.app_name.setText(header_data.get("app_name", ""))
            self.data_version.setText(header_data.get("data_version", ""))
            self.file_type.setText(header_data.get("file_type", ""))
            self.app_name.setEnabled(True)
            self.data_version.setEnabled(True)
            self.file_type.setEnabled(True)
            self.header_data_ref = header_data

        if settings.api_key:
            self.fetch_models_if_valid()

    def get_fields(self):
        self.binder.from_gui()
        settings = self.binder.instance

        if self.header_data_ref:
            self.header_data_ref["app_name"] = settings.app_name
            self.header_data_ref["data_version"] = settings.data_version
            self.header_data_ref["file_type"] = settings.file_name

        settings.default_model = self.default_model_combobox.currentData()
        self.secrets.set_secret("Venice_API_KEY", settings.api_key)
        self.ini_handler.create_or_update_option("CRPromptManager", "default_model", settings.default_model)
        self.ini_handler.create_or_update_option("CRPromptManager", "default_prompt_file", settings.default_prompt_file)
        self.ini_handler.save_changes()

        return True

    def fetch_models_if_valid(self):
        api_key = self.venice_ai_api.text().strip()
        if not api_key:
            return

        models_list, models_dict = self.get_available_models(api_key)
        self.default_model_combobox.clear()

        for model in models_list:
            display = f"{model} (Tokens: {models_dict.get(model, 'N/A')})"
            self.default_model_combobox.addItem(display, model)

        saved = self.ini_handler.read_value("CRPromptManager", "default_model")
        if saved in models_list:
            self.default_model_combobox.setCurrentIndex(models_list.index(saved))

    def get_available_models(self, api_key):
        venice_models = VeniceModels(api_key)
        venice_models.fetch_models()
        # model_dict = venice_models.get_model_tokens_dict()
        model_dict = venice_models.get_model_detail_dict()
        return sorted(model_dict), model_dict

    def select_default_prompt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a file", self.project_dir, "All Files (*)")
        if file_path:
            self.default_prompt_file.setText(file_path)

    def accept(self):
        if not self.binder.all_fields_filled(['api_key', 'default_model']):
            QMessageBox.warning(self, "Missing Information", "Please fill in all required fields before saving.")
            return

        if self.get_fields():
            super().accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")


if __name__ == "__main__":
    app = QApplication([])
    dialog = SettingsDialog()
    if dialog.exec():
        print(dialog.get_fields())
    else:
        print("Canceled")
