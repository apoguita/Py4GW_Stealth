"""Read-only check: is the client still running, and is its window responding?

Nothing here connects, patches or writes: it enumerates the process and asks Windows whether the
window it owns is hung (``IsHungAppWindow``), which is what "the application is not responding"
means. It also re-reads the two entry points the capability layer patches, so "the hooks are out"
is checked rather than assumed.

Usage: (elevated) python tests/probe_client_health.py [report-path]
"""

from __future__ import annotations

import ctypes
import json
import sys
from ctypes import wintypes
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

HOOK_ENTRY = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
OBSERVE_ENTRY = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")
HOOK_RESOLVER = "game_thread.leave_game_thread_func"
OBSERVE_RESOLVER = "ui.send_ui_message_func"

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.IsHungAppWindow.argtypes = (wintypes.HWND,)
user32.IsHungAppWindow.restype = wintypes.BOOL
user32.EnumWindows.argtypes = (ctypes.c_void_p, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int


def windows_of(pid: int) -> list[dict[str, Any]]:
    """Every top-level window owned by ``pid``, with whether Windows calls it hung."""

    found: list[dict[str, Any]] = []

    def visit(hwnd: int, _: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid:
            return True
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        found.append(
            {
                "hwnd": hex(hwnd),
                "title": title.value,
                "hung": bool(user32.IsHungAppWindow(hwnd)),
            }
        )
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(visit), 0)
    return found


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    report["process"] = str(clients[0].get("path"))

    module = win32.get_main_module(pid)
    from py4gw.memory import ProcessMemoryReader
    from py4gw.scanner import PatternCatalog, RemoteScanner

    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")

        entries = {}
        for name, expected in (
            (HOOK_RESOLVER, HOOK_ENTRY),
            (OBSERVE_RESOLVER, OBSERVE_ENTRY),
        ):
            result = catalog.resolve(name, scanner)
            if not result.ok:
                entries[name] = {"resolved": False, "message": result.message}
                continue
            address = int(result.value)
            observed = reader.read(address, len(expected))
            entries[name] = {
                "resolved": True,
                "address": hex(address),
                "entry": observed.hex(" "),
                "original": observed == expected,
            }
        report["entries"] = entries

    report["windows"] = windows_of(pid)
    report["hung_windows"] = [
        window["title"] for window in report["windows"] if window["hung"]
    ]
    # Only the client's own top-level window speaks for the client: an IME helper window
    # ("Default IME", "MSCTFIME UI") is routinely reported as hung and is not the game.
    game = [
        window
        for window in report["windows"]
        if str(window["title"]).startswith("Guild Wars")
    ]
    report["game_windows"] = [window["title"] for window in game]
    report["responding"] = (not any(window["hung"] for window in game)) if game else None
    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
