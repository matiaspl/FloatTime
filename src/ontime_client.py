"""Client for communicating with Ontime API."""
import requests
import json
import socket
import uuid
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event, Lock
from dataclasses import dataclass, field, replace
from logger import get_logger

logger = get_logger(__name__)

# Client identity for Ontime server (clientSet message + optional HTTP headers)
try:
    from __init__ import __version__
except ImportError:
    __version__ = "1.0.0"

# Generate a unique client name: "FloatTime@hostname-shortid"
_hostname = socket.gethostname().split('.')[0]  # Short hostname (no domain)
_short_id = uuid.uuid4().hex[:4]
CLIENT_NAME = f"{_hostname} {_short_id}"
# Ontime WebSocket: identify client so server can list us (same as apps/client socket.ts MessageTag.ClientSet)
# Tag value is kebab-case (common in TypeScript string enums)
WS_TAG_CLIENT_SET = "client-set"

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
    timer_source: str = 'main'  # 'main' | 'aux1' | 'aux2' | 'aux3'
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
        self._timer_source: str = 'main'  # 'main' | 'aux1' | 'aux2' | 'aux3'
        self.last_main_data: Optional[TimerData] = None
        self.last_aux_data: Dict[str, Optional[TimerData]] = {'1': None, '2': None, '3': None}
        self.use_websocket = use_websocket and (SOCKETIO_AVAILABLE or WEBSOCKET_AVAILABLE)
        self.websocket_connected = False
        self._ws_send_lock = Lock()
    
    def _parse_data(self, raw_data: Dict[str, Any]) -> Optional[TimerData]:
        """Unified parser for Ontime API responses."""
        if not isinstance(raw_data, dict):
            return None

        # Parse auxiliary timers when present (full poll or granular ontime-auxtimerN)
        for aux_id in ('1', '2', '3'):
            key = f'auxtimer{aux_id}'
            if key in raw_data and isinstance(raw_data.get(key), dict):
                self.last_aux_data[aux_id] = self._aux_to_timer_data(aux_id, raw_data[key])

        # If this message only contains aux timer data, skip main parsing
        if not any(raw_data.get(k) for k in ('timer', 'eventNow', 'currentEvent', 'eventNext')):
            if any(f'auxtimer{i}' in raw_data for i in ('1', '2', '3')):
                return self._get_display_data()

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

        # Message-only payload: merge blink/blackout into cached display data so we don't reset timer values.
        if not has_timer_data and not raw_data.get('currentEvent') and not raw_data.get('eventNow'):
            if self.last_main_data is not None:
                self.last_main_data = replace(
                    self.last_main_data,
                    blink=self.last_blink,
                    blackout=self.last_blackout,
                )
            for aux_id in ('1', '2', '3'):
                aux_data = self.last_aux_data.get(aux_id)
                if aux_data is not None:
                    self.last_aux_data[aux_id] = replace(
                        aux_data,
                        blink=self.last_blink,
                        blackout=self.last_blackout,
                    )
            # If selected source has no cached data yet, _get_display_data() will return a fallback TimerData.
            return self._get_display_data()

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

        main_data = TimerData(
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
            timer_source='main',
            timer_dict=timer_dict,
            raw_data=raw_data
        )
        if raw_data.get('timer') is not None or raw_data.get('eventNow') or raw_data.get('currentEvent'):
            self.last_main_data = main_data
        return self._get_display_data()

    def _aux_to_timer_data(self, aux_id: str, aux: Dict[str, Any]) -> TimerData:
        """Build TimerData from an auxiliary timer dict (duration, current, playback, direction)."""
        if not isinstance(aux, dict):
            return TimerData(timer_source=f'aux{aux_id}', title=f'Aux {aux_id}')
        direction = (aux.get('direction') or 'count-down').lower().replace('-', ' ')
        timer_type = 'count up' if 'up' in direction else 'count down'
        playback = aux.get('playback', 'stop')
        running = playback == 'play'
        current = aux.get('current')
        duration = aux.get('duration') if isinstance(aux.get('duration'), (int, float)) else None
        return TimerData(
            timer_ms=current,
            timer_type=timer_type,
            title=f'Aux {aux_id}',
            next_event_title='',
            has_next_event=False,
            has_previous_event=False,
            status=playback,
            running=running,
            time_warning=None,
            time_danger=None,
            duration=duration,
            blink=self.last_blink,
            blackout=self.last_blackout,
            timer_source=f'aux{aux_id}',
            timer_dict=aux,
            raw_data=aux
        )

    def _get_display_data(self) -> Optional[TimerData]:
        """Return TimerData for the currently selected source (main or aux1/2/3)."""
        if self._timer_source == 'main':
            out = self.last_main_data
        else:
            # aux1 -> "1"
            key = self._timer_source[-1]
            out = self.last_aux_data.get(key)
        if out is None:
            out = TimerData(timer_source=self._timer_source, title='Aux' if self._timer_source != 'main' else '')
        return out

    def set_timer_source(self, source: str):
        """Set which timer to display: 'main', 'aux1', 'aux2', 'aux3'."""
        if source in ('main', 'aux1', 'aux2', 'aux3'):
            self._timer_source = source

    def get_timer_source(self) -> str:
        return self._timer_source

    def refresh_display(self):
        """Re-send current display data (e.g. after changing timer source)."""
        data = self._get_display_data()
        if data:
            self._notify(data)

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
            # Handle Ontime format: { "tag": "poll", "payload": {...} } or { "type": "ontime-*", "payload": {...} }
            if 'tag' in raw:
                payload = raw.get('payload', raw)
            elif 'type' in raw:
                t = raw.get('type', '')
                payload = raw.get('payload', raw)
                # Granular aux timer updates: wrap so _parse_data sees auxtimer1/2/3 key
                if t == 'ontime-auxtimer1':
                    payload = {'auxtimer1': payload} if isinstance(payload, dict) else {'auxtimer1': {}}
                elif t == 'ontime-auxtimer2':
                    payload = {'auxtimer2': payload} if isinstance(payload, dict) else {'auxtimer2': {}}
                elif t == 'ontime-auxtimer3':
                    payload = {'auxtimer3': payload} if isinstance(payload, dict) else {'auxtimer3': {}}
            else:
                payload = raw
            data = self._parse_data(payload)
            if data: self._notify(data)
        except Exception as e:
            logger.error(f"WS message error: {e}")

    def _ws_loop(self):
        """Standard WebSocket loop with auto-reconnect."""
        ws_url = self.server_url.replace('http', 'ws', 1) + "/ws"

        def on_open(ws):
            # App may already be stopping when the socket finishes opening.
            if self.stop_event.is_set():
                return
            try:
                logger.info("WebSocket connected")
                self.websocket_connected = True
                # Identify as FloatTime (same protocol as Ontime web client, see socket.ts)
                ws.send(json.dumps({
                    "tag": WS_TAG_CLIENT_SET,
                    "payload": {
                        "type": "floattime",
                        #"origin": "floattime",
                        #"path": "/",
                        "name": CLIENT_NAME,
                    },
                }))
                ws.send(json.dumps({"tag": "poll"}))
            except Exception as e:
                # Harmless race: socket opened and closed during app shutdown/source switch.
                self.websocket_connected = False
                if not self.stop_event.is_set():
                    logger.error(f"WebSocket on_open error: {e}")

        def on_close(ws, *args):
            self.websocket_connected = False

        while not self.stop_event.is_set():
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
                self.websocket_connected = False
            finally:
                self.websocket_connected = False
                self.ws = None

            if self.stop_event.is_set():
                break

            # Auto-reconnect every 3 seconds when connection fails/drops.
            logger.warning("WebSocket disconnected; reconnecting in 3 seconds...")
            self.stop_event.wait(3)

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
        if self.ws:
            try:
                # Tell websocket-client loop to stop.
                self.ws.keep_running = False
            except Exception:
                pass
            # Intentionally do not force ws.close() here. websocket-client may log
            # "'NoneType' object has no attribute 'sock' - goodbye" during shutdown
            # when close races with internal teardown. keep_running=False is enough.
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

    def start_aux_timer(self, aux_id: int) -> bool:
        """Start auxiliary timer 1, 2, or 3."""
        if aux_id not in (1, 2, 3):
            return False
        return self._send_ws({"tag": "auxtimer", "payload": {str(aux_id): "start"}})

    def pause_aux_timer(self, aux_id: int) -> bool:
        """Pause auxiliary timer 1, 2, or 3."""
        if aux_id not in (1, 2, 3):
            return False
        return self._send_ws({"tag": "auxtimer", "payload": {str(aux_id): "pause"}})

    def stop_aux_timer(self, aux_id: int) -> bool:
        """Stop auxiliary timer 1, 2, or 3."""
        if aux_id not in (1, 2, 3):
            return False
        return self._send_ws({"tag": "auxtimer", "payload": {str(aux_id): "stop"}})

    def add_aux_time_ms(self, aux_id: int, ms: int) -> bool:
        """Add time to auxiliary timer (e.g. 60000 for +1 minute)."""
        if aux_id not in (1, 2, 3):
            return False
        return self._send_ws({"tag": "auxtimer", "payload": {str(aux_id): {"addtime": ms}}})

    def set_timer_blackout(self, blackout: bool) -> bool:
        """Set timer screen blackout on or off."""
        return self._send_ws({"tag": "message", "payload": {"timer": {"blackout": blackout}}})

    def set_timer_blink(self, blink: bool) -> bool:
        """Set timer blink on or off."""
        return self._send_ws({"tag": "message", "payload": {"timer": {"blink": blink}}})
