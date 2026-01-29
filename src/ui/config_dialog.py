"""Configuration dialog for setting Ontime server URL."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt


class ConfigDialog(QDialog):
    """Dialog for configuring Ontime server URL."""
    
    def __init__(self, current_url: str = "", parent=None):
        """Initialize configuration dialog."""
        super().__init__(parent)
        self.current_url = current_url
        self.result_url = None
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
        
        if not url:
            QMessageBox.warning(
                self, 
                "Invalid URL", 
                "Please enter a valid server URL."
            )
            return
        
        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "URL must start with http:// or https://"
            )
            return
        
        self.result_url = url
        self.accept()

