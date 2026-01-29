"""Main application for FloatTime."""
import sys
import os
from pathlib import Path
from typing import Optional

# Setup path
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent
    sys.path.insert(0, str(base_path / 'src'))
else:
    sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QDialog
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QPointF
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QCursor
from logger import get_logger, DEBUG_LOGGING

# Application modules
from config import Config
from timer_widget import TimerWidget
from tray_manager import TrayIconManager

logger = get_logger(__name__)

class TimerUpdateSignal(QObject):
    timer_updated = pyqtSignal(object) # Using object for TimerData

class FloatTimeWindow(QMainWindow):
    """Main window with refactored logic and modular components."""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.client = None
        self.timer_signal = TimerUpdateSignal()
        self.timer_signal.timer_updated.connect(self.on_timer_update)
        
        self.is_locked = self.config.get_locked()
        self._updating_fonts = False
        
        self.setup_ui()
        self.tray_manager = TrayIconManager(self)
        
        # Load settings
        self.timer_widget.set_display_mode(self.config.get_display_mode())
        self.timer_widget.set_background_visible(self.config.get_background_visible())
        
        # Delayed connection
        QTimer.singleShot(100, self.load_configuration)

    def setup_ui(self):
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("FloatTime")
        
        self.timer_widget = TimerWidget()
        self.setCentralWidget(self.timer_widget)
        
        self.setMinimumSize(150, 100)
        size = self.config.get_window_size() or (300, 150)
        self.resize(*size)
        
        self.setMouseTracking(True)
        self.timer_widget.setMouseTracking(True)
        self.setup_shortcuts()
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def setup_shortcuts(self):
        for key, func in [("Ctrl+Q", self.quit_application), ("Ctrl+W", self.quit_application), ("Escape", self.hide)]:
            QShortcut(QKeySequence(key), self).activated.connect(func)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Re-use logic from tray manager or define standard actions
        actions = [
            ("Configure...", self.show_config_dialog),
            (None, None), # Separator
            ("Hide", self.hide),
            ("Always on Top", self.toggle_always_on_top, True, bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)),
            ("Show Background", self.toggle_background, True, self.timer_widget.background_visible),
            ("Lock in Place", self.toggle_locked, True, self.is_locked),
            (None, None),
            ("Show Clock" if self.timer_widget.display_mode == 'timer' else "Show Timer", self.toggle_display_mode, True, self.timer_widget.display_mode == 'clock'),
            (None, None),
            ("Reset Size", self.reset_window_size),
            (None, None),
            ("Quit", self.quit_application)
        ]
        
        for text, func, *extra in actions:
            if text is None:
                menu.addSeparator()
            else:
                action = QAction(text, self)
                if extra:
                    action.setCheckable(extra[0])
                    action.setChecked(extra[1])
                action.triggered.connect(func)
                menu.addAction(action)
        
        menu.exec(self.mapToGlobal(pos))

    def load_configuration(self):
        url = self.config.get_server_url()
        if not url:
            self.show_config_dialog()
        else:
            self.start_client(url)

    def start_client(self, url: str):
        if self.client: self.client.stop()
        from ontime_client import OntimeClient
        self.client = OntimeClient(url, update_callback=self.timer_signal.timer_updated.emit)
        self.client.start()

    def on_timer_update(self, data):
        self.timer_widget.update_timer(data)

    def show_config_dialog(self):
        from ui.config_dialog import ConfigDialog
        curr_url = self.config.get_server_url() or self.config.get_default_url()
        dialog = ConfigDialog(curr_url, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_url:
            self.config.set_server_url(dialog.result_url)
            self.start_client(dialog.result_url)

    def toggle_display_mode(self):
        new_mode = 'clock' if self.timer_widget.display_mode == 'timer' else 'timer'
        self.timer_widget.set_display_mode(new_mode)
        self.config.set_display_mode(new_mode)
        self.tray_manager.update_menu_states()

    def toggle_background(self):
        visible = not self.timer_widget.background_visible
        self.timer_widget.set_background_visible(visible)
        self.config.set_background_visible(visible)
        self.tray_manager.update_menu_states()

    def toggle_locked(self):
        self.is_locked = not self.is_locked
        self.config.set_locked(self.is_locked)
        self.tray_manager.update_menu_states()
        if not self.is_locked: self.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_always_on_top(self):
        if self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.tray_manager.update_menu_states()

    def reset_window_size(self):
        self.resize(300, 150)
        self.config.set_window_size(300, 150)

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        if self.client: self.client.stop()
        QApplication.quit()

    # --- Mouse handling for Drag/Resize ---
    def _get_resize_corner(self, pos):
        w, h, sz = self.width(), self.height(), 40
        if pos.x() <= sz and pos.y() <= sz: return 'top-left'
        if pos.x() >= w - sz and pos.y() <= sz: return 'top-right'
        if pos.x() <= sz and pos.y() >= h - sz: return 'bottom-left'
        if pos.x() >= w - sz and pos.y() >= h - sz: return 'bottom-right'
        return None

    def _get_cursor(self, corner):
        if corner in ['top-left', 'bottom-right']: return Qt.CursorShape.SizeBDiagCursor
        if corner in ['top-right', 'bottom-left']: return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event):
        if self.is_locked or event.button() != Qt.MouseButton.LeftButton: return
        pos = event.position().toPoint()
        self.resize_corner = self._get_resize_corner(pos)
        self.initial_pos = event.globalPosition().toPoint()
        self.initial_win_pos = self.pos()
        self.initial_size = self.size()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        corner = self._get_resize_corner(pos)
        self.setCursor(self._get_cursor(corner) if corner else Qt.CursorShape.ArrowCursor)
        
        if self.is_locked or not (event.buttons() & Qt.MouseButton.LeftButton): return
        
        delta = event.globalPosition().toPoint() - self.initial_pos
        if self.resize_corner:
            # Resize logic
            nw, nh = self.initial_size.width(), self.initial_size.height()
            nx, ny = self.initial_win_pos.x(), self.initial_win_pos.y()
            
            if 'left' in self.resize_corner:
                nw = max(150, nw - delta.x())
                nx = self.initial_win_pos.x() + (self.initial_size.width() - nw)
            if 'right' in self.resize_corner:
                nw = max(150, nw + delta.x())
            if 'top' in self.resize_corner:
                nh = max(100, nh - delta.y())
                ny = self.initial_win_pos.y() + (self.initial_size.height() - nh)
            if 'bottom' in self.resize_corner:
                nh = max(100, nh + delta.y())
                
            self.move(nx, ny)
            self.resize(nw, nh)
        else:
            # Drag logic
            self.move(self.initial_win_pos + delta)

    def mouseReleaseEvent(self, event):
        self.config.set_window_size(self.width(), self.height())
        self.resize_corner = None

    def resizeEvent(self, event):
        if not self._updating_fonts:
            self._updating_fonts = True
            self.timer_widget.update_font_sizes(self.width(), self.height())
            self._updating_fonts = False
        super().resizeEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.quit_application()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

def main():
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = FloatTimeWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
