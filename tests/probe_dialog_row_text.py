"""Read-only probe: is the dialog row's tail the reference to the dialog's text?

This build's dialog table is 58 rows of ``0x24`` bytes. The five fields the sources name are the
first five words — ``event_handler``, the dialog's *name* pointer, ``flags``, ``content_id``,
``property_id`` — and four words follow them that no source mentions:

```text
id 0  AgentCommander0   tail 0x187ca 0xdc   0x11 0x37
id 1  AgentCommander1   tail 0x187ca 0xdd   0x11 0x38
id 7  Announcement      tail 0x337   0x12a  0x11 0x6a
```

The second and fourth words move together, one per id. The game's text is addressed by an
``(index, key)`` pair — the port reads both out of an encoded string
(``string_table._parse_codepoints``) and the key is a 64-bit value
(``string_table._decode_entry``) — so the tail may be exactly that pair in plain form, which
would make ``DialogLoader_GetText`` a step that turns the row's reference into the encoded
string the client's decoder takes.

This probe answers it the only way that settles anything: it reads the reference out of each row
and decodes it with the game's own string table, then prints the text. Readable dialog text means
the tail is the reference; nonsense for every packing tried means it is something else, and that
is a finding too.

Read-only in what it asks of the client: the dialog table, and the archive read the ported
GW.dat chain already does. That read calls the client's own file API, so the connection installs
the capability layer (``game_thread=True``, the default) and its ``close()`` puts the client's
bytes back — the same connection ``tests/test_live_dat.py`` uses. Nothing is sent and no client
function outside that chain is called.

Usage: (elevated) python tests/probe_dialog_row_text.py [report-path]
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

#: One row's size, from the sources' own constant.
ROW_SIZE = dialog.FLAGS_STRIDE

#: Which ids to look at, and which language's files hold the entries.
DIALOG_IDS = (0, 1, 2, 7, 8, 9, 20, 40)
LANGUAGE = 0


def packings(tail: list[int]) -> dict[str, tuple[int, int]]:
    """The candidate ``(index, key)`` readings of one row's tail, keyed by how they were made."""

    index, first, second, third = tail
    return {
        "index=tail0, key=tail1|tail2<<16|tail3<<32": (
            index,
            first | (second << 16) | (third << 32),
        ),
        "index=tail0, key=tail3|tail2<<16|tail1<<32": (
            index,
            third | (second << 16) | (first << 32),
        ),
        "index=tail0, key=tail1": (index, first),
        "index=tail0, key=tail0|tail1<<16|tail2<<32": (
            index,
            index | (first << 16) | (second << 32),
        ),
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

    with py4gw.connect(process) as client:
        parser = client.read_text_parser()
        if parser is None:
            report["error"] = "the connected client has no readable TextParser context"
            return write_report(report)
        entries_per_file = int(parser.entries_per_file)

        tables = client.dialog_tables
        addrs = tables.get()
        if not addrs.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        loaded: dict[int, dict[int, bytes]] = {}
        rows: list[dict[str, Any]] = []
        for dialog_id in DIALOG_IDS:
            raw = client.reader.read(
                addrs.event_handler_base + dialog_id * ROW_SIZE, ROW_SIZE
            )
            words = list(struct.unpack(f"<{ROW_SIZE // 4}I", raw))
            row: dict[str, Any] = {
                "dialog_id": dialog_id,
                "words": [hex(word) for word in words],
                "readings": {},
            }
            for how, (index, key) in packings(words[5:9]).items():
                reading: dict[str, Any] = {
                    "index": index,
                    "key": hex(key),
                }
                holder = index // entries_per_file
                if holder not in loaded:
                    slot = parser.get_file_slot(holder, LANGUAGE)
                    if slot is None or not slot.file_hash_ptr:
                        reading["text"] = None
                        reading["note"] = f"file slot {holder} holds no file"
                        row["readings"][how] = reading
                        continue
                    data = dat_reader.read_file_by_hash(slot.file_hash) or b""
                    table: dict[int, bytes] = {}
                    string_table._parse_string_file(data, int(slot.start_index), table)
                    loaded[holder] = table
                table = loaded[holder]
                entry = table.get(index)
                if entry is None:
                    reading["text"] = None
                    reading["note"] = f"index {index} is not in its file"
                else:
                    # A wrong key makes the payload arbitrary bytes, and the port's decoder
                    # raises on an odd UTF-16 payload rather than answering — the probe records
                    # that as this packing's answer instead of stopping the run.
                    try:
                        decoded = string_table._decode_entry(entry, key) or ""
                        reading["text"] = string_table._postprocess(decoded, table)[:120]
                    except (UnicodeDecodeError, ValueError, IndexError) as error:
                        reading["text"] = None
                        reading["note"] = f"{type(error).__name__}: {error}"
                    reading["entry_bytes"] = len(entry)
                row["readings"][how] = reading
            rows.append(row)

        report["rows"] = rows

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
