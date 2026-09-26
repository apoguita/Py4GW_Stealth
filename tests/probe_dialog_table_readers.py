"""Read-only probe: every function in the client's code that reads the dialog table.

The dialog table is the one structure this project has already resolved and verified on this
build: 58 rows of ``0x24`` bytes at ``0xb5cf08``, each row a dialog's event handler, name
pointer, flags, content id, property id and four more words (``tests/probe_dialog_rows.py``).
``DialogLoader_GetText`` takes a dialog id and answers that dialog's text, so **whatever it does
internally, it is a function of that id** — and the shortest route to finding it is the complete
list of functions that touch a dialog's record.

An earlier pass looked for the table's *column base addresses* exactly (``0xb5cf08``,
``0xb5cf0c``, ``0xb5cf10``) and found one function. That is too narrow: a reader that adds a row
offset to a base, or reads a later column, embeds an address *inside* the table rather than at its
first word. This probe therefore scans the whole code section for any four-byte value that lands
anywhere in the table, and reports the function each one is in.

Read-only: the connection is the read-only one, no hook is placed, no client function is called
and nothing is written.

Usage: (elevated) python tests/probe_dialog_table_readers.py [report-path]
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

#: How far past the table's own end a value may land and still be a pointer into it. Zero would
#: miss a reader that reaches one past the last row; anything large swallows the *neighbouring*
#: arrays, which is what a first pass with 0x2000 did — 919 "readers", nearly all of them reading
#: something else that happens to live nearby.
SLACK = 0x24

#: The entry shapes a client function has on this build, and how far ahead its first ``ret`` may
#: be for it to count as small.
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")
SMALL_BYTES = 0x80


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    with py4gw.connect(process, game_thread=False) as client:
        tables = client.dialog_tables
        addrs = tables.get()
        if not addrs.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        rows_bytes = (dialog.MAX_DIALOG_ID + 1) * dialog.FLAGS_STRIDE
        low = addrs.event_handler_base - SLACK
        high = addrs.event_handler_base + rows_bytes + SLACK
        report["table"] = {
            "base": hex(addrs.event_handler_base),
            "rows": dialog.MAX_DIALOG_ID + 1,
            "stride": dialog.FLAGS_STRIDE,
            "scanned": [hex(low), hex(high)],
        }

        scanner = client._scanner  # type: ignore[attr-defined]
        text = scanner.get_section_range("text")
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}
        code = client.reader.read(text.start, text.end - text.start)

        hits: dict[int, list[str]] = {}
        for index in range(0, len(code) - 4):
            value = struct.unpack_from("<I", code, index)[0]
            if not low <= value < high:
                continue
            site = text.start + index
            entry = scanner.to_function_start(site)
            if entry is None:
                continue
            field = (value - addrs.event_handler_base) % dialog.FLAGS_STRIDE
            hits.setdefault(entry, []).append(
                f"{hex(site)} -> {hex(value)} (row+0x{field:X})"
            )

        readers = []
        for entry in sorted(hits):
            head = client.reader.read(entry, 0x40)
            ret = next(
                (i for i, byte in enumerate(head) if byte in (0xC3, 0xC2)), None
            )
            readers.append(
                {
                    "entry": hex(entry),
                    "head": head.hex(" "),
                    "prologue": any(head.startswith(p) for p in ENTRY_PREFIXES),
                    "takes_one_argument": head[:6] == b"\x55\x8b\xec\x8b\x45\x08",
                    "first_ret_within_40": ret,
                    "small": ret is not None and ret <= SMALL_BYTES,
                    "sites": hits[entry][:6],
                    "site_count": len(hits[entry]),
                }
            )
        report["readers"] = readers
        report["reader_count"] = len(readers)

    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
