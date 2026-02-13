"""Local countdown timer for headless mode (no Ontime server)."""
from typing import Optional, Callable, List
from PyQt6.QtCore import QObject, QTimer

from ontime_client import TimerData


class LocalTimer(QObject):
    """Local countdown with 3 presets (minutes). Emits TimerData via callback for display."""

    def __init__(
        self,
        preset_minutes: List[int],
        update_callback: Optional[Callable[[TimerData], None]] = None,
        warning_ms: int = 120000,
        danger_ms: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        if not preset_minutes or len(preset_minutes) != 3:
            preset_minutes = [15, 20, 30]
        self._presets = [max(1, min(999, int(m))) for m in preset_minutes]
        self._preset_index = 0
        self._start_ms: float = self._presets[self._preset_index] * 60 * 1000.0
        self._remaining_ms: float = self._start_ms
        self._warning_ms = max(0, int(warning_ms))
        self._danger_ms = max(0, int(danger_ms))
        self._blink_on = False
        self._blackout_on = False
        self._running = False
        self._update_callback = update_callback
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)  # 1 s
        self._emit()

    def _tick(self):
        if not self._running:
            return
        self._remaining_ms -= 1000
        self._emit()

    def _emit(self):
        if self._update_callback is None:
            return
        presets = self._presets
        idx = self._preset_index
        start_minutes = max(0, int(round(self._start_ms / 60000.0)))
        data = TimerData(
            timer_ms=self._remaining_ms,
            timer_type='count down',
            title=f"{start_minutes} min",
            next_event_title=f"{presets[(idx + 1) % 3]} min",
            has_next_event=True,
            has_previous_event=True,
            status='play' if self._running else 'stop',
            running=self._running,
            time_warning=self._warning_ms,
            time_danger=self._danger_ms,
            duration=self._start_ms,
            blink=self._blink_on,
            blackout=self._blackout_on,
            timer_source='main',
        )
        self._update_callback(data)

    def start(self) -> None:
        """Start or resume without resetting remaining time."""
        self._running = True
        self._emit()

    def pause(self) -> None:
        """Pause the countdown."""
        self._running = False
        self._emit()

    def resume(self) -> None:
        """Resume from current remaining time."""
        if self._remaining_ms > 0:
            self._running = True
        self._emit()

    def restart(self) -> None:
        """Reset to the selected preset's original value, preserving run/pause state."""
        self._start_ms = self._presets[self._preset_index] * 60 * 1000.0
        self._remaining_ms = self._start_ms
        self._emit()

    def next_preset(self) -> None:
        """Switch to next preset (15→20→30→15) and set as new start value."""
        self._preset_index = (self._preset_index + 1) % 3
        self._start_ms = self._presets[self._preset_index] * 60 * 1000.0
        self._remaining_ms = self._start_ms
        self._running = False
        self._emit()

    def previous_preset(self) -> None:
        """Switch to previous preset (30→20→15→30) and set as new start value."""
        self._preset_index = (self._preset_index - 1) % 3
        self._start_ms = self._presets[self._preset_index] * 60 * 1000.0
        self._remaining_ms = self._start_ms
        self._running = False
        self._emit()

    def add_time_ms(self, ms: int) -> None:
        """Add time to remaining and current start value (temporary per selected preset/event)."""
        self._remaining_ms = max(0, self._remaining_ms + ms)
        self._start_ms = max(0, self._start_ms + ms)
        self._emit()

    def remove_time_ms(self, ms: int) -> None:
        """Remove time from remaining and current start value (temporary per selected preset/event)."""
        self._remaining_ms = max(0, self._remaining_ms - ms)
        self._start_ms = max(0, self._start_ms - ms)
        self._emit()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def preset_index(self) -> int:
        return self._preset_index

    @property
    def preset_minutes(self) -> List[int]:
        return list(self._presets)

    def set_preset_minutes(self, preset_minutes: List[int]) -> None:
        """Update presets (must be 3 positive ints). Does not change current index or remaining."""
        if isinstance(preset_minutes, list) and len(preset_minutes) == 3:
            old_selected = self._presets[self._preset_index]
            self._presets = [max(1, min(999, int(m))) for m in preset_minutes]
            # If current start still matches the previous selected preset value, keep it aligned.
            if int(round(self._start_ms / 60000.0)) == old_selected:
                self._start_ms = self._presets[self._preset_index] * 60 * 1000.0
                if not self._running:
                    self._remaining_ms = self._start_ms
            self._emit()

    def stop(self) -> None:
        """Stop ticking and pause timer."""
        self._running = False
        self._tick_timer.stop()

    def set_warning_danger_ms(self, warning_ms: int, danger_ms: int) -> None:
        """Update warning/danger thresholds for simple timer colors."""
        self._warning_ms = max(0, int(warning_ms))
        self._danger_ms = max(0, int(danger_ms))
        self._emit()

    def toggle_blink(self) -> bool:
        """Toggle blink state for simple timer and return the new value."""
        self._blink_on = not self._blink_on
        self._emit()
        return self._blink_on

    def toggle_blackout(self) -> bool:
        """Toggle blackout state for simple timer and return the new value."""
        self._blackout_on = not self._blackout_on
        self._emit()
        return self._blackout_on
