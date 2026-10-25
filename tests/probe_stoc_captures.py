"""Read-only probe: what every StoC header's capture would do, before anything is installed.

The inbound half of the packet sniffer installs one emitted stub per header — 487 of them — and each
stub's copy length comes from that header's own field template (`GW::StoC::GetPacketSize`'s walk,
``stoc_methods.cpp:181-235``). That is the part of the port a live run cannot afford to learn by
trial: a template this project mis-describes would be a copy of the wrong length taken on the client's
own thread. So this probe walks **every** header's template with the port's own
:func:`~py4gw.game_thread.packets.describe_template` and reports, per header, what the install would
do — and nothing is installed, replaced or written.

What it answers:

* how many headers the client's array holds, and how many of the source's ``kStoCHeaderCount`` (488)
  are inside it — the last header of native's loop is the one its own `size > header` check drops
  (``stoc_methods.cpp:55``);
* how many entries have **no handler at all**, which native registers anyway and which a previous
  version of this port refused (measured live on 2026-10-24: header 79);
* how many templates end in a nested struct, whose copy length is the one number the host cannot know
  without the packet;
* the widest fixed template, and any header whose template this project cannot describe at all (a
  nested struct inside a nested struct is refused by name).

**Read-only.** The client's memory is read through a ``ProcessMemoryReader`` — no connection, no
block, no hook, no write, and no elevation.

Usage: python tests/probe_stoc_captures.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.game_thread.packets import (
    K_MAX_STOC_PACKET_BUFFER,
    describe_template,
    read_template,
)
from py4gw.game_thread.shared_block import PacketCapture
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: ``stoc.handler_table_addr``, and native's own walk to the array (``stoc_patterns.cpp:43-50``).
RESOLVER = "stoc.handler_table_addr"
GAME_SERVER_CODEC_OFFSET = 0x8
CODEC_HANDLERS_OFFSET = 0x2C

#: ``kStoCHeaderCount`` (``stoc.h:24``): the headers native's loop walks.
K_STOC_HEADER_COUNT = 0x1E8


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if "error" not in report else 1


def read_u32(reader: ProcessMemoryReader, address: int) -> int:
    return int.from_bytes(reader.read(address, 4), "little")


def walk_to_handlers(reader: ProcessMemoryReader, table_address: int) -> tuple[int, int, int]:
    """Follow ``ResolveGameServerHandlers`` and return the array's buffer, capacity and size."""

    game_server = read_u32(reader, table_address)
    if not game_server:
        raise RuntimeError(f"the game server pointer at 0x{table_address:08X} is null")
    codec = read_u32(reader, game_server + GAME_SERVER_CODEC_OFFSET)
    if not codec:
        raise RuntimeError(f"the game server at 0x{game_server:08X} has no codec")
    address = codec + CODEC_HANDLERS_OFFSET
    buffer, capacity, size = (
        int.from_bytes(reader.read(address + offset, 4), "little")
        for offset in (0x0, 0x4, 0x8)
    )
    if not buffer:
        raise RuntimeError(f"the handler array at 0x{address:08X} has no entries buffer")
    return buffer, capacity, size


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    report["connect"] = "not used: this probe reads directly, so no elevation is required"

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        result = patterns.resolve(RESOLVER, scanner)
        report["resolver"] = {
            "name": result.name,
            "ok": bool(result.ok),
            "value": hex(int(result.value)),
        }
        if not result.ok or not result.value:
            report["error"] = f"{RESOLVER} did not resolve: {result.message}"
            return write_report(report)

        buffer, capacity, size = walk_to_handlers(reader, int(result.value))
        report["array"] = {
            "buffer": hex(buffer),
            "capacity": capacity,
            "size": size,
            "source_header_count": K_STOC_HEADER_COUNT,
            "headers_native_would_register": min(size, K_STOC_HEADER_COUNT),
        }

        entry_size = 0xC
        headers: list[dict[str, Any]] = []
        null_handlers: list[int] = []
        nested: list[dict[str, Any]] = []
        unreadable: list[int] = []
        refused: list[dict[str, Any]] = []
        widest = {"header": -1, "fixed_bytes": -1}
        copy_would_clip = 0
        captures: dict[int, PacketCapture] = {}

        for header in range(min(size, K_STOC_HEADER_COUNT)):
            entry = buffer + header * entry_size
            try:
                handler = read_u32(reader, entry + 0x8)
                descriptors, field_count = read_template(reader, entry)
            except Exception as error:  # noqa: BLE001 - reported per header
                unreadable.append(header)
                headers.append(
                    {"header": header, "error": f"{type(error).__name__}: {error}"}
                )
                continue
            if not handler:
                null_handlers.append(header)
            row: dict[str, Any] = {
                "header": header,
                "field_count": field_count,
                "has_handler": bool(handler),
            }
            try:
                capture = describe_template(descriptors, K_MAX_STOC_PACKET_BUFFER)
            except ValueError as error:
                row["refused"] = str(error)
                refused.append(row)
                headers.append(row)
                continue
            captures[header] = capture
            row["fixed_bytes"] = capture.fixed_bytes
            row["nested_stride"] = capture.nested_stride
            row["repeat_offset"] = capture.repeat_offset
            if capture.fixed_bytes > widest["fixed_bytes"]:
                widest = {"header": header, "fixed_bytes": capture.fixed_bytes}
            if capture.fixed_bytes > K_MAX_STOC_PACKET_BUFFER:
                copy_would_clip += 1
            if capture.has_nested_struct:
                nested.append(
                    {
                        "header": header,
                        "fixed_bytes": capture.fixed_bytes,
                        "nested_stride": capture.nested_stride,
                    }
                )
            headers.append(row)

        report["walked"] = len(headers)
        report["null_handlers"] = null_handlers
        report["nested_struct_headers"] = nested
        report["unreadable_entries"] = unreadable
        report["refused_templates"] = refused
        report["widest_fixed"] = widest
        report["headers_whose_copy_would_clip_at_512"] = copy_would_clip
        report["headers"] = headers

        report["note"] = (
            "read-only: nothing was written, no entry was replaced, no code was placed. "
            "``null_handlers`` are the entries that have no handler at all — native registers them "
            "(the entry stays null, so nothing is chained), and so does this port. "
            "``nested_struct_headers`` are the ones whose copy length comes from a repeat count read "
            "out of the packet itself; the stub reads it, the host cannot."
        )
    except Exception as error:  # noqa: BLE001 - reported, then closed
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        reader.close()

    return write_report(report)


if __name__ == "__main__":
    sys.exit(main())
