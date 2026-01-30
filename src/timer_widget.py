"""Widget for displaying Ontime timer."""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QFont, QMouseEvent, QFontMetrics
from typing import Optional
from datetime import datetime
from logger import get_logger
from ontime_client import TimerData

logger = get_logger(__name__)

class TimerWidget(QWidget):
    """Widget that displays the Ontime timer and/or clock."""
    
    def __init__(self, parent=None):
        """Initialize timer widget."""
        super().__init__(parent)
        self.display_mode = 'timer'  # 'timer' or 'clock'
        self.timer_data: Optional[TimerData] = None
        self.timer_type = None  # Track current timer type from Ontime
        
        # Base dimensions and font sizes (for scaling)
        self.base_width = 300
        self.base_height = 150
        self.base_margin = 20
        self.base_spacing = 5
        self.base_timer_font_size = 48
        self.base_clock_font_size = 36
        
        self.setup_ui()
        self.setup_clock_timer()
    
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(self.base_margin, self.base_margin, self.base_margin, self.base_margin)
        layout.setSpacing(self.base_spacing)
        
        # Timer label (for Ontime timer)
        self.timer_label = QLabel("--:--")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color: #ffffff;")
        
        # Clock label (for system clock)
        self.clock_label = QLabel("")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("color: #ffff00;")
        
        layout.addWidget(self.timer_label)
        layout.addWidget(self.clock_label)
        
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # Initial style and state
        self.background_visible = True
        self.update_background()
        self.update_display_mode()
        # Initial sizing
        QTimer.singleShot(0, self.update_font_sizes)

    def set_background_visible(self, visible: bool):
        """Set background visibility."""
        if self.background_visible != visible:
            self.background_visible = visible
            self.update_background()
    
    def update_background(self):
        """Update background style based on visibility."""
        if self.background_visible:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 200); border-radius: 10px;")
        else:
            self.setStyleSheet("background-color: transparent;")
    
    def setup_clock_timer(self):
        """Setup timer for updating clock display."""
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        
        # Calculate delay to sync with the start of the next second
        now = datetime.now()
        delay_ms = 1000 - (now.microsecond // 1000)
        self.clock_timer.setSingleShot(True)
        self.clock_timer.timeout.connect(self._start_regular_clock_updates)
        self.clock_timer.start(delay_ms)
        self.update_clock()

    def _start_regular_clock_updates(self):
        self.clock_timer.setSingleShot(False)
        self.clock_timer.start(1000)
        self.update_clock()
    
    def update_clock(self):
        """Update the clock display with current system time."""
        if self.display_mode == 'clock' or (self.timer_type == 'clock' and self.display_mode == 'timer'):
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            target = self.clock_label if self.display_mode == 'clock' else self.timer_label
            if target.text() != time_str:
                target.setText(time_str)
                # Font size should stay constant for clock (always HH:MM:SS)
                # Only update on first display
                if not hasattr(self, '_clock_font_set'):
                    self.update_font_sizes()
                    self._clock_font_set = True
            if self.display_mode == 'clock':
                self.timer_label.setText("")
        else:
            self.clock_label.setText("")
            self._clock_font_set = False

    def set_display_mode(self, mode: str):
        """Set display mode: 'timer' or 'clock'."""
        if mode not in ['timer', 'clock'] or self.display_mode == mode:
            return
        
        self.display_mode = mode
        self.update_display_mode()
        self.update_clock()
        if self.timer_data:
            self.update_timer(self.timer_data)
        self.update_font_sizes()
    
    def update_display_mode(self):
        """Update visibility of labels based on display mode."""
        is_timer = self.display_mode == 'timer'
        self.timer_label.setVisible(is_timer)
        self.clock_label.setVisible(not is_timer)

    def update_timer(self, data: TimerData):
        """Update the timer display with structured TimerData."""
        self.timer_data = data
        self.timer_type = data.timer_type
        
        if self.display_mode != 'timer':
            return

        old_text = self.timer_label.text()
        
        if data.timer_type == 'none':
            self.timer_label.setVisible(False)
        elif data.timer_type == 'clock':
            self.timer_label.setVisible(True)
            self.timer_label.setStyleSheet("color: #ffffff;")
            self.update_clock()
        else:
            self.timer_label.setVisible(True)
            if data.timer_ms is not None:
                formatted = self._format_time(data.timer_ms)
                self.timer_label.setText(formatted)
                
                # Color thresholds
                color = "#ffffff"
                if data.timer_type == 'count down':
                    color = self._get_timer_color_countdown(data.timer_ms, data.time_warning, data.time_danger)
                elif data.timer_type == 'count up':
                    color = self._get_timer_color_countup(data.timer_ms, data.duration)
                
                self.timer_label.setStyleSheet(f"color: {color};")
            elif data.status == 'stopped' or data.timer_type == 'none':
                self.timer_label.setText("--:--")
                self.timer_label.setStyleSheet("color: #ffffff;")

        # Only resize if text length changed (e.g., MM:SS -> HH:MM:SS)
        new_text = self.timer_label.text()
        if len(new_text) != len(old_text):
            self.update_font_sizes()

    def _format_time(self, ms: float) -> str:
        """Format milliseconds to MM:SS or HH:MM:SS."""
        is_neg = ms < 0
        total_sec = int(abs(ms) / 1000)
        h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
        
        time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        return f"-{time_str}" if is_neg else time_str

    def _get_timer_color_countdown(self, ms: float, warning: Optional[float], danger: Optional[float]) -> str:
        if ms < 0: return "#FA5656" # Red
        if danger is not None and ms <= danger: return "#FA5656"
        if warning is not None and ms <= warning: return "#FFA528" # Orange
        return "#ffffff"

    def _get_timer_color_countup(self, ms: float, duration: Optional[float]) -> str:
        if duration is not None and ms > duration: return "#FFA528"
        return "#ffffff"

    def update_font_sizes(self, width: int = None, height: int = None):
        """Dynamically scale fonts to fill the window - text adapts to window size."""
        width = width or self.width()
        height = height or self.height()
        
        if width < 50 or height < 50:
            return

        # Use layout margins (from setup_ui)
        margin = self.base_margin
        avail_w = width - (2 * margin)
        avail_h = height - (2 * margin)
        
        def calculate_optimal_font_size(label, bold=True):
            """Find largest font size that fits the window."""
            if not label.isVisible() or not label.text():
                return
            
            text = label.text()
            min_size, max_size = 8, 300  # Search range
            
            # Binary search for optimal font size
            best_size = min_size
            for _ in range(20):  # More iterations for better precision
                mid_size = (min_size + max_size) // 2
                font = QFont("Arial", mid_size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
                metrics = QFontMetrics(font)
                
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()
                
                # Try to use as much space as possible (98% to avoid clipping)
                fits = text_width <= avail_w * 0.90 and text_height <= avail_h * 0.98
                
                if fits:
                    best_size = mid_size
                    min_size = mid_size + 1  # Try even larger
                else:
                    max_size = mid_size - 1  # Too big, go smaller
            
            # Set the font with the best size found
            font = QFont("Arial", best_size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
            label.setFont(font)
            
        calculate_optimal_font_size(self.timer_label, bold=True)
        calculate_optimal_font_size(self.clock_label, bold=True)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Forward events to parent for cursor handling."""
        parent = self.parent()
        if parent:
            global_pos = self.mapToGlobal(event.position().toPoint())
            parent_pos = parent.mapFromGlobal(global_pos)
            parent_event = QMouseEvent(
                event.type(), QPointF(parent_pos), event.globalPosition(),
                event.button(), event.buttons(), event.modifiers()
            )
            parent.mouseMoveEvent(parent_event)
        super().mouseMoveEvent(event)
