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
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QPointF, QPoint, QSize, QRect
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QCursor, QGuiApplication
from logger import get_logger, DEBUG_LOGGING

# Application modules
from config import Config
from timer_widget import TimerWidget
from timer_controls import TopControlOverlay, BottomControlOverlay
from tray_manager import TrayIconManager

logger = get_logger(__name__)

# macOS: NSWindow level constants (Qt's WindowStaysOnTopHint is often ignored)
NSNormalWindowLevel = 0
NSFloatingWindowLevel = 3
NSStatusWindowLevel = 25  # More aggressive "always on top"


def _set_macos_window_level(window, floating: bool):
    """Set NSWindow level on macOS so the window actually stays on top of other apps.
    
    Requires pyobjc-framework-Cocoa: pip install pyobjc-framework-Cocoa
    """
    if sys.platform != "darwin":
        return
    try:
        # Use PyObjC to get NSWindow from NSView pointer
        import objc
        from ctypes import c_void_p
        from AppKit import NSView
        
        qwindow = window.windowHandle()
        print(f"[macOS] windowHandle = {qwindow}")
        if not qwindow:
            print("[macOS] ERROR: windowHandle is None")
            return
        
        # winId() returns the NSView* pointer as an integer
        nsview_ptr = int(qwindow.winId())
        print(f"[macOS] NSView pointer = {hex(nsview_ptr)}")
        
        # Convert the pointer to an NSView object using PyObjC
        nsview = objc.objc_object(c_void_p=nsview_ptr)
        print(f"[macOS] NSView object = {nsview}")
        
        # Get the NSWindow from the NSView
        nswindow = nsview.window()
        print(f"[macOS] NSWindow = {nswindow}")
        
        if not nswindow:
            print("[macOS] ERROR: Could not get NSWindow from NSView")
            return
        
        # Set window level using PyObjC
        level = NSStatusWindowLevel if floating else NSNormalWindowLevel
        print(f"[macOS] Setting window level to {level} (floating={floating})")
        nswindow.setLevel_(level)
        nswindow.setHidesOnDeactivate_(False)  # Don't hide when losing focus
        print(f"[macOS] ✓ Window level set successfully")
        
    except ImportError as e:
        print(f"[macOS] PyObjC not available: {e}")
        print("[macOS] Install with: pip install pyobjc-framework-Cocoa")
        print("[macOS] Falling back to Qt's WindowStaysOnTopHint (may not work across apps)")
    except Exception as e:
        print(f"[macOS] ERROR: {e}")
        import traceback
        traceback.print_exc()


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
        self._blink_on = False
        self._blackout_on = False
        
        # Debounce timer for resize events (smoother resizing)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_font_resize)
        self._pending_resize = None
        
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

        # On-hover timer control overlays (top and bottom)
        self.top_overlay = TopControlOverlay(self)
        self.top_overlay.hide()
        self.bottom_overlay = BottomControlOverlay(self)
        self.bottom_overlay.hide()
        
        self._overlay_hide_timer = QTimer(self)
        self._overlay_hide_timer.setSingleShot(True)
        self._overlay_hide_timer.timeout.connect(self._hide_controls_overlays)
        self._connect_control_overlays()

    def _connect_control_overlays(self):
        """Connect overlay buttons to Ontime client control API."""
        def do_start():
            if self.client:
                self.client.start_timer()
        def do_pause():
            if self.client:
                self.client.pause_timer()
        def do_reload():
            if self.client:
                self.client.reload_timer()
        def do_add_minute():
            if self.client:
                self.client.add_time_ms(60000)
        def do_remove_minute():
            if self.client:
                self.client.remove_time_ms(60000)
        def do_previous_event():
            if self.client:
                self.client.load_previous_event()
        def do_next_event():
            if self.client:
                self.client.load_next_event()
        
        # Connect bottom overlay
        self.bottom_overlay.start_clicked.connect(do_start)
        self.bottom_overlay.pause_clicked.connect(do_pause)
        self.bottom_overlay.restart_clicked.connect(do_reload)
        self.bottom_overlay.previous_clicked.connect(do_previous_event)
        self.bottom_overlay.next_clicked.connect(do_next_event)
        
        # Connect top overlay
        self.top_overlay.add_minute_clicked.connect(do_add_minute)
        self.top_overlay.remove_minute_clicked.connect(do_remove_minute)

    def _hide_controls_overlays(self):
        """Hide both control overlays."""
        self.top_overlay.hide()
        self.bottom_overlay.hide()

    def _position_control_overlays(self):
        """Position overlays: +1/-1 at top, play/pause/restart at bottom, both centered."""
        w, h = self.width(), self.height()
        
        # Top overlay (+1, -1) - centered at top edge
        top_w = self.top_overlay.sizeHint().width()
        top_h = self.top_overlay.sizeHint().height()
        self.top_overlay.setGeometry((w - top_w) // 2, 4, top_w, top_h)
        
        # Bottom overlay (play, pause, restart) - centered at bottom edge
        bottom_w = self.bottom_overlay.sizeHint().width()
        bottom_h = self.bottom_overlay.sizeHint().height()
        self.bottom_overlay.setGeometry((w - bottom_w) // 2, h - bottom_h - 4, bottom_w, bottom_h)

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
            ("+/- 1 also change event length", self.toggle_addtime_affects_event_duration, True, self.config.get_addtime_affects_event_duration()),
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
                if text == "Reset Size":
                    # Insert Timer submenu before Reset Size
                    timer_menu = QMenu("Timer", self)
                    for item in [
                        ("Start", self.timer_control_start),
                        ("Pause", self.timer_control_pause),
                        ("Restart", self.timer_control_reload),
                        ("Previous event", self.timer_control_previous_event),
                        ("Next event", self.timer_control_next_event),
                        ("+1 min", self.timer_control_add_minute),
                        ("-1 min", self.timer_control_remove_minute),
                        ("Blink", self.timer_control_blink, True, lambda: self._blink_on),
                        ("Blackout", self.timer_control_blackout, True, lambda: self._blackout_on),
                    ]:
                        label, fn = item[0], item[1]
                        a = QAction(label, self)
                        a.triggered.connect(fn)
                        if len(item) >= 4 and item[2]:
                            a.setCheckable(True)
                            a.setChecked(item[3]() if callable(item[3]) else item[3])
                        timer_menu.addAction(a)
                    menu.addMenu(timer_menu)
                    menu.addSeparator()
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
        self._blink_on = data.blink
        self._blackout_on = data.blackout
        self.tray_manager.update_menu_states()
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

    def timer_control_start(self):
        if self.client:
            self.client.start_timer()

    def timer_control_pause(self):
        if self.client:
            self.client.pause_timer()

    def timer_control_reload(self):
        if self.client:
            self.client.reload_timer()

    def timer_control_previous_event(self):
        if self.client:
            self.client.start_previous_event()

    def timer_control_next_event(self):
        if self.client:
            self.client.start_next_event()

    def timer_control_blink(self):
        self._blink_on = not self._blink_on
        if self.client:
            self.client.set_timer_blink(self._blink_on)
        self.tray_manager.update_menu_states()

    def timer_control_blackout(self):
        self._blackout_on = not self._blackout_on
        if self.client:
            self.client.set_timer_blackout(self._blackout_on)
        self.tray_manager.update_menu_states()

    def timer_control_add_minute(self):
        if self.client:
            self.client.add_time_ms(60000)
            if self.config.get_addtime_affects_event_duration():
                self.client.change_current_event_duration(60000)

    def timer_control_remove_minute(self):
        if self.client:
            self.client.remove_time_ms(60000)
            if self.config.get_addtime_affects_event_duration():
                self.client.change_current_event_duration(-60000)

    def toggle_addtime_affects_event_duration(self):
        value = not self.config.get_addtime_affects_event_duration()
        self.config.set_addtime_affects_event_duration(value)
        self.tray_manager.update_menu_states()

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
        if corner in ['top-left', 'bottom-right']: return Qt.CursorShape.SizeFDiagCursor
        if corner in ['top-right', 'bottom-left']: return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _clamp_to_screen(self, pos: QPoint, size: QSize) -> QPoint:
        """Clamp window position so the window stays within the available screen geometry."""
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return pos
        available = screen.availableGeometry()
        w, h = size.width(), size.height()
        x = max(available.left(), min(pos.x(), available.right() - w))
        y = max(available.top(), min(pos.y(), available.bottom() - h))
        return QPoint(x, y)

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
            
            clamped = self._clamp_to_screen(QPoint(nx, ny), QSize(nw, nh))
            self.move(clamped)
            self.resize(nw, nh)
        else:
            # Drag logic
            new_pos = self.initial_win_pos + delta
            clamped = self._clamp_to_screen(QPoint(new_pos.x(), new_pos.y()), self.size())
            self.move(clamped)

    def mouseReleaseEvent(self, event):
        self.config.set_window_size(self.width(), self.height())
        self.resize_corner = None

    def _apply_font_resize(self):
        """Apply the pending font size update."""
        if self._pending_resize and not self._updating_fonts:
            self._updating_fonts = True
            w, h = self._pending_resize
            self.timer_widget.update_font_sizes(w, h)
            self._updating_fonts = False
            self._pending_resize = None
    
    def resizeEvent(self, event):
        # Debounce font updates for smoother resize
        self._pending_resize = (self.width(), self.height())
        self._resize_timer.start(10)  # 10ms debounce
        
        # Always reposition overlays immediately
        self._position_control_overlays()
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "darwin":
            on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            _set_macos_window_level(self, on_top)

    def enterEvent(self, event):
        self._overlay_hide_timer.stop()
        self._position_control_overlays()
        self.top_overlay.show()
        self.top_overlay.raise_()
        self.bottom_overlay.show()
        self.bottom_overlay.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._overlay_hide_timer.start(300)
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.timer_control_reload()
            self.timer_control_start()

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
