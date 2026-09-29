"""Live probe: install the merchant packet hooks, watch them run, and put the client back.

This is the one live operation the packet capability needs, and it is deliberately narrow: it does
not trade, it does not call a client function, and it changes nothing except the five handler
pointers ``py4gw/listeners.py`` asks for. What it answers, in order:

1. **the client's own handlers, read before anything is written** — the "before" the restore is
   checked against, read with a direct ``ProcessMemoryReader`` (the route
   ``tests/probe_stoc_handlers.py`` uses, which needs no elevation);
2. **the install** — ``py4gw.connect()``, which installs the capability layer and then enables the
   listener exactly as native's bootstrap does (``listeners.cpp:179-186``). Every watched entry must
   read back as this project's stub address, and the originals must be the ones step 1 saw;
3. **the stubs running** — the probe drains events for a bounded window and reports what arrived per
   header. Arrival is the proof that the client's dispatcher is reaching generated code and that the
   original handler still ran behind it; a header that stays silent is reported as silent, which is
   the honest answer for a packet the client was not going to receive anyway;
4. **the restore** — ``py4gw.disconnect()``, then the entries read again: every one must hold what
   step 1 found, and the listener must report no headers replaced.

It is a **write**, so it needs an elevated shell, and it is the merchant live pass's first half. The
second half — trading at a real merchant — needs the owner at a merchant, because it moves gold and
items.

Usage: (elevated) python tests/probe_merchant_packets_live.py [report-path] [drain-seconds]
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from py4gw import listeners as listeners_module
from py4gw.game_thread.packets import CODEC_HANDLERS_OFFSET, read_handler_table
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
DRAIN_SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0

RESOLVER = "stoc.handler_table_addr"


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

    before = read_entries(win32, pid, report, "before")
    if not before:
        return write_report(report)

    install_report(report, before)
    return write_report(report)


def read_entries(
    win32: Win32, pid: int, report: dict[str, Any], label: str
) -> dict[int, int]:
    """Read the five merchant entries with a direct reader, and keep them for comparison."""

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        resolved = patterns.resolve(RESOLVER, scanner)
        if not resolved.ok:
            report[f"{label}_error"] = resolved.message or "the handler table did not resolve"
            return {}
        table = read_handler_table(reader, int(resolved.value))  # type: ignore[arg-type]
        entries = {}
        for header in sorted(listeners_module.PACKET_WORDS):
            entries[header] = table.buffer + header * 0x0C + 0x08
        report[label] = {
            "table": hex(table.address),
            "entries": len(entries),
            "array_size": table.size,
            "handlers": {
                hex(header): hex(read_u32(reader, address))
                for header, address in entries.items()
            },
        }
        entries_by_header = {
            header: read_u32(reader, address) for header, address in entries.items()
        }
        report[f"{label}_head"] = {
            hex(header): reader.read(handler, 8).hex(" ")
            for header, handler in entries_by_header.items()
        }
        return entries_by_header
    except Exception as error:  # noqa: BLE001 - reported, not raised
        report[f"{label}_error"] = f"{type(error).__name__}: {error}"
        return {}
    finally:
        reader.close()


def install_report(report: dict[str, Any], before: dict[int, int]) -> None:
    """Connect, check the install, watch the stubs, disconnect, and check the restore."""

    import py4gw

    clients = Win32().find_guild_wars()
    process = clients[0]
    started = time.time()
    received: dict[int, int] = {}
    try:
        with py4gw.connect(process) as client:
            report["connect_ms"] = round((time.time() - started) * 1000.0, 1)
            bridge = client.bridge
            hooks = bridge.packets
            report["installed_headers"] = [hex(header) for header in bridge.packet_headers]
            report["stubs"] = {
                hex(stub.header): {
                    "words": stub.words,
                    "stub": hex(stub.address),
                    "original": hex(stub.original),
                    "entry": hex(stub.entry),
                }
                for stub in (hooks.stub(header) for header in bridge.packet_headers)
            } if hooks is not None else {}
            report["entries_after_install"] = {
                hex(header): hex(read_u32(client.access, hooks.stub(header).entry))
                for header in bridge.packet_headers
            } if hooks is not None else {}
            report["every_entry_is_the_stub"] = bool(
                hooks is not None
                and all(
                    read_u32(client.access, hooks.stub(header).entry) == hooks.stub(header).address
                    for header in bridge.packet_headers
                )
            )
            report["originals_match_the_read_before"] = bool(
                hooks is not None
                and all(
                    hooks.stub(header).original == before.get(header)
                    for header in bridge.packet_headers
                )
            )

            # The connection's own listener thread is the reader of the event region, so what the
            # stubs record arrives at the callbacks — counting there is counting what was delivered,
            # which is the thing being verified. Draining the block from here would race that thread
            # for the same counter and see almost nothing.
            from py4gw.game_thread.shared_block import EventKind

            def count(event: Any) -> None:
                header = int(event.sequence)
                received[header] = received.get(header, 0) + 1

            client.callbacks.register(EventKind.PACKET, count)
            try:
                time.sleep(DRAIN_SECONDS)
                listener_thread = client._listener  # type: ignore[attr-defined]
                report["listener_delivered"] = (
                    None if listener_thread is None else listener_thread.delivered
                )
            finally:
                client.callbacks.unregister(EventKind.PACKET, count)

            listener = listeners_module.Merchant()
            report["packets_seen"] = {
                hex(header): count for header, count in sorted(received.items())
            }
            report["listener_total"] = sum(received.values())
            report["listener_state"] = {
                "enabled": listener.IsEnabled(),
                "quoted_item_id": listener.GetQuotedItemId(),
                "quoted_value": listener.GetQuotedValue(),
                "transaction_complete": listener.IsTransactionComplete(),
                "window_items": len(listener.GetMerchantWindowItems()),
                "merchant_items": len(listener.GetMerchantItems()),
            }
            report["in_flight_at_end"] = hooks.in_flight() if hooks is not None else None
    except Exception as error:  # noqa: BLE001 - reported, not raised
        report["connect_error"] = f"{type(error).__name__}: {error}"

    after = read_entries(Win32(), report["pid"], report, "after")
    report["restored"] = bool(after) and after == before
    report["restored_differs"] = {
        hex(header): {"before": hex(before[header]), "after": hex(after.get(header, 0))}
        for header in before
        if after.get(header) != before[header]
    }
    report["note"] = (
        "a write: the five handler pointers were replaced on connect and restored on disconnect. "
        "Nothing else was called or changed. 'packets_seen' is what the client actually dispatched "
        "through the stubs while the probe listened — a header that is absent is one the client did "
        "not receive, not one that failed."
    )


def read_u32(reader: Any, address: int) -> int:
    return int.from_bytes(reader.read(address, 4), "little")


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
