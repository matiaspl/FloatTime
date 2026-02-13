"""Configuration dialog for setting Ontime server URL."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt


class ConfigDialog(QDialog):
    """Dialog for configuring Ontime server URL."""
    
    def __init__(
        self,
        current_url: str = "",
        simple_presets: list[int] | None = None,
        simple_warning_sec: int = 120,
        simple_danger_sec: int = 0,
        parent=None,
    ):
        """Initialize configuration dialog."""
        super().__init__(parent)
        self.current_url = current_url
        self.result_url = None
        presets = simple_presets if simple_presets and len(simple_presets) == 3 else [15, 20, 30]
        self.result_simple_presets = list(presets)
        self.result_simple_warning_sec = max(0, int(simple_warning_sec))
        self.result_simple_danger_sec = max(0, int(simple_danger_sec))
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Configure Ontime Server")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Instructions
        info_label = QLabel(
            "Enter the URL of your Ontime server:\n"
            "(e.g., http://localhost:4001)"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("Server URL:")
        self.url_input = QLineEdit()
        self.url_input.setText(self.current_url)
        self.url_input.setPlaceholderText("http://localhost:4001")
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Simple timer settings
        simple_group = QGroupBox("Simple timer settings")
        simple_layout = QVBoxLayout()

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Start values (min):"))
        self.preset1_input = QSpinBox()
        self.preset1_input.setRange(1, 999)
        self.preset1_input.setValue(int(self.result_simple_presets[0]))
        self.preset2_input = QSpinBox()
        self.preset2_input.setRange(1, 999)
        self.preset2_input.setValue(int(self.result_simple_presets[1]))
        self.preset3_input = QSpinBox()
        self.preset3_input.setRange(1, 999)
        self.preset3_input.setValue(int(self.result_simple_presets[2]))
        preset_layout.addWidget(self.preset1_input)
        preset_layout.addWidget(self.preset2_input)
        preset_layout.addWidget(self.preset3_input)
        simple_layout.addLayout(preset_layout)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Warning (sec):"))
        self.warning_input = QSpinBox()
        self.warning_input.setRange(0, 36000)
        self.warning_input.setValue(int(self.result_simple_warning_sec))
        threshold_layout.addWidget(self.warning_input)
        threshold_layout.addWidget(QLabel("Danger (sec):"))
        self.danger_input = QSpinBox()
        self.danger_input.setRange(0, 36000)
        self.danger_input.setValue(int(self.result_simple_danger_sec))
        threshold_layout.addWidget(self.danger_input)
        simple_layout.addLayout(threshold_layout)

        simple_group.setLayout(simple_layout)
        layout.addWidget(simple_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_config)
        self.ok_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept_config(self):
        """Validate and accept the configuration."""
        url = self.url_input.text().strip()

        # Basic URL validation when provided
        if url and not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "URL must start with http:// or https://"
            )
            return

        self.result_url = url or None
        self.result_simple_presets = [
            int(self.preset1_input.value()),
            int(self.preset2_input.value()),
            int(self.preset3_input.value()),
        ]
        self.result_simple_warning_sec = int(self.warning_input.value())
        self.result_simple_danger_sec = int(self.danger_input.value())
        self.accept()

