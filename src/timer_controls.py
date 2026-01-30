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
    """Bottom overlay with previous, play, pause, restart, next buttons."""

    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    restart_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 6, 8, 6)

        _icon_font = QFont("Arial", 14, QFont.Weight.Bold)

        # Previous event
        prev_btn = QPushButton("\u2039")  # Single left angle
        prev_btn.setStyleSheet(_BTN_STYLE)
        prev_btn.setFont(_icon_font)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        prev_btn.clicked.connect(self.previous_clicked.emit)

        # Play, Pause, Restart
        play_btn = QPushButton("\u25B6")  # Play triangle
        play_btn.setStyleSheet(_BTN_STYLE)
        play_btn.setFont(_icon_font)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        play_btn.clicked.connect(self.start_clicked.emit)

        pause_btn = QPushButton("\u23F8")  # Pause
        pause_btn.setStyleSheet(_BTN_STYLE)
        pause_btn.setFont(_icon_font)
        pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pause_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pause_btn.clicked.connect(self.pause_clicked.emit)

        restart_btn = QPushButton("\u21BB")  # Restart / redo
        restart_btn.setStyleSheet(_BTN_STYLE)
        restart_btn.setFont(_icon_font)
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        restart_btn.clicked.connect(self.restart_clicked.emit)

        # Next event
        next_btn = QPushButton("\u203A")  # Single right angle
        next_btn.setStyleSheet(_BTN_STYLE)
        next_btn.setFont(_icon_font)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        next_btn.clicked.connect(self.next_clicked.emit)

        layout.addWidget(prev_btn)
        layout.addWidget(play_btn)
        layout.addWidget(pause_btn)
        layout.addWidget(restart_btn)
        layout.addWidget(next_btn)

        self.setStyleSheet(_OVERLAY_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.adjustSize()
