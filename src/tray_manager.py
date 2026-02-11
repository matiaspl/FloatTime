"""Tray icon management for FloatTime."""
from PyQt6.QtWidgets import QSystemTrayIcon
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QObject
from logger import get_logger

logger = get_logger(__name__)

class TrayIconManager(QObject):
    """Manages the system tray icon and its menu."""
    
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.window = parent_window
        self.tray_icon = None
        self._setup_tray()

    def _setup_tray(self):
        """Initialize the tray icon and context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
            return

        self.tray_icon = QSystemTrayIcon(self.window)
        self.tray_icon.setIcon(self._create_tray_icon())
        self.tray_icon.setToolTip("FloatTime - Ontime Overlay Timer")
        
        # Use shared menu from window
        menu, action_refs = self.window.build_app_menu(parent=None)
        self.window._menu_action_refs = action_refs
        self.tray_icon.setContextMenu(menu)
        menu.aboutToShow.connect(self.window.update_menu_states)
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _create_tray_icon(self) -> QIcon:
        """Create a simple tray icon pixmap."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawEllipse(2, 2, 12, 12)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.drawLine(8, 8, 8, 4)
        painter.drawLine(8, 8, 11, 8)
        
        painter.end()
        return QIcon(pixmap)

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.window.show_window()
