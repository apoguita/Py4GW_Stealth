"""Read-only probe: find real encoded dialog text in the client, then find what hands it out.

**Superseded for its scan half, and the reason is in the tool that replaced it.** Everything this
probe searches for is in a *file*, not in a running process: ``Gw.exe`` is on disk, its data
sections hold the strings, and `tools/dialog_loader_hunt.py strings` reads them there — with no
client, no capability layer, no elevation, and no UAC prompt, and with the port's own validator and
the client's own addresses. This probe's first run is also the reason that matters: the scan ran in
pure Python against a live process, re-scanning five megabytes of ``.text`` once per string it
found, and it had to be killed by hand. It is kept because it is the live counterpart of the same
question — the decode step below uses the string table out of ``gw.dat`` through the client's own
file API, which the offline tool cannot do — and because a probe that was run is part of the
record.

Every other attempt at this build's ``DialogLoader_GetText`` searched for a *function* and had to
guess what one looks like. This one searches for what the loader **returns**: a pointer to an
encoded string. Those strings are recognisable without any guesswork, because this project already
has the two halves that judge them —

- ``py4gw.ui.encoded_str.is_valid_enc_str`` is the port of the source's own ``EncStrValidate``
  (``ui_methods.cpp:260-362``), which is the check a dialog string passes; and
- ``py4gw.internals.string_table`` decodes an ``(index, key)`` pair out of the game's own archive,
  which is what turns a valid codepoint array into readable text.

So: read the client's data sections, keep every wide-string-shaped run that the source's validator
accepts **and** that decodes, through the game's own table, to readable text; then ask who
references those addresses. A function that hands one of them out is the loader, and a table of
them is the table it indexes.

Read-only in what it asks of the client, with one honest exception: the string table comes out of
``gw.dat`` through the ported chain, and that chain **calls the client's own file API**, so the
connection installs the capability layer (``game_thread=True``, the default) exactly as
``tests/test_live_dat.py`` does, and ``close()`` puts the client's bytes back. Nothing is sent, no
client function outside that chain is called, and nothing is written into the client's memory.

Usage: (elevated) python tests/probe_dialog_text_blobs.py [report-path]
"""

from __future__ import annotations

import json
import re
import struct
import sys
import time
from typing import Any

import py4gw
from py4gw import dat_reader
from py4gw.internals import string_table
from py4gw.ui.encoded_str import is_valid_enc_str
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The language whose files hold the entries, and how much of a section to read at a time.
LANGUAGE = 0
CHUNK = 0x100000

#: The longest run of code units one dialog string may occupy, and how many valid ones to keep.
MAX_WORDS = 96
MAX_FOUND = 64

#: A decoded text is kept when it is at least this long and mostly letters, spaces and the
#: punctuation dialog text uses — the filter that separates a real string from a lucky one.
MIN_TEXT = 3

#: How long the whole scan may take. A probe that can run for ever is a probe that has to be
#: killed by hand, which is what happened the first time this one ran: it re-scanned the code
#: section once per string it found, and the section is five megabytes. It now makes one pass and
#: stops on this budget, reporting what it has.
TIME_BUDGET_S = 90.0


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
        scanner = client._scanner  # type: ignore[attr-defined]
        reader = client.reader

        tables: dict[int, dict[int, bytes]] = {}

        def table_for(index: int) -> dict[int, bytes] | None:
            """The file that holds one table index, read once."""

            holder = index // entries_per_file
            if holder in tables:
                return tables[holder]
            slot = parser.get_file_slot(holder, LANGUAGE)
            if slot is None or not slot.file_hash_ptr:
                return None
            data = dat_reader.read_file_by_hash(slot.file_hash) or b""
            table: dict[int, bytes] = {}
            string_table._parse_string_file(data, int(slot.start_index), table)
            tables[holder] = table
            return table

        found: list[dict[str, Any]] = []
        deadline = time.monotonic() + TIME_BUDGET_S
        scanned = 0
        for name in ("rdata", "data"):
            area = scanner.get_section_range(name)
            address = area.start
            while address < area.end and len(found) < MAX_FOUND:
                if time.monotonic() > deadline:
                    break
                size = min(CHUNK, area.end - address)
                try:
                    chunk = reader.read(address, size)
                except OSError:
                    break
                count = len(chunk) // 2
                words = struct.unpack(f"<{count}H", chunk[: count * 2])
                scanned += count
                offset = 0
                while offset < count - 2:
                    # A cheap pre-filter, on integers alone: an encoded string starts with a code
                    # unit that can begin a digit, and its next two units can continue one. The
                    # run is only sliced once those hold, which is what makes this pass affordable
                    # — slicing ninety-six code units at every offset of two megabytes is not.
                    first = words[offset]
                    if first == 0 or (first & 0x7FFF) < 0x100:
                        offset += 1
                        continue
                    second = words[offset + 1]
                    if second != 0 and (second & 0x7FFF) < 0x100:
                        offset += 1
                        continue
                    run: list[int] = []
                    for word in words[offset : offset + MAX_WORDS]:
                        run.append(word)
                        if word == 0:
                            break
                    offset += 1
                    if not run or run[-1] != 0:
                        continue
                    if not is_valid_enc_str(run):
                        continue
                    index, key = string_table._parse_codepoints(tuple(run))
                    if not index:
                        continue
                    table = table_for(index)
                    if table is None:
                        continue
                    entry = table.get(index)
                    if entry is None:
                        continue
                    try:
                        decoded = string_table._decode_entry(entry, key) or ""
                        text = string_table._postprocess(decoded, table)
                    except (UnicodeDecodeError, ValueError, IndexError):
                        continue
                    letters = sum(1 for c in text if c.isalpha() or c == " ")
                    if len(text) < MIN_TEXT or letters < len(text) - 1:
                        continue
                    found.append(
                        {
                            "address": hex(address + (offset - 1) * 2),
                            "words": len(run) - 1,
                            "index": index,
                            "key": hex(key),
                            "text": text[:80],
                        }
                    )
                    print(
                        f"  {len(found):3}. {address + (offset - 1) * 2:#010x} "
                        f"index {index} -> {text[:60]!r}",
                        flush=True,
                    )
                    if len(found) >= MAX_FOUND:
                        break
                address += size
            if time.monotonic() > deadline:
                break

        report["found"] = found
        report["found_count"] = len(found)
        report["code_units_scanned"] = scanned
        print(f"scan done: {len(found)} strings, {scanned} code units", flush=True)

        # Who references them? One pass over the code section for all of them at once — the first
        # version asked the scanner once per string, which is what made it unkillable.
        users: dict[int, list[str]] = {}
        if found:
            text_area = scanner.get_section_range("text")
            code = reader.read(text_area.start, text_area.end - text_area.start)
            by_address = {int(row["address"], 16): row for row in found}
            alternatives = b"|".join(
                re.escape(value.to_bytes(4, "little")) for value in by_address
            )
            for match in re.finditer(alternatives, code):
                value = struct.unpack_from("<I", code, match.start())[0]
                row = by_address.get(value)
                if row is None:
                    continue
                site = text_area.start + match.start()
                entry = scanner.to_function_start(site)
                if entry is None:
                    continue
                users.setdefault(entry, []).append(
                    f"{hex(site)} -> {row['address']} ({row['text'][:24]!r})"
                )
        report["users"] = [
            {"entry": hex(entry), "sites": sites[:8], "count": len(sites)}
            for entry, sites in sorted(users.items(), key=lambda item: -len(item[1]))
        ]

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
