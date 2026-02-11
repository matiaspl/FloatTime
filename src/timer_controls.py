"""On-hover timer control overlays with play, pause, restart, +1, -1 buttons."""
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

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

_OVERLAY_STYLE = "background-color: rgba(0, 0, 0, 180); border-radius: 8px;"


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

        # -1 and +1 buttons (order: -1 on left, +1 on right)
        remove_btn = QPushButton("-1")
        remove_btn.setStyleSheet(_BTN_STYLE)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        remove_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        remove_btn.clicked.connect(self.remove_minute_clicked.emit)

        add_btn = QPushButton("+1")
        add_btn.setStyleSheet(_BTN_STYLE)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        add_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        add_btn.clicked.connect(self.add_minute_clicked.emit)

        layout.addWidget(remove_btn)
        layout.addWidget(add_btn)

        self.setStyleSheet(_OVERLAY_STYLE)
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

        _icon_font = QFont("Arial", 14, QFont.Weight.Bold)

        # Previous event (main only)
        self.prev_btn = QPushButton("\u2039")
        self.prev_btn.setStyleSheet(_BTN_STYLE)
        self.prev_btn.setFont(_icon_font)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.prev_btn.clicked.connect(self.previous_clicked.emit)

        # Play, Pause
        play_btn = QPushButton("\u25B6")
        play_btn.setStyleSheet(_BTN_STYLE)
        play_btn.setFont(_icon_font)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        play_btn.clicked.connect(self.start_clicked.emit)

        pause_btn = QPushButton("\u23F8")
        pause_btn.setStyleSheet(_BTN_STYLE)
        pause_btn.setFont(_icon_font)
        pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pause_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pause_btn.clicked.connect(self.pause_clicked.emit)

        # Restart (main only)
        self.restart_btn = QPushButton("\u21BB")
        self.restart_btn.setStyleSheet(_BTN_STYLE)
        self.restart_btn.setFont(_icon_font)
        self.restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.restart_btn.clicked.connect(self.restart_clicked.emit)

        # Stop (aux only)
        self.stop_btn = QPushButton("\u25A0")  # Stop square
        self.stop_btn.setStyleSheet(_BTN_STYLE)
        self.stop_btn.setFont(_icon_font)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.stop_btn.setVisible(False)

        # Next event (main only)
        self.next_btn = QPushButton("\u203A")
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

        self.setStyleSheet(_OVERLAY_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.adjustSize()
