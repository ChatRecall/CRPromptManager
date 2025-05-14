from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QDialogButtonBox, QCheckBox
)
from typing import Optional
from WrapAI import SchemaField, SchemaBuilder, extract_schema_fields_from_json, reconcile_schema_fields


class OutputFieldDialog(QDialog):
    def __init__(self, field_names: list[str], existing_schema: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Define Output Fields")
        self.field_names = field_names
        self.existing_schema = existing_schema

        self.input_fields = {}  # { field_name: (QComboBox, QLineEdit) }

        # Resulting reconciled JSON schema (updated on accept)
        self.updated_schema_json: Optional[dict] = None

        # Internal prefilled fields from schema
        self._reconciled_fields: list[SchemaField] = self._reconcile_fields()
        self._build_ui()

    def _reconcile_fields(self) -> list[SchemaField]:
        """
        Reconcile given field_names with existing schema.
        For new fields: required=False.
        For existing fields: preserve required value.
        """
        if self.existing_schema:
            raw_schema = self.existing_schema["json_schema"]["schema"]
            existing_props = raw_schema.get("properties", {})
            existing_required = set(raw_schema.get("required", []))

            fields = []
            for name in self.field_names:
                existing = existing_props.get(name, {})
                field_type = existing.get("type", "string")
                description = existing.get("description", "")
                is_required = name in existing_required

                # For arrays, get item_type if available
                item_type = None
                if field_type == "array":
                    item_type = existing.get("items", {}).get("type", "string")

                fields.append(SchemaField(
                    name=name,
                    type=field_type,
                    description=description,
                    required=is_required,
                    item_type=item_type
                ))
            return fields
        else:
            # If no existing schema, default to required=False for all
            return [
                SchemaField(name=name, type="string", required=False)
                for name in self.field_names
            ]

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name | Type | Description | Required"))

        for field in self._reconciled_fields:
            hbox = QHBoxLayout()

            name_label = QLabel(field.name)
            type_combo = QComboBox()
            required_checkbox = QCheckBox()
            required_checkbox.setChecked(field.required)

            type_combo.addItems(["string", "number", "integer", "boolean", "array"])
            if field.type in ["string", "number", "integer", "boolean", "array"]:
                type_combo.setCurrentText(field.type)

            desc_input = QLineEdit()
            if field.description:
                desc_input.setText(field.description)

            hbox.addWidget(name_label)
            hbox.addWidget(type_combo)
            hbox.addWidget(desc_input)
            hbox.addWidget(required_checkbox)

            layout.addLayout(hbox)
            self.input_fields[field.name] = (type_combo, desc_input, required_checkbox)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def accept(self):
        """Collect form data into a reconciled JSON schema."""
        updated_fields = []

        for name, (type_combo, desc_input, required_checkbox) in self.input_fields.items():
            updated_fields.append(SchemaField(
                name=name,
                type=type_combo.currentText(),
                description=desc_input.text().strip(),
                required=required_checkbox.isChecked()
            ))

        builder = SchemaBuilder("PromptOutputSchema").load_properties(updated_fields)
        self.updated_schema_json = builder.build()

        super().accept()
