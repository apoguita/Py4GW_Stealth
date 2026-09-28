"""Live, elevated, **value-preserving**: the acting ``UIManager`` members that can be driven without
changing anything the client is showing.

Every write here puts back the value that was just read, so the call path is exercised end to end —
the game-thread connection, the call form, the client's own setter — while the client's state stays as
it was. That is the project's own discipline (``AGENTS.md``: a live write is deliberate, bounded, and
attributable) and it is the first rung of the acting-members verification.

Covered: ``SetFPSLimit``, ``SetWindowVisible``, and the four typed setters. **Not covered, and
deliberately**: ``SendUIMessage`` / ``SendUIMessageRaw``, ``Keydown`` / ``Keyup`` / ``Keypress``,
``SetWindowPosition`` and the dialog clicks — those change the game (a key press moves the character,
a UI message can do anything the client listens for), so they need the owner watching the client.

Usage: (elevated) python tests/probe_ui_manager_writes_live.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw.enums_src.ui_enums import EnumPreference, FlagPreference, NumberPreference
from py4gw.ui_manager import UIManager
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
WINDOW_ID = 0


def _ask(call: Any) -> Any:
    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())

    with py4gw.connect(process, game_thread=True) as _client:
        report["game_thread"] = True

        # --- what the values are now ------------------------------------
        before = {
            "fps_limit": _ask(UIManager.GetFPSLimit),
            "window_visible": _ask(lambda: UIManager.IsWindowVisible(WINDOW_ID)),
            "frame_limiter": _ask(
                lambda: UIManager.GetEnumPreference(int(EnumPreference.FrameLimiter))
            ),
            "text_language": _ask(
                lambda: UIManager.GetIntPreference(int(NumberPreference.TextLanguage))
            ),
            "is_windowed": _ask(
                lambda: UIManager.GetBoolPreference(int(FlagPreference.IsWindowed))
            ),
            "string_pref": _ask(lambda: UIManager.GetStringPreference(0)),
        }
        report["before"] = before

        # --- the writes, each putting back what was read ------------------
        report["writes"] = {}

        if isinstance(before["fps_limit"], int):
            report["writes"]["SetFPSLimit"] = _ask(
                lambda: UIManager.SetFPSLimit(int(before["fps_limit"]))
            )
        if isinstance(before["window_visible"], bool):
            report["writes"]["SetWindowVisible"] = _ask(
                lambda: UIManager.SetWindowVisible(WINDOW_ID, before["window_visible"])
            )
        if isinstance(before["frame_limiter"], int):
            report["writes"]["SetEnumPreference"] = _ask(
                lambda: UIManager.SetEnumPreference(
                    int(EnumPreference.FrameLimiter), int(before["frame_limiter"])
                )
            )
        if isinstance(before["text_language"], int):
            report["writes"]["SetIntPreference"] = _ask(
                lambda: UIManager.SetIntPreference(
                    int(NumberPreference.TextLanguage), int(before["text_language"])
                )
            )
        if isinstance(before["is_windowed"], bool):
            report["writes"]["SetBoolPreference"] = _ask(
                lambda: UIManager.SetBoolPreference(
                    int(FlagPreference.IsWindowed), before["is_windowed"]
                )
            )
        if isinstance(before["string_pref"], str) and before["string_pref"]:
            report["writes"]["SetStringPreference"] = _ask(
                lambda: UIManager.SetStringPreference(0, before["string_pref"])
            )

        # --- and the same reads again ------------------------------------
        report["after"] = {
            "fps_limit": _ask(UIManager.GetFPSLimit),
            "window_visible": _ask(lambda: UIManager.IsWindowVisible(WINDOW_ID)),
            "frame_limiter": _ask(
                lambda: UIManager.GetEnumPreference(int(EnumPreference.FrameLimiter))
            ),
            "text_language": _ask(
                lambda: UIManager.GetIntPreference(int(NumberPreference.TextLanguage))
            ),
            "is_windowed": _ask(
                lambda: UIManager.GetBoolPreference(int(FlagPreference.IsWindowed))
            ),
            "string_pref": _ask(lambda: UIManager.GetStringPreference(0)),
        }
        report["unchanged"] = report["before"] == report["after"]
        report["note"] = (
            "every write put back the value just read, so the call path is exercised and the client's "
            "state is unchanged. The game-changing members are a separate run with the owner watching."
        )

    return _write(report)


def _write(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
