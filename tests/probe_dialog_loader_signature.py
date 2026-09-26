"""Read-only probe: narrow down this build's ``DialogLoader_GetText`` by signature.

The sources' address for that function is stale here (`RESEARCH.md`, 2026-09-25), so it has to be
found the way the offsets catalog finds everything: an anchor in the client's own data, a walk to
the function that uses it, and a look at how that function is called.

Two anchors, both from the client's own assertion strings:

* ``dialog < DIALOGS`` and the other dialog-bound assertions — a loader that takes a dialog id
  would bound it, and the assertion lands **inside** that function;
* the dialog source paths and messages a previous probe found in ``.rdata``.

The narrowing step is the interesting one: a function called with a **small immediate** (a dialog
id is 0..0x39) is a very different thing from one called with pointers. So for every function an
anchor lands in, this scans the code for near calls to it and looks back for the ``push`` of its
first argument.

Read-only: nothing is called, nothing is written.

Usage: (elevated) python tests/probe_dialog_loader_signature.py [report-path]
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The largest value a dialog id can have (``DialogMemory::MAX_DIALOG_ID``).
MAX_DIALOG_ID = dialog.MAX_DIALOG_ID

#: How far back from a call site to look for the push of the first argument.
PUSH_WINDOW = 24

CALL_OPCODE = b"\xe8"
PUSH_IMM8 = 0x6A
PUSH_IMM32 = 0x68

#: Assertion messages from the client's own ``.rdata``, found by an earlier probe.
ANCHORS = (
    "dialog < DIALOGS",
    "dialog < arrsize(s_floatingDialogs)",
    "dialog < arrsize(templateToDialogMap)",
    "dialog < GM_INT_TEMPLATES_DIALOGS",
    "DialogGetFrame(frame, dialog)",
    "!DialogGetFrame(frame, dialog)",
    "!DialogGetFrame(frame, DLG_TEMPLATES_MANAGE)",
    "!DialogGetFrame(frame, DLG_TRADE)",
    "MISSIONS != dialogMission.mission",
    "dialog < GM_INT_TEMPLATES_DIALOGS",
)


def read_section(client: Any, start: int, end: int) -> bytes:
    """Read a whole section, or as much of it as is readable."""

    out = bytearray()
    address = start
    while address < end:
        size = min(0x10000, end - address)
        try:
            out += client.reader.read(address, size)
        except OSError:
            break
        address += size
    return bytes(out)


def call_sites_to(code: bytes, base: int, target: int) -> list[int]:
    """Every ``call rel32`` in ``code`` whose target is ``target``."""

    sites: list[int] = []
    position = code.find(CALL_OPCODE)
    while position >= 0:
        if position + 5 <= len(code):
            displacement = struct.unpack_from("<i", code, position + 1)[0]
            if base + position + 5 + displacement == target:
                sites.append(base + position)
        position = code.find(CALL_OPCODE, position + 1)
    return sites


def first_argument(code: bytes, base: int, site: int, window: int = PUSH_WINDOW) -> list[str]:
    """The immediates pushed just before a call site, as the caller's first argument would be."""

    start = max(0, site - base - window)
    end = site - base
    pushes: list[str] = []
    for index in range(start, end):
        byte = code[index]
        if byte == PUSH_IMM8 and index + 2 <= end:
            pushes.append(f"push8 {code[index + 1]}")
        elif byte == PUSH_IMM32 and index + 5 <= end:
            value = struct.unpack_from("<I", code, index + 1)[0]
            pushes.append(f"push32 0x{value:X}")
    return pushes


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    with py4gw.connect(clients[0], game_thread=False) as client:
        module = win32.get_main_module(client.pid)
        scanner = client._scanner  # type: ignore[attr-defined]
        text = scanner.get_section_range("text")
        report["pid"] = client.pid
        report["module"] = hex(int(module["base_address"]))
        report["text"] = [hex(text.start), hex(text.end)]

        code = read_section(client, text.start, text.end)
        report["text_bytes"] = len(code)

        functions: dict[int, dict[str, Any]] = {}
        anchors: list[dict[str, Any]] = []
        for anchor in ANCHORS:
            site = scanner.find_nth_use_of_string(anchor, 0)
            entry = {
                "anchor": anchor,
                "use_site": hex(site) if site else None,
                "function": None,
                "entry_bytes": None,
            }
            if site:
                function = scanner.to_function_start(site)
                if function:
                    entry["function"] = hex(function)
                    entry["entry_bytes"] = client.reader.read(function, 8).hex(" ")
                    functions.setdefault(
                        function, {"found_by": [], "call_sites": 0, "small_pushes": []}
                    )["found_by"].append(anchor)
            anchors.append(entry)
        report["anchors"] = anchors

        for function, info in functions.items():
            sites = call_sites_to(code, text.start, function)
            info["call_sites"] = len(sites)
            for site in sites[:8]:
                pushes = first_argument(code, text.start, site)
                small = [
                    push
                    for push in pushes
                    if (push.startswith("push8") and int(push.split()[1]) <= MAX_DIALOG_ID)
                ]
                if small:
                    info["small_pushes"].append({"site": hex(site), "pushes": pushes})
        report["functions"] = {
            hex(function): info for function, info in functions.items()
        }

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
