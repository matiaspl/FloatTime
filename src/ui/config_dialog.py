"""Configuration dialog for setting Ontime server URL, simple timer, and colors."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QSpinBox, QGroupBox, QColorDialog,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

# Avoid circular import: use factory defaults from config for Reset
from config import (
    FACTORY_DEFAULT_URL,
    FACTORY_DEFAULT_HEADLESS_PRESETS,
    FACTORY_DEFAULT_HEADLESS_WARNING_SEC,
    FACTORY_DEFAULT_HEADLESS_DANGER_SEC,
    FACTORY_DEFAULT_COLOR_TIMER_LABEL,
    FACTORY_DEFAULT_COLOR_CLOCK_LABEL,
    FACTORY_DEFAULT_COLOR_WARNING,
    FACTORY_DEFAULT_COLOR_DANGER,
    FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND,
    FACTORY_DEFAULT_COLOR_OVERLAY_BAR,
)


def _hex_to_qcolor(hex_str: str) -> QColor:
    """Parse #RRGGBB to QColor (alpha 255)."""
    c = QColor(hex_str)
    return c if c.isValid() else QColor(255, 255, 255)


def _qcolor_to_hex(c: QColor) -> str:
    return c.name() if c.isValid() else "#ffffff"


def _rgba_to_qcolor(rgba: list) -> QColor:
    if not isinstance(rgba, list) or len(rgba) != 4:
        return QColor(0, 0, 0, 200)
    return QColor(rgba[0], rgba[1], rgba[2], rgba[3])


def _qcolor_to_rgba(c: QColor) -> list:
    return [c.red(), c.green(), c.blue(), c.alpha()] if c.isValid() else [0, 0, 0, 200]


class ConfigDialog(QDialog):
    """Dialog for configuring Ontime server URL, simple timer, and appearance colors."""
    
    def __init__(
        self,
        current_url: str = "",
        simple_presets: list[int] | None = None,
        simple_warning_sec: int = 120,
        simple_danger_sec: int = 0,
        color_timer_label: str = FACTORY_DEFAULT_COLOR_TIMER_LABEL,
        color_clock_label: str = FACTORY_DEFAULT_COLOR_CLOCK_LABEL,
        color_warning: str = FACTORY_DEFAULT_COLOR_WARNING,
        color_danger: str = FACTORY_DEFAULT_COLOR_DANGER,
        color_timer_background: list | None = None,
        color_overlay_bar: list | None = None,
        parent=None,
    ):
        """Initialize configuration dialog."""
        super().__init__(parent)
        self.current_url = current_url
        self.result_url = None
        presets = simple_presets if simple_presets and len(simple_presets) == 3 else list(FACTORY_DEFAULT_HEADLESS_PRESETS)
        self.result_simple_presets = list(presets)
        self.result_simple_warning_sec = max(0, int(simple_warning_sec))
        self.result_simple_danger_sec = max(0, int(simple_danger_sec))
        self.result_color_timer_label = color_timer_label if color_timer_label else FACTORY_DEFAULT_COLOR_TIMER_LABEL
        self.result_color_clock_label = color_clock_label if color_clock_label else FACTORY_DEFAULT_COLOR_CLOCK_LABEL
        self.result_color_warning = color_warning if color_warning else FACTORY_DEFAULT_COLOR_WARNING
        self.result_color_danger = color_danger if color_danger else FACTORY_DEFAULT_COLOR_DANGER
        self.result_color_timer_background = list(color_timer_background) if color_timer_background and len(color_timer_background) == 4 else list(FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND)
        self.result_color_overlay_bar = list(color_overlay_bar) if color_overlay_bar and len(color_overlay_bar) == 4 else list(FACTORY_DEFAULT_COLOR_OVERLAY_BAR)
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

        # Appearance / Colors — labels in column 0, color patches in column 1 (one column)
        colors_group = QGroupBox("Appearance")
        colors_layout = QGridLayout()
        self._color_buttons = {}
        row_idx = 0
        # Timer label, clock label, warning, danger (hex)
        for key, label in [
            ("color_timer_label", "Timer label:"),
            ("color_clock_label", "Clock label:"),
            ("color_warning", "Warning color:"),
            ("color_danger", "Danger color:"),
        ]:
            colors_layout.addWidget(QLabel(label), row_idx, 0)
            btn = QPushButton()
            btn.setFixedSize(80, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            val = getattr(self, f"result_{key}")
            btn.setStyleSheet(f"background-color: {val}; border: 1px solid #888; border-radius: 4px;")
            btn.setProperty("_color_key", key)
            btn.setProperty("_is_rgba", False)
            btn.clicked.connect(self._on_color_clicked)
            self._color_buttons[key] = btn
            colors_layout.addWidget(btn, row_idx, 1)
            row_idx += 1
        # Timer background, overlay bar (RGBA)
        for key, label in [
            ("color_timer_background", "Timer background:"),
            ("color_overlay_bar", "Control bar background:"),
        ]:
            colors_layout.addWidget(QLabel(label), row_idx, 0)
            btn = QPushButton()
            btn.setFixedSize(80, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            val = getattr(self, f"result_{key}")
            btn.setStyleSheet("background-color: rgba({},{},{},{}); border: 1px solid #888; border-radius: 4px;".format(*val))
            btn.setProperty("_color_key", key)
            btn.setProperty("_is_rgba", True)
            btn.clicked.connect(self._on_color_clicked)
            self._color_buttons[key] = btn
            colors_layout.addWidget(btn, row_idx, 1)
            row_idx += 1
        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)
        
        # Buttons: Reset to default, then Cancel / OK
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset to default")
        self.reset_button.clicked.connect(self._reset_to_factory)
        button_layout.addWidget(self.reset_button)
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
    
    def _on_color_clicked(self):
        sender = self.sender()
        if not sender or sender not in self._color_buttons.values():
            return
        key = sender.property("_color_key")
        is_rgba = sender.property("_is_rgba")
        if is_rgba:
            val = getattr(self, f"result_{key}")
            initial = _rgba_to_qcolor(val)
            opts = QColorDialog.ColorDialogOption.ShowAlphaChannel
            color = QColorDialog.getColor(initial, self, f"Choose {key.replace('_', ' ').title()}", opts)
            if color.isValid():
                setattr(self, f"result_{key}", _qcolor_to_rgba(color))
                sender.setStyleSheet("background-color: rgba({},{},{},{}); border: 1px solid #888; border-radius: 4px;".format(*getattr(self, f"result_{key}")))
        else:
            val = getattr(self, f"result_{key}")
            initial = _hex_to_qcolor(val)
            color = QColorDialog.getColor(initial, self, f"Choose {key.replace('_', ' ').title()}")
            if color.isValid():
                hex_val = _qcolor_to_hex(color)
                setattr(self, f"result_{key}", hex_val)
                sender.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #888; border-radius: 4px;")
    
    def _reset_to_factory(self):
        """Fill all form fields with factory defaults (does not save; OK will save)."""
        self.url_input.setText(FACTORY_DEFAULT_URL)
        self.preset1_input.setValue(FACTORY_DEFAULT_HEADLESS_PRESETS[0])
        self.preset2_input.setValue(FACTORY_DEFAULT_HEADLESS_PRESETS[1])
        self.preset3_input.setValue(FACTORY_DEFAULT_HEADLESS_PRESETS[2])
        self.warning_input.setValue(FACTORY_DEFAULT_HEADLESS_WARNING_SEC)
        self.danger_input.setValue(FACTORY_DEFAULT_HEADLESS_DANGER_SEC)
        self.result_color_timer_label = FACTORY_DEFAULT_COLOR_TIMER_LABEL
        self.result_color_clock_label = FACTORY_DEFAULT_COLOR_CLOCK_LABEL
        self.result_color_warning = FACTORY_DEFAULT_COLOR_WARNING
        self.result_color_danger = FACTORY_DEFAULT_COLOR_DANGER
        self.result_color_timer_background = list(FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND)
        self.result_color_overlay_bar = list(FACTORY_DEFAULT_COLOR_OVERLAY_BAR)
        for key, btn in self._color_buttons.items():
            if key in ("color_timer_background", "color_overlay_bar"):
                val = getattr(self, f"result_{key}")
                btn.setStyleSheet("background-color: rgba({},{},{},{}); border: 1px solid #888; border-radius: 4px;".format(*val))
            else:
                val = getattr(self, f"result_{key}")
                btn.setStyleSheet(f"background-color: {val}; border: 1px solid #888; border-radius: 4px;")
    
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

