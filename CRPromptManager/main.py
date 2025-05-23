# main.py

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit,
    QFileDialog, QMessageBox, QCheckBox, QComboBox, QInputDialog, QTabWidget, QStatusBar,
)
from PySide6.QtCore import Qt

import sys
import json
from functools import partial
import copy

import logging

# from WrapAIVenice.data.constants import DEFAULT_SYSTEM_PROMPT

logging.basicConfig(
    level=logging.INFO,
    format = '%(name)s - %(levelname)s - %(message)s (line: %(lineno)d)',
    handlers=[
        logging.StreamHandler(),  # Log to console
        # logging.FileHandler('app.log')  # Log to file
    ]
)

logger = logging.getLogger(__name__)

from WrapSideSix.layouts.grid_layout import WSGridLayoutHandler, WSGridRecord, WSGridPosition
from WrapSideSix.toolbars.toolbar_icon import WSToolbarIcon, DropdownItem
from WrapSideSix.widgets.list_widget import WSListSelectionWidget

# from WrapAIVenice import VeniceParameters, WEB_SEARCH_MODES
from WrapAI import VeniceParameters, WEB_SEARCH_MODES, PromptTemplate
from WrapConfig import RuntimeConfig, INIHandler, SecretsManager

from dialog_about import AboutDialog
from dialog_settings2 import SettingsDialog
from dialog_output_format import OutputFieldDialog
from dialog_prompt_runner import PromptRunDialog
from file_backup import FileBackupManager
from cp_core import (prompt_roles, prompt_subtypes, DEFAULT_SYSTEM_PROMPT, DEFAULT_AI_MODEL,
                     API_KEY_NAME, SECRETS_FILE_NAME, populate_runtime_models,
                     DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY, DEFAULT_MAX_COMPLETION_TOKENS, DEFAULT_VENICE_PARAMS,
                     PROMPT_TYPES, display_label)


class PromptEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatRecall Prompt Editor")
        self.setGeometry(100, 100, 800, 600)

        # Extract prompt data
        self.venice_prompt_runner = None

        # Dialogs
        self.dialog_about = AboutDialog(self)
        self.dialog_settings = SettingsDialog(self)

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QHBoxLayout(central_widget)

        self.status_bar = QStatusBar()

        self.tab_widget = QTabWidget()
        self.toolbar = WSToolbarIcon('toolbar')

        self.prompts = {}  # Store prompts loaded from a file
        self.current_prompt = None
        self.prompt_library_file = None

        # Grids
        self.main_grid =  WSGridLayoutHandler()
        self.detail_grid =  WSGridLayoutHandler()

        self.library_grid = WSGridLayoutHandler()
        self.prompt_grid = WSGridLayoutHandler()
        self.prompt_placeholder_grid = WSGridLayoutHandler()
        self.prompt_placeholder_groupbox = None
        self.attribute_grid =  WSGridLayoutHandler()
        self.response_format_grid = WSGridLayoutHandler()
        self.notes_grid = WSGridLayoutHandler()
        self.venice_parameters_grid = WSGridLayoutHandler()
        self.venice_parameters_groupbox = None  # QGroupBox()

        # Widgets
        ## Prompt Library widgets
        self.prompt_list = WSListSelectionWidget()

        ## Prompt text widgets
        self.prompt_type = QComboBox()
        self.prompt_subtype = QComboBox()
        self.prompt_text = QTextEdit()
        self.full_response_button = QPushButton("Full Response")

        ## Attribute widgets
        self.system_prompt_label = QLabel("System Prompt")
        self.system_prompt_use = QCheckBox()
        self.system_prompt_input = QLineEdit(DEFAULT_SYSTEM_PROMPT)
        self.temperature_use = QCheckBox()
        self.temperature_input = QDoubleSpinBox()
        self.top_p_use = QCheckBox()
        self.top_p_input = QDoubleSpinBox()
        self.frequency_penalty_use = QCheckBox()
        self.frequency_penalty_input = QDoubleSpinBox()
        self.presence_penalty_use = QCheckBox()
        self.presence_penalty_input = QDoubleSpinBox()
        self.max_tokens_use = QCheckBox()
        self.max_tokens_input = QSpinBox()

        self.include_venice_params = QCheckBox()
        self.custom_system_prompt_use = QCheckBox()
        self.custom_system_prompt_input = QComboBox()
        self.enable_web_search_use = QCheckBox()
        self.enable_web_search_input = QComboBox()
        self.character_slug_use = QCheckBox()
        self.character_slug_input = QLineEdit()
        self.response_format_use = QCheckBox()
        self.response_format_type = QComboBox()
        self.response_format_input = QTextEdit()

        # Buttons
        self.placeholder_text_button = QPushButton("Text")
        self.placeholder_file_button = QPushButton("File")
        self.placeholder_output_button = QPushButton("Output")

        self.build_response_button = QPushButton("Build Response")

        # Potential New widgets
        ## repetition_penalty
        ## n
        ## max_temp
        ## min_temp
        ## max_completion_tokens
        ## top_k
        ## min_p
        ## stop
        ## stop_token_ids
        ## stream
        ## stream_options
        ## user
        ## parallel_tool_calls
        ## tools {}
        ## tool_choice {}

        # Prompt notes widgets
        self.prompt_notes = QTextEdit()

        # Set widget ranges
        self.set_widget_ranges()

        self.run_time = RuntimeConfig()
        self.ini_handler = INIHandler(self.run_time.ini_file_name)
        self.secrets = SecretsManager(SECRETS_FILE_NAME)

        self.api_key = self.secrets.get_secret(API_KEY_NAME)
        self.model = DEFAULT_AI_MODEL

        self.prompt_file_header = {
            "app_name": "",
            "data_version": "",
            "file_type": ""
        }

        # Initiate methods
        self.init_ui()
        self.init_toolbar()
        self.init_status_bar()
        self.connect_signals()

        self.init_defaults()

        if not self.api_key:
            self.show_settings()

        # Populate global variables
        populate_runtime_models(self.api_key, self.run_time)

        if self.prompt_library_file:
            logger.debug("Selected folder:", self.prompt_library_file)

    # Support init methods
    def init_ui(self):
        prompt_library_widgets = [
            WSGridRecord(widget=QLabel("Prompt Library:"),
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.prompt_list,
                         position=WSGridPosition(row=1, column=0),
                         col_stretch=0),
        ]
        self.library_grid.add_widget_records(prompt_library_widgets)

        prompt_placeholder_widgets = [
            # WSGridRecord(widget=QLabel("Insert Placeholder"),
            #              position=WSGridPosition(row=0, column=0),
            #              col_stretch=0),
            WSGridRecord(widget=self.placeholder_text_button,
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.placeholder_file_button,
                         position=WSGridPosition(row=0, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.placeholder_output_button,
                         position=WSGridPosition(row=0, column=2),
                         col_stretch=0),
        ]
        self.prompt_placeholder_grid.add_widget_records(prompt_placeholder_widgets)
        self.prompt_placeholder_groupbox = self.prompt_placeholder_grid.as_groupbox_widget("Insert Placeholder")

        prompt_widgets = [
            WSGridRecord(widget=QLabel("Prompt Type:"),
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.prompt_type,
                         position=WSGridPosition(row=0, column=1),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Prompt Subtype:"),
                         position=WSGridPosition(row=1, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.prompt_subtype,
                         position=WSGridPosition(row=1, column=1),
                         col_stretch=0),

            WSGridRecord(widget=self.prompt_placeholder_groupbox,
                         position=WSGridPosition(row=2, column=0),
                         col_span=2),
            WSGridRecord(widget=QLabel(""),
                         position=WSGridPosition(row=3, column=0),
                         col_span=2),

            WSGridRecord(widget=QLabel("Prompt"),
                         position=WSGridPosition(row=4, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.prompt_text,
                         position=WSGridPosition(row=5, column=0),
                         col_span=2
                         ),
        ]
        self.prompt_grid.add_widget_records(prompt_widgets)

        venice_custom_attributes_widgets = [
            WSGridRecord(widget=QLabel("Custom System Prompt"),
                         position=WSGridPosition(row=1, column=0),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.custom_system_prompt_use,
                         position=WSGridPosition(row=1, column=1),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.custom_system_prompt_input,
                         position=WSGridPosition(row=1, column=2),
                         col_stretch=0,
                         row_stretch=0),

            WSGridRecord(widget=QLabel("Enable Web Search"),
                         position=WSGridPosition(row=2, column=0),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.enable_web_search_use,
                         position=WSGridPosition(row=2, column=1),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.enable_web_search_input,
                         position=WSGridPosition(row=2, column=2),
                         col_stretch=0,
                         row_stretch=0),

            WSGridRecord(widget=QLabel("Character Slug"),
                         position=WSGridPosition(row=3, column=0),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.character_slug_use,
                         position=WSGridPosition(row=3, column=1),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.character_slug_input,
                         position=WSGridPosition(row=3, column=2),
                         col_stretch=0,
                         row_stretch=0)
        ]
        self.venice_parameters_grid.add_widget_records(venice_custom_attributes_widgets)
        self.venice_parameters_groupbox = self.venice_parameters_grid.as_groupbox_widget("Venice Parameters")

        attribute_widgets = [
            WSGridRecord(widget=self.system_prompt_label,
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.system_prompt_use,
                         position=WSGridPosition(row=0, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.system_prompt_input,
                         position=WSGridPosition(row=0, column=2),
                         col_stretch=0),


            WSGridRecord(widget=QLabel("Temperature"),
                         position=WSGridPosition(row=1, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.temperature_use,
                         position=WSGridPosition(row=1, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.temperature_input,
                         position=WSGridPosition(row=1, column=2),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Top p"),
                         position=WSGridPosition(row=2, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.top_p_use,
                         position=WSGridPosition(row=2, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.top_p_input,
                         position=WSGridPosition(row=2, column=2),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Frequency penalty"),
                         position=WSGridPosition(row=3, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.frequency_penalty_use,
                         position=WSGridPosition(row=3, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.frequency_penalty_input,
                         position=WSGridPosition(row=3, column=2),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Presence penalty"),
                         position=WSGridPosition(row=4, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.presence_penalty_use,
                         position=WSGridPosition(row=4, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.presence_penalty_input,
                         position=WSGridPosition(row=4, column=2),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Max Tokens"),
                         position=WSGridPosition(row=5, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.max_tokens_use,
                         position=WSGridPosition(row=5, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.max_tokens_input,
                         position=WSGridPosition(row=5, column=2),
                         col_stretch=0),

            WSGridRecord(widget=QLabel("Response Format"),
                         position=WSGridPosition(row=6, column=0),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.response_format_use,
                         position=WSGridPosition(row=6, column=1),
                         col_stretch=0,
                         row_stretch=0),
            WSGridRecord(widget=self.response_format_type,
                         position=WSGridPosition(row=6, column=2),
                         col_stretch=0,
                         row_stretch=0),

            WSGridRecord(widget=QLabel("Include Venice Parameters"),
                         position=WSGridPosition(row=7, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.include_venice_params,
                         position=WSGridPosition(row=7, column=1),
                         col_stretch=0),
            WSGridRecord(widget=QLabel("\n\n"),
                         position=WSGridPosition(row=7, column=2),
                         col_stretch=0),

            WSGridRecord(widget=self.venice_parameters_groupbox,
                         position=WSGridPosition(row=8, column=0),
                         col_stretch=0,
                         row_stretch=0,
                         col_span=3,
                         alignment=Qt.AlignmentFlag.AlignTop),
        ]

        self.attribute_grid.add_widget_records(attribute_widgets)

        response_widgets = [
            WSGridRecord(widget=QLabel("Response Format:"),
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.build_response_button,
                         position=WSGridPosition(row=1, column=0),
                         col_stretch=0,
                         alignment=Qt.AlignmentFlag.AlignLeft),
            WSGridRecord(widget=self.response_format_input,
                         position=WSGridPosition(row=2, column=0),
                         col_stretch=0),

        ]
        self.response_format_grid.add_widget_records(response_widgets)

        prompt_notes_widgets = [
            WSGridRecord(widget=self.prompt_notes,
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
        ]
        self.notes_grid.add_widget_records(prompt_notes_widgets)

        self.tab_widget.addTab(self.prompt_grid.as_widget(), "Prompt")  # Index 0
        self.tab_widget.addTab(self.attribute_grid.as_widget(), "Attributes")  # Index 1
        self.tab_widget.addTab(self.response_format_grid.as_widget(), "Response Format")  #Index 2
        self.tab_widget.addTab(self.notes_grid.as_widget(), "Notes")  # Index 3
        self.tab_widget.setTabVisible(2, False)

        main_widgets = [
            WSGridRecord(widget=self.library_grid.as_widget(),
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=1),
            WSGridRecord(widget=self.tab_widget,
                         position=WSGridPosition(row=0, column=1),
                         col_stretch=3),
        ]
        self.main_grid.add_widget_records(main_widgets)

        self.setCentralWidget(self.main_grid.as_widget())
        self.toggle_venice_params()

    def init_toolbar(self):
        self.addToolBar(self.toolbar)
        self.toolbar.clear_toolbar()

        self.toolbar.add_action_to_toolbar(
            "new",
            "New Prompt",
            "Add new prompt",
            self.new_prompt,
            ":/icons/mat_des/add_24dp.png")

        self.toolbar.add_action_to_toolbar(
            "rename",
            "Rename Prompt",
            "Rename selected prompt",
            self.rename_prompt,
            ":/icons/mat_des/mode_edit_24dp.png")

        self.toolbar.add_action_to_toolbar(
            "delete",
            "Delete Prompt",
            "Delete selected prompt",
            self.delete_prompt,
            ":/icons/mat_des/delete_24dp.png")

        self.toolbar.add_action_to_toolbar(
            "load",
            "Load Prompts",
            "Load prompts from file",
            self.load_prompts_from_file,
            ":/icons/mat_des/drive_folder_upload_24dp")

        self.toolbar.add_action_to_toolbar(
            "save",
            "Save Prompts",
            "Save prompts to file",
            self.save_prompts,
            ":/icons/mat_des/save_24dp.png")

        # self.toolbar.add_action_to_toolbar(
        #     "build",
        #     "Build Prompt",
        #     "Build prompt",
        #     self.show_not_implemented_dialog,
        #     ":/icons/mat_des/build_24dp.png")

        # dropdown_run_icons = [
        #     DropdownItem("Question", partial(self.run_prompt, "Question")),
        #     DropdownItem("Chat", partial(self.run_prompt, "Chat")),
        # ]

        dropdown_run_icons = [
            DropdownItem(display_label(ptype), partial(self.run_prompt, ptype))
            for ptype in PROMPT_TYPES
        ]

        self.toolbar.update_dropdown_menu(
            name="Run",
            icon=":/icons/mat_des/play_arrow_24dp.png",
            dropdown_definitions=dropdown_run_icons
        )

        self.toolbar.add_action_to_toolbar(
            "settings",
            "Settings",
            "Settings",
            self.show_settings,
            ":/icons/mat_des/settings_24dp.png")

        dropdown_help_icons = [
            DropdownItem("Help", self.show_not_implemented_dialog),
            DropdownItem("About", self.show_about),
        ]

        self.toolbar.update_dropdown_menu(
            name="Help",
            icon=":/icons/mat_des/question_mark_24dp.png",
            dropdown_definitions=dropdown_help_icons
        )

        self.toolbar.add_action_to_toolbar(
            "close",
            "Close",
            "Close Program",
            self.close,
            ":/icons/mat_des/exit_to_app_24dp.png")

        # self.toolbar.hide_action_by_name("filter")

    def init_status_bar(self):
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    def set_widget_ranges(self):
        self.temperature_input.setRange(0.0, 2.0)
        self.top_p_input.setRange(0.0, 1.0)
        self.frequency_penalty_input.setRange(-2.0, 2.0)
        self.presence_penalty_input.setRange(-2.0, 2.0)
        self.max_tokens_input.setMaximum(10000)
        self.enable_web_search_input.addItems(WEB_SEARCH_MODES)
        self.prompt_type.addItems(prompt_roles)
        self.prompt_subtype.addItems(prompt_subtypes)
        self.response_format_type.addItems(["json_schema"])

    def connect_signals(self):
        self.prompt_list.itemClicked.connect(self.set_prompt)
        self.response_format_use.stateChanged.connect(self.toggle_response_tab)
        self.prompt_type.currentTextChanged.connect(self.on_prompt_type_changed)
        self.prompt_subtype.currentTextChanged.connect(self.on_prompt_subtype_changed)

        self.custom_system_prompt_use.stateChanged.connect(self.select_system_prompt)
        self.include_venice_params.stateChanged.connect(self.toggle_venice_params)

        self.build_response_button.clicked.connect(self.show_output_dialog)
        self.placeholder_text_button.clicked.connect(lambda: self.insert_prompt_placeholder("Insert Text Placeholder", "Text placeholder:", "<< {} >>"))
        self.placeholder_file_button.clicked.connect(lambda: self.insert_prompt_placeholder("Insert File Placeholder", "File placeholder:", "%% {} %%"))
        self.placeholder_output_button.clicked.connect(lambda: self.insert_prompt_placeholder("Insert Output Placeholder", "Output placeholder:", "@@ {} @@"))

    def init_defaults(self):
        self.ini_handler.reload()
        self.model = self.ini_handler.read_value('CRPromptManager', 'default_model')
        self.prompt_library_file = self.ini_handler.read_value('CRPromptManager', 'default_prompt_file')

        logger.info(f"Model (init): {self.model}")
        logger.info(f"Prompt Library File: {self.prompt_library_file}")

        if self.prompt_library_file:
            with open(self.prompt_library_file, "r") as file:
                data = json.load(file)
                self.prompts = data.get("data", {})
                self.update_prompt_list()

                # Now automatically go to the first item if there is one:
                if self.prompt_list.count() > 0:
                    first_item = self.prompt_list.item(0)
                    self.prompt_list.setCurrentItem(first_item)
                    self.prompt_file_header = data.get("header", {
                        "app_name": "",
                        "data_version": "",
                        "file_type": ""
                    })
                    self.set_prompt(first_item)

    # Status bar methods
    def update_status_bar(self, message="Welcome to ChatRecall Prompt Manager", duration=5000):
        self.statusBar().showMessage(message, duration)
        QApplication.processEvents()

    def clear_status_bar(self):
        self.statusBar().clearMessage()

    # Misc signals
    def select_system_prompt(self, state):
        self.toggle_system_prompt()
        if state == 2:  # Qt.Checked
            system_prompts = [
                name for name, data in self.prompts.items()
                if data.get("type") == "system"]
            self.custom_system_prompt_input.clear()
            self.custom_system_prompt_input.addItems(system_prompts)
        else:
            self.custom_system_prompt_input.clear()

    def toggle_venice_params(self):
        self.venice_parameters_groupbox.setEnabled(self.include_venice_params.isChecked())
        self.toggle_system_prompt()

    def toggle_system_prompt(self):
        enabled = not self.custom_system_prompt_use.isChecked() or not self.include_venice_params.isChecked()
        self.system_prompt_label.setEnabled(enabled)
        self.system_prompt_use.setEnabled(enabled)
        self.system_prompt_input.setEnabled(enabled)

        if not enabled:
            self.system_prompt_use.setChecked(False)

    def insert_prompt_placeholder(self, dialog_title: str, dialog_label: str, wrap_format: str):
        text, ok = QInputDialog.getText(self, dialog_title, dialog_label)
        if ok and text.strip():
            cursor = self.prompt_text.textCursor()
            placeholder = wrap_format.format(text.strip())
            cursor.insertText(placeholder)

    # Tab methods
    def toggle_response_tab(self, state):
        self.tab_widget.setTabVisible(2, state ==2) # 2 means checked, 0 means unchecked

    def on_tab_select(self):
        pass

    def on_tab_changed(self, index):
        pass

    def on_prompt_type_changed(self, prompt_type: str):
        is_system = prompt_type == "system"
        self.tab_widget.setTabEnabled(1, not is_system)  # Attributes tab
        self.tab_widget.setTabEnabled(2, not is_system)  # Response Format tab
        self.prompt_subtype.setEnabled(not is_system)
        self.prompt_placeholder_groupbox.setEnabled(not is_system)

    def on_prompt_subtype_changed(self, prompt_subtype: str):
        pass

    # CRUD methods
    def new_prompt(self):
        prompt_name, ok = QInputDialog.getText(self, "New Prompt", "Enter prompt name:")
        if ok and prompt_name:
            self.prompts[prompt_name] = {"prompt_text": "", "default_attributes": {}}
            self.update_prompt_list()

            # Find the just-added prompt by its text
            items = self.prompt_list.findItems(prompt_name, Qt.MatchFlag.MatchExactly)
            if items:
                item = items[0]
                self.prompt_list.setCurrentItem(item)
                self.set_prompt(item)

    def rename_prompt(self):
        item = self.prompt_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a prompt to rename.")
            return

        current_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Prompt", "Enter new prompt name:", text=current_name)

        if not ok or new_name.strip() == "":
            return

        new_name = new_name.strip()
        if new_name == current_name:
            return  # No change

        if new_name in self.prompts:
            QMessageBox.warning(self, "Name Exists", f"A prompt named '{new_name}' already exists.")
            return

        # Perform the rename
        self.prompts[new_name] = self.prompts.pop(current_name)
        self.current_prompt = new_name
        self.update_prompt_list()

        # Reselect the renamed item
        items = self.prompt_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.prompt_list.setCurrentItem(items[0])

        self.update_status_bar(f"Renamed '{current_name}' to '{new_name}'")

    def set_prompt(self, item):
        """Switch to a selected prompt while saving the current one."""
        if self.current_prompt:
            self.update_current_prompt_data()  # Save current prompt before switching

        prompt_name = item.text()
        self.current_prompt = prompt_name
        prompt_data = self.prompts.get(prompt_name, {})

        self.prompt_text.setText(prompt_data.get("prompt_text", ""))
        self.prompt_type.setCurrentText(prompt_data.get("type", "user"))
        self.prompt_subtype.setCurrentText(prompt_data.get("subtype", "query"))
        self.prompt_notes.setText(prompt_data.get("notes", ""))
        attributes = prompt_data.get("default_attributes", {})
        self.system_prompt_use.setChecked(prompt_data.get("prompt_system_use", False))
        self.system_prompt_input.setText((prompt_data.get("prompt_system_text", DEFAULT_SYSTEM_PROMPT)))

        def set_value_and_checkbox(field, checkbox, value, default):
            checkbox.setChecked(value is not None)
            if hasattr(field, "setValue"):
                field.setValue(value if value is not None else default)
            elif hasattr(field, "setText"):
                # Handle JSON objects specially
                if isinstance(value, dict) or isinstance(value, list):
                    field.setText(json.dumps(value, indent=4))
                else:
                    field.setText(str(value if value is not None else default))

        set_value_and_checkbox(self.temperature_input, self.temperature_use, attributes.get("temperature"), DEFAULT_TEMPERATURE)
        set_value_and_checkbox(self.top_p_input, self.top_p_use, attributes.get("top_p"), DEFAULT_TOP_P)
        set_value_and_checkbox(self.frequency_penalty_input, self.frequency_penalty_use,
                               attributes.get("frequency_penalty"), DEFAULT_FREQUENCY_PENALTY)
        set_value_and_checkbox(self.presence_penalty_input, self.presence_penalty_use,
                               attributes.get("presence_penalty"), DEFAULT_PRESENCE_PENALTY)
        set_value_and_checkbox(self.max_tokens_input, self.max_tokens_use, attributes.get("max_completion_tokens"), DEFAULT_MAX_COMPLETION_TOKENS)

        # Handle response_format specially
        response_format = attributes.get("response_format")
        self.response_format_use.setChecked(response_format is not None)
        if response_format is not None:
            self.response_format_input.setText(json.dumps(response_format, indent=4))
        else:
            self.response_format_input.setText("{}")

        venice_params = attributes.get("venice_parameters", DEFAULT_VENICE_PARAMS)

        # 🧠 Include Venice Param Master Toggle
        self.include_venice_params.setChecked(bool(venice_params))

        # 🧠 Custom System Prompt
        custom_prompt_name = attributes.get("custom_system_prompt_name")
        self.custom_system_prompt_use.setChecked(custom_prompt_name is not None)
        if custom_prompt_name:
            self.custom_system_prompt_input.setCurrentText(custom_prompt_name)

        # 🧠 Web Search
        has_web_search = "enable_web_search" in venice_params
        self.enable_web_search_use.setChecked(has_web_search)
        if has_web_search:
            web_mode = venice_params.get("enable_web_search", "")
            self.enable_web_search_input.setCurrentText(web_mode)

        # 🧠 Character Slug
        has_slug = "character_slug" in venice_params
        self.character_slug_use.setChecked(has_slug)
        if has_slug:
            self.character_slug_input.setText(venice_params["character_slug"])

        # # 🧠 Response Format
        # has_response_format = "response_format" in venice_params
        # self.response_format_use.setChecked(has_response_format)
        # if has_response_format:
        #     self.response_format_input.setText(json.dumps(
        #         venice_params["response_format"], indent=4
        #     ))

    def update_prompt_list(self):
        self.prompt_list.clear()
        # for key in self.prompts:
        #     self.prompt_list.addItem(key)
        for key in sorted(list(self.prompts.keys()), key=lambda k: k.casefold()):
            self.prompt_list.addItem(key)

    def update_current_prompt_data(self):
        """Update the currently selected prompt data from UI elements."""
        if not self.current_prompt:
            return

        try:
            response_format_data = json.loads(self.response_format_input.toPlainText() or "{}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Invalid JSON", "Response format must be valid JSON.")
            return

        default_attributes = {}

        def add_if_checked(field, checkbox, key):
            if checkbox.isChecked():
                if isinstance(field, (QSpinBox, QDoubleSpinBox)):
                    default_attributes[key] = field.value()
                elif isinstance(field, QTextEdit) or isinstance(field, QPlainTextEdit):
                    # For text fields that might contain JSON
                    try:
                        if key == "response_format":
                            default_attributes[key] = json.loads(field.toPlainText() or "{}")
                        else:
                            default_attributes[key] = field.toPlainText()
                    except json.JSONDecodeError:
                        default_attributes[key] = field.toPlainText()
                else:
                    default_attributes[key] = field.text()

        # Add standard parameters
        add_if_checked(self.temperature_input, self.temperature_use, "temperature")
        add_if_checked(self.top_p_input, self.top_p_use, "top_p")
        add_if_checked(self.frequency_penalty_input, self.frequency_penalty_use, "frequency_penalty")
        add_if_checked(self.presence_penalty_input, self.presence_penalty_use, "presence_penalty")
        add_if_checked(self.max_tokens_input, self.max_tokens_use, "max_completion_tokens")

        # Handle response_format separately
        if self.response_format_use.isChecked():
            default_attributes["response_format"] = response_format_data

        if self.include_venice_params.isChecked():
            venice_parameters = {}

            if self.custom_system_prompt_use.isChecked():
                venice_parameters["include_venice_system_prompt"] = True
                default_attributes["custom_system_prompt_name"] = self.custom_system_prompt_input.currentText()

            if self.enable_web_search_use.isChecked():
                selected = self.enable_web_search_input.currentText()
                venice_parameters["enable_web_search"] = selected

            if self.character_slug_use.isChecked():
                venice_parameters["character_slug"] = self.character_slug_input.text()

            if self.include_venice_params.isChecked() and venice_parameters:
                default_attributes["venice_parameters"] = venice_parameters

        self.prompts[self.current_prompt] = {
            "prompt_text": self.prompt_text.toPlainText(),
            "type": self.prompt_type.currentText(),
            "subtype": self.prompt_subtype.currentText(),
            "notes": self.prompt_notes.toPlainText(),
            "default_attributes": default_attributes,
            "prompt_system_use": self.system_prompt_use.isChecked(),
            "prompt_system_text": self.system_prompt_input.text(),
        }

    def delete_prompt(self, item=None):
        """Delete the selected prompt after confirmation."""
        if not isinstance(item, QWidget) and not hasattr(item, "text"):
            item = self.prompt_list.currentItem()

        if item is None or not hasattr(item, "text"):
            QMessageBox.warning(self, "No Selection", "Please select a prompt to delete.")
            return

        prompt_name = item.text()
        confirm = QMessageBox.question(
            self,
            "Delete Prompt",
            f"Are you sure you want to delete the prompt '{prompt_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # Remove from data and UI
            if prompt_name in self.prompts:
                del self.prompts[prompt_name]
            self.update_prompt_list()

            # If the deleted prompt was active, clear or switch
            if self.current_prompt == prompt_name:
                self.current_prompt = None
                self.prompt_text.clear()
                self.prompt_notes.clear()
                # You may want to clear other fields too

                # Automatically select the first available prompt
                if self.prompt_list.count() > 0:
                    first_item = self.prompt_list.item(0)
                    self.prompt_list.setCurrentItem(first_item)
                    self.set_prompt(first_item)

            self.update_status_bar(f"Deleted prompt '{prompt_name}'")

    # IO methods
    def load_prompts_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Prompt File", "", "JSON Files (*.json)")
        if file_path:
            self.prompt_library_file = file_path
            with open(file_path, "r") as file:
                data = json.load(file)
                self.prompts = data.get("data", {})
                self.update_prompt_list()

    def save_prompts(self):
        """Save the current prompt and write all prompts to a JSON file."""
        if not self.current_prompt:
            QMessageBox.warning(self, "Warning", "No prompt selected to save.")
            return

        # Ensure the current prompt data is updated in memory
        self.update_current_prompt_data()
        print(self.prompts[self.current_prompt])

        # If no file is currently loaded, ask the user where to save
        if not self.prompt_library_file:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Prompt File", "", "JSON Files (*.json)")
            if not file_path:  # User canceled
                return
            self.prompt_library_file = file_path

        try:
            # Backup json file
            backup = FileBackupManager(self.prompt_library_file)
            backup.backup_current_file()

            # ✅ Write header and prompts to JSON file
            with open(self.prompt_library_file, "w", encoding="utf-8") as file:
                json.dump({
                    "header": self.prompt_file_header,
                    "data": self.prompts
                }, file, indent=4)

            self.update_status_bar(f"Prompts saved successfully to {self.prompt_library_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save prompts: {e}")

    def run_prompt(self, response_type):
        if self.prompt_type.currentText() == "system":
            QMessageBox.warning(self, "System Prompt Selected", "Please select a user prompt to run.")
            return

        if not self.current_prompt:
            QMessageBox.warning(self, "No Prompt Selected", "Please select a prompt to run.")
            return

        # 🔧 Ensure updated UI values are saved before we load them
        self.update_current_prompt_data()

        prompt_data = self.prompts.get(self.current_prompt, {})
        # attributes = prompt_data.get("default_attributes", {})
        attributes = dict(prompt_data.get("default_attributes", {}))  # shallow copy

        prompt_text = self.prompt_text.toPlainText()

        # Get system prompt separately
        if self.system_prompt_use.isChecked():
            system_prompt = self.system_prompt_input.text()
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT

        # Strip system_prompt out of default_attributes if it got added (for safety)
        attributes.pop("system_prompt", None)

        # 🧠 Extract Venice Parameters and custom prompt name
        custom_system_prompt_name = attributes.pop("custom_system_prompt_name", None)
        venice_raw = attributes.get("venice_parameters", {})

        # ✅ Only pass allowed keys into VeniceParameters
        attributes["venice_parameters"] = VeniceParameters(**venice_raw)

        # 🧠 Apply custom system prompt if needed
        if custom_system_prompt_name and venice_raw.get("include_venice_system_prompt"):
            selected = self.prompts.get(custom_system_prompt_name)
            if selected and selected.get("type") == "system":
                system_prompt = selected.get("prompt_text", system_prompt)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid System Prompt",
                    f"Selected prompt '{custom_system_prompt_name}' is not a valid system prompt."
                )
                return

        logger.info(f"System Prompt:\n{system_prompt}")

        dialog = PromptRunDialog(
            api_key=self.api_key,
            model=self.model,
            prompt_text=prompt_text,
            response_type=response_type,
            system_prompt=system_prompt,
            attributes=attributes,
            parent=self
        )
        dialog.exec()

    # Dialogs
    def show_about(self):
        self.dialog_about.show()

    def show_settings(self):
        logger.debug("showing dialog")
        # self.dialog_settings.set_fields()
        self.dialog_settings.set_fields(self.prompt_file_header if self.prompt_library_file else None)

        old_header = copy.deepcopy(self.prompt_file_header) if self.prompt_file_header else {}
        result = self.dialog_settings.exec()
        if result:
            # self.init_defaults()  # if left in, this doesn't save the values from settings so it overrides them as blank strings
            logger.info(f"Model: {self.model}")
            # Get updated header info from the dialog instance
            new_header = self.dialog_settings.header_data_ref or {}
            if old_header != new_header:
                self.prompt_file_header = self.dialog_settings.header_data_ref
                logger.info(f"Updated Header Info: {self.prompt_file_header}")
                logger.info(f"Header Info: {self.prompt_file_header}")
                self.save_prompts()  # if I want the prompt file written with the ini file and secrets.

        self.update_status_bar(f"Library file: {self.prompt_library_file}")
        self.init_defaults()
        logger.info(f"Model: {self.model}")

    def show_output_dialog(self):
        self.update_current_prompt_data()
        prompt_data = self.prompts.get(self.current_prompt, {})
        prompt_text = prompt_data.get("prompt_text", "")
        attributes = prompt_data.get("default_attributes", {})

        # Get any existing schema from response_format
        existing_schema = attributes.get("response_format") if isinstance(attributes.get("response_format"),
                                                                          dict) else None

        # Extract output fields from prompt
        prompt_template = PromptTemplate(
            type=prompt_data.get("type", "user"),
            subtype=prompt_data.get("subtype", ""),
            prompt_text=prompt_text
        )
        output_fields = prompt_template.get_output_placeholders()
        logger.info(f"Extracted output fields: {output_fields}")

        dialog = OutputFieldDialog(field_names=output_fields, existing_schema=existing_schema)
        if dialog.exec():
            updated_schema_json = dialog.updated_schema_json
            logger.info("Updated schema:")
            logger.info(updated_schema_json)
            self.response_format_input.setText(json.dumps(updated_schema_json, indent=4))
            # self.response_format_use.setChecked(True)

    # Other methods
    def show_not_implemented_dialog(self):
        QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.", QMessageBox.StandardButton.Ok)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PromptEditor()
    window.show()
    sys.exit(app.exec())
