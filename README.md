# FloatTime – Ontime Overlay Timer

Lightweight desktop app that shows an Ontime timer in always-on-top mode. Ideal for displaying the timer over PowerPoint or other applications.

**Polish documentation:** [README.pl.md](README.pl.md)

## Configuration

The app stores configuration in a JSON file in the user directory:

**Windows:**
```
C:\Users\<username>\.floattime\config.json
```

**Linux/macOS:**
```
~/.floattime/config.json
```

Configuration options:
- `server_url` – Ontime server URL
- `display_mode` – Display mode: `"timer"` or `"clock"`
- `background_visible` – Background visibility (true/false)
- `window_size` – Window size: `[width, height]`
- `locked` – Window lock state (true/false)

You can edit this file manually or use the app’s context menu.

## Features

### Core
- **Always-on-top** – Timer stays above other windows (on macOS via native NSWindow level when PyObjC is installed)
- **Lightweight** – Python + PyQt6 (no Electron)
- **Cross-platform** – Windows, macOS, Linux
- **URL configuration** – Just set the Ontime server URL
- **System tray** – Runs in the background with a tray icon

### Window interaction
- **Dragging** – Move the window by dragging with the mouse
- **Resizing** – Resize from all four corners
- **Smart cursor** – Cursor changes when hovering over corners
- **Auto-scaling** – Timer text scales to fit the window (binary search for optimal font size)

### Timer controls (hover overlays)
- **Top edge** – **+1** and **−1** (add/subtract minute), centered
- **Bottom edge** – **▶ Start**, **⏸ Pause**, **↻ Restart**, centered
- Both groups appear when hovering over the window

### Display
- **Display modes** – Switch between Ontime timer and system clock
- **Timer types** – Supports `count up`, `count down`, `clock`, `none`
- **Threshold colors** – Text color changes:
  - **White** – Normal
  - **Orange** (`#FFA528`) – Warning threshold
  - **Red** (`#FA5656`) – Danger/overtime
- **Transparent background** – Option to hide background for a fully transparent window

### Shortcuts and persistence
- **Saved settings** – Server URL, window size, display mode, background visibility
- **Shortcuts**:
  - `Ctrl+Q` / `Ctrl+W` – Quit
  - `Escape` – Hide window
  - **Double-click** – Quit

## Requirements

- Python 3.9+
- Ontime server (local or remote)
- **macOS:** optional `pyobjc-framework-Cocoa` for reliable always-on-top (`pip install pyobjc-framework-Cocoa`)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
python run.py
```

Or directly:
```bash
python src/main.py
```

## Configuration

### First run

On first run you’ll be asked for the Ontime server URL (e.g. `http://localhost:4001`).

### Changing settings

- **System tray** – Right-click the tray icon → “Configure...”
- **Context menu** – Right-click the timer window

### Menu options

- **Configure...** – Set Ontime server URL
- **Show / Hide** – Show or hide the window
- **Always on Top** – Toggle always-on-top
- **Show Background** – Toggle background (transparent/solid)
- **Lock in Place** – Lock position (disable drag and resize)
- **Show Clock / Show Timer** – Switch between timer and system clock
- **Reset Size** – Restore default window size
- **Timer** (submenu) – Start, Pause, Restart, +1 min, −1 min
- **Quit** – Exit the app

## Building an executable

The build script creates an isolated `.build_venv`, installs dependencies there, and runs PyInstaller so your main Python environment stays clean.

```bash
python build.py
```

Output in `dist/floattime/` (onedir mode). On macOS: `dist/floattime/floattime.app` or `dist/floattime/floattime`.

## Usage

### Basics

1. Start the app – it appears in the system tray.
2. Set the Ontime URL if prompted.
3. Timer updates in real time via WebSocket.
4. Drag the window to move it (when not locked).
5. Hover over a corner and drag to resize.
6. Hover over the window to show +1/−1 at the top and Start/Pause/Restart at the bottom.

### Resizing

- Hover over any of the four corners; the cursor changes (↖↘ or ↗↙).
- Click and drag to resize.
- Timer text automatically scales to use ~98% of the available space.

### Display modes

- **Timer** – Ontime timer (default)
- **Clock** – System clock
- Toggle via tray or context menu.

### Threshold colors

- **Count down:** White (normal) → Orange (warning) → Red (danger/overtime)
- **Count up:** White (within time) → Orange (over duration)

## Project structure

```
FloatTime/
├── src/
│   ├── main.py              # Main application
│   ├── ontime_client.py     # Ontime API client (WebSocket)
│   ├── timer_widget.py      # Timer display widget
│   ├── timer_controls.py    # Control overlays (top: +1/−1, bottom: play/pause/restart)
│   ├── tray_manager.py      # System tray icon and menu
│   ├── config.py            # Configuration
│   ├── logger.py             # Logging (FLOATTIME_DEBUG)
│   └── ui/
│       └── config_dialog.py  # Config dialog
├── hooks/                    # PyInstaller hooks (e.g. PyQt6)
├── requirements.txt
├── build.py                  # Build script (venv + PyInstaller)
├── run.py
├── README.md                 # This file (English)
└── README.pl.md              # Polish documentation
```

## Ontime API

The app connects to Ontime via WebSockets.

### WebSocket

- **Endpoint:** `ws://<server-url>/ws` (derived from configured `server_url` by replacing `http` with `ws` and appending `/ws`).
- **On connect:** the client sends `{"tag": "poll"}` to request initial/runtime data.
- **Incoming messages:** JSON with optional `tag` and `payload`; the app uses `payload` (or the whole message) as Ontime runtime data.
- **Control (send):**
  - `{"tag": "start"}` – start the timer
  - `{"tag": "pause"}` – pause
  - `{"tag": "reload"}` – reload/restart current event
  - `{"tag": "addtime", "payload": {"add": ms}}` – add time (e.g. 60000 for +1 min)
  - `{"tag": "addtime", "payload": {"remove": ms}}` – remove time (e.g. 60000 for −1 min)

### Data format (parsed from server)

The app parses Ontime-style JSON:

- **Top-level or nested:** `timer` (object or value), `timerType`, `currentEvent` / `eventNow`, `nextEvent` / `loaded` / `next`, `status`, `running`.
- **Timer object:** `current`, `remaining`, `elapsed`, `state`, `running`, `timerType`, `timeWarning`, `timeDanger`, `duration`.
- **Event:** `title`, `timerType`, `timeWarning`, `timeDanger`, `duration`.

## Debugging

Enable verbose logging with:

```bash
export FLOATTIME_DEBUG=true   # Linux/macOS
set FLOATTIME_DEBUG=true      # Windows (cmd)
```

Then run the app; logs appear in the console.

## Troubleshooting

**Timer not updating**
- Check that the Ontime server is running and reachable at the configured URL.
- Enable `FLOATTIME_DEBUG=true` and check logs.
- Ensure the port isn’t blocked by a firewall.

**Window not visible**
- Check the system tray; the window may be hidden. Right-click the tray icon → “Show”.

**Always-on-top not working on macOS**
- Install: `pip install pyobjc-framework-Cocoa`
- Ensure “Always on Top” is enabled in the menu.

**Colors not changing**
- In Ontime, set `timeWarning` and `timeDanger` for the event.
- Use `FLOATTIME_DEBUG=true` to verify timer type detection.

## License

GNU GPL — see [LICENSE.md](LICENSE.md).
