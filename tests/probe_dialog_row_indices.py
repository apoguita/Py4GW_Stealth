"""Read-only-ish probe: what the dialog rows point at, and what the anchored functions do.

Two questions, one run:

1. **What the three anchor-verified functions look like.** ``0xA6DAA0`` asserts ``dialog < DIALOGS``
   (the same bound the sources' queue makes), ``0x6F2300`` asserts ``dialog < arrsize(s_floatingDialogs)``
   and ``0x79A000`` asserts ``dialog < GM_INT_TEMPLATES_DIALOGS``. Their entry bytes say how many
   arguments they take; a loader takes a dialog id.
2. **Whether a dialog row carries its text as a string-table index.** The row is ``0x24`` bytes and
   the sources name only its first five dwords; the four after that held values like ``0x187CA``
   (100,298) for dialog 0 — a number in the same range as the index of a dialog body this project
   already decoded live (99,942). This reads the string-table file that holds each such value and
   decodes it with the port's own decoder, so "the row points at the text" can be **seen** rather
   than assumed.

The dialog table read and the archive read are reads of the client; the connection itself is the
one write, as every live test here is.

Usage: (elevated) python tests/probe_dialog_row_indices.py [report-path]
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any

import py4gw
from py4gw import dat_reader, dialog
from py4gw.internals import string_table
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The functions the signature probe anchored, and how much of each to read.
FUNCTIONS = (0xA6DAA0, 0x6F2300, 0x79A000)
FUNCTION_BYTES = 0x60

#: Which dialog rows to examine, and which of the row's four unnamed dwords to treat as a
#: possible string-table index (values in the table's range, not pointers).
ROW_IDS = tuple(range(8))
NAMED_WORDS = 5
TABLE_MIN_INDEX = 1024
TABLE_MAX_INDEX = 200_000


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    with py4gw.connect(process) as client:
        module = win32.get_main_module(client.pid)
        report["pid"] = client.pid
        report["module"] = hex(int(module["base_address"]))

        report["function_bodies"] = {
            hex(address): client.reader.read(address, FUNCTION_BYTES).hex(" ")
            for address in FUNCTIONS
        }

        tables = client.dialog_tables
        addresses = tables.get()
        report["flags_base"] = hex(addresses.flags_base)
        if not addresses.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        # Read one string-table file per index we need, and decode it. The port's own DAT read and
        # decoder, so what comes out is what the port renders, not a guess.
        language = 0
        parser = client.read_text_parser()
        if parser is None:
            report["error"] = "no readable TextParser, so there is no string table"
            return write_report(report)
        entries_per_file = int(parser.entries_per_file)
        report["entries_per_file"] = entries_per_file

        def decode_index(index: int) -> str:
            if index // entries_per_file not in loaded:
                _, data, table, count = read_slot(client, parser, index // entries_per_file)
                loaded[index // entries_per_file] = table
            table = loaded.get(index // entries_per_file) or {}
            entry = table.get(index)
            if entry is None:
                return ""
            return string_table._decode_entry(entry, 0) or ""

        loaded: dict[int, dict[int, bytes]] = {}
        rows = []
        for dialog_id in ROW_IDS:
            address = addresses.event_handler_base + dialog_id * dialog.FLAGS_STRIDE
            words = list(
                struct.unpack("<9I", client.reader.read(address, dialog.FLAGS_STRIDE))
            )
            row: dict[str, Any] = {
                "dialog_id": dialog_id,
                "address": hex(address),
                "words": [hex(word) for word in words],
            }
            name_pointer = words[1]
            row["name"] = read_wide(client, name_pointer)
            candidates = {}
            for position in range(NAMED_WORDS, len(words)):
                value = words[position]
                if not TABLE_MIN_INDEX <= value <= TABLE_MAX_INDEX:
                    continue
                candidates[f"word{position}"] = {
                    "value": value,
                    "text": decode_index(value),
                }
            row["index_candidates"] = candidates

            # The same values, asked for as **DAT file ids** rather than string indices: the
            # port's own archive read, which is proven live, and a payload that comes back
            # says what the field names.
            files = {}
            for position in range(NAMED_WORDS, len(words)):
                value = words[position]
                if not 1 <= value <= TABLE_MAX_INDEX:
                    continue
                data = dat_reader.read_file_by_id(value, 1) or b""
                files[f"word{position}"] = {
                    "file_id": value,
                    "bytes": len(data),
                    "head": data[:16].hex(" ") if data else None,
                    "ascii_head": (
                        data[:32].decode("ascii", "replace") if data else None
                    ),
                }
            row["file_candidates"] = files
            rows.append(row)
        report["rows"] = rows

    return write_report(report)


def read_slot(
    client: Any, parser: Any, slot_index: int
) -> tuple[Any, bytes, dict[int, bytes], int]:
    """Read one string-table file and parse it, the way the load does."""

    slot = parser.get_file_slot(slot_index, 0)
    if slot is None or not slot.file_hash_ptr:
        return None, b"", {}, 0
    data = dat_reader.read_file_by_hash(slot.file_hash) or b""
    table: dict[int, bytes] = {}
    count = string_table._parse_string_file(data, int(slot.start_index), table)
    return slot, data, table, count


def read_wide(client: Any, address: int, limit: int = 32) -> str | None:
    """Read a wide string at an address, or ``None`` when it is not one."""

    if not address:
        return None
    units: list[int] = []
    for index in range(limit):
        word = client.dialog_tables.read_uint32(address + index * 2)
        if word is None:
            return None
        unit = int(word) & 0xFFFF
        if unit == 0:
            break
        units.append(unit)
    text = "".join(chr(unit) for unit in units)
    return text if text and all(character.isprintable() for character in text) else None


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
