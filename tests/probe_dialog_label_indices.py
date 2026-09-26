"""Read-only probe: does a button's announced label name a real string-table entry?

A dialog button's label is the one string this port decodes that the source's own guard accepts
and the client's parser then asserts on (``IsParam(data)``, ``TextParser.cpp:724``), which is why
the handover is withheld and the caption is the label taken as its own text. Two readings of that
are possible and they lead opposite ways:

- the label is **not** a real table reference, so no caption can be decoded from it and the
  withheld handover is a permanent divergence (the reading recorded in ``docs/RESEARCH.md``);
- the label **is** a real reference, and the string the client asserted on was read at a moment
  the client had not finished filling it — a timing defect this port can fix.

The (index, key) the live runs' reads parse to is the discriminator, and it can be settled without
the client's decoder: read the file that holds each index through the ported chain, decode the
entry with the parsed key, and look at what comes out. Readable text means the index is a real
reference; non-text means it is not.

The indices come from the three live reads on record, each with the key the port's own
``_parse_codepoints`` derived from it:

- ``0x455B 0xC143 0x0A92 0x4006`` — what the module captured for buttons 4484 and 6020 on
  2026-09-25, after the withheld handover landed (a valid encoded string, index 17499);
- ``0x4481 0xC02F 0x0A92 0x4006 0x4A23`` — the string in the fatal crash report (index 17281);
- ``0x1DD4 0xC030 0x0A92 0x4006 0x0F`` — a read of the same announced pointer a second later
  (index 7380), which is where the earlier "does not carry a table reference" reading came from.

Read-only in what it asks of the client: it installs the capability layer the ported GW.dat chain
needs and calls the client's own file API, which is the same chain ``tests/test_live_dat.py``
uses. Nothing is written into the client and no dialog interaction is driven — the indices are
constants from the runs on record.

Usage: (elevated) python tests/probe_dialog_label_indices.py
"""

from __future__ import annotations

import sys
from typing import Any

import py4gw
from py4gw import dat_reader
from py4gw.internals import string_table
from py4gw.win32 import Win32

#: The language whose files hold the entries, as ``tests/test_live_dat.py`` reads them.
LANGUAGE = 0

#: One read per label on record: the words the port parsed, and what they parsed to. The index
#: and key are repeated here rather than recomputed so this probe reads the runs' own numbers.
LABELS = (
    ("captured, 2026-09-25 (module)", (0x455B, 0xC143, 0x0A92, 0x4006, 0x0000)),
    ("crash report, 2026-09-25", (0x4481, 0xC02F, 0x0A92, 0x4006, 0x4A23, 0x0000)),
    ("read a second later, 2026-09-25", (0x1DD4, 0xC030, 0x0A92, 0x4006, 0x0F, 0x0000)),
)


def is_printable(text: str) -> bool:
    """Whether a decoded text reads as text, which is what a real caption looks like."""

    return bool(text) and all(
        character.isprintable() or character in "\n\t" for character in text
    )


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
        return 2
    if not win32.is_elevated():
        print("the controller must be elevated: the GW.dat chain calls the client")
        return 3

    tables: dict[int, dict[int, bytes]] = {}
    entries_per_file = 0
    with py4gw.connect(clients[0]) as client:
        parser = client.read_text_parser()
        if parser is None:
            print("the connected client has no readable TextParser context")
            return 4
        entries_per_file = int(parser.entries_per_file)
        print(
            f"pid {client.pid}, entries per file {entries_per_file}, "
            f"slot 0 covers 0..{entries_per_file - 1}"
        )

        for name, words in LABELS:
            index, key = string_table._parse_codepoints(words)
            print(f"\n--- {name} ---")
            print(f"  words       = {[hex(word) for word in words]}")
            print(f"  parsed      = index {index}, key 0x{key:X}")
            if not index:
                print("  the words name no index, so there is nothing to decode")
                continue

            holder = index // entries_per_file
            if holder not in tables:
                slot = parser.get_file_slot(holder, LANGUAGE)
                if slot is None or not slot.file_hash_ptr:
                    print(f"  file slot {holder} holds no file")
                    continue
                data = dat_reader.read_file_by_hash(slot.file_hash) or b""
                table: dict[int, bytes] = {}
                count = string_table._parse_string_file(
                    data, int(slot.start_index), table
                )
                tables[holder] = table
                print(
                    f"  file slot {holder} read: {count} entries, {len(data)} bytes"
                )

            table = tables[holder]
            entry = table.get(index)
            if entry is None:
                print(f"  index {index} is not in file slot {holder}")
                continue

            decoded = string_table._decode_entry(entry, key) or ""
            rendered = string_table._postprocess(decoded, table)
            decoded_no_key = string_table._decode_entry(entry, 0) or ""
            rendered_no_key = string_table._postprocess(decoded_no_key, table)
            print(f"  entry       = {len(entry)} bytes, {entry[:32].hex(' ')}")
            print(f"  with key    = {rendered[:120]!r} printable={is_printable(rendered)}")
            print(
                f"  key 0       = {rendered_no_key[:120]!r} "
                f"printable={is_printable(rendered_no_key)}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
