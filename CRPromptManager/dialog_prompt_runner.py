from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QMessageBox, QComboBox, QTabWidget, QProgressDialog
)
from PySide6.QtCore import Qt, QTimer
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from WrapAIVenice import VeniceTextPrompt, VeniceChatPrompt, PromptTemplate, FILE_HANDLERS
from WrapAIVenice.data.constants import CUSTOM_SYSTEM_PROMPT
from WrapCapPDF import CapPDFHandler
from dialog_placeholder import PlaceholderDialog


class PromptRunDialog(QDialog):
    def __init__(self, api_key, model, prompt_text, system_prompt="You are a helpful assistant.",
                 attributes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Prompt")
        self.setMinimumSize(800, 600)
        self.progress = None
        self.runner = None
        self.runner_mode = None

        self.api_key = api_key
        self.model = model
        # self.prompt_text = prompt_text
        self.system_prompt = system_prompt
        self.attributes = attributes or {}
        self.response = None
        self.runner = None

        self.layout = QVBoxLayout(self)

        # Form selector (Question / Chat)
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Form:"))
        self.form_combo = QComboBox()
        self.form_combo.addItems(["Question", "Chat"])
        form_layout.addWidget(self.form_combo)
        self.layout.addLayout(form_layout)

        # Prompt text display
        self.prompt_display = QTextEdit()
        self.prompt_display.setPlainText(prompt_text)
        # self.prompt_display.setReadOnly(True)
        self.layout.addWidget(QLabel("Prompt:"))
        self.layout.addWidget(self.prompt_display)

        # Response area
        self.response_display = QTextEdit()
        self.response_display.setReadOnly(True)
        self.layout.addWidget(QLabel("Response:"))
        self.layout.addWidget(self.response_display)

        # Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Prompt")
        self.details_button = QPushButton("Full Response")
        self.details_button.setEnabled(False)
        self.close_button = QPushButton("Close")
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.details_button)
        button_layout.addWidget(self.close_button)
        self.layout.addLayout(button_layout)

        self.run_button.clicked.connect(self.run_prompt)
        self.details_button.clicked.connect(self.show_detailed_response)
        self.close_button.clicked.connect(self.accept)

    def get_runner(self):
        mode = self.form_combo.currentText()

        if mode == self.runner_mode and self.runner:
            return self.runner  # ✅ Reuse same runner (preserve chat memory)

        # New runner (or mode switch)
        if mode == "Chat":
            self.runner = VeniceChatPrompt(self.api_key, self.model)
        else:
            self.runner = VeniceTextPrompt(self.api_key, self.model)

        self.runner.set_attributes(**self.attributes)
        self.runner_mode = mode
        return self.runner

    def run_prompt(self):
        self.progress = QProgressDialog("Running prompt...", "", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setCancelButtonText("")
        self.progress.setMinimumDuration(0)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.show()

        # Delay actual prompt run to allow UI to update
        QTimer.singleShot(100, self._run_prompt_internal)

    def _run_prompt_internal(self):
        try:
            self.runner = self.get_runner()
            raw_prompt = self.prompt_display.toPlainText()

            formatted_prompt = self.build_prompt_text(raw_prompt)

            self.prompt_display.setPlainText(formatted_prompt)
            self.response = self.runner.prompt(formatted_prompt, system_prompt=self.system_prompt)

            if not self.response:
                QMessageBox.warning(self, "No Response", "No response returned from the API.")
                return


            summary = self.response.get("response", "No summary available.")
            self.response_display.setPlainText(summary)
            self.details_button.setEnabled(True)

        except Exception as e:
            logger.exception("Prompt failed")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.progress.close()

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

        add_tab("Response", self.response.get("response", ""))
        add_tab("Think", self.response.get("think", ""))

        usage = self.response.get("usage", {})
        usage_text = (
            f"Model: {self.response.get('model', 'Unknown')}\n"
            f"Total Tokens: {usage.get('total_tokens', 'N/A')}\n"
            f"Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}\n"
            f"Completion Tokens: {usage.get('completion_tokens', 'N/A')}\n"
        )
        add_tab("Model & Usage", usage_text)

        add_tab("Parameters", json.dumps(self.response.get("parameters", {}), indent=4))
        add_tab("Full JSON", json.dumps(self.response, indent=4))

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
            program="example",
            type="user",
            name="temp",
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

