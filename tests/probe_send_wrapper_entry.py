"""Read-only probe: the entry bytes of the client's outbound send wrapper.

Native hooks one function for its CToS packet capture — the wrapper it resolves as
``packet_sniffer.ctos_send_target`` (``packet_sniffer_patterns.cpp:10-19``) and whose detour it
declares as ``void __cdecl SendPacket(void* ctx, uint32_t size, const void* packet)``
(``packet_sniffer.h:51-52``). Its detour replaces the function's first bytes with a jump, which means
those bytes have to be **whole instructions** — a trampoline replays them at another address, and a
half instruction replayed elsewhere is a crash.

Native never has to think about that: MinHook disassembles the entry and displaces whole instructions
itself. This project has no disassembler by design, so every hook declares its own span — and the send
wrapper's span has never been measured. ``ConnectedClient._entry_span`` knows the two prologue shapes
the client's own functions have (``55 8B EC 83 EC xx``, five bytes; ``55 8B EC 81 EC …``, eight) and
refuses anything else by name rather than guessing. This probe is what turns that refusal into a
decision: it prints what the resolved target actually begins with, so the declared span either matches
a known shape or a new one is written down from evidence.

**Read-only.** A ``ProcessMemoryReader`` reads the client's memory directly — the route
``tests/probe_stoc_handlers.py`` established — so no connection is made, nothing is patched, nothing
is called, and no elevation is required.

Usage: python tests/probe_send_wrapper_entry.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.client import _entry_span
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The resolver the sniffer calls, as the catalog names it.
RESOLVER = "packet_sniffer.ctos_send_target"

#: How much of the entry to print. Enough for the widest prologue shape plus the first whole
#: instructions after it, which is what a longer span would be declared from.
HEAD_BYTES = 32


def write_report(report: dict[str, Any]) -> int:
    """Print the report and write it out when a path was given."""

    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if "error" not in report else 1


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    pid = int(process["pid"])
    report["pid"] = pid
    report["elevated"] = bool(win32.is_elevated())
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
            "trace": [
                {
                    "step": step.name,
                    "op": step.operation,
                    "in": hex(step.input_value),
                    "out": hex(step.output_value),
                    "ok": bool(step.ok),
                    "detail": step.detail,
                }
                for step in result.trace
            ],
        }
        if not result.ok or not result.value:
            report["error"] = f"{RESOLVER} did not resolve: {result.message}"
            return write_report(report)

        target = int(result.value)
        head = reader.read(target, HEAD_BYTES)
        report["target"] = hex(target)
        report["head"] = head.hex(" ")
        span = _entry_span(head)
        report["entry_span"] = None if span is None else span.hex(" ")
        report["displaceable"] = span is not None
        if span is None:
            report["error"] = (
                "the entry is neither ``55 8B EC 83 EC xx`` nor ``55 8B EC 81 EC xx xx xx xx``, so "
                "``ConnectedClient.install_send_capture`` would refuse to place the outbound "
                "capture. The bytes above are what a new span has to be declared from."
            )
    finally:
        reader.close()

    return write_report(report)


if __name__ == "__main__":
    sys.exit(main())
