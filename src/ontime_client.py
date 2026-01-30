"""Client for communicating with Ontime API."""
import requests
import json
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event, Lock
from dataclasses import dataclass, field, replace
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
    has_next_event: bool = False  # True when there is a different next event (no wrap)
    has_previous_event: bool = False  # True when there is a previous event (no wrap)
    status: str = ""
    running: bool = False
    time_warning: Optional[float] = None
    time_danger: Optional[float] = None
    duration: Optional[float] = None
    blink: bool = False
    blackout: bool = False
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
        self.last_current_event_id: Optional[str] = None
        self.last_current_event_duration: Optional[float] = None
        self.last_blink: bool = False
        self.last_blackout: bool = False
        # Cache thresholds so they persist across runtime updates that don't include event details
        self.cached_time_warning: Optional[float] = None
        self.cached_time_danger: Optional[float] = None
        self.cached_duration: Optional[float] = None
        self.cached_has_next_event: bool = False
        self.cached_has_previous_event: bool = False
        self.use_websocket = use_websocket and (SOCKETIO_AVAILABLE or WEBSOCKET_AVAILABLE)
        self.websocket_connected = False
        self._ws_send_lock = Lock()
    
    def _parse_data(self, raw_data: Dict[str, Any]) -> Optional[TimerData]:
        """Unified parser for Ontime API responses."""
        if not isinstance(raw_data, dict):
            return None

        # Extract nested structures (use `or {}` to handle explicit null values)
        timer_dict = raw_data.get('timer')
        if not isinstance(timer_dict, dict):
            timer_dict = {'current': timer_dict} if timer_dict is not None else {}
            
        # current_event: from eventNow/currentEvent, or payload may be the event itself (granular update)
        current_event = raw_data.get('eventNow') or raw_data.get('currentEvent') or {}
        if not current_event and isinstance(raw_data.get('payload'), dict):
            pl = raw_data['payload']
            if pl.get('id') is not None and (pl.get('duration') is not None or pl.get('title') is not None):
                current_event = pl
        if not current_event and raw_data.get('id') is not None and (raw_data.get('duration') is not None or raw_data.get('title') is not None):
            current_event = raw_data  # payload was the event object directly
        next_event = raw_data.get('eventNext') or raw_data.get('nextEvent') or {}
        
        # Check if we're in idle state (no event loaded)
        playback = timer_dict.get('playback', '')
        no_event_loaded = not current_event or (not current_event.get('id') and not current_event.get('title'))
        is_idle = playback == 'idle' or (no_event_loaded and playback in ('', 'stop'))
        
        # Determine timer type
        if is_idle:
            timer_type = 'none'
        else:
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
        if timer_type != 'none':
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

        # Next/previous event detection - use rundown index as primary source (always update when available)
        next_title = ""
        has_next_event = self.cached_has_next_event
        has_previous_event = self.cached_has_previous_event
        
        # Check rundown data to detect first/last event
        rundown = raw_data.get('rundown', {})
        if isinstance(rundown, dict):
            selected_idx = rundown.get('selectedEventIndex')
            num_events = rundown.get('numEvents', 0)
            if selected_idx is not None and num_events > 0:
                # At first event (index 0) = no previous
                has_previous_event = selected_idx > 0
                self.cached_has_previous_event = has_previous_event
                # At last event = no next
                has_next_event = selected_idx < num_events - 1
                self.cached_has_next_event = has_next_event
        
        if isinstance(next_event, dict) and next_event:
            next_title = next_event.get('title', "")
            # Fallback wrap detection: compare timeStart (next before current = wrap)
            if has_next_event:  # Only check if rundown didn't already set to False
                next_start = next_event.get('timeStart')
                current_start = current_event.get('timeStart') if isinstance(current_event, dict) else None
                if next_start is not None and current_start is not None and next_start < current_start:
                    has_next_event = False
                    self.cached_has_next_event = False
        elif next_event:
            next_title = str(next_event)

        # Store current event id and duration for change_current_event_duration
        if isinstance(current_event, dict) and current_event:
            eid = current_event.get('id')
            if eid is not None:
                self.last_current_event_id = str(eid)
            dur = current_event.get('duration') or timer_dict.get('duration')
            if dur is not None:
                self.last_current_event_duration = float(dur)

        # Message/timer display state (blink, blackout) - from message.timer or top-level timer message
        msg_block = raw_data.get('message') if isinstance(raw_data.get('message'), dict) else None
        timer_msg = (msg_block.get('timer') or raw_data.get('timer')) if isinstance(msg_block, dict) else raw_data.get('timer')
        if isinstance(timer_msg, dict):
            if 'blink' in timer_msg:
                self.last_blink = bool(timer_msg['blink'])
            if 'blackout' in timer_msg:
                self.last_blackout = bool(timer_msg['blackout'])
        # Also handle payload that is message state only (tag "message" response)
        if isinstance(raw_data, dict) and 'timer' in raw_data and isinstance(raw_data.get('timer'), dict):
            t = raw_data['timer']
            if 'blink' in t:
                self.last_blink = bool(t['blink'])
            if 'blackout' in t:
                self.last_blackout = bool(t['blackout'])

        # Message-only payload: merge blink/blackout into last_timer_data so we don't reset the display
        if not has_timer_data and self.last_timer_data is not None:
            if not raw_data.get('currentEvent') and not raw_data.get('eventNow'):
                return replace(self.last_timer_data, blink=self.last_blink, blackout=self.last_blackout)

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
            has_next_event=has_next_event,
            has_previous_event=has_previous_event,
            status=timer_dict.get('state', raw_data.get('status', "")),
            running=timer_dict.get('running', raw_data.get('running', False)),
            time_warning=time_warning,
            time_danger=time_danger,
            duration=duration,
            blink=self.last_blink,
            blackout=self.last_blackout,
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
            if not isinstance(raw, dict):
                return
            # Handle Ontime format: { "tag": "poll", "payload": {...} } or { "type": "ontime-eventNow", "payload": {...} }
            if 'tag' in raw:
                payload = raw.get('payload', raw)
            elif 'type' in raw and raw.get('type', '').startswith('ontime-'):
                payload = raw.get('payload', raw)
            else:
                payload = raw
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

    def load_next_event(self) -> bool:
        """Load the next event (without starting)."""
        return self._send_ws({"tag": "load", "payload": "next"})

    def load_previous_event(self) -> bool:
        """Load the previous event (without starting)."""
        return self._send_ws({"tag": "load", "payload": "previous"})

    def add_time_ms(self, ms: int) -> bool:
        """Add time to the running timer (e.g. 60000 for +1 minute)."""
        return self._send_ws({"tag": "addtime", "payload": {"add": ms}})

    def remove_time_ms(self, ms: int) -> bool:
        """Remove time from the running timer (e.g. 60000 for -1 minute)."""
        return self._send_ws({"tag": "addtime", "payload": {"remove": ms}})

    def change_current_event_duration(self, delta_ms: int) -> bool:
        """Change the current event's duration by delta_ms. Returns True if sent."""
        if self.last_current_event_id is None or self.last_current_event_duration is None:
            return False
        new_duration = int(self.last_current_event_duration) + delta_ms
        if new_duration < 0:
            new_duration = 0
        msg = {"tag": "change", "payload": {self.last_current_event_id: {"duration": new_duration}}}
        if not self._send_ws(msg):
            return False
        self.last_current_event_duration = new_duration
        return True

    def set_timer_blackout(self, blackout: bool) -> bool:
        """Set timer screen blackout on or off."""
        return self._send_ws({"tag": "message", "payload": {"timer": {"blackout": blackout}}})

    def set_timer_blink(self, blink: bool) -> bool:
        """Set timer blink on or off."""
        return self._send_ws({"tag": "message", "payload": {"timer": {"blink": blink}}})
