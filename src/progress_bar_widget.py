"""Resizable progress bar with normal, warning and danger zones (Ontime-style: timeline revealed left to right)."""
from typing import Optional
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from ontime_client import TimerData

# Semi-transparent overlay covering the "remaining" part of the bar (dark brown/grey)
OVERLAY_COLOR = (40, 35, 30, 200)


class ProgressBarWidget(QWidget):
    """Horizontal progress bar: full timeline (normal/warning/danger) with overlay that recedes left-to-right as time elapses."""

    BAR_HEIGHT = 8
    RADIUS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer_data: Optional[TimerData] = None
        self._color_normal = "#ffffff"
        self._color_warning = "#FFA528"
        self._color_danger = "#FA5656"
        self._color_idle = "#666666"

    def update_timer(self, data: TimerData) -> None:
        """Update bar from TimerData (same as timer widget)."""
        self._timer_data = data
        self.update()

    def apply_color_settings(self, config) -> None:
        """Apply colors from config (same as timer widget)."""
        self._color_normal = config.get_color_timer_label()
        self._color_warning = config.get_color_warning()
        self._color_danger = config.get_color_danger()
        self.update()

    def _elapsed_ratio(self) -> Optional[float]:
        """Return elapsed time ratio 0..1 (how much of the timeline is revealed from the left). None if idle/no data."""
        d = self._timer_data
        if not d or d.timer_type in ('none', 'clock'):
            return None
        duration = d.duration
        if duration is None or duration <= 0:
            return None
        ms = d.timer_ms
        if ms is None:
            return None
        if d.timer_type == 'count down':
            elapsed = duration - ms
            return max(0.0, min(1.0, elapsed / duration))
        else:
            return max(0.0, min(1.0, ms / duration))

    def _segment_limits(self) -> Optional[tuple[float, float, float]]:
        """Return (x_normal_end, x_warning_end, x_danger_end) as ratios 0..1. Count down: three zones; count up: full normal."""
        d = self._timer_data
        if not d or d.timer_type in ('none', 'clock'):
            return None
        duration = d.duration
        if duration is None or duration <= 0:
            return None
        if d.timer_type != 'count down':
            # Count up: whole bar is normal
            return (1.0, 1.0, 1.0)
        # Time from start (ms) at which we enter warning and danger
        warning_ms = (duration - d.time_warning) if d.time_warning is not None else duration
        danger_ms = (duration - d.time_danger) if d.time_danger is not None else duration
        warning_ms = max(0, min(duration, warning_ms))
        danger_ms = max(0, min(duration, danger_ms))
        if danger_ms < warning_ms:
            danger_ms = warning_ms
        return (warning_ms / duration, danger_ms / duration, 1.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        rect = QRectF(0, 0, w, h)
        full_path = QPainterPath()
        full_path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        segments = self._segment_limits()
        elapsed = self._elapsed_ratio()

        if segments is None or elapsed is None:
            # Idle: full bar in neutral, no overlay
            painter.fillPath(full_path, QColor(self._color_idle))
            return

        # 1) Draw full-width timeline in normal / warning / danger segments (left to right)
        x_n_end, x_d_end, _ = segments
        # Normal: 0 -> x_n_end
        # Warning: x_n_end -> x_d_end
        # Danger: x_d_end -> 1
        def draw_segment(x0: float, x1: float, color: str) -> None:
            if x1 <= x0:
                return
            seg_rect = QRectF(x0 * w, 0, (x1 - x0) * w, h)
            seg_path = QPainterPath()
            seg_path.addRect(seg_rect)
            painter.fillPath(seg_path, QColor(color))

        painter.setClipPath(full_path)
        draw_segment(0.0, x_n_end, self._color_normal)
        draw_segment(x_n_end, x_d_end, self._color_warning)
        draw_segment(x_d_end, 1.0, self._color_danger)

        # 2) Semi-transparent overlay from (elapsed * w) to right, so timeline is revealed left to right
        overlay_left = elapsed * w
        if overlay_left < w:
            overlay_rect = QRectF(overlay_left, 0, w - overlay_left, h)
            overlay_path = QPainterPath()
            overlay_path.addRect(overlay_rect)
            painter.fillPath(overlay_path, QColor(*OVERLAY_COLOR))
        painter.setClipPath(QPainterPath())
