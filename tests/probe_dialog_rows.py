"""Read-only probe: what one row of the client's dialog table actually holds.

The five column bases the port resolves (``flags_base``, ``frame_type_base``, ``event_handler_base``,
``content_id_base``, ``property_id_base``) are four bytes apart with a ``0x24`` stride, which is
the layout of an array of ``0x24``-byte records whose first five dwords are those five fields.
The sources only ever read those five dwords. This probe prints the **whole row** for a few
dialog ids and marks any dword that looks like a pointer, then reads a little wide text at it —
all read-only, and no client function is called.

Usage: (elevated) python tests/probe_dialog_rows.py [report-path]
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

#: ``DialogMemory::FLAGS_STRIDE`` (``dialog.h``): one row's size.
ROW_SIZE = dialog.FLAGS_STRIDE

#: The first id of the row range to print, and how many rows.
FIRST_ID = 0
ROW_COUNT = 8

#: ``EVENT_HANDLER_BASE`` is the first of the five, so a row starts there.
ROW_FIELDS = ("event_handler", "frame_type", "flags", "content_id", "property_id")

#: How many code units to read at a dword that looks like a pointer.
WIDE_LIMIT = 24


def looks_like_pointer(value: int, module_base: int, module_size: int) -> bool:
    """Whether a dword could be an address rather than a small number."""

    if value < 0x10000:
        return False
    if module_base <= value < module_base + module_size:
        return True
    return 0x01000000 <= value < 0x80000000


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    # Read-only: no hook, no block, no call. The tables resolve the same way they do for a
    # reader, which is what this probe is asking about.
    with py4gw.connect(process, game_thread=False) as client:
        module = win32.get_main_module(client.pid)
        module_base = int(module["base_address"])
        module_size = int(module["size"])
        report["module"] = {"base": hex(module_base), "size": hex(module_size)}

        tables = client.dialog_tables
        addrs = tables.get()
        report["bases"] = {
            "event_handler": hex(addrs.event_handler_base),
            "frame_type": hex(addrs.frame_type_base),
            "flags": hex(addrs.flags_base),
            "content_id": hex(addrs.content_id_base),
            "property_id": hex(addrs.property_id_base),
        }
        if not addrs.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        rows = []
        for dialog_id in range(FIRST_ID, FIRST_ID + ROW_COUNT):
            address = addrs.event_handler_base + dialog_id * ROW_SIZE
            raw = client.reader.read(address, ROW_SIZE)
            words = list(struct.unpack(f"<{ROW_SIZE // 4}I", raw))
            row: dict[str, Any] = {
                "dialog_id": dialog_id,
                "address": hex(address),
                "words": [hex(word) for word in words],
                "named": {
                    name: hex(words[index])
                    for index, name in enumerate(ROW_FIELDS)
                    if index < len(words)
                },
            }
            pointers = {}
            for index, word in enumerate(words):
                if not looks_like_pointer(word, module_base, module_size):
                    continue
                units = read_wide(client, word)
                pointers[f"word{index}"] = {
                    "address": hex(word),
                    "in_module": module_base <= word < module_base + module_size,
                    "code_units": [hex(unit) for unit in units[:WIDE_LIMIT]] if units else None,
                    "text": as_text(units),
                }
            row["pointers"] = pointers
            rows.append(row)
        report["rows"] = rows

    return write_report(report)


def read_wide(client: Any, address: int) -> list[int] | None:
    """Read up to ``WIDE_LIMIT`` code units at an address, stopping at a terminator."""

    units: list[int] = []
    for index in range(WIDE_LIMIT):
        try:
            word = client.dialog_tables.read_uint32(address + index * 2)
        except OSError:
            return None
        if word is None:
            return None
        unit = int(word) & 0xFFFF
        units.append(unit)
        if unit == 0:
            break
    return units


def as_text(units: list[int] | None) -> str | None:
    """The code units as text, when they are printable, else ``None``."""

    if not units:
        return None
    text = "".join(chr(unit) for unit in units[:-1]) if units[-1] == 0 else "".join(
        chr(unit) for unit in units
    )
    if text and all(character.isprintable() for character in text):
        return text
    return None


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
