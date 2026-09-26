"""Live, read-only probe: the GW.dat chain's inputs.

What it asks the running client, and nothing else:

1. do the five ``gw_dat_reader`` resolvers find their functions in this build?
2. does the ``TextParser`` context hold file slots, and does each slot's hash convert to a
   file id with the ported ``FileHashToFileId``?

It connects **read-only** (``game_thread=False``): no patch, no hook, no call into the client.
What it does not do is read a file — that is the call chain, and it needs the capability
layer.

Usage: (elevated) python tests/probe_dat_chain.py [report-path]
"""

from __future__ import annotations

import json
import sys

import py4gw
from py4gw import dat_reader

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

NAMES = (
    dat_reader.OPEN_FILE_BY_FILE_ID,
    dat_reader.FILE_HASH_TO_REC_OBJ,
    dat_reader.READ_FILE_BUFFER,
    dat_reader.FREE_FILE_BUFFER,
    dat_reader.CLOSE_REC_OBJ,
)


def main() -> int:
    report: dict[str, object] = {}
    processes = py4gw.win32.list_processes()
    clients = [row for row in processes if "Gw" in str(row.get("name", ""))]

    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["process"] = {
        key: str(value) for key, value in process.items() if key != "handle"
    }

    with py4gw.connect(process, game_thread=False) as client:
        report["pid"] = client.pid
        report["resolvers"] = {name: client.resolves(name) for name in NAMES}

        parser = client.read_text_parser()
        if parser is None:
            report["text_parser"] = None
            return write_report(report)

        report["text_parser"] = {
            "language_id": int(parser.language_id),
            "entries_per_file": int(parser.entries_per_file),
            "cache_ptr": hex(parser.cache_ptr),
        }

        languages = []
        for language in range(len(parser.language_slots)):
            language_slot = parser.language_slots[language]
            slots = []
            for index in range(int(language_slot.slot_count)):
                slot = parser.get_file_slot(index, language)
                if slot is None:
                    slots.append({"index": index, "slot": None})
                    continue
                file_hash = slot.file_hash
                slots.append(
                    {
                        "index": index,
                        "file_hash_ptr": hex(int(slot.file_hash_ptr)),
                        "code_units": [ord(unit) for unit in file_hash],
                        "file_id": string_table_file_id(file_hash),
                        "start_index": int(slot.start_index),
                        "end_index": int(slot.end_index),
                    }
                )
            languages.append(
                {
                    "language": language,
                    "slot_count": int(language_slot.slot_count),
                    "slots": slots,
                }
            )
        report["languages"] = languages

    return write_report(report)


def string_table_file_id(file_hash: str) -> int:
    """The ported ``FileHashToFileId``, so the report shows what the chain would ask for."""

    return dat_reader.file_hash_to_file_id(file_hash)


def write_report(report: dict[str, object]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
