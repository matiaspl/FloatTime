# Plan: Reuse one menu for tray and pop-up (pop-up as source)

## Status

- Implemented.
- This planning document is retained for reference.
- For the final post-implementation state since `v0.3.0`, see `docs/RELEASE_NOTES_SINCE_v0.3.0.md`.

## Goal
Single source of truth for the application menu. Use the current **pop-up (context) menu** logic in `main.py` as the source; tray menu will use the same builder.

## Current state
- **Pop-up** (`main.py` `show_context_menu`): Builds a `QMenu` from an `actions` list + loop; includes separators, "Timer source" submenu, "Timer controls" submenu before Reset Size; then `menu.exec(self.mapToGlobal(pos))`. Uses "Hide" and "Quit".
- **Tray** (`tray_manager.py` `_create_menu`): Builds a separate `QMenu` with explicit `addAction` calls; stores refs to checkable actions (`always_on_top_action`, `blink_action`, etc.) for `update_menu_states()`. Uses "Show" and "Quit".
- **Difference**: Tray has "Show" (to show window from tray); pop-up has "Hide". Everything else is duplicated.

## Design

### 1. Single builder in `main.py`
- Add **`build_app_menu(self, parent=None)`** that:
  - Takes an optional `parent` (e.g. `self` for pop-up, or no parent for tray).
  - Builds the **same** menu structure as the current pop-up (actions list + loop, Timer source submenu, Timer controls submenu).
  - **Show/Hide**: Use one entry that shows **"Show"** when window is hidden and **"Hide"** when visible; triggered action calls `show_window()` if hidden else `hide()`. Same behaviour from both tray and window.
  - Returns **`(menu, action_refs)`**:
    - `menu`: the `QMenu` to show.
    - `action_refs`: a small dict of `str -> QAction` for actions whose **checked** state must be updated when app state changes (e.g. `'always_on_top'`, `'background_visible'`, `'locked'`, `'hover_controls'`, `'addtime_affects_duration'`, `'blink'`, `'blackout'`). Used so the tray menu (which is created once) can be refreshed without rebuilding.

### 2. Pop-up (context menu)
- **`show_context_menu(self, pos)`**:
  - `menu, _ = self.build_app_menu(self)`
  - `menu.exec(self.mapToGlobal(pos))`
- No need to keep `action_refs`; menu is recreated each time so state is always current.

### 3. Tray
- **Setup**:
  - Call `menu, action_refs = self.window.build_app_menu(parent=None)` (or parent the tray icon/widget).
  - `self.tray_icon.setContextMenu(menu)`.
  - Store `action_refs` on the window or tray manager (e.g. `self.window._menu_action_refs = action_refs`).
  - Connect **`menu.aboutToShow`** to a method that updates checked states using `action_refs` (so every time the user opens the tray menu, states are up to date).
- **`update_menu_states`** (in `main.py` or tray):
  - Signature becomes **`update_menu_states(self, action_refs=None)`**.
  - If `action_refs` is None, use `getattr(self, '_menu_action_refs', {})` so pop-up path doesn’t need to pass refs.
  - Update `action_refs['always_on_top'].setChecked(...)`, etc., and the **Show/Hide** action text (e.g. `action_refs['show_hide'].setText('Hide' if self.isVisible() else 'Show')`).
- **Remove** `tray_manager._create_menu()` and all duplicate menu-building code from the tray. Tray only calls the window’s builder and wires `aboutToShow` to `update_menu_states`.

### 4. Action refs to expose from the builder
From the current tray `update_menu_states`, the refs needed are:
- `always_on_top`
- `background_visible`
- `locked`
- `hover_controls`
- `addtime_affects_duration`
- `blink`
- `blackout`
- `show_hide` (for Show/Hide text and possibly enabled state)

Timer source and display mode are reflected by which item is checked in the Timer source submenu; that submenu is rebuilt from current state each time the menu is built, so no refs needed for those if we rebuild the menu on `aboutToShow`. But the tray menu is set once, so we **don’t** rebuild it on `aboutToShow`; we only update the existing actions’ checked state. So Timer source submenu items **do** need to be updated when state changes — either we store refs for those too, or we rebuild the whole menu on tray `aboutToShow`. Simpler approach: **rebuild the tray menu on `aboutToShow`**. Then we don’t need to store or update any refs for the tray; we just call `menu = self.window.build_app_menu()` and `tray_icon.setContextMenu(menu)` every time the user is about to see the menu. So:
- **Tray**: On **`aboutToShow`** (we need the tray icon to expose when its context menu is about to show — `QSystemTrayIcon` doesn’t have that; the **menu** does). So we set the tray’s context menu to a **stub menu** that has `aboutToShow` connected: when it fires, we build a **new** menu with `build_app_menu()`, then… we can’t replace the menu that’s already opening. So we can’t “rebuild on aboutToShow” for the tray without changing which menu is shown. So we **must** keep the menu once and update its actions. So the builder returns `(menu, action_refs)` and we update those refs in `update_menu_states` and also connect `menu.aboutToShow` to `update_menu_states` so the menu is up to date when opened.

### 5. Timer source submenu state
The Timer source submenu has 5 checkable items (Main, Aux 1, Aux 2, Aux 3, System clock). Those are created when the menu is built. If the tray menu is built once, their checked state is fixed unless we store refs for them. So we have two options:
- **Option A**: Builder returns refs for those five actions too; `update_menu_states` sets their checked state from `config.get_timer_source()` and `timer_widget.display_mode`.
- **Option B**: Don’t store refs; in `update_menu_states` we only update the refs we have (always_on_top, blink, etc.). For Timer source we’d need to either add refs (Option A) or accept that the tray menu’s Timer source check marks don’t update until the next time the tray menu is rebuilt (e.g. restart). Option A is better UX.

So: **builder returns refs for all checkable/toggleable items**, including the five Timer source options. We can key them e.g. `timer_source_main`, `timer_source_aux1`, …, `timer_source_clock`, or a list `timer_source_actions` in order [Main, Aux1, Aux2, Aux3, System clock]. Then `update_menu_states` sets the checked state for the current timer source and display mode.

## Implementation steps (summary)
1. In **main.py**, extract the current pop-up menu construction into **`build_app_menu(parent=None)`**:
   - Use the same `actions` list and loop.
   - Add a **Show/Hide** entry: label "Show" when `not self.isVisible()`, "Hide" when visible; trigger = `show_window()` if hidden else `hide()`.
   - When creating checkable actions (and the Timer source submenu items), store each in a dict keyed by a stable name.
   - Return `(menu, action_refs)`.
2. **`show_context_menu`**: `menu, _ = self.build_app_menu(self)` then `menu.exec(...)`.
3. **Tray**: Remove `_create_menu()`. In `_setup_tray()`, call `menu, action_refs = self.window.build_app_menu()`, set `self.window._menu_action_refs = action_refs`, `self.tray_icon.setContextMenu(menu)`, and connect `menu.aboutToShow` to `self.window.update_menu_states` (or a lambda that calls it with no args).
4. Move **`update_menu_states`** from tray_manager to **main.py** (so it can see `self.timer_widget`, `self.config`, etc.). It takes no args and uses `self._menu_action_refs` to update all checkable actions (including Timer source and Show/Hide text). Tray_manager no longer has `update_menu_states`; the window does.
5. Replace all **`self.tray_manager.update_menu_states()`** calls with **`self.update_menu_states()`** (or keep the call on tray_manager and have it delegate to `self.window.update_menu_states()`).
6. Remove duplicate menu code from tray_manager; ensure tray icon still gets its menu from the window’s builder.

## File changes
| File | Change |
|------|--------|
| `main.py` | Add `build_app_menu(parent=None) -> (QMenu, dict)`. Add `update_menu_states()`. Simplify `show_context_menu` to use builder. Add Show/Hide entry in builder. |
| `tray_manager.py` | Remove `_create_menu()`. In `_setup_tray()`, get menu from `window.build_app_menu()`, set refs on window, connect `menu.aboutToShow` to `window.update_menu_states`. Remove `update_menu_states` from tray (or make it call `window.update_menu_states()`). |
| Call sites | All `tray_manager.update_menu_states()` → `self.update_menu_states()` (or keep tray_manager as a thin wrapper). |

## Edge cases
- **Show/Hide**: Tray menu is built once; the Show/Hide action’s **text** must be updated in `update_menu_states` (and possibly when window is shown/hidden) so it shows "Show" when window hidden and "Hide" when visible.
- **Display mode / Timer source**: All five options’ checked state updated in `update_menu_states` from `config.get_timer_source()` and `timer_widget.display_mode`.
