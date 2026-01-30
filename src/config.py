"""Configuration management for FloatTime."""
import json
import os
from pathlib import Path
from typing import Optional, Any, Dict
from logger import get_logger

logger = get_logger(__name__)

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
