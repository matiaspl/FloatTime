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

from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QDialog, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QPointF, QPoint, QSize, QRect, QEvent
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QCursor, QGuiApplication
from logger import get_logger, DEBUG_LOGGING

# Application modules
from config import Config
from timer_widget import TimerWidget
from progress_bar_widget import ProgressBarWidget
from timer_controls import TopControlOverlay, BottomControlOverlay
from tray_manager import TrayIconManager
from local_timer import LocalTimer

logger = get_logger(__name__)

# macOS: NSWindow level constants (Qt's WindowStaysOnTopHint is often ignored)
NSNormalWindowLevel = 0
NSFloatingWindowLevel = 3
NSStatusWindowLevel = 25  # More aggressive "always on top"

# macOS: Event monitor for preventWindowOrdering
_macos_no_activate_monitor = None


def _setup_macos_no_activate_monitor(nswindow):
    """Set up local event monitor to call preventWindowOrdering on mouse down in our window."""
    global _macos_no_activate_monitor
    if _macos_no_activate_monitor is not None or sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSEvent, NSLeftMouseDownMask, NSRightMouseDownMask
        window_number = nswindow.windowNumber()

        def handle_mouse_down(event):
            if event.windowNumber() == window_number:
                NSApp.preventWindowOrdering()
            return event

        mask = NSLeftMouseDownMask | NSRightMouseDownMask
        _macos_no_activate_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(mask, handle_mouse_down)
        logger.debug("[macOS] Event monitor set up (preventWindowOrdering)")
    except Exception as e:
        logger.warning(f"[macOS] Failed to set up event monitor: {e}")


def _reapply_macos_activation_policy():
    """Re-apply accessory activation policy (Qt may reset it when window is shown)."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyAccessory
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        logger.debug("[macOS] Activation policy re-applied (accessory)")
    except Exception as e:
        logger.warning(f"[macOS] Failed to re-apply activation policy: {e}")


def _set_macos_window_level(window, floating: bool):
    """Set NSWindow level on macOS so the window actually stays on top of other apps.
    
    Requires pyobjc-framework-Cocoa: pip install pyobjc-framework-Cocoa
    """
    if sys.platform != "darwin":
        return
    try:
        import objc
        from ctypes import c_void_p
        from AppKit import NSView
        
        qwindow = window.windowHandle()
        if not qwindow:
            logger.warning("[macOS] windowHandle is None")
            return
        
        # winId() returns the NSView* pointer as an integer
        nsview_ptr = int(qwindow.winId())
        nsview = objc.objc_object(c_void_p=nsview_ptr)
        nswindow = nsview.window()
        
        if not nswindow:
            logger.warning("[macOS] Could not get NSWindow from NSView")
            return
        
        # Set window level
        level = NSStatusWindowLevel if floating else NSNormalWindowLevel
        nswindow.setLevel_(level)
        nswindow.setHidesOnDeactivate_(False)
        
        # Collection behaviors for Spaces and window cycling
        from AppKit import (
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorStationary,
            NSWindowCollectionBehaviorIgnoresCycle
        )
        behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces |
                    NSWindowCollectionBehaviorStationary |
                    NSWindowCollectionBehaviorIgnoresCycle)
        nswindow.setCollectionBehavior_(behavior)
        
        # Enable mouse tracking even when window is not active
        nswindow.setAcceptsMouseMovedEvents_(True)
        
        # Undocumented API: prevents window (and app) from activating on click (if available).
        try:
            if hasattr(nswindow, "_setPreventsActivation_"):
                nswindow._setPreventsActivation_(True)
                logger.debug("[macOS] _setPreventsActivation(True) applied")
            elif hasattr(nswindow, "setPreventsActivation_"):
                nswindow.setPreventsActivation_(True)
                logger.debug("[macOS] setPreventsActivation(True) applied")
        except Exception:
            pass
        
        # Event monitor: prevent window ordering on mouse down
        _setup_macos_no_activate_monitor(nswindow)
        
        logger.debug(f"[macOS] Window level set to {level}")
        
    except ImportError as e:
        logger.warning(f"[macOS] PyObjC not available: {e}. Install with: pip install pyobjc-framework-Cocoa")
    except Exception as e:
        logger.error(f"[macOS] Failed to set window level: {e}")


def _set_windows_no_activate(window):
    """Set WS_EX_NOACTIVATE on Windows so clicking the overlay does not steal focus from other apps."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000

        wh = window.windowHandle()
        if not wh:
            return
        hwnd = int(wh.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        # Extended style is 32-bit; use c_void_p for pointer-sized HWND/LONG_PTR on 32/64 bit
        user32.GetWindowLongPtrW.restype = ctypes.c_void_p
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        ex_style = ex_style or 0
        new_style = (ex_style if isinstance(ex_style, int) else getattr(ex_style, 'value', 0) or 0) | WS_EX_NOACTIVATE
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_style)
    except Exception as e:
        logger.debug("Could not set WS_EX_NOACTIVATE: %s", e)


class TimerUpdateSignal(QObject):
    timer_updated = pyqtSignal(object) # Using object for TimerData

class FloatTimeWindow(QMainWindow):
    """Main window with refactored logic and modular components."""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.client = None
        self.local_timer = None  # Set when headless (no Ontime server)
        self.timer_signal = TimerUpdateSignal()
        self.timer_signal.timer_updated.connect(self.on_timer_update)
        
        self.is_locked = self.config.get_locked()
        self._updating_fonts = False
        self._blink_on = False
        self._blackout_on = False
        self._screen_changed_connected = False
        
        # Debounce timer for resize events (smoother resizing)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_font_resize)
        self._pending_resize = None
        
        # Drag/resize state (set in mousePressEvent; must exist if move arrives before press)
        self.resize_corner = None
        self._drag_or_resize_started = False
        self.initial_pos = QPoint(0, 0)
        self.initial_win_pos = QPoint(0, 0)
        self.initial_size = QSize(0, 0)
        
        self.setup_ui()
        self.tray_manager = TrayIconManager(self)
        
        # Load settings
        self.timer_widget.set_display_mode(self.config.get_display_mode())
        self.timer_widget.set_background_visible(self.config.get_background_visible())
        self.progress_bar_widget.setVisible(self.config.get_progress_bar_visible())
        self._apply_color_settings()
        
        # Delayed connection
        QTimer.singleShot(100, self.load_configuration)

    def setup_ui(self):
        flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        # On macOS, prevent window from stealing focus when clicked
        if sys.platform == "darwin":
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)  # Enable hover events even when not active
        self.setWindowTitle("FloatTime")
        
        self.timer_widget = TimerWidget()
        self.progress_bar_widget = ProgressBarWidget()
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.timer_widget, 1)
        layout.addWidget(self.progress_bar_widget, 0)
        self.setCentralWidget(container)
        
        self.setMinimumSize(150, 100)
        size = self.config.get_window_size() or (300, 150)
        self.resize(*size)
        self._restore_window_position()
        
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
        self.bottom_overlay.set_mode('aux' if self.config.get_timer_source() != 'main' else 'main')
        
        self._overlay_hide_timer = QTimer(self)
        self._overlay_hide_timer.setSingleShot(True)
        self._overlay_hide_timer.timeout.connect(self._hide_controls_overlays)
        self._overlay_idle_timer = QTimer(self)
        self._overlay_idle_timer.setSingleShot(True)
        self._overlay_idle_timer.timeout.connect(self._hide_controls_overlays_if_not_hovered)
        self._overlay_idle_timeout_ms = 1500
        self._connect_control_overlays()
        # Global mouse events to hide overlays on outside click and keep idle timeout fresh on interaction.
        QApplication.instance().installEventFilter(self)
        
        # macOS: poll mouse position since enter/leave events don't work when inactive
        self._mouse_over_window = False
        if sys.platform == "darwin":
            self._hover_poll_timer = QTimer(self)
            self._hover_poll_timer.timeout.connect(self._poll_mouse_position)
            self._hover_poll_timer.start(100)  # Check every 100ms

    def _connect_control_overlays(self):
        """Connect overlay buttons to timer control (Ontime client or local headless timer)."""
        def _aux_id():
            src = self.client.get_timer_source() if self.client else 'main'
            return int(src[-1]) if src.startswith('aux') else None

        def do_stop_aux():
            if self.client:
                aid = _aux_id()
                if aid:
                    self.client.stop_aux_timer(aid)

        # Use timer_control_* so overlays work with both client and local_timer (headless)
        self.bottom_overlay.start_clicked.connect(self.timer_control_start)
        self.bottom_overlay.pause_clicked.connect(self.timer_control_pause)
        self.bottom_overlay.restart_clicked.connect(self.timer_control_reload)
        self.bottom_overlay.stop_clicked.connect(do_stop_aux)
        self.bottom_overlay.previous_clicked.connect(self.timer_control_previous_event)
        self.bottom_overlay.next_clicked.connect(self.timer_control_next_event)
        self.top_overlay.remove_minute_clicked.connect(self.timer_control_remove_minute)
        self.top_overlay.add_minute_clicked.connect(self.timer_control_add_minute)

    def _hide_controls_overlays(self):
        """Hide both control overlays."""
        self.top_overlay.hide()
        self.bottom_overlay.hide()
        self._overlay_idle_timer.stop()

    def _window_contains_global_pos(self, global_pos):
        return self.frameGeometry().contains(global_pos)

    def _overlay_contains_global_pos(self, global_pos):
        top_rect = QRect(self.top_overlay.mapToGlobal(self.top_overlay.rect().topLeft()), self.top_overlay.size())
        bottom_rect = QRect(self.bottom_overlay.mapToGlobal(self.bottom_overlay.rect().topLeft()), self.bottom_overlay.size())
        return top_rect.contains(global_pos) or bottom_rect.contains(global_pos)

    def _show_controls_overlays(self):
        self._overlay_hide_timer.stop()
        self._position_control_overlays()
        self.top_overlay.show()
        self.bottom_overlay.show()
        self.top_overlay.raise_()
        self.bottom_overlay.raise_()
        self._overlay_idle_timer.start(self._overlay_idle_timeout_ms)

    def _hide_controls_overlays_if_not_hovered(self):
        pos = QCursor.pos()
        if not (self._window_contains_global_pos(pos) or self._overlay_contains_global_pos(pos)):
            self._hide_controls_overlays()
        else:
            self._overlay_idle_timer.start(self._overlay_idle_timeout_ms)

    def _poll_mouse_position(self):
        """macOS: poll cursor position to detect hover since enter/leave don't work when inactive."""
        if not self.isVisible() or not self.config.get_hover_controls_enabled() or self.timer_widget.display_mode == 'clock':
            if self._mouse_over_window:
                self._mouse_over_window = False
                self._overlay_hide_timer.start(300)
            return
        
        cursor_pos = QCursor.pos()
        window_rect = self.geometry()
        is_over = window_rect.contains(cursor_pos)
        
        if is_over and not self._mouse_over_window:
            # Mouse entered
            self._mouse_over_window = True
            self._show_controls_overlays()
        elif not is_over and self._mouse_over_window:
            # Mouse left
            self._mouse_over_window = False
            self._overlay_hide_timer.start(300)
        elif is_over and self.top_overlay.isVisible():
            self._overlay_idle_timer.start(self._overlay_idle_timeout_ms)

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

    def build_app_menu(self, parent=None):
        """Build the shared application menu (tray and context). Returns (menu, action_refs)."""
        parent = parent or self
        menu = QMenu(parent)
        refs = {}
        
        def do_show_hide():
            if self.isVisible():
                self.hide()
            else:
                self.show_window()
        
        actions = [
            ("Configure...", self.show_config_dialog),
            (None, None),
            ("show_hide", do_show_hide),  # special: label set from visibility
            ("Always on Top", self.toggle_always_on_top, True, bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint), "always_on_top"),
            ("Show Background", self.toggle_background, True, self.timer_widget.background_visible, "background_visible"),
            ("Show progress bar", self.toggle_progress_bar, True, self.progress_bar_widget.isVisible(), "progress_bar_visible"),
            ("Lock in Place", self.toggle_locked, True, self.is_locked, "locked"),
            ("On-hover controls", self.toggle_hover_controls, True, self.config.get_hover_controls_enabled(), "hover_controls"),
            (None, None),
            ("+/- 1 changes event length", self.toggle_addtime_affects_event_duration, True, self.config.get_addtime_affects_event_duration(), "addtime_affects_duration"),
            (None, None),
            ("Timer source", None),
            (None, None),
            ("Reset Size", self.reset_window_size),
            (None, None),
            ("Quit", self.quit_application)
        ]
        
        for item in actions:
            if item[0] is None:
                menu.addSeparator()
                continue
            text, func = item[0], item[1]
            if text == "Timer source":
                src_menu = QMenu("Timer source", parent)
                is_clock = self.timer_widget.display_mode == 'clock'
                current = self.config.get_timer_source()
                is_simple = self.local_timer is not None
                for label, value in [("Main", "main"), ("Aux 1", "aux1"), ("Aux 2", "aux2"), ("Aux 3", "aux3"), ("System clock", "clock"), ("Simple timer", "simple")]:
                    a = QAction(label, parent)
                    a.setCheckable(True)
                    a.setChecked(
                        (value == "simple" and is_simple)
                        or (value == "clock" and not is_simple and is_clock)
                        or (value not in ("clock", "simple") and not is_simple and not is_clock and current == value)
                    )
                    a.triggered.connect(lambda checked, v=value: self.set_timer_source(v))
                    src_menu.addAction(a)
                    refs[f"timer_source_{value}"] = a
                menu.addMenu(src_menu)
                continue
            if text == "show_hide":
                action = QAction("Hide" if self.isVisible() else "Show", parent)
                action.triggered.connect(do_show_hide)
                refs["show_hide"] = action
                menu.addAction(action)
                continue
            # (text, func) or (text, func, checkable, checked, ref_key)
            extra = list(item[2:]) if len(item) > 2 else []
            ref_key = extra.pop() if len(extra) == 3 else None  # last optional is ref key
            action = QAction(text, parent)
            if len(extra) >= 2:
                action.setCheckable(extra[0])
                action.setChecked(extra[1])
                if ref_key:
                    refs[ref_key] = action
            action.triggered.connect(func)
            if text == "Reset Size":
                timer_menu = QMenu("Timer controls", parent)
                is_clock = self.timer_widget.display_mode == 'clock'
                current_src = self.config.get_timer_source()
                in_aux = current_src in ('aux1', 'aux2', 'aux3')
                headless = self.local_timer is not None
                for titem in [
                    ("Start", self.timer_control_start, "timer_start"),
                    ("Pause", self.timer_control_pause, "timer_pause"),
                    ("Restart", self.timer_control_reload, "timer_restart"),
                    ("Previous event", self.timer_control_previous_event, "timer_prev_event"),
                    ("Next event", self.timer_control_next_event, "timer_next_event"),
                    ("+1 min", self.timer_control_add_minute, "timer_add_min"),
                    ("-1 min", self.timer_control_remove_minute, "timer_remove_min"),
                    ("Blink", self.timer_control_blink, True, lambda: self._blink_on, "blink"),
                    ("Blackout", self.timer_control_blackout, True, lambda: self._blackout_on, "blackout"),
                ]:
                    label, fn = titem[0], titem[1]
                    a = QAction(label, parent)
                    a.triggered.connect(fn)
                    if len(titem) >= 5 and titem[2]:
                        a.setCheckable(True)
                        a.setChecked(titem[3]() if callable(titem[3]) else titem[3])
                        ref_key = titem[4]
                        refs[ref_key] = a
                    else:
                        ref_key = titem[2] if len(titem) >= 3 else None
                        if ref_key:
                            refs[ref_key] = a
                    # In headless all timer controls enabled; otherwise disable in clock, prev/next in aux1-3
                    a.setEnabled(headless or not is_clock)
                    if ref_key in ('timer_prev_event', 'timer_next_event'):
                        a.setEnabled(headless or (not is_clock and not in_aux))
                    timer_menu.addAction(a)
                menu.addMenu(timer_menu)
                menu.addSeparator()
            menu.addAction(action)
        self._attach_menu_auto_dismiss(menu)
        return menu, refs

    def _attach_menu_auto_dismiss(self, menu: QMenu):
        """Close popup menu as soon as the cursor leaves the menu area.

        - An *open grace* period (800 ms) lets the user move from the tray
          icon to the menu before tracking starts (tray menus open away
          from the cursor on Windows).
        - A *leave grace* period (300 ms) prevents flicker when the cursor
          travels between a parent menu item and its child submenu.
        """
        if getattr(menu, "_auto_dismiss_attached", False):
            return

        OPEN_GRACE_MS = 800     # ignore cursor position right after open
        LEAVE_GRACE_MS = 300    # submenu-transition grace period
        POLL_MS = 30            # cursor check interval (~33 fps)

        state = {"tracking": False}   # start tracking only after open grace

        open_timer = QTimer(menu)
        open_timer.setSingleShot(True)
        open_timer.setInterval(OPEN_GRACE_MS)

        leave_timer = QTimer(menu)
        leave_timer.setSingleShot(True)
        leave_timer.setInterval(LEAVE_GRACE_MS)

        poll_timer = QTimer(menu)
        poll_timer.setInterval(POLL_MS)

        def _cursor_over_any_menu() -> bool:
            pos = QCursor.pos()
            for w in QApplication.topLevelWidgets():
                if isinstance(w, QMenu) and w.isVisible() and w.geometry().contains(pos):
                    return True
            popup = QApplication.activePopupWidget()
            if isinstance(popup, QMenu) and popup.isVisible() and popup.geometry().contains(pos):
                return True
            return False

        def _close_all():
            for w in QApplication.topLevelWidgets():
                if isinstance(w, QMenu) and w.isVisible():
                    w.close()

        def _on_open_grace_done():
            state["tracking"] = True

        def _on_leave_timeout():
            if menu.isVisible() and not _cursor_over_any_menu():
                _close_all()

        def _poll():
            if not menu.isVisible() or not state["tracking"]:
                return
            if _cursor_over_any_menu():
                leave_timer.stop()
            elif not leave_timer.isActive():
                leave_timer.start()

        def _on_show():
            state["tracking"] = False
            leave_timer.stop()
            open_timer.start()
            poll_timer.start()

        def _on_hide():
            poll_timer.stop()
            open_timer.stop()
            leave_timer.stop()
            state["tracking"] = False

        open_timer.timeout.connect(_on_open_grace_done)
        leave_timer.timeout.connect(_on_leave_timeout)
        poll_timer.timeout.connect(_poll)

        menu.aboutToShow.connect(_on_show)
        menu.aboutToHide.connect(_on_hide)

        menu._auto_dismiss_attached = True
        menu._auto_dismiss_open_timer = open_timer
        menu._auto_dismiss_leave_timer = leave_timer
        menu._auto_dismiss_poll_timer = poll_timer

    def update_menu_states(self):
        """Update checked state and Show/Hide text for the shared menu (used by tray)."""
        refs = getattr(self, '_menu_action_refs', None)
        if not refs:
            return
        if 'show_hide' in refs:
            refs['show_hide'].setText("Hide" if self.isVisible() else "Show")
        if 'always_on_top' in refs:
            refs['always_on_top'].setChecked(bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        if 'background_visible' in refs:
            refs['background_visible'].setChecked(self.timer_widget.background_visible)
        if 'progress_bar_visible' in refs:
            refs['progress_bar_visible'].setChecked(self.progress_bar_widget.isVisible())
        if 'locked' in refs:
            refs['locked'].setChecked(self.is_locked)
        if 'hover_controls' in refs:
            refs['hover_controls'].setChecked(self.config.get_hover_controls_enabled())
        if 'addtime_affects_duration' in refs:
            refs['addtime_affects_duration'].setChecked(self.config.get_addtime_affects_event_duration())
        if 'blink' in refs:
            refs['blink'].setChecked(self._blink_on)
        if 'blackout' in refs:
            refs['blackout'].setChecked(self._blackout_on)
        is_clock = self.timer_widget.display_mode == 'clock'
        current = self.config.get_timer_source()
        in_aux = current in ('aux1', 'aux2', 'aux3')
        headless = self.local_timer is not None
        for value in ('main', 'aux1', 'aux2', 'aux3', 'clock', 'simple'):
            key = f'timer_source_{value}'
            if key in refs:
                refs[key].setChecked(
                    (value == "simple" and headless)
                    or (value == "clock" and not headless and is_clock)
                    or (value not in ("clock", "simple") and not headless and not is_clock and current == value)
                )
        # Timer controls: in headless all enabled; otherwise disabled in clock, prev/next disabled in aux1-3
        for key in ('timer_start', 'timer_pause', 'timer_restart', 'timer_add_min', 'timer_remove_min', 'blink', 'blackout'):
            if key in refs:
                refs[key].setEnabled(headless or not is_clock)
        for key in ('timer_prev_event', 'timer_next_event'):
            if key in refs:
                refs[key].setEnabled(headless or (not is_clock and not in_aux))

    def show_context_menu(self, pos):
        menu, _ = self.build_app_menu(self)
        menu.exec(self.mapToGlobal(pos))

    def load_configuration(self):
        selected_source = self.config.get_selected_timer_source()
        if selected_source == 'simple':
            self._enable_simple_timer()
            return
        if selected_source == 'clock':
            self._disable_simple_timer()
            self.timer_widget.set_display_mode('clock')
            self.config.set_display_mode('clock')
            self.update_menu_states()
            return
        url = self.config.get_server_url()
        if not url:
            self.show_config_dialog()
            return
        self.start_client(url)
        # Restore last selected Ontime source (main/aux1/aux2/aux3).
        if selected_source in ('main', 'aux1', 'aux2', 'aux3'):
            self.config.set_timer_source(selected_source)
            self._apply_timer_source_to_ui()
            self.client.refresh_display()

    def start_client(self, url: str):
        if self.client: self.client.stop()
        from ontime_client import OntimeClient
        self.client = OntimeClient(url, update_callback=self.timer_signal.timer_updated.emit)
        self.client.set_timer_source(self.config.get_timer_source())
        self.client.start()
        self._apply_timer_source_to_ui()

    def _enable_simple_timer(self):
        """Enable local simple timer source and stop Ontime client updates."""
        if self.client:
            self.client.stop()
            self.client = None
        presets = self.config.get_headless_preset_minutes()
        warning_sec = self.config.get_headless_time_warning_sec()
        danger_sec = self.config.get_headless_time_danger_sec()
        warning_ms = warning_sec * 1000
        danger_ms = danger_sec * 1000
        if self.local_timer:
            self.local_timer.set_preset_minutes(presets)
            self.local_timer.set_warning_danger_ms(warning_ms, danger_ms)
        else:
            self.local_timer = LocalTimer(
                preset_minutes=presets,
                update_callback=self.timer_signal.timer_updated.emit,
                warning_ms=warning_ms,
                danger_ms=danger_ms,
                parent=self,
            )
        self.timer_widget.set_display_mode('timer')
        self.config.set_display_mode('timer')
        self.bottom_overlay.set_mode('main')

    def _disable_simple_timer(self):
        """Disable local simple timer source."""
        if self.local_timer:
            self.local_timer.stop()
            self.local_timer.deleteLater()
            self.local_timer = None

    def _apply_timer_source_to_ui(self):
        """Sync overlay mode and client source from config."""
        src = self.config.get_timer_source()
        if self.client:
            self.client.set_timer_source(src)
        self.bottom_overlay.set_mode('aux' if src != 'main' else 'main')

    def on_timer_update(self, data):
        self._blink_on = data.blink
        self._blackout_on = data.blackout
        self.bottom_overlay.set_mode('aux' if data.timer_source != 'main' else 'main')
        self.update_menu_states()
        self.timer_widget.update_timer(data)
        self.progress_bar_widget.update_timer(data)

    def _apply_color_settings(self):
        """Apply color settings from config to timer widget and progress bar."""
        self.timer_widget.apply_color_settings(self.config)
        self.progress_bar_widget.apply_color_settings(self.config)

    def show_config_dialog(self):
        from ui.config_dialog import ConfigDialog
        curr_url = self.config.get_server_url() or self.config.get_default_url()
        dialog = ConfigDialog(
            current_url=curr_url or "",
            simple_presets=self.config.get_headless_preset_minutes(),
            simple_warning_sec=self.config.get_headless_time_warning_sec(),
            simple_danger_sec=self.config.get_headless_time_danger_sec(),
            color_timer_label=self.config.get_color_timer_label(),
            color_clock_label=self.config.get_color_clock_label(),
            color_warning=self.config.get_color_warning(),
            color_danger=self.config.get_color_danger(),
            color_timer_background=self.config.get_color_timer_background(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.set_headless_preset_minutes(dialog.result_simple_presets)
            self.config.set_headless_time_warning_sec(dialog.result_simple_warning_sec)
            self.config.set_headless_time_danger_sec(dialog.result_simple_danger_sec)
            self.config.set_color_timer_label(dialog.result_color_timer_label)
            self.config.set_color_clock_label(dialog.result_color_clock_label)
            self.config.set_color_warning(dialog.result_color_warning)
            self.config.set_color_danger(dialog.result_color_danger)
            self.config.set_color_timer_background(dialog.result_color_timer_background)
            self._apply_color_settings()

            if self.local_timer:
                self._enable_simple_timer()

            url_to_save = dialog.result_url if dialog.result_url else ""
            self.config.set_server_url(url_to_save)
            if url_to_save and not self.local_timer:
                self.start_client(url_to_save)
            elif not url_to_save and self.client:
                self.client.stop()
                self.client = None

    def toggle_display_mode(self):
        new_mode = 'clock' if self.timer_widget.display_mode == 'timer' else 'timer'
        self.timer_widget.set_display_mode(new_mode)
        self.config.set_display_mode(new_mode)
        if new_mode == 'clock':
            self._hide_controls_overlays()
        self.update_menu_states()

    def toggle_background(self):
        visible = not self.timer_widget.background_visible
        self.timer_widget.set_background_visible(visible)
        self.config.set_background_visible(visible)
        self.update_menu_states()

    def toggle_progress_bar(self):
        visible = not self.progress_bar_widget.isVisible()
        self.progress_bar_widget.setVisible(visible)
        self.config.set_progress_bar_visible(visible)
        self.update_menu_states()

    def toggle_locked(self):
        self.is_locked = not self.is_locked
        self.config.set_locked(self.is_locked)
        self.update_menu_states()
        if not self.is_locked: self.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_always_on_top(self):
        new_flags = self.windowFlags()
        if new_flags & Qt.WindowType.WindowStaysOnTopHint:
            new_flags &= ~Qt.WindowType.WindowStaysOnTopHint
        else:
            new_flags |= Qt.WindowType.WindowStaysOnTopHint
        # Ensure macOS keeps WindowDoesNotAcceptFocus
        if sys.platform == "darwin":
            new_flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(new_flags)
        self.show()
        self.update_menu_states()

    def reset_window_size(self):
        self.resize(300, 150)
        self.config.set_window_size(300, 150)

    def timer_control_start(self):
        if self.local_timer:
            self.local_timer.start()
            return
        if self.client:
            if self.client.get_timer_source() == 'main':
                self.client.start_timer()
            else:
                src = self.client.get_timer_source()
                if src.startswith('aux'):
                    self.client.start_aux_timer(int(src[-1]))

    def timer_control_pause(self):
        if self.local_timer:
            self.local_timer.pause()
            return
        if self.client:
            if self.client.get_timer_source() == 'main':
                self.client.pause_timer()
            else:
                src = self.client.get_timer_source()
                if src.startswith('aux'):
                    self.client.pause_aux_timer(int(src[-1]))

    def timer_control_reload(self):
        if self.local_timer:
            self.local_timer.restart()
            return
        if self.client:
            if self.client.get_timer_source() == 'main':
                self.client.reload_timer()
            else:
                src = self.client.get_timer_source()
                if src.startswith('aux'):
                    self.client.stop_aux_timer(int(src[-1]))

    def timer_control_previous_event(self):
        if self.local_timer:
            self.local_timer.previous_preset()
            return
        if self.client and self.client.last_timer_data and self.client.last_timer_data.has_previous_event:
            self.client.load_previous_event()

    def timer_control_next_event(self):
        if self.local_timer:
            self.local_timer.next_preset()
            return
        if self.client and self.client.last_timer_data and self.client.last_timer_data.has_next_event:
            self.client.load_next_event()

    def timer_control_blink(self):
        if self.local_timer:
            self._blink_on = self.local_timer.toggle_blink()
            self.update_menu_states()
            return
        self._blink_on = not self._blink_on
        if self.client:
            self.client.set_timer_blink(self._blink_on)
        self.update_menu_states()

    def timer_control_blackout(self):
        if self.local_timer:
            self._blackout_on = self.local_timer.toggle_blackout()
            self.update_menu_states()
            return
        self._blackout_on = not self._blackout_on
        if self.client:
            self.client.set_timer_blackout(self._blackout_on)
        self.update_menu_states()

    def timer_control_add_minute(self):
        if self.local_timer:
            self.local_timer.add_time_ms(60000)
            self.update_menu_states()
            return
        if self.client:
            if self.client.get_timer_source() == 'main':
                if self.config.get_addtime_affects_event_duration():
                    self.client.change_current_event_duration(60000)
                else:
                    self.client.add_time_ms(60000)
            else:
                src = self.client.get_timer_source()
                if src.startswith('aux'):
                    self.client.add_aux_time_ms(int(src[-1]), 60000)

    def timer_control_remove_minute(self):
        if self.local_timer:
            self.local_timer.remove_time_ms(60000)
            self.update_menu_states()
            return
        if self.client:
            if self.client.get_timer_source() == 'main':
                if self.config.get_addtime_affects_event_duration():
                    self.client.change_current_event_duration(-60000)
                else:
                    self.client.remove_time_ms(60000)
            else:
                src = self.client.get_timer_source()
                if src.startswith('aux'):
                    self.client.add_aux_time_ms(int(src[-1]), -60000)

    def toggle_addtime_affects_event_duration(self):
        value = not self.config.get_addtime_affects_event_duration()
        self.config.set_addtime_affects_event_duration(value)
        self.update_menu_states()

    def toggle_hover_controls(self):
        value = not self.config.get_hover_controls_enabled()
        self.config.set_hover_controls_enabled(value)
        if not value:
            self._hide_controls_overlays()
        self.update_menu_states()

    def set_timer_source(self, source: str):
        """Switch displayed timer to Ontime sources, system clock, or local simple timer."""
        if source == 'simple':
            self._enable_simple_timer()
            self.config.set_selected_timer_source('simple')
            self.update_menu_states()
            return
        if source == 'clock':
            self._disable_simple_timer()
            self.timer_widget.set_display_mode('clock')
            self.config.set_display_mode('clock')
            self.config.set_selected_timer_source('clock')
            self._hide_controls_overlays()
            self.update_menu_states()
            return
        if source not in ('main', 'aux1', 'aux2', 'aux3'):
            return
        self._disable_simple_timer()
        self.config.set_selected_timer_source(source)
        if not self.client:
            url = self.config.get_server_url()
            if url:
                self.start_client(url)
        self.timer_widget.set_display_mode('timer')
        self.config.set_display_mode('timer')
        self.config.set_timer_source(source)
        self._apply_timer_source_to_ui()
        if self.client:
            self.client.refresh_display()
        self.update_menu_states()

    def show_window(self):
        self.show()
        # On macOS, don't steal focus - the window will be visible due to high level
        if sys.platform != "darwin":
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

    def _position_in_available_geometry(self, x: int, y: int, w: int, h: int) -> bool:
        """Return True if the rectangle (x, y, w, h) fits within at least one screen's available geometry."""
        for screen in QGuiApplication.screens():
            if screen is None:
                continue
            available = screen.availableGeometry()
            if x >= available.left() and y >= available.top() and x + w <= available.right() and y + h <= available.bottom():
                return True
        return False

    def _default_window_position(self, w: int = 0, h: int = 0) -> QPoint:
        """Return default position: centered on primary screen's available geometry."""
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = available.left() + max(0, (available.width() - w) // 2)
            y = available.top() + max(0, (available.height() - h) // 2)
            return QPoint(x, y)
        return QPoint(50, 50)

    def _restore_window_position(self):
        """Restore window position from config; if outside available area or no saved position, use default (centered)."""
        saved = self.config.get_window_position()
        w, h = self.width(), self.height()
        if saved and self._position_in_available_geometry(saved[0], saved[1], w, h):
            self.move(saved[0], saved[1])
        else:
            default = self._default_window_position(w, h)
            self.move(default)

    def mousePressEvent(self, event):
        if self.is_locked or event.button() != Qt.MouseButton.LeftButton: return
        pos = event.position().toPoint()
        self.resize_corner = self._get_resize_corner(pos)
        self.initial_pos = event.globalPosition().toPoint()
        self.initial_win_pos = self.pos()
        self.initial_size = self.size()
        self._drag_or_resize_started = True

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        corner = self._get_resize_corner(pos)
        self.setCursor(self._get_cursor(corner) if corner else Qt.CursorShape.ArrowCursor)
        if self.top_overlay.isVisible() and self.config.get_hover_controls_enabled():
            self._overlay_idle_timer.start(self._overlay_idle_timeout_ms)
        
        if self.is_locked or not (event.buttons() & Qt.MouseButton.LeftButton): return
        if not self._drag_or_resize_started:
            return  # Move before press (e.g. first show); avoid using unset initial_* 
        
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
        self.config.set_window_position(self.x(), self.y())
        self.resize_corner = None
        self._drag_or_resize_started = False

    def _apply_font_resize(self):
        """Apply the pending font size update."""
        if self._pending_resize and not self._updating_fonts:
            self._updating_fonts = True
            w, h = self._pending_resize
            # Use timer widget's area for font scaling (smaller when progress bar is visible)
            h_timer = h - (self.progress_bar_widget.height() if self.progress_bar_widget.isVisible() else 0)
            self.timer_widget.update_font_sizes(w, h_timer)
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
            # Re-apply accessory policy (Qt may reset it when window is shown)
            QTimer.singleShot(0, _reapply_macos_activation_policy)
        if sys.platform == "win32":
            _set_windows_no_activate(self)
        # React to HiDPI / screen changes when window moves between monitors
        wh = self.windowHandle()
        if wh and not self._screen_changed_connected:
            wh.screenChanged.connect(self._on_screen_changed)
            self._screen_changed_connected = True

    def _on_screen_changed(self, screen):
        """Called when window moves to another screen (e.g. HiDPI to non-HiDPI). Refresh layout."""
        if screen is None:
            return
        QTimer.singleShot(0, self._refresh_after_screen_change)

    def _refresh_after_screen_change(self):
        """Update fonts and overlay positions after screen/DPR change."""
        self._position_control_overlays()
        if not self._updating_fonts:
            self._updating_fonts = True
            self.timer_widget.update_font_sizes(self.width(), self.height())
            self._updating_fonts = False

    def enterEvent(self, event):
        # On macOS, hover is handled by _poll_mouse_position (works when app inactive)
        if sys.platform != "darwin":
            if self.config.get_hover_controls_enabled() and self.timer_widget.display_mode != 'clock':
                self._show_controls_overlays()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # On macOS, hover is handled by _poll_mouse_position (works when app inactive)
        if sys.platform != "darwin":
            self._overlay_hide_timer.start(300)
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        # Global click-outside handling for hover overlays
        if self.top_overlay.isVisible() or self.bottom_overlay.isVisible():
            et = event.type()
            if et == QEvent.Type.MouseMove:
                pos = QCursor.pos()
                if self._window_contains_global_pos(pos) or self._overlay_contains_global_pos(pos):
                    self._overlay_idle_timer.start(self._overlay_idle_timeout_ms)
            elif et == QEvent.Type.MouseButtonPress:
                gpos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
                if not (self._window_contains_global_pos(gpos) or self._overlay_contains_global_pos(gpos)):
                    self._hide_controls_overlays()
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.timer_control_reload()
            self.timer_control_start()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

def main():
    # Enable HiDPI scaling so the app looks correct on high-DPI and mixed-DPI setups
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')
    attr = getattr(Qt, 'ApplicationAttribute', None)
    if attr is not None and hasattr(attr, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(attr.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # macOS: Set app as "accessory" so it doesn't steal focus when clicked
    if sys.platform == "darwin":
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            logger.debug("[macOS] App set to accessory activation policy")
        except Exception as e:
            logger.warning(f"[macOS] Failed to set activation policy: {e}")
    
    window = FloatTimeWindow()
    window.show()
    # macOS: Re-apply activation policy after show (Qt may reset it shortly after)
    if sys.platform == "darwin":
        QTimer.singleShot(100, _reapply_macos_activation_policy)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
