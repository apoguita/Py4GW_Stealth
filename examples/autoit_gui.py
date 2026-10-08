"""An AutoIt-style GUI written with Py4GW Stealth's AutoIt-compatible GUI layer.

This is the shape a GwAu3 script already has — a window, a group, a character combo, an
"On Top" checkbox, Start/Refresh buttons, a progress bar and a log list — written in Python
with AutoIt's own function names:

    python examples\\autoit_gui.py

Run it, click the buttons, and close the window. Nothing here touches the game client: the
example exists to show the API, and every call in it is an AutoIt v3 GUI reference call.
"""

from __future__ import annotations

import py4gw.gui as g

STATE: dict[str, object] = {"on_top": False, "started": False, "log": [], "closed": False}


def log(message: str) -> None:
    """Append a line to the window's log list.

    AutoIt's GUICtrlSetData() on a List destroys the previous list when the data starts with
    the separator character (Opt("GUIDataSeparatorChar"), "|" by default), which is how the
    log is redrawn.
    """

    entries = STATE["log"]
    assert isinstance(entries, list)
    entries.append(message)
    g.GUICtrlSetData(LOG_LIST, "|" + "|".join(str(entry) for entry in entries))


def on_start() -> None:
    """Handle the Start button (OnEvent mode: @GUI_CtrlId names the sender)."""

    STATE["started"] = not STATE["started"]
    g.GUICtrlSetData(START_BUTTON, "Stop" if STATE["started"] else "Start")
    g.GUICtrlSetData(PROGRESS, 50 if STATE["started"] else 0)
    log(f"Start pressed (control ID {g.GUI_CtrlId}, window {g.GUI_WinHandle})")


def on_refresh() -> None:
    """Handle the Refresh button."""

    g.GUICtrlSetData(PROGRESS, 100)
    log("Refresh pressed")


def on_on_top() -> None:
    """Handle the On Top checkbox, which switches the window's $WS_EX_TOPMOST style."""

    STATE["on_top"] = g.GUICtrlRead(ON_TOP_CHECK) == g.GUI_CHECKED
    checked = bool(STATE["on_top"])
    g.GUISetStyle(g.WS_OVERLAPPEDWINDOW, g.WS_EX_TOPMOST if checked else 0, WINDOW)
    log(f"On Top is now {'checked' if checked else 'unchecked'}")


def on_close() -> None:
    """Handle the window closing (the $GUI_EVENT_CLOSE system event)."""

    log("Close requested")
    g.GUIDelete(WINDOW)
    STATE["closed"] = True


# OnEvent mode is the AutoIt mode where the GUI calls functions instead of the script
# polling: the same Opt("GUIOnEventMode", 1) switch, and the same idle loop below.
g.Opt("GUIOnEventMode", 1)

WINDOW = g.GUICreate(
    "Py4GW Stealth - AutoIt GUI example", 500, 350, -1, -1, g.WS_OVERLAPPEDWINDOW
)
g.GUISetOnEvent(g.GUI_EVENT_CLOSE, on_close)

g.GUICtrlCreateGroup("Select Your Character", 8, 8, 475, 120)
g.GUICtrlCreateLabel("Character:", 24, 32, 70, 20)
CHARACTER_COMBO = g.GUICtrlCreateCombo(
    "Stealth Agent", 100, 30, 160, 200, g.BitOR(g.CBS_DROPDOWN, g.CBS_AUTOHSCROLL)
)
g.GUICtrlSetData(CHARACTER_COMBO, "Test Runner|Observer", "Stealth Agent")
ON_TOP_CHECK = g.GUICtrlCreateCheckbox("On Top", 280, 30, 70, 24)
g.GUICtrlSetOnEvent(ON_TOP_CHECK, on_on_top)
START_BUTTON = g.GUICtrlCreateButton("Start", 24, 72, 90, 25)
g.GUICtrlSetOnEvent(START_BUTTON, on_start)
REFRESH_BUTTON = g.GUICtrlCreateButton("Refresh", 124, 72, 90, 25)
g.GUICtrlSetOnEvent(REFRESH_BUTTON, on_refresh)
g.GUICtrlCreateGroup("", -99, -99, 1, 1)

g.GUICtrlCreateGroup("Status", 8, 140, 475, 80)
g.GUICtrlCreateLabel("Progress:", 24, 170, 60, 20)
PROGRESS = g.GUICtrlCreateProgress(90, 168, 380, 22)
g.GUICtrlCreateGroup("", -99, -99, 1, 1)

g.GUICtrlCreateLabel("Event log", 8, 228, 100, 20)
LOG_LIST = g.GUICtrlCreateList("", 8, 250, 475, 90, g.BitOR(g.LBS_NOTIFY, g.WS_VSCROLL))

g.GUISetFont(9, 400, g.GUI_FONTNORMAL, "Segoe UI")
g.GUISetState(g.SW_SHOW, WINDOW)
log(f"Window created with handle {WINDOW}")

# The AutoIt OnEvent idle loop: "The While loop must be restricted to Sleep() to reduce CPU
# usage. No action on the GUI inside the loop." The ported Sleep() delivers GUI events
# while it waits, which is what makes that loop work.
while not STATE["closed"]:
    g.Sleep(50)
