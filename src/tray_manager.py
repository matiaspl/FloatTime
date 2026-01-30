"""Tray icon management for FloatTime."""
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush, QPen
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
        
        # Create tray menu
        tray_menu = self._create_menu()
        self.tray_icon.setContextMenu(tray_menu)
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _create_menu(self) -> QMenu:
        """Create the tray context menu."""
        menu = QMenu()
        
        # Configure action
        config_action = QAction("Configure...", self.window)
        config_action.triggered.connect(self.window.show_config_dialog)
        menu.addAction(config_action)
        
        # Show/Hide action
        self.show_action = QAction("Show", self.window)
        self.show_action.triggered.connect(self.window.show_window)
        menu.addAction(self.show_action)
        
        # Always on top toggle
        self.always_on_top_action = QAction("Always on Top", self.window)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(True)
        self.always_on_top_action.triggered.connect(self.window.toggle_always_on_top)
        menu.addAction(self.always_on_top_action)
        
        # Background visibility toggle
        self.background_visible_action = QAction("Show Background", self.window)
        self.background_visible_action.setCheckable(True)
        self.background_visible_action.setChecked(self.window.config.get_background_visible())
        self.background_visible_action.triggered.connect(self.window.toggle_background)
        menu.addAction(self.background_visible_action)
        
        # Lock in place toggle
        self.locked_action = QAction("Lock in Place", self.window)
        self.locked_action.setCheckable(True)
        self.locked_action.setChecked(self.window.is_locked)
        self.locked_action.triggered.connect(self.window.toggle_locked)
        menu.addAction(self.locked_action)

        # On-hover controls toggle
        self.hover_controls_action = QAction("On-hover controls", self.window)
        self.hover_controls_action.setCheckable(True)
        self.hover_controls_action.setChecked(self.window.config.get_hover_controls_enabled())
        self.hover_controls_action.triggered.connect(self.window.toggle_hover_controls)
        menu.addAction(self.hover_controls_action)
        
        menu.addSeparator()
        
        # Display mode toggle
        self.display_mode_action = QAction("Show Clock", self.window)
        self.display_mode_action.setCheckable(True)
        self.display_mode_action.setChecked(False)
        self.display_mode_action.triggered.connect(self.window.toggle_display_mode)
        menu.addAction(self.display_mode_action)

        # +/- 1 also change event length
        self.addtime_affects_duration_action = QAction("+/- 1 changes event length", self.window)
        self.addtime_affects_duration_action.setCheckable(True)
        self.addtime_affects_duration_action.setChecked(self.window.config.get_addtime_affects_event_duration())
        self.addtime_affects_duration_action.triggered.connect(self.window.toggle_addtime_affects_event_duration)
        menu.addAction(self.addtime_affects_duration_action)
        
        menu.addSeparator()

        # Timer controls submenu
        timer_menu = QMenu("Timer", menu)
        start_action = QAction("Start", self.window)
        start_action.triggered.connect(self.window.timer_control_start)
        timer_menu.addAction(start_action)
        pause_action = QAction("Pause", self.window)
        pause_action.triggered.connect(self.window.timer_control_pause)
        timer_menu.addAction(pause_action)
        reload_action = QAction("Restart", self.window)
        reload_action.triggered.connect(self.window.timer_control_reload)
        timer_menu.addAction(reload_action)
        prev_event_action = QAction("Previous event", self.window)
        prev_event_action.triggered.connect(self.window.timer_control_previous_event)
        timer_menu.addAction(prev_event_action)
        next_event_action = QAction("Next event", self.window)
        next_event_action.triggered.connect(self.window.timer_control_next_event)
        timer_menu.addAction(next_event_action)
        timer_menu.addSeparator()
        add_min_action = QAction("+1 min", self.window)
        add_min_action.triggered.connect(self.window.timer_control_add_minute)
        timer_menu.addAction(add_min_action)
        remove_min_action = QAction("\u2212 1 min", self.window)
        remove_min_action.triggered.connect(self.window.timer_control_remove_minute)
        timer_menu.addAction(remove_min_action)
        timer_menu.addSeparator()
        self.blink_action = QAction("Blink", self.window)
        self.blink_action.setCheckable(True)
        self.blink_action.setChecked(False)
        self.blink_action.triggered.connect(self.window.timer_control_blink)
        timer_menu.addAction(self.blink_action)
        self.blackout_action = QAction("Blackout", self.window)
        self.blackout_action.setCheckable(True)
        self.blackout_action.setChecked(False)
        self.blackout_action.triggered.connect(self.window.timer_control_blackout)
        timer_menu.addAction(self.blackout_action)
        menu.addMenu(timer_menu)

        menu.addSeparator()
        
        # Reset size action
        reset_size_action = QAction("Reset Size", self.window)
        reset_size_action.triggered.connect(self.window.reset_window_size)
        menu.addAction(reset_size_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self.window)
        quit_action.triggered.connect(self.window.quit_application)
        menu.addAction(quit_action)
        
        return menu

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

    def update_menu_states(self):
        """Update the checked states of menu actions based on window state."""
        self.background_visible_action.setChecked(self.window.config.get_background_visible())
        self.locked_action.setChecked(self.window.is_locked)
        
        current_mode = self.window.timer_widget.display_mode
        self.display_mode_action.blockSignals(True)
        self.display_mode_action.setChecked(current_mode == 'clock')
        self.display_mode_action.setText("Show Timer" if current_mode == 'clock' else "Show Clock")
        self.display_mode_action.blockSignals(False)
        
        self.always_on_top_action.setChecked(
            bool(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )
        self.addtime_affects_duration_action.setChecked(
            self.window.config.get_addtime_affects_event_duration()
        )
        self.hover_controls_action.setChecked(self.window.config.get_hover_controls_enabled())
        self.blink_action.setChecked(self.window._blink_on)
        self.blackout_action.setChecked(self.window._blackout_on)

