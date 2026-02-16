"""On-hover timer control overlays with play, pause, restart, +1, -1 buttons."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase

# Circular button style: dark background, white border, white text
_BTN_STYLE = """
    QPushButton {
        background-color: rgba(40, 40, 40, 220);
        border: 2px solid #ffffff;
        border-radius: 18px;
        color: #ffffff;
        font-weight: bold;
        min-width: 36px;
        min-height: 36px;
        max-width: 36px;
        max-height: 36px;
    }
    QPushButton:hover {
        background-color: rgba(80, 80, 80, 240);
    }
    QPushButton:pressed {
        background-color: rgba(120, 120, 120, 255);
    }
"""

def _load_control_icon_font() -> str:
    """Load Simple Line Icons font and return family name."""
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    font_path = base / 'fonts' / 'Simple-Line-Icons.ttf'
    if font_path.exists():
        fid = QFontDatabase.addApplicationFont(str(font_path))
        if fid != -1:
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                return families[0]
    # Font is bundled with the app. Keep an explicit family name if runtime loading fails.
    return "Simple-Line-Icons"


def _resolve_control_icon_set():
    """Resolve icon font family and glyph map at runtime (after QApplication exists)."""
    family = _load_control_icon_font()
    icons = {
        "start": "\ue06f",   # control-start
        "play": "\ue071",    # control-play
        "pause": "\ue072",   # control-pause
        "reload": "\ue099",  # reload
        "end": "\ue074",     # control-end
        "stop": "\ue073",    # control-stop
    }
    return family, icons


class TopControlOverlay(QWidget):
    """Top overlay with +1 and -1 minute buttons."""

    add_minute_clicked = pyqtSignal()
    remove_minute_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 6, 8, 6)
        icon_family = _load_control_icon_font()

        # -1 and +1 buttons (order: -1 on left, +1 on right)
        remove_btn = QPushButton("-1")
        remove_btn.setStyleSheet(_BTN_STYLE)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        remove_btn.setFont(QFont(icon_family, 12, QFont.Weight.Bold))
        remove_btn.clicked.connect(self.remove_minute_clicked.emit)

        add_btn = QPushButton("+1")
        add_btn.setStyleSheet(_BTN_STYLE)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        add_btn.setFont(QFont(icon_family, 12, QFont.Weight.Bold))
        add_btn.clicked.connect(self.add_minute_clicked.emit)

        layout.addWidget(remove_btn)
        layout.addWidget(add_btn)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.adjustSize()


class BottomControlOverlay(QWidget):
    """Bottom overlay: main = prev, play, pause, restart, next; aux = play, pause, stop."""

    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    restart_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._mode = 'main'
        self.setup_ui()

    def set_mode(self, mode: str):
        """Switch between 'main' (prev, play, pause, restart, next) and 'aux' (play, pause, stop)."""
        if mode not in ('main', 'aux'):
            return
        self._mode = mode
        is_main = mode == 'main'
        self.prev_btn.setVisible(is_main)
        self.restart_btn.setVisible(is_main)
        self.next_btn.setVisible(is_main)
        self.stop_btn.setVisible(not is_main)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 6, 8, 6)

        icon_family, icons = _resolve_control_icon_set()
        _icon_font = QFont(icon_family, 12, QFont.Weight.Bold)

        # Previous event (main only)
        self.prev_btn = QPushButton(icons["start"])
        self.prev_btn.setStyleSheet(_BTN_STYLE)
        self.prev_btn.setFont(_icon_font)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.prev_btn.clicked.connect(self.previous_clicked.emit)

        # Play, Pause
        play_btn = QPushButton(icons["play"])
        play_btn.setStyleSheet(_BTN_STYLE)
        play_btn.setFont(_icon_font)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        play_btn.clicked.connect(self.start_clicked.emit)

        pause_btn = QPushButton(icons["pause"])
        pause_btn.setStyleSheet(_BTN_STYLE)
        pause_btn.setFont(_icon_font)
        pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pause_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pause_btn.clicked.connect(self.pause_clicked.emit)

        # Restart (main only)
        self.restart_btn = QPushButton(icons["reload"])
        self.restart_btn.setStyleSheet(_BTN_STYLE)
        self.restart_btn.setFont(_icon_font)
        self.restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.restart_btn.clicked.connect(self.restart_clicked.emit)

        # Stop (aux only)
        self.stop_btn = QPushButton(icons["stop"])
        self.stop_btn.setStyleSheet(_BTN_STYLE)
        self.stop_btn.setFont(_icon_font)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.stop_btn.setVisible(False)

        # Next event (main only)
        self.next_btn = QPushButton(icons["end"])
        self.next_btn.setStyleSheet(_BTN_STYLE)
        self.next_btn.setFont(_icon_font)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.next_btn.clicked.connect(self.next_clicked.emit)

        layout.addWidget(self.prev_btn)
        layout.addWidget(play_btn)
        layout.addWidget(pause_btn)
        layout.addWidget(self.restart_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.next_btn)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.adjustSize()
