"""Live, read-only, **unelevated**: the ``UIManager`` reads that need no call into the client.

Six of this class's members are pure reads — a resolved address plus words — so they can be verified
against the running client without a write connection, and therefore without elevation. That is the
same route ``tests/probe_agent_effects_live.py`` established: a ``ProcessMemoryReader`` and a
``RemoteScanner`` over the client's main module, a stand-in registered where ``require_client`` looks,
and the ported members run unmodified.

What it covers, and why these six:

- ``IsWorldMapShowing`` (the ``0x80000`` mask), ``IsUIDrawn`` (**inverted**, ``true`` for an address
  that does not resolve), ``IsShiftScreenshot`` — the client's own state words;
- ``GetCurrentTooltipAddress`` — the port's documented one-dereference read;
- ``GetSettings`` — the ``GW::Array<unsigned char>`` at the client's settings address;
- ``GetWindoPosition`` / ``IsWindowVisible`` — the same record, over six ids inside ``0x66``;
- **``GetKeyMappings``** — the one that matters most: the table sits in ``.data``'s uninitialised tail,
  so its ``0x75`` words exist only at runtime and this is the only witness that the offline
  derivation (``ui.key_mappings_table``, ``tools/key_mappings_hunt.py``) lands on the client's own
  remap table.

**What it deliberately does not cover**, and why: every member that *calls* the client
(``GetTextLanguage``'s preference getter, ``GetFPSLimit``, the four typed getters, ``SendUIMessage``,
``Keydown``, the dialog clicks) needs the game thread and the write path, which an unelevated shell
cannot have — those are the elevated run's business, ``tests/probe_ui_manager_live.py``.

Usage: (no elevation needed) python tests/probe_ui_manager_reads_live.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.enums_src.ui_enums import EnumPreference
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.ui.frame import FrameArray
from py4gw.ui_manager import UIManager
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
WINDOW_IDS = (0, 1, 12, 0x16, 0x40, 0x65)
SAMPLE_WORDS = 8


class _Tooltip:
    """``client.current_tooltip``'s one call: the global's address, resolved from the catalog."""

    def __init__(self, patterns: PatternCatalog, scanner: RemoteScanner) -> None:
        self._patterns = patterns
        self._scanner = scanner

    def resolve_address(self) -> int:
        result = self._patterns.resolve("ui.current_tooltip_ptr", self._scanner)
        return int(result.value) if result.ok else 0


class _LiveClient:
    """The surface these six members use: resolutions, the reader, and the tooltip global."""

    def __init__(
        self,
        reader: ProcessMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        self._reader = reader
        self.reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self.current_tooltip = _Tooltip(patterns, scanner)
        #: The frame array the dialog family's reads walk, built the way the connection builds it.
        self.frame_array = FrameArray(reader, scanner, patterns)

    def resolves(self, name: str) -> bool:
        return bool(self._patterns.resolve(name, self._scanner).ok)

    def _resolve(self, name: str) -> int:
        result = self._patterns.resolve(name, self._scanner)
        if not result.ok:
            raise RuntimeError(result.message or f"{name} did not resolve")
        return int(result.value)


def _ask(label: str, call: Any) -> Any:
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
    pid = int(process["pid"])
    report["pid"] = pid
    report["elevated"] = bool(win32.is_elevated())
    report["connect"] = "not used: this probe reads directly, so no elevation is required"

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        client = _LiveClient(reader, scanner, patterns)
    except Exception as error:  # noqa: BLE001 - reported, then closed
        report["error"] = f"{type(error).__name__}: {error}"
        reader.close()
        return _write(report)

    import py4gw.client as client_module

    client_module._current_client = client  # type: ignore[attr-defined]

    try:
        report["resolvers"] = {
            name: client.resolves(name)
            for name in (
                "ui.world_map_state_addr",
                "ui.ui_drawn_addr",
                "ui.shift_screenshot_addr",
                "ui.game_settings_addr",
                "ui.window_positions_array",
                "ui.key_mappings_table",
                "ui.current_tooltip_ptr",
            )
        }

        report["state"] = {
            "IsWorldMapShowing": _ask("IsWorldMapShowing", UIManager.IsWorldMapShowing),
            "IsUIDrawn": _ask("IsUIDrawn", UIManager.IsUIDrawn),
            "IsShiftScreenshot": _ask("IsShiftScreenshot", UIManager.IsShiftScreenshot),
            "GetCurrentTooltipAddress": _ask(
                "GetCurrentTooltipAddress", UIManager.GetCurrentTooltipAddress
            ),
        }

        settings = _ask("GetSettings", UIManager.GetSettings)
        report["settings_bytes"] = len(settings) if isinstance(settings, list) else settings

        report["preference_options"] = {
            "FrameLimiter": _ask(
                "GetPreferenceOptions",
                lambda: UIManager.GetPreferenceOptions(int(EnumPreference.FrameLimiter)),
            ),
            "AntiAliasing": _ask(
                "GetPreferenceOptions",
                lambda: UIManager.GetPreferenceOptions(int(EnumPreference.AntiAliasing)),
            ),
        }

        report["dialog"] = {
            "IsNPCDialogVisible": _ask("IsNPCDialogVisible", UIManager.IsNPCDialogVisible),
            "IsLockedChestWindowVisible": _ask(
                "IsLockedChestWindowVisible", UIManager.IsLockedChestWindowVisible
            ),
        }

        report["windows"] = {
            str(window_id): {
                "position": _ask(
                    "GetWindoPosition", lambda i=window_id: UIManager.GetWindoPosition(i)
                ),
                "visible": _ask(
                    "IsWindowVisible", lambda i=window_id: UIManager.IsWindowVisible(i)
                ),
            }
            for window_id in WINDOW_IDS
        }

        table = _ask("key table address", lambda: client._resolve("ui.key_mappings_table"))
        report["key_mappings_table"] = table if isinstance(table, str) else hex(table) if table else 0
        words = _ask("GetKeyMappings", UIManager.GetKeyMappings)
        report["key_mappings"] = (
            {
                "words": len(words),
                "first": words[:SAMPLE_WORDS],
                "nonzero": sum(1 for word in words if word),
                "max": max(words),
            }
            if isinstance(words, list)
            else words
        )
        report["note"] = (
            "read-only and unelevated: direct memory reads, no connect, no hook, no patch, no call. "
            "The members that call the client are the elevated probe's business."
        )
    finally:
        client_module._current_client = None  # type: ignore[attr-defined]
        reader.close()

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
