"""Configuration management for FloatTime."""
import json
import os
from pathlib import Path
from typing import Optional, Any, Dict, List
from logger import get_logger

logger = get_logger(__name__)

# Factory defaults for reset-to-default. Colors: hex (#RRGGBB) for labels/thresholds, [r,g,b,a] for backgrounds.
FACTORY_DEFAULT_URL = "http://localhost:4001"
FACTORY_DEFAULT_HEADLESS_PRESETS: List[int] = [15, 20, 30]
FACTORY_DEFAULT_HEADLESS_WARNING_SEC = 120
FACTORY_DEFAULT_HEADLESS_DANGER_SEC = 0
FACTORY_DEFAULT_COLOR_TIMER_LABEL = "#ffffff"
FACTORY_DEFAULT_COLOR_CLOCK_LABEL = "#ffff00"
FACTORY_DEFAULT_COLOR_WARNING = "#FFA528"
FACTORY_DEFAULT_COLOR_DANGER = "#FA5656"
FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND: List[int] = [0, 0, 0, 200]


class Config:
    """Manages application configuration with in-memory caching."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config_dir = Path.home() / ".floattime"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, Any] = self._load_from_disk()
    
    def _load_from_disk(self) -> Dict[str, Any]:
        """Load configuration from disk into memory."""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load config from disk: {e}")
            return {}

    def _save_to_disk(self) -> bool:
        """Write current cached configuration to disk."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Failed to save config to disk: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from cache."""
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value in cache and save to disk."""
        self._cache[key] = value
        return self._save_to_disk()

    def get_server_url(self) -> Optional[str]:
        """Get the Ontime server URL from configuration."""
        return self.get('server_url')
    
    def set_server_url(self, url: str) -> bool:
        """Save the Ontime server URL to configuration."""
        return self.set('server_url', url.strip())
    
    def get_default_url(self) -> str:
        """Get default server URL."""
        return "http://localhost:4001"
    
    def get_display_mode(self) -> str:
        """Get display mode: 'timer' or 'clock'."""
        mode = self.get('display_mode', 'timer')
        return mode if mode in ['timer', 'clock'] else 'timer'
    
    def set_display_mode(self, mode: str) -> bool:
        """Save display mode: 'timer' or 'clock'."""
        if mode not in ['timer', 'clock']:
            return False
        return self.set('display_mode', mode)
    
    def get_background_visible(self) -> bool:
        """Get background visibility setting."""
        return self.get('background_visible', True)
    
    def set_background_visible(self, visible: bool) -> bool:
        """Save background visibility setting."""
        return self.set('background_visible', bool(visible))
    
    def get_window_size(self) -> Optional[tuple]:
        """Get saved window size (width, height)."""
        size = self.get('window_size')
        if size and isinstance(size, list) and len(size) == 2:
            return tuple(size)
        return None
    
    def set_window_size(self, width: int, height: int) -> bool:
        """Save window size."""
        return self.set('window_size', [int(width), int(height)])

    def get_window_position(self) -> Optional[tuple]:
        """Get saved window position (x, y)."""
        pos = self.get('window_position')
        if pos and isinstance(pos, list) and len(pos) == 2:
            return (int(pos[0]), int(pos[1]))
        return None

    def set_window_position(self, x: int, y: int) -> bool:
        """Save window position."""
        return self.set('window_position', [int(x), int(y)])
    
    def get_locked(self) -> bool:
        """Get locked state (prevents moving and resizing)."""
        return self.get('locked', False)
    
    def set_locked(self, locked: bool) -> bool:
        """Save locked state."""
        return self.set('locked', bool(locked))

    def get_addtime_affects_event_duration(self) -> bool:
        """Get whether +/- 1 min also changes current event's duration."""
        return self.get('addtime_affects_event_duration', False)

    def set_addtime_affects_event_duration(self, value: bool) -> bool:
        """Save whether +/- 1 min also changes current event's duration."""
        return self.set('addtime_affects_event_duration', bool(value))

    def get_hover_controls_enabled(self) -> bool:
        """Get whether on-hover control overlays are enabled."""
        return self.get('hover_controls_enabled', True)

    def set_hover_controls_enabled(self, value: bool) -> bool:
        """Save whether on-hover control overlays are enabled."""
        return self.set('hover_controls_enabled', bool(value))

    def get_timer_source(self) -> str:
        """Get which timer to display: 'main', 'aux1', 'aux2', 'aux3'."""
        v = self.get('timer_source', 'main')
        return v if v in ('main', 'aux1', 'aux2', 'aux3') else 'main'

    def set_timer_source(self, value: str) -> bool:
        """Save which timer to display."""
        if value not in ('main', 'aux1', 'aux2', 'aux3'):
            return False
        return self.set('timer_source', value)

    def get_selected_timer_source(self) -> str:
        """Get selected source across runs: main/aux1/aux2/aux3/clock/simple.

        Defaults:
        - clock when display_mode is clock
        - otherwise current timer_source (default main)
        """
        v = self.get('selected_timer_source')
        allowed = ('main', 'aux1', 'aux2', 'aux3', 'clock', 'simple')
        if isinstance(v, str) and v in allowed:
            return v
        if self.get_display_mode() == 'clock':
            return 'clock'
        return self.get_timer_source()

    def set_selected_timer_source(self, value: str) -> bool:
        """Persist selected source across runs."""
        if value not in ('main', 'aux1', 'aux2', 'aux3', 'clock', 'simple'):
            return False
        return self.set('selected_timer_source', value)

    def get_headless_preset_minutes(self) -> List[int]:
        """Get the 3 preset durations in minutes for headless timer. Default [15, 20, 30]."""
        raw = self.get('headless_preset_minutes', [15, 20, 30])
        if not isinstance(raw, list) or len(raw) != 3:
            return [15, 20, 30]
        out = []
        for x in raw:
            try:
                v = int(x)
                if 1 <= v <= 999:
                    out.append(v)
                else:
                    return [15, 20, 30]
            except (TypeError, ValueError):
                return [15, 20, 30]
        return out

    def set_headless_preset_minutes(self, value: List[int]) -> bool:
        """Save headless preset minutes. Must be exactly 3 positive integers (1-999)."""
        if not isinstance(value, list) or len(value) != 3:
            return False
        out = []
        for x in value:
            try:
                v = int(x)
                if 1 <= v <= 999:
                    out.append(v)
                else:
                    return False
            except (TypeError, ValueError):
                return False
        return self.set('headless_preset_minutes', out)

    def get_headless_time_warning_sec(self) -> int:
        """Get warning threshold in seconds for simple timer countdown color. Default 120 (2:00)."""
        raw = self.get('headless_time_warning_sec')
        if raw is None:
            # Backward compatibility: migrate from old millisecond key if present.
            old_ms = self.get('headless_time_warning_ms')
            if old_ms is not None:
                try:
                    return max(0, int(old_ms) // 1000)
                except (TypeError, ValueError):
                    return 120
            return 120
        try:
            v = int(raw)
            return max(0, v)
        except (TypeError, ValueError):
            return 120

    def set_headless_time_warning_sec(self, value: int) -> bool:
        """Save warning threshold in seconds for simple timer countdown color."""
        try:
            v = int(value)
        except (TypeError, ValueError):
            return False
        return self.set('headless_time_warning_sec', max(0, v))

    def get_headless_time_danger_sec(self) -> int:
        """Get danger threshold in seconds for simple timer countdown color. Default 0."""
        raw = self.get('headless_time_danger_sec')
        if raw is None:
            # Backward compatibility: migrate from old millisecond key if present.
            old_ms = self.get('headless_time_danger_ms')
            if old_ms is not None:
                try:
                    return max(0, int(old_ms) // 1000)
                except (TypeError, ValueError):
                    return 0
            return 0
        try:
            v = int(raw)
            return max(0, v)
        except (TypeError, ValueError):
            return 0

    def set_headless_time_danger_sec(self, value: int) -> bool:
        """Save danger threshold in seconds for simple timer countdown color."""
        try:
            v = int(value)
        except (TypeError, ValueError):
            return False
        return self.set('headless_time_danger_sec', max(0, v))

    # --- Color settings (hex for solid, [r,g,b,a] for backgrounds) ---

    def get_color_timer_label(self) -> str:
        """Timer label normal color (hex). Default #ffffff."""
        v = self.get('color_timer_label')
        return v if isinstance(v, str) and v.startswith('#') else FACTORY_DEFAULT_COLOR_TIMER_LABEL

    def set_color_timer_label(self, value: str) -> bool:
        if not isinstance(value, str) or not value.startswith('#'):
            return False
        return self.set('color_timer_label', value)

    def get_color_clock_label(self) -> str:
        """Clock label color (hex). Default #ffff00."""
        v = self.get('color_clock_label')
        return v if isinstance(v, str) and v.startswith('#') else FACTORY_DEFAULT_COLOR_CLOCK_LABEL

    def set_color_clock_label(self, value: str) -> bool:
        if not isinstance(value, str) or not value.startswith('#'):
            return False
        return self.set('color_clock_label', value)

    def get_color_warning(self) -> str:
        """Warning threshold color (hex). Default #FFA528."""
        v = self.get('color_warning')
        return v if isinstance(v, str) and v.startswith('#') else FACTORY_DEFAULT_COLOR_WARNING

    def set_color_warning(self, value: str) -> bool:
        if not isinstance(value, str) or not value.startswith('#'):
            return False
        return self.set('color_warning', value)

    def get_color_danger(self) -> str:
        """Danger/overtime color (hex). Default #FA5656."""
        v = self.get('color_danger')
        return v if isinstance(v, str) and v.startswith('#') else FACTORY_DEFAULT_COLOR_DANGER

    def set_color_danger(self, value: str) -> bool:
        if not isinstance(value, str) or not value.startswith('#'):
            return False
        return self.set('color_danger', value)

    def get_color_timer_background(self) -> List[int]:
        """Timer panel background RGBA [r,g,b,a], 0-255. Default [0,0,0,200]."""
        v = self.get('color_timer_background')
        if isinstance(v, list) and len(v) == 4:
            try:
                out = [int(x) & 255 for x in v]
                return out
            except (TypeError, ValueError):
                pass
        return list(FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND)

    def set_color_timer_background(self, value: List[int]) -> bool:
        if not isinstance(value, list) or len(value) != 4:
            return False
        try:
            out = [int(x) & 255 for x in value]
            return self.set('color_timer_background', out)
        except (TypeError, ValueError):
            return False

    def reset_to_factory_defaults(self) -> bool:
        """Set URL, simple timer, and all color keys to factory defaults and save."""
        self._cache['server_url'] = FACTORY_DEFAULT_URL
        self._cache['headless_preset_minutes'] = list(FACTORY_DEFAULT_HEADLESS_PRESETS)
        self._cache['headless_time_warning_sec'] = FACTORY_DEFAULT_HEADLESS_WARNING_SEC
        self._cache['headless_time_danger_sec'] = FACTORY_DEFAULT_HEADLESS_DANGER_SEC
        self._cache['color_timer_label'] = FACTORY_DEFAULT_COLOR_TIMER_LABEL
        self._cache['color_clock_label'] = FACTORY_DEFAULT_COLOR_CLOCK_LABEL
        self._cache['color_warning'] = FACTORY_DEFAULT_COLOR_WARNING
        self._cache['color_danger'] = FACTORY_DEFAULT_COLOR_DANGER
        self._cache['color_timer_background'] = list(FACTORY_DEFAULT_COLOR_TIMER_BACKGROUND)
        return self._save_to_disk()
