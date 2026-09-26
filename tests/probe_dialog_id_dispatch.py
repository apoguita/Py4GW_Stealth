"""Read-only probe: what dispatches on a dialog id in this build?

``DialogLoader_GetText(uint32 dialog_id)`` answers a dialog's text, and the id space is settled:
``MAX_DIALOG_ID`` is ``0x39`` (``dialog.h:89``), which is one less than the dialog table's 58 rows.
The table itself does **not** hold the text — all five functions that touch it are now known
(``tests/probe_dialog_table_readers.py``) and none is a getter — so the mapping lives somewhere
else, and a mapping over 58 fixed ids has one characteristic shape in compiled code: a **jump
table bounded at 57**.

This probe looks for exactly that: a comparison against ``0x39`` immediately followed by an
indirect jump through a table of four-byte entries. A hit is a function that switches on a dialog
id, and the function's own head and its near-by ``mov reg, imm32`` values say whether it answers a
pointer (a text) or does something else.

Read-only: read-only connection, no hook, no call, no write.

Usage: (elevated) python tests/probe_dialog_id_dispatch.py [report-path]
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

#: ``cmp r32, imm8`` (``83 /7``) and ``cmp eax, imm32`` (``3D``), then ``jmp [reg*4+disp32]``
#: (``FF 24 8x``) — the shape a switch over a bounded id compiles to.
CMP_R32_IMM8 = 0x83
CMP_EAX_IMM32 = 0x3D
JMP_TABLE = b"\xff\x24\x85"

#: How far after the comparison the indirect jump may sit.
WINDOW = 24

#: The entry shapes a client function has on this build.
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")


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
        scanner = client._scanner  # type: ignore[attr-defined]
        text = scanner.get_section_range("text")
        code = client.reader.read(text.start, text.end - text.start)
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}
        report["bound"] = dialog.MAX_DIALOG_ID

        hits: dict[int, list[dict[str, Any]]] = {}
        for index in range(len(code) - WINDOW):
            matches = False
            # ``cmp eax, 39`` as ``3D 39 00 00 00``.
            if (
                code[index] == CMP_EAX_IMM32
                and struct.unpack_from("<I", code, index + 1)[0] == dialog.MAX_DIALOG_ID
            ):
                matches = True
            # ``cmp r32, 39`` as ``83 F8 39`` and its siblings.
            elif (
                code[index] == CMP_R32_IMM8
                and code[index + 1] in (0xF8, 0xF9, 0xFA, 0xFB, 0xFE, 0xFF)
                and code[index + 2] == dialog.MAX_DIALOG_ID
            ):
                matches = True
            if not matches:
                continue

            window = code[index : index + WINDOW]
            jump_at = window.find(JMP_TABLE)
            if jump_at < 0:
                continue

            site = text.start + index
            entry = scanner.to_function_start(site)
            if entry is None:
                continue
            head = client.reader.read(entry, 0x60)
            hits.setdefault(entry, []).append(
                {
                    "site": hex(site),
                    "jump": hex(site + jump_at),
                }
            )
            report.setdefault("heads", {})[hex(entry)] = head.hex(" ")

        report["switches"] = [
            {
                "entry": hex(entry),
                "head": report["heads"][hex(entry)],
                "prologue": any(
                    bytes.fromhex(report["heads"][hex(entry)]).startswith(prefix)
                    for prefix in ENTRY_PREFIXES
                ),
                "sites": info,
            }
            for entry, info in sorted(hits.items())
        ]
        report.pop("heads", None)
        report["switch_count"] = len(hits)

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
