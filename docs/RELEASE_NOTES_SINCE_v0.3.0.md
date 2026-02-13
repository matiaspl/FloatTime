# Release Notes Since `v0.3.0`

This document captures the current state of the app since the last tag (`v0.3.0`), including committed changes and current unreleased work in the working tree.

## Scope

- Base tag: `v0.3.0`
- Branch: `main`
- Includes:
  - commits already on branch after `v0.3.0`
  - local uncommitted updates currently in progress

## Committed Since `v0.3.0`

### Menu and tray unification

- Unified tray/context menu behavior around a single builder flow in `main`.
- Added centralized menu state refresh, including checkmarks and dynamic enable/disable behavior.
- Consolidated tray menu wiring and reduced duplicated menu definitions.

Key files:
- `src/main.py`
- `src/tray_manager.py`
- `docs/MENU_UNIFICATION_PLAN.md`

### Timer source and controls behavior

- Expanded timer source handling and control logic for main/aux/clock contexts.
- Improved enable/disable rules for timer controls depending on selected source/mode.
- Improved overlay control interaction and event handling.

Key files:
- `src/main.py`
- `src/timer_controls.py`
- `src/ontime_client.py`

### Config foundation updates

- Added config support for additional runtime behavior and toggles.

Key file:
- `src/config.py`

## Current Unreleased Additions (Working Tree)

### Simple Timer mode (local, no Ontime server)

- Added `Simple timer` as a selectable item in the `Timer source` menu.
- Added local timer implementation (`src/local_timer.py`) to run without Ontime server.
- Switching between Ontime sources, system clock, and simple timer is supported from the menu.

Key files:
- `src/local_timer.py` (new)
- `src/main.py`

### Simple timer behavior

- Three configurable start presets are supported.
- `Next/Previous event` in simple mode switch between those presets.
- `+/- 1` temporarily adjusts current timer/start baseline.
- `Play` resumes and does not force reset.
- `Reset` restores the selected preset's original value and preserves running/paused state.
- Timer is allowed to run past zero (overtime supported).
- Blink and blackout now function in simple mode using local state updates.

Key file:
- `src/local_timer.py`

### Simple timer configuration in UI

- Config dialog now includes:
  - three simple timer start values
  - warning threshold
  - danger threshold
- Values are persisted and applied immediately when simple timer is active.

Defaults:
- Presets: `15`, `20`, `30` minutes
- Warning: `2:00` (`120000 ms`)
- Danger: `0:00` (`0 ms`)

Key files:
- `src/ui/config_dialog.py`
- `src/config.py`
- `src/main.py`

### WebSocket resilience

- Added automatic websocket reconnect loop with 3-second retry interval after disconnect/failure.

Key file:
- `src/ontime_client.py`

## Files Changed Summary

### Since `v0.3.0` (committed)

- `docs/MENU_UNIFICATION_PLAN.md`
- `src/config.py`
- `src/main.py`
- `src/ontime_client.py`
- `src/timer_controls.py`
- `src/tray_manager.py`

### Current local/unreleased

- `src/config.py`
- `src/main.py`
- `src/ontime_client.py`
- `src/ui/config_dialog.py`
- `src/local_timer.py` (new)

## Notes

- Existing macOS import warnings (`AppKit`/`objc`) remain environment-dependent and unchanged in intent.
- This note is intended as a release handoff snapshot; update it when tagging the next release.
