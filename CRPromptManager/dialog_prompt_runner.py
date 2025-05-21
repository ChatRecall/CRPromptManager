# dialog_prompt_runner.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QMessageBox, QTabWidget, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

import json
import re
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# from WrapAIVenice import VeniceTextPrompt, VeniceChatPrompt, PromptTemplate, FILE_HANDLERS, PromptAttributes
from WrapAI import VeniceTextPrompt, VeniceChatPrompt, PromptTemplate, FILE_HANDLERS, parse_response_with_schema
from WrapSideSix import (run_in_thread, WSProgressHandler,
                         WSGridLayoutHandler, WSGridRecord, WSGridPosition
                         )
from dialog_placeholder import PlaceholderDialog
from cp_core import (PROMPT_TYPE_QUESTION, PROMPT_TYPE_CHAT)
from cp_core import populate_model_combo_list, get_model_attributes
from WrapConfig import RuntimeConfig


class PromptRunDialog(QDialog):
    def __init__(self, api_key, model, prompt_text, response_type=PROMPT_TYPE_QUESTION, system_prompt="You are a helpful assistant.",
                 attributes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Prompt")
        self.setMinimumSize(800, 600)
        self.progress = None
        self.runner = None
        self.runner_mode = None
        self.formatted_prompt = None

        self.api_key = api_key
        self.model = model
        self.run_time = RuntimeConfig()
        # self.prompt_text = prompt_text
        self.prompt_text = re.sub(r'@@\s*[\w.-]+\s*@@', '', prompt_text)

        self.response_type = response_type
        self.system_prompt = system_prompt
        self.prompt_attributes = attributes or {}
        self.response = None
        self.runner = None

        # Display widgets
        self.main_grid = WSGridLayoutHandler()
        self.model_grid = WSGridLayoutHandler()
        self.question_response_grid = WSGridLayoutHandler()
        self.button_grid = WSGridLayoutHandler()

        self.model_combobox = QComboBox()
        self.prompt_display = QTextEdit()
        self.response_display = QTextEdit()
        self.run_button = QPushButton("Run Prompt")
        self.details_button = QPushButton("Full Response")
        self.details_button.setEnabled(False)
        self.close_button = QPushButton("Close")

        self.layout = QVBoxLayout(self)
        form_layout = QHBoxLayout()
        self.layout.addLayout(form_layout)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        if self.response_type== PROMPT_TYPE_QUESTION:
            prompt_row = 0
            response_row = 2
        elif self.response_type == PROMPT_TYPE_CHAT:
            prompt_row = 2
            response_row = 0
        else:
            logger.error(f"Unknown prompt type {self.response_type}")
            return

        # Common field setup
        self.prompt_display.setPlainText(self.prompt_text)
        self.response_display.setReadOnly(True)
        self.populate_model_combobox()

        # Grid setup
        model_widgets = [
            WSGridRecord(widget=QLabel("Model:"),
                         position=WSGridPosition(row=0, column=0),
                         alignment=Qt.AlignmentFlag.AlignLeft,
                         col_stretch=0),
            WSGridRecord(widget=self.model_combobox,
                         position=WSGridPosition(row=0, column=1),
                         # alignment = Qt.AlignmentFlag.AlignTrailing,
                         col_stretch=10)
        ]
        self.model_grid.add_widget_records(model_widgets)

        question_response_widgets = [
            WSGridRecord(widget=QLabel("Prompt:"),
                         position=WSGridPosition(row=prompt_row, column=0),
                         col_stretch=1),
            WSGridRecord(widget=self.prompt_display,
                         position=WSGridPosition(row=prompt_row+1, column=0),
                         col_stretch=3),
            WSGridRecord(widget=QLabel("Response:"),
                         position=WSGridPosition(row=response_row, column=0),
                         col_stretch=1),
            WSGridRecord(widget=self.response_display,
                         position=WSGridPosition(row=response_row+1, column=0),
                         col_stretch=3),
        ]
        self.question_response_grid.add_widget_records(question_response_widgets)

        button_grid_widgets = [
            WSGridRecord(widget=self.run_button,
                         position=WSGridPosition(row=0, column=0),
                         col_stretch=0),
            WSGridRecord(widget=self.details_button,
                         position=WSGridPosition(row=0, column=1),
                         col_stretch=0),
            WSGridRecord(widget=self.close_button,
                         position=WSGridPosition(row=0, column=2),
                         col_stretch=0),
        ]

        self.button_grid.add_widget_records(button_grid_widgets)

        main_grid_widgets = [
            WSGridRecord(widget=self.model_grid.as_widget(),
                         position=WSGridPosition(row=0, column=0)),
            WSGridRecord(widget=self.question_response_grid.as_widget(),
                         position=WSGridPosition(row=1, column=0)),
            WSGridRecord(widget=self.button_grid.as_widget(),
                         position=WSGridPosition(row=2, column=0)),
        ]
        self.main_grid.add_widget_records(main_grid_widgets)

        self.layout.addWidget(self.main_grid.as_widget())

    def connect_signals(self):
        self.run_button.clicked.connect(self.run_prompt)
        self.details_button.clicked.connect(self.show_detailed_response)
        self.close_button.clicked.connect(self.accept)
        self.model_combobox.currentTextChanged.connect(self.update_model)

    def get_runner(self):
        # mode = self.form_combo.currentText()
        mode = self.response_type

        if mode == self.runner_mode and self.runner:
            return self.runner  # ✅ Reuse same runner (preserve chat memory)

        # New runner (or mode switch)
        if mode == PROMPT_TYPE_CHAT:
            self.runner = VeniceChatPrompt(self.api_key, self.model)
        else:
            self.runner = VeniceTextPrompt(self.api_key, self.model)

        self.runner.set_attributes(**self.prompt_attributes)
        # self.runner.set_attributes(self.attributes)

        self.runner_mode = mode
        return self.runner


    def run_prompt(self):
        if not self.validate_prompt():
            return

        self.run_button.setEnabled(False)

        self.progress = WSProgressHandler(self, use_dialog=True, title="Running AI Prompt", indeterminate=True)
        self.progress.show()

        raw_prompt = self.prompt_display.toPlainText()
        self.formatted_prompt = self.build_prompt_text(raw_prompt)
        self.prompt_display.setPlainText(self.formatted_prompt)

        def task(**kwargs):
            self.runner = self.get_runner()
            return self.runner.prompt(self.formatted_prompt, system_prompt=self.system_prompt)

        def on_start():
            logger.info("Prompt started...")

        def on_finish(response):
            self.response = response
            self.progress.close()
            self.run_button.setEnabled(True)

            if not self.response:
                QMessageBox.warning(self, "No Response", "No response returned from the API.")
                return

            text = self.response.response if self.response.response is not None else "No response available."

            schema_json = self.prompt_attributes.get("response_format")
            use_json = schema_json is not None and isinstance(schema_json, dict)

            if self.response_type == PROMPT_TYPE_QUESTION:
                if use_json:
                    try:
                        parsed_data = parse_response_with_schema(
                            response_json=json.loads(text),
                            schema_json=schema_json,
                            include_missing_optionals=False
                        )
                        formatted = "\n\n".join(f"=== {key} ===\n{value}" for key, value in parsed_data.items())
                        self.response_display.setPlainText(formatted)
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON response with schema: {e}")
                        self.response_display.setPlainText(text)
                else:
                    self.response_display.setPlainText(text)

            if self.response_type == PROMPT_TYPE_CHAT:
                existing_html = self.response_display.toHtml()
                formatted_html = (
                    f'{existing_html}'
                    f'<div align="left" style="background-color:#f0f0f0; padding:8px; margin-top:1em; border-radius:6px; white-space:pre-wrap;">'
                    f'{self.formatted_prompt}</div>'
                    f'<div align="right" style="background-color:#e8f4ff; padding:8px; margin-top:0.5em; border-radius:6px; white-space:pre-wrap;">'
                    f'{text}</div>'
                )
                self.response_display.setHtml(formatted_html)
                self.response_display.moveCursor(QTextCursor.MoveOperation.End)

            self.details_button.setEnabled(True)
            self.citations = self.response.citations if self.response.citations is not None else []

        def on_error(error_info):
            exception, tb = error_info
            logger.exception("Prompt failed")
            self.progress.close()
            QMessageBox.critical(self, "Error", str(exception))
            self.run_button.setEnabled(True)

        run_in_thread(
            task,
            on_finish=on_finish,
            on_error=on_error,
            on_start=on_start,
            parent=self
        )

    def show_detailed_response(self):
        if not self.response:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Full Response")
        dialog.setMinimumSize(700, 500)

        tab_widget = QTabWidget(dialog)

        def add_tab(label, content):
            edit = QTextEdit()
            edit.setPlainText(content)
            edit.setReadOnly(True)
            tab_widget.addTab(edit, label)

        # add_tab("Response", self.response.get("response", ""))
        # add_tab("Think", self.response.get("think", ""))

        add_tab("Response", self.response.response or "")
        add_tab("Think", self.response.think or "")

        usage = self.response.usage or {}
        usage_text = (
            f"Model: {self.response.model or 'Unknown'}\n"
            f"Total Tokens: {usage.get('total_tokens', 'N/A')}\n"
            f"Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}\n"
            f"Completion Tokens: {usage.get('completion_tokens', 'N/A')}\n"
        )
        add_tab("Model & Usage", usage_text)

        add_tab("Parameters", json.dumps(self.response.parameters or {}, indent=4))

        # For full JSON, convert the entire PromptResponse object to a dict first
        add_tab("Full JSON", json.dumps(self.response.to_dict() if hasattr(self.response, "to_dict") else {}, indent=4))

        # Add Citations tab
        citations = getattr(self.response, "citations", [])
        if citations:
            citations_lines = []
            for cite in citations:
                citations_lines.append(f"📰 {cite.get('title', 'No Title')}")
                citations_lines.append(f"📅 Date: {cite.get('date', 'No Date')}")
                citations_lines.append(f"🔗 URL: {cite.get('url', 'No URL')}")
                citations_lines.append(f"📝 Summary: {cite.get('content', 'No Summary')}\n")
            citations_text = "\n".join(citations_lines)
            add_tab("Citations", citations_text)

        if isinstance(self.runner, VeniceChatPrompt):
            history = self.runner.memory.message_history
            formatted = "\n\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)
            add_tab("Chat History", formatted)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)

        layout = QVBoxLayout()
        layout.addWidget(tab_widget)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def build_prompt_text(self, raw_prompt_text: str) -> str:
        """Replaces both variable and file placeholders properly before sending the prompt."""
        temp_prompt = PromptTemplate(
            type="user",
            subtype="",
            prompt_text=raw_prompt_text
        )

        placeholders = temp_prompt.get_placeholders()
        file_placeholders = temp_prompt.get_file_placeholders()

        if not placeholders and not file_placeholders:
            return raw_prompt_text

        dialog = PlaceholderDialog(placeholders, file_placeholders, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return raw_prompt_text  # user cancelled

        values = dialog.values
        prompt_text = raw_prompt_text  # start with raw

        # 🔹Inline replace file placeholders early
        for fph in file_placeholders:
            file_path = Path(values.get(fph, ""))
            if file_path.exists():
                ext = file_path.suffix.lower()
                handler = FILE_HANDLERS.get(ext)
                if handler:
                    try:
                        content = handler(file_path).strip()
                    except Exception as e:
                        content = f"[Error reading file: {file_path.name}]"
                        logger.error(f"Handler error for {file_path}: {e}")
                else:
                    content = f"[Unsupported file type: {ext}]"
            else:
                content = f"[Missing file: {file_path.name}]"

            prompt_text = prompt_text.replace(f"%% {fph} %%", content)

        # 🔹 Replace variable placeholders
        for ph in placeholders:
            if ph in values:
                prompt_text = re.sub(fr"<<\s*{re.escape(ph)}\s*>>", values[ph], prompt_text)

        return prompt_text

    def validate_prompt(self):
        # Get model attributes using shared utility
        model_attributes = get_model_attributes(self.model, self.api_key, self.run_time)
        model_spec = model_attributes.get("model_spec", {})
        caps = model_spec.get("capabilities", {})

        logger.debug(f"Get details on current model {self.model}")
        logger.debug(f"Details: {model_attributes}")
        logger.debug(f"Response schema: {caps.get("supportsResponseSchema")}")
        logger.debug(f"Reasoning: {caps.get("supportsReasoning")}")

        # Get prompt information
        logger.debug('Prompt information')
        logger.debug(f"Attribute: {self.prompt_attributes}")
        logger.debug(f"Prompt Response Type: {self.response_type}")
        logger.debug(f"Json format: {self.prompt_attributes.get('response_format')}")

        prompt_formatted_response = self.prompt_attributes.get('response_format') is not None
        model_formatted_response = caps.get("supportsResponseSchema")

        # Condition 1: Chat type with JSON response not allowed
        if self.response_type == PROMPT_TYPE_CHAT and prompt_formatted_response:
            QMessageBox.critical(
                self,
                "Invalid Prompt Type",
                "You cannot use a JSON-formatted response (response_format) with chat prompts.\n"
                "Please switch to a standard prompt type or remove the response_format."
            )
            return False

        # Condition 2: Model does not support JSON response schema
        if not model_formatted_response and prompt_formatted_response:
            QMessageBox.critical(
                self,
                "Model Incompatible",
                f"The selected model ({self.model}) does not support structured JSON responses (response_schema).\n"
                "Please select a compatible model or remove the response_format from the prompt."
            )
            return False

        return True

    def populate_model_combobox(self, refresh=False):
        populate_model_combo_list(self.model_combobox, self.model, self.api_key, self.run_time, refresh=refresh)


    def update_model(self):
        self.model = self.model_combobox.currentData()

        # If in chat mode, preserve memory across runner swaps
        if self.response_type == PROMPT_TYPE_CHAT and isinstance(self.runner, VeniceChatPrompt):
            old_memory = self.runner.memory
            self.runner = VeniceChatPrompt(self.api_key, self.model)
            self.runner.memory = old_memory  # Transfer whole ConversationMemory object
        else:
            self.runner = None  # For text/question mode, just clear runner

        print(f"Model changed to: {self.model} (chat memory preserved)")
