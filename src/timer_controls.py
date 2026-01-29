"""On-hover timer control overlay with play, pause, restart, +1, -1 buttons."""
from PyQt6.QtWidgets import QWidget, QPushButton, QGridLayout, QSizePolicy
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


class TimerControlOverlay(QWidget):
    """Overlay with start, pause, restart, +1 min, -1 min buttons."""

    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    restart_clicked = pyqtSignal()
    add_minute_clicked = pyqtSignal()
    remove_minute_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 6, 8, 8)

        # Top row: Play, Pause, Restart
        play_btn = QPushButton("\u25B6")  # Play triangle
        play_btn.setStyleSheet(_BTN_STYLE)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        play_btn.clicked.connect(self.start_clicked.emit)

        pause_btn = QPushButton("\u23F8")  # Pause
        pause_btn.setStyleSheet(_BTN_STYLE)
        pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pause_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pause_btn.clicked.connect(self.pause_clicked.emit)

        restart_btn = QPushButton("\u21BB")  # Restart / redo
        restart_btn.setStyleSheet(_BTN_STYLE)
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        restart_btn.clicked.connect(self.restart_clicked.emit)

        layout.addWidget(play_btn, 0, 0)
        layout.addWidget(pause_btn, 0, 1)
        layout.addWidget(restart_btn, 0, 2)

        # Bottom row: +1, -1
        add_btn = QPushButton("+1")
        add_btn.setStyleSheet(_BTN_STYLE)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        add_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        add_btn.clicked.connect(self.add_minute_clicked.emit)

        remove_btn = QPushButton("\u2212 1")  # Minus 1
        remove_btn.setStyleSheet(_BTN_STYLE)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        remove_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        remove_btn.clicked.connect(self.remove_minute_clicked.emit)

        layout.addWidget(add_btn, 1, 0)
        layout.addWidget(remove_btn, 1, 1)

        self.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 8px;")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.adjustSize()
