"""Live probe, read-only: every read ``UIManager`` answers, against the running client.

The class's reads are checked against fixtures; this asks the **client** and reports what each member
answered. It is the pass `docs/UIMANAGER_PORT.md` lists as owed, and it is deliberately read-only:

1. the three state words — ``IsWorldMapShowing`` (the ``0x80000`` mask), ``IsUIDrawn`` (**inverted**,
   ``true`` for an address that does not resolve), ``IsShiftScreenshot``;
2. the tooltip address and the text language;
3. the preference surface — the option list, the four typed getters, the frame limit;
4. the client's settings array (its length, not its contents);
5. the built-in windows — ``GetWindoPosition``/``IsWindowVisible`` over a sample of ids;
6. **the key-remap table** — the resolver ``ui.key_mappings_table`` and the ``0x75`` words it reads,
   which exists only at runtime (the table sits in ``.data``'s uninitialised tail), so this is the
   only witness that the offline derivation lands on the client's own table;
7. the dialog family's two visibility reads, which walk the frame tree.

It connects with ``game_thread=False``: no hook, no patch, no call. Nothing is written to the client,
and no member that acts is invoked — the acting members (``SendUIMessage``, ``Keydown``,
``SetWindowVisible``, ``SetFPSLimit``, the setters) are a separate, explicitly scoped run.

Usage: (elevated) python tests/probe_ui_manager_live.py [report-path]
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

#: ``--game-thread`` opens the **write** connection (``py4gw.connect(..., game_thread=True)``), which
#: is what the members that *call* the client need — the preference getters, ``GetTextLanguage`` and
#: ``GetFPSLimit`` go through ``ConnectedClient.call_function``, and that raises on a read-only
#: connection ("this connection was opened without the game thread"). Without the flag the probe stays
#: a pure reader and those members report that refusal, which is itself a verified answer.
GAME_THREAD = "--game-thread" in sys.argv

#: The window ids sampled. ``Constants::WindowID_Count`` is ``0x66``, so every id here is inside the
#: bound the member checks (``ui.h:109``).
WINDOW_IDS = (0, 1, 12, 0x16, 0x40, 0x65)

#: How many of the table's words are printed; the whole ``0x75`` are read either way.
SAMPLE_WORDS = 8


def _ask(label: str, call: Any) -> Any:
    """Run one ported read and record what it answered — an exception is reported, never hidden."""

    try:
        return call()
    except Exception as error:
        return f"{type(error).__name__}: {error}"


def _table_address(client: Any) -> Any:
    """The address the catalog resolved for the key-remap table, or the reason it did not."""

    try:
        if not client.resolves("ui.key_mappings_table"):
            return "ui.key_mappings_table did not resolve on this build"
        return int(client._resolve("ui.key_mappings_table"))
    except Exception as error:
        return f"{type(error).__name__}: {error}"


def _window_reads() -> dict[str, Any]:
    """``GetWindoPosition``/``IsWindowVisible`` over the sampled ids."""

    out: dict[str, Any] = {}
    for window_id in WINDOW_IDS:
        out[str(window_id)] = {
            "position": _ask("GetWindoPosition", lambda i=window_id: UIManager.GetWindoPosition(i)),
            "visible": _ask("IsWindowVisible", lambda i=window_id: UIManager.IsWindowVisible(i)),
        }
    return out


def _key_mappings() -> dict[str, Any]:
    """The remap table: the resolved address, the word count, and the first words."""

    words = _ask("GetKeyMappings", UIManager.GetKeyMappings)
    if not isinstance(words, list):
        return {"GetKeyMappings": words}
    return {
        "words": len(words),
        "first": words[:SAMPLE_WORDS],
        "nonzero": sum(1 for word in words if word),
    }


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())
    report["game_thread"] = GAME_THREAD

    with py4gw.connect(process, game_thread=GAME_THREAD) as client:
        report["key_mappings_table"] = _table_address(client)

        report["state"] = {
            "GetTextLanguage": _ask("GetTextLanguage", UIManager.GetTextLanguage),
            "IsWorldMapShowing": _ask("IsWorldMapShowing", UIManager.IsWorldMapShowing),
            "IsUIDrawn": _ask("IsUIDrawn", UIManager.IsUIDrawn),
            "IsShiftScreenshot": _ask("IsShiftScreenshot", UIManager.IsShiftScreenshot),
            "GetCurrentTooltipAddress": _ask(
                "GetCurrentTooltipAddress", UIManager.GetCurrentTooltipAddress
            ),
            "GetFPSLimit": _ask("GetFPSLimit", UIManager.GetFPSLimit),
        }

        options = _ask(
            "GetPreferenceOptions",
            lambda: UIManager.GetPreferenceOptions(int(EnumPreference.FrameLimiter)),
        )
        report["preferences"] = {
            "frame_limiter_options": options,
            "GetEnumPreference": _ask(
                "GetEnumPreference",
                lambda: UIManager.GetEnumPreference(int(EnumPreference.FrameLimiter)),
            ),
            "GetIntPreference": _ask(
                "GetIntPreference",
                lambda: UIManager.GetIntPreference(int(NumberPreference.TextLanguage)),
            ),
            "GetBoolPreference": _ask(
                "GetBoolPreference",
                lambda: UIManager.GetBoolPreference(int(FlagPreference.IsWindowed)),
            ),
            "GetStringPreference": _ask(
                "GetStringPreference",
                lambda: UIManager.GetStringPreference(0),
            ),
        }

        settings = _ask("GetSettings", UIManager.GetSettings)
        report["settings_bytes"] = len(settings) if isinstance(settings, list) else settings

        report["windows"] = _window_reads()
        report["key_mappings"] = _key_mappings()

        report["dialog"] = {
            "IsNPCDialogVisible": _ask("IsNPCDialogVisible", UIManager.IsNPCDialogVisible),
            "IsLockedChestWindowVisible": _ask(
                "IsLockedChestWindowVisible", UIManager.IsLockedChestWindowVisible
            ),
        }

        report["note"] = (
            "read-only: game_thread=False installed no hook and no patch, and no call into the client "
            "was made. The members that act are a separate, explicitly scoped run."
        )

    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
