"""Read-only probe: what the client's own data section says about dialogs.

The offsets catalog's patterns are anchored on the client's **own** assertion strings — a file
name and a message, e.g. ``GrImage.cpp`` / ``bits || !palette`` (``gw_dat_reader.json``). This
probe applies the same idea to the dialog code: it reads ``.rdata`` once for every string that
mentions a dialog, reads ``.text`` once for every ``push imm32`` that points into ``.rdata``, and
reports which code references those strings. Both halves are reads, and no address is executed.

The point is to find this build's dialog code — and with it a candidate for
``DialogLoader_GetText``, whose hardcoded address is stale here (``RESEARCH.md``, 2026-09-25).

Usage: (elevated) python tests/probe_dialog_strings.py [report-path]
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How much of a section to read at a time.
CHUNK = 0x10000

#: What a dialog string looks like, and how many to report.
NEEDLE = b"ialog"
MAX_HITS = 80

#: How many references to keep per string.
MAX_REFERENCES = 4

PUSH_OPCODE = b"\x68"


def read_section(client: Any, start: int, end: int) -> bytes:
    """Read a whole section, or as much of it as is readable."""

    out = bytearray()
    address = start
    while address < end:
        size = min(CHUNK, end - address)
        try:
            out += client.reader.read(address, size)
        except OSError:
            break
        address += size
    return bytes(out)


def c_string_at(data: bytes, base: int, address: int, width: int = 48) -> str | None:
    """The NUL-terminated ASCII string around ``address``, if there is one."""

    offset = address - base
    if not 0 <= offset < len(data):
        return None
    start = offset
    while start > 0 and data[start - 1] != 0 and offset - start < width:
        start -= 1
    end = offset
    while end < len(data) and data[end] != 0 and end - offset < width * 2:
        end += 1
    text = data[start:end]
    if not text or any(byte < 0x20 or byte > 0x7E for byte in text):
        return None
    return text.decode("ascii", "replace")


def push_sites(code: bytes, base: int, low: int, high: int) -> dict[int, list[int]]:
    """Every ``push imm32`` whose value lands in ``[low, high)``, keyed by that value."""

    found: dict[int, list[int]] = {}
    position = code.find(PUSH_OPCODE)
    while position >= 0:
        if position + 5 <= len(code):
            value = struct.unpack_from("<I", code, position + 1)[0]
            if low <= value < high:
                sites = found.setdefault(value, [])
                if len(sites) < MAX_REFERENCES:
                    sites.append(base + position)
        position = code.find(PUSH_OPCODE, position + 1)
    return found


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    with py4gw.connect(clients[0], game_thread=False) as client:
        win32_module = win32.get_main_module(client.pid)
        scanner = client._scanner  # type: ignore[attr-defined]
        text = scanner.get_section_range("text")
        data = scanner.get_section_range("rdata")
        report["pid"] = client.pid
        report["module"] = hex(int(win32_module["base_address"]))
        report["sections"] = {
            "text": [hex(text.start), hex(text.end)],
            "rdata": [hex(data.start), hex(data.end)],
        }

        rdata = read_section(client, data.start, data.end)
        report["rdata_bytes"] = len(rdata)

        hits: list[dict[str, Any]] = []
        position = rdata.find(NEEDLE)
        while position >= 0 and len(hits) < MAX_HITS:
            address = data.start + position
            text_value = c_string_at(rdata, data.start, address)
            if text_value:
                hits.append({"address": hex(address), "text": text_value})
            position = rdata.find(NEEDLE, position + 1)

        code = read_section(client, text.start, text.end)
        report["text_bytes"] = len(code)
        sites = push_sites(code, text.start, data.start, data.end)

        for hit in hits:
            address = int(hit["address"], 16)
            hit["references"] = [hex(site) for site in sites.get(address, [])]

        report["hits"] = hits
        report["strings_referenced"] = sum(1 for hit in hits if hit["references"])

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
