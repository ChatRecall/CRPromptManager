import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from version import __version__ as program_version


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)

        # Set the window title
        self.setWindowTitle("About")

        # Initialize the layout
        layout = QVBoxLayout()

        # Add a logo (optional)
        # logo_label = QLabel(self)
        # pixmap = QPixmap("path_to_logo.png")
        # logo_label.setPixmap(pixmap)
        # layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)


        # Description with versions
        description_label = QLabel("ChatRecall PromptManager", self)
        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(f"Program version: {program_version}", self)
        layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # db_version_label = QLabel(f"Database version: {db_version}")
        # layout.addWidget(db_version_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Copyright or any other additional info
        copyright_label = QLabel("© 2025 ChatRecall", self)
        layout.addWidget(copyright_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Divider
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

        # Set the size of the dialog
        self.resize(300, 200)


# Main application execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = AboutDialog()
    main_window.show()
    sys.exit(app.exec())
