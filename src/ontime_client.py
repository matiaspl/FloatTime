"""Client for communicating with Ontime API."""
import requests
import json
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event, Lock
from dataclasses import dataclass, field
from logger import get_logger

logger = get_logger(__name__)

# Try to import Socket.IO client
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

# Fallback to regular websocket
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

@dataclass
class TimerData:
    """Structured timer data for FloatTime."""
    timer_ms: Optional[float] = None
    timer_type: str = 'count down'
    title: str = ""
    next_event_title: str = ""
    status: str = ""
    running: bool = False
    time_warning: Optional[float] = None
    time_danger: Optional[float] = None
    duration: Optional[float] = None
    timer_dict: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

class OntimeClient:
    """Client for fetching and parsing timer data from Ontime server."""
    
    def __init__(self, server_url: str, update_callback: Optional[Callable[[TimerData], None]] = None, use_websocket: bool = True):
        self.server_url = server_url.rstrip('/')
        self.update_callback = update_callback
        self.running = False
        self.ws_thread = None
        self.sio = None
        self.ws = None
        self.stop_event = Event()
        self.last_timer_data: Optional[TimerData] = None
        self.last_known_timer_type: Optional[str] = None
        # Cache thresholds so they persist across runtime updates that don't include event details
        self.cached_time_warning: Optional[float] = None
        self.cached_time_danger: Optional[float] = None
        self.cached_duration: Optional[float] = None
        self.use_websocket = use_websocket and (SOCKETIO_AVAILABLE or WEBSOCKET_AVAILABLE)
        self.websocket_connected = False
        self._ws_send_lock = Lock()
    
    def _parse_data(self, raw_data: Dict[str, Any]) -> Optional[TimerData]:
        """Unified parser for Ontime API responses."""
        if not isinstance(raw_data, dict):
            return None

        # Extract nested structures
        timer_dict = raw_data.get('timer', {})
        if not isinstance(timer_dict, dict):
            timer_dict = {'current': timer_dict} # Handle direct value
            
        current_event = raw_data.get('currentEvent', raw_data.get('eventNow', {}))
        next_event = raw_data.get('nextEvent', raw_data.get('loaded', raw_data.get('next', {})))
        
        # Determine timer type
        timer_type = (
            raw_data.get('timerType') or 
            current_event.get('timerType') or 
            timer_dict.get('timerType') or 
            timer_dict.get('type') or 
            timer_dict.get('mode') or
            self.last_known_timer_type or
            'count down'
        )
        if isinstance(timer_type, str):
            timer_type = timer_type.lower().replace('-', ' ').replace('_', ' ').strip()
        self.last_known_timer_type = timer_type

        # Determine timer value (ms)
        timer_ms = None
        has_timer_data = False
        
        if timer_type == 'count up':
            timer_ms = timer_dict.get('elapsed')
            if timer_ms is not None: has_timer_data = True
        elif timer_type == 'count down':
            timer_ms = timer_dict.get('current') or timer_dict.get('remaining')
            if timer_ms is not None: has_timer_data = True
        
        if timer_ms is None:
            # Fallback to general keys
            for key in ['timer', 'currentTime', 'time', 'elapsed', 'remaining', 'current']:
                val = raw_data.get(key) if key in raw_data else timer_dict.get(key)
                if isinstance(val, (int, float)):
                    timer_ms = val
                    has_timer_data = True
                    break

        # If this is just a clock heartbeat (no timer data, no title/event change), ignore it
        is_heartbeat = not has_timer_data and not raw_data.get('timer') and not raw_data.get('eventNow') and not raw_data.get('currentEvent')
        if is_heartbeat and 'clock' in raw_data:
            return None

        # Next event title
        next_title = ""
        if isinstance(next_event, dict):
            next_title = next_event.get('title', "")
        elif next_event:
            next_title = str(next_event)

        # Extract thresholds, update cache if present, or use cached values
        time_warning = current_event.get('timeWarning') or timer_dict.get('timeWarning')
        if time_warning is not None:
            self.cached_time_warning = time_warning
        elif self.cached_time_warning is not None:
            time_warning = self.cached_time_warning

        time_danger = current_event.get('timeDanger') or timer_dict.get('timeDanger')
        if time_danger is not None:
            self.cached_time_danger = time_danger
        elif self.cached_time_danger is not None:
            time_danger = self.cached_time_danger

        duration = current_event.get('duration') or timer_dict.get('duration')
        if duration is not None:
            self.cached_duration = duration
        elif self.cached_duration is not None:
            duration = self.cached_duration

        data = TimerData(
            timer_ms=timer_ms,
            timer_type=timer_type,
            title=current_event.get('title', raw_data.get('title', "")),
            next_event_title=next_title,
            status=timer_dict.get('state', raw_data.get('status', "")),
            running=timer_dict.get('running', raw_data.get('running', False)),
            time_warning=time_warning,
            time_danger=time_danger,
            duration=duration,
            timer_dict=timer_dict,
            raw_data=raw_data
        )
        
        return data

    def _notify(self, data: TimerData):
        """Invoke update callback with new data."""
        self.last_timer_data = data
        if self.update_callback:
            try:
                self.update_callback(data)
            except Exception as e:
                logger.error(f"Error in update callback: {e}")

    def _socketio_loop(self):
        """Socket.IO connection and event loop."""
        self.sio = socketio.Client()
        
        @self.sio.event
        def connect():
            logger.info("Socket.IO connected")
            self.websocket_connected = True
            for chan in ['timer', 'ontime']:
                self.sio.emit('subscribe', {'channel': chan})

        @self.sio.on('*')
        def catch_all(event, *args):
            if args:
                data = self._parse_data(args[0])
                if data: self._notify(data)

        try:
            self.sio.connect(self.server_url, wait_timeout=5)
            while not self.stop_event.is_set() and self.websocket_connected:
                self.stop_event.wait(1)
        except Exception as e:
            logger.error(f"Socket.IO loop error: {e}")
        finally:
            self.websocket_connected = False

    def _ws_on_message(self, ws, message):
        try:
            raw = json.loads(message)
            # Handle Ontime tagged format
            payload = raw.get('payload', raw) if isinstance(raw, dict) and 'tag' in raw else raw
            data = self._parse_data(payload)
            if data: self._notify(data)
        except Exception as e:
            logger.error(f"WS message error: {e}")

    def _ws_loop(self):
        """Standard WebSocket loop."""
        ws_url = self.server_url.replace('http', 'ws', 1) + "/ws"
        
        def on_open(ws):
            logger.info("WebSocket connected")
            self.websocket_connected = True
            ws.send(json.dumps({"tag": "poll"}))

        def on_close(ws, *args):
            self.websocket_connected = False

        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._ws_on_message,
                on_open=on_open,
                on_close=on_close
            )
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"WebSocket loop error: {e}")

    def start(self):
        if self.running: return
        self.running = True
        self.stop_event.clear()
        
        if self.use_websocket:
            self.ws_thread = Thread(target=self._ws_loop, daemon=True)
            self.ws_thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()
        if self.sio: self.sio.disconnect()
        if self.ws: self.ws.close()
        if self.ws_thread: self.ws_thread.join(timeout=1)

    def test_connection(self) -> bool:
        try:
            return requests.get(self.server_url, timeout=2).status_code < 500
        except:
            return False

    def _send_ws(self, msg: dict) -> bool:
        """Send a control message over WebSocket. Thread-safe. Returns True if sent."""
        if not WEBSOCKET_AVAILABLE or not self.ws or not self.websocket_connected:
            return False
        with self._ws_send_lock:
            try:
                self.ws.send(json.dumps(msg))
                return True
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                return False

    def start_timer(self) -> bool:
        """Start the loaded event."""
        return self._send_ws({"tag": "start"})

    def pause_timer(self) -> bool:
        """Pause the running timer."""
        return self._send_ws({"tag": "pause"})

    def reload_timer(self) -> bool:
        """Reload/restart the current event."""
        return self._send_ws({"tag": "reload"})

    def add_time_ms(self, ms: int) -> bool:
        """Add time to the running timer (e.g. 60000 for +1 minute)."""
        return self._send_ws({"tag": "addtime", "payload": {"add": ms}})

    def remove_time_ms(self, ms: int) -> bool:
        """Remove time from the running timer (e.g. 60000 for -1 minute)."""
        return self._send_ws({"tag": "addtime", "payload": {"remove": ms}})
