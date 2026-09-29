"""Put the client's own StoC handlers back after a controller died while connected.

**Why this exists.** A controller that is killed while the packet hooks are installed never runs its
restore: the client's handler entries keep pointing at the emitted stubs, and the process that placed
them — and the block those stubs write into — is gone. The port refuses to *chain* to a handler that is
not the client's own code (``game_thread/packets.py``), which is what stops a later attach from jumping
into it, but a refusal cannot repair the entries: the originals lived in the dead controller's memory,
exactly as native's ``g_original_functions`` lives in its own. **And because the connection installs the
merchant listener on connect, a client in that state cannot be connected to at all** — the refusal
happens inside ``connect``. This tool is the way back.

**What it does is the port's own entry-patch recovery.** ``ConnectedClient._prepare_target`` knows the
original bytes of the three functions it patches because they are pinned per client build, and it puts
them back when it finds a jump left by a controller that died. These five handlers have the same kind of
pinned values — read from the running client, read-only, on this build — and this tool writes them back,
but only where an entry is **not** the client's own code:

* an entry that already points inside the client module is the client's own handler (or this project's
  restoration of it) and is left exactly as it is;
* an entry that points outside it is a stub somebody placed and did not take out, and is restored to the
  value below;
* an entry holding anything else is reported and **not** written: this tool restores what it can prove.

**It writes directly, with no connection and no hook.** Nothing is dispatched, nothing is called, and
each write is one aligned four-byte store — atomic on this target. That is deliberate: the connection is
exactly what cannot be used on a client in this state.

The values are per client build (``0xf3f1a0``, ``0xf3f1c0``, ``0xf3f1e0``, ``0xf3fd00``, ``0xf402f0``).
They were read from this client's own array by ``tests/probe_stoc_handlers.py`` and corroborated by two
further runs (``live_reports/stoc_handlers.json``, ``live_reports/merchant_packets.json``) before
anything was ever written to the array. On a different client build they are wrong — run the read-only
probe first on any client this has not seen.

It is a **write**, so it needs an elevated shell.

Usage: (elevated) python tools/restore_stoc_handlers.py [report-path]
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any

from py4gw.game_thread.packets import read_handler_table
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else "live_reports/restore_stoc_handlers.json"

RESOLVER = "stoc.handler_table_addr"

#: Where ``handler_func`` sits inside one ``StoCHandler`` (``stoc_patterns.cpp:9-13``).
ENTRY_HANDLER_OFFSET = 0x08
ENTRY_SIZE = 0x0C

#: The client's own handler for each merchant header on this build, as the read-only probe found them.
ORIGINALS: dict[int, int] = {
    0x0084: 0xF3F1A0,  # GAME_SMSG_WINDOW_ADD_ITEMS
    0x0085: 0xF3F1C0,  # GAME_SMSG_WINDOW_ITEMS_END
    0x0086: 0xF3F1E0,  # GAME_SMSG_WINDOW_ITEM_STREAM_END
    0x00CC: 0xF3FD00,  # GAME_SMSG_TRANSACTION_DONE
    0x00F7: 0xF402F0,  # GAME_SMSG_ITEM_PRICE_QUOTE
}


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    report["elevated"] = bool(win32.is_elevated())
    if not report["elevated"]:
        report["error"] = "this is a write; it needs an elevated shell"
        return write_report(report)

    module = win32.get_main_module(pid)
    module_base = int(module["base_address"])
    module_end = module_base + int(module["size"])
    report["module"] = {"base": hex(module_base), "end": hex(module_end)}

    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, module_base, int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        resolved = patterns.resolve(RESOLVER, scanner)
        if not resolved.ok:
            report["error"] = resolved.message or "the handler table did not resolve"
            return write_report(report)
        table = read_handler_table(reader, int(resolved.value))  # type: ignore[arg-type]
        report["table"] = hex(table.address)

        entries = {
            header: table.buffer + header * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
            for header in ORIGINALS
        }

        rows: list[dict[str, Any]] = []
        for header, entry in sorted(entries.items()):
            before = read_u32(reader, entry)
            row: dict[str, Any] = {
                "header": hex(header),
                "entry": hex(entry),
                "before": hex(before),
                "recorded": hex(ORIGINALS[header]),
                "action": _action(before, ORIGINALS[header], module_base, module_end),
            }
            if row["action"] == "restore":
                # **Where the original actually is.** The recorded values above are this file's own
                # record of one client *instance*, and a restart relocates the module: on 2026-09-30
                # the same build came back with its image at ``0xA20000`` instead of ``0x400000``, so
                # every recorded address was 0x620000 out. The one copy that always belongs to the
                # instance being repaired is inside **this project's own stub**: it was emitted with
                # the original baked in as the immediate of the ``mov eax`` it chains through
                # (``payload.build_packet_stub``), so the stub still says what it replaced.
                recovered = _original_from_stub(reader, before, module_base, module_end)
                row["recovered_from_stub"] = None if recovered is None else hex(recovered)
                if recovered is not None:
                    row["target"] = hex(recovered)
                    row["source"] = "the orphaned stub's own chained-original immediate"
                else:
                    row["target"] = row["recorded"]
                    row["source"] = "this file's recorded value (the stub could not be read)"
            rows.append(row)
        report["entries_before"] = rows

        # **Nothing is written from the record alone.** Either the stub gave back the original — which
        # is this instance's own value, and is checked against the module — or at least one of the five
        # entries must still hold the recorded value, which is what proves a client of this build
        # answers to this file. Without either proof nothing is written: another build's function
        # addresses in this build's array would be worse than the state being repaired.
        matches = [row for row in rows if int(row["before"], 16) == int(row["recorded"], 16)]
        recoverable = [row for row in rows if row.get("recovered_from_stub")]
        report["entries_matching_the_record"] = len(matches)
        report["entries_recoverable_from_stub"] = len(recoverable)
        if not matches and not recoverable:
            report["error"] = (
                "no entry holds the value recorded for it and no orphaned stub could be read, so "
                "there is nothing here this tool can prove. Run tests/probe_stoc_handlers.py "
                "(read-only) on this client and record what it finds; nothing was written. Restarting "
                "the client is the other way."
            )
            return write_report(report)

        access = WriteAccess(pid)
        try:
            for row in rows:
                if row["action"] != "restore":
                    continue
                access.write(int(row["entry"], 16), struct.pack("<I", int(row["target"], 16)))
        finally:
            access.close()

        for row in rows:
            if row["action"] != "restore":
                continue
            after = read_u32(reader, int(row["entry"], 16))
            row["after"] = hex(after)
            row["action"] = (
                "restored" if after == ORIGINALS[int(row["header"], 16)] else "WRITE DID NOT LAND"
            )
        report["entries_after"] = rows
        report["restored"] = sum(1 for row in rows if row["action"] == "restored")
        report["note"] = (
            "a write, and only where an entry was not the client's own code. Nothing was called, no "
            "hook was placed and no connection was made: this puts back what a killed controller left "
            "behind."
        )
    finally:
        reader.close()

    return write_report(report)


def _action(before: int, original: int, module_base: int, module_end: int) -> str:
    """What this tool will do with one entry, and why."""

    if before == original:
        return "already the recorded original"
    if module_base <= before < module_end:
        return "left alone: this is the client's own code"
    if before > module_end:
        return "restore"
    return "refused: this is not a stub outside the module, and not the recorded original"


#: The stub's opening: ``pushad`` then ``inc dword [imm32]`` — the in-flight count taken on entry,
#: which is what ``payload.build_packet_stub`` emits first and what tells this project's own code from
#: anything else that could be sitting in the entry.
_STUB_OPENING = bytes((0x60, 0xFF, 0x05))

#: ``mov eax, imm32`` followed by ``call eax`` — the chain to the original, and the only place the
#: address this entry held before it was replaced is still written down.
_CHAIN = (0xB8, 0xFF, 0xD0)

#: How much of the stub to read. One is ~220 bytes with eighteen packet words; this is that and more,
#: and it is bounded so a wild pointer cannot make this read far.
_STUB_READ = 512


def _original_from_stub(
    reader: Any, stub: int, module_base: int, module_end: int
) -> int | None:
    """Return the handler an orphaned stub chains to, or ``None`` if this is not one of ours.

    The stub is emitted with the handler it replaced baked in as the immediate of the ``mov eax`` it
    calls through, so an entry pointing at one of our own stubs from a controller that died still
    records what it took. The answer is only accepted when it lands **inside the client module** and
    the bytes there look like the entry of a function — which is the check that keeps a misread from
    being written back as a handler.
    """

    if module_base <= stub < module_end:
        return None

    try:
        code = reader.read(stub, _STUB_READ)
    except OSError:
        return None

    if not code.startswith(_STUB_OPENING):
        return None

    for index in range(len(code) - 6):
        if code[index] != _CHAIN[0] or code[index + 5 : index + 7] != bytes(_CHAIN[1:]):
            continue
        candidate = int.from_bytes(code[index + 1 : index + 5], "little")
        if not module_base <= candidate < module_end:
            continue
        try:
            head = reader.read(candidate, 3)
        except OSError:
            continue
        # A function's entry on this build is a frame prologue; anything else is a misread.
        if head[:2] != b"\x55\x8b":
            continue
        return candidate
    return None


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
