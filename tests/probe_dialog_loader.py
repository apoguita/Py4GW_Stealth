"""Read-only probe: find candidate ``DialogLoader_GetText`` addresses on this build.

The sources reach the loader through a hardcoded address that is stale here (``RESEARCH.md``,
2026-09-25). What this build *does* give is the dialog table, whose first column is a function
pointer per dialog — the dialog's event handler — and those handlers are the client's own dialog
code. A handler that shows a dialog has to get its text from somewhere, so the candidates are
the **targets of the near calls inside those handlers**.

Everything here is a read: the table, the handlers' code, and the entry bytes of each candidate.
No client function is called, nothing is written, and no address is executed — which is the point,
because the last unvalidated address this project called crashed the client.

Usage: (elevated) python tests/probe_dialog_loader.py [report-path]
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

#: How much of each handler to read for call sites, and the longest function prefix checked.
HANDLER_BYTES = 0x800
ENTRY_BYTES = 8
CALL_OPCODE = 0xE8

#: The entry shapes a client function has on this build (see ``DialogTables._is_function_entry``).
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")


def function_entry(reader: Any, address: int) -> bytes | None:
    """The first bytes at an address, or ``None`` when they cannot be read."""

    try:
        return reader.read(address, ENTRY_BYTES)
    except OSError:
        return None


def looks_like_a_function(head: bytes | None) -> bool:
    return bool(head) and any(head.startswith(prefix) for prefix in ENTRY_PREFIXES)  # type: ignore[arg-type]


def call_targets(code: bytes, base: int) -> list[tuple[int, int]]:
    """Every ``call rel32`` in ``code``, as ``(call site, target)`` pairs."""

    found: list[tuple[int, int]] = []
    for index in range(len(code) - 5):
        if code[index] != CALL_OPCODE:
            continue
        displacement = struct.unpack_from("<i", code, index + 1)[0]
        found.append((base + index, base + index + 5 + displacement))
    return found


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
        module = win32.get_main_module(client.pid)
        module_base = int(module["base_address"])
        module_size = int(module["size"])
        text = client._scanner.get_section_range("text")  # type: ignore[attr-defined]
        report["module"] = {"base": hex(module_base), "size": hex(module_size)}
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}

        tables = client.dialog_tables
        addrs = tables.get()
        if not addrs.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        handlers: dict[int, list[int]] = {}
        for dialog_id in range(dialog.MAX_DIALOG_ID + 1):
            handler = tables.read_uint32(addrs.event_handler_base + dialog_id * dialog.FLAGS_STRIDE)
            if not handler or not (text.start <= handler < text.end):
                continue
            handlers.setdefault(int(handler), []).append(dialog_id)
        report["handlers"] = {
            hex(address): ids for address, ids in sorted(handlers.items())
        }

        candidates: dict[int, dict[str, Any]] = {}
        for address in sorted(handlers):
            head = function_entry(client.reader, address)
            code = read_code(client, address)
            report.setdefault("handler_entries", {})[hex(address)] = {
                "head": head.hex(" ") if head else None,
                "looks_like_a_function": looks_like_a_function(head),
                "call_sites": len(call_targets(code, address)),
            }
            for call_site, target in call_targets(code, address):
                if not (text.start <= target < text.end):
                    continue
                entry = candidates.setdefault(
                    target,
                    {"callers": [], "entry": function_entry(client.reader, target)},
                )
                entry["callers"].append(
                    {"handler": hex(address), "call_site": hex(call_site)}
                )

        ranked = []
        for target, info in candidates.items():
            head = info["entry"]
            ranked.append(
                {
                    "target": hex(target),
                    "callers": len(info["callers"]),
                    "entry": head.hex(" ") if head else None,
                    "looks_like_a_function": looks_like_a_function(head),
                    "called_from": info["callers"][:6],
                }
            )
        ranked.sort(key=lambda row: (-row["callers"], row["target"]))
        report["candidates"] = ranked[:40]
        report["candidate_count"] = len(ranked)

    return write_report(report)


def read_code(client: Any, address: int) -> bytes:
    """Read a handler's first bytes through the project's reader."""

    try:
        return client.reader.read(address, HANDLER_BYTES)
    except OSError:
        return b""


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
