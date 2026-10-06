"""What each kind of access costs, measured — the numbers a runtime decision needs.

The port's access paths differ from Reforged's by orders of magnitude for one structural reason:
Reforged runs *inside* the client, so a read is a pointer dereference and a client function call is
a direct call. This project runs outside it, so a read is ``ReadProcessMemory`` and a client
function call is a **command ring**: the host publishes a record, the client's own thread takes it
when its hooked function next runs, executes it, and the host waits for the answer.

Three families, and the script measures each one on its own:

1. **A host-side read** (``ProcessMemoryReader`` over a real cross-process target). Section 1 spawns
   a child of this interpreter, fills known buffers there, and reads them back through the port's
   own reader — no client, no elevation, and the same API the client is read with.
2. **Host-side work on the bytes** (struct construction, the string table's decode). Measured on
   synthetic records and entries, because it is the same arithmetic whatever the bytes came from.
3. **Anything that has to run inside the client** (the ring): a ping per command, the hook-hit rate
   that bounds how often a command can be taken, the GW.dat chain phase by phase, and the ported
   members that ride on them. Section 3 needs the client and an elevated shell.

Usage::

    python tests/perf_access_cost.py                # sections 1-2 (no client needed)
    python tests/perf_access_cost.py --live         # all three (client running, elevated shell)
"""

from __future__ import annotations

import ctypes
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from py4gw.context.gw_array import GWArray  # noqa: E402
from py4gw.context.agent_array import AgentStruct  # noqa: E402
from py4gw.internals import string_table  # noqa: E402
from py4gw.memory import ProcessMemoryReader  # noqa: E402
from py4gw.win32 import Win32  # noqa: E402
from tests.test_string_table_offline import entry  # noqa: E402

#: Buffer sizes the read half is sampled at: a word, a GUID-sized record, an agent record, a page,
#: a string file, a megabyte, and the largest read the port allows itself in one call.
READ_SIZES = (4, 0x10, 0xC4, 0x1000, 0x10000, 0x100000, 0x400000)

#: One sample count per size, so the small reads are timed enough times to be meaningful and the
#: large ones do not dominate the run.
READ_ITERATIONS = {4: 2000, 0x10: 2000, 0xC4: 1000, 0x1000: 1000, 0x10000: 200, 0x100000: 40, 0x400000: 8}

CHILD_SCRIPT = '''
import ctypes, json, os, sys, time

sizes = [int(value) for value in sys.argv[3].split(",")]
holders = []
info = {"pid": os.getpid(), "buffers": {}}
for size in sizes:
    buffer = ctypes.create_string_buffer(size)
    ctypes.memset(buffer, 0xA5, size)
    holders.append(buffer)
    info["buffers"][str(size)] = ctypes.addressof(buffer)

info_path, stop_path = sys.argv[1], sys.argv[2]
with open(info_path, "w", encoding="utf-8") as handle:
    json.dump(info, handle)

while not os.path.exists(stop_path):
    time.sleep(0.05)

# Keep the holders alive to the last moment: a collected buffer is an unmapped address.
print(len(holders), file=sys.stderr)
'''


def _row(name: str, samples: list[float], unit: str = "ms", extra: str = "") -> None:
    """Print one measured metric: count, min, median, mean."""

    if not samples:
        print(f"{name:<44} (no samples)")
        return
    print(
        f"{name:<44} n={len(samples):5d}  "
        f"min={min(samples):9.4f} {unit}  "
        f"med={statistics.median(samples):9.4f} {unit}  "
        f"mean={statistics.mean(samples):9.4f} {unit}"
        f"{('  ' + extra) if extra else ''}"
    )


def _time(operation: Callable[[], Any], iterations: int) -> list[float]:
    """Return one duration in milliseconds per call."""

    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000.0)
    return samples


def section_read_cost() -> None:
    """1. A cross-process read, by size, through the port's own reader."""

    print("== 1. host-side read (ReadProcessMemory, through py4gw.memory.ProcessMemoryReader) ==")
    workdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "tests/live_reports", "perf_tmp")
    os.makedirs(workdir, exist_ok=True)
    info_path = os.path.join(workdir, "buffers.json")
    stop_path = os.path.join(workdir, "stop")
    script_path = os.path.join(workdir, "child.py")
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(CHILD_SCRIPT)

    child = subprocess.Popen(
        [sys.executable, script_path, info_path, stop_path, ",".join(str(size) for size in READ_SIZES)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    reader = None
    try:
        deadline = time.time() + 20.0
        while time.time() < deadline and not os.path.exists(info_path):
            time.sleep(0.02)
        with open(info_path, encoding="utf-8") as handle:
            info = json.load(handle)

        win32 = Win32()
        reader = ProcessMemoryReader(win32, int(info["pid"]))
        print(f"{'target':<44} pid={info['pid']} (a child of this interpreter, same bitness)")
        for size in READ_SIZES:
            address = int(info["buffers"][str(size)])
            iterations = READ_ITERATIONS[size]
            samples = _time(lambda: reader.read(address, size), max(4, iterations // 10))
            samples = _time(lambda: reader.read(address, size), iterations)
            rate = ""
            if samples and size >= 0x1000:
                rate = f"{size / 1048576 / (statistics.median(samples) / 1000):8.1f} MiB/s"
            _row(f"read {size:#x} bytes", samples, "ms", rate)

        # The host's own half of a command: one 64-byte record written into the target. If this is
        # microseconds, then a command's cost is the client's pickup and work, not this side.
        from py4gw.win32.write_access import WriteAccess

        try:
            with WriteAccess(int(info["pid"])) as access:
                target = int(info["buffers"][str(0x1000)]) + 0x800
                payload = bytes(64)
                _row(
                    "write 64 B (one command record)",
                    _time(lambda: access.write(target, payload), 2000),
                )
        except OSError as error:
            print(f"{'write 64 B (one command record)':<44} unavailable: {error}")
    finally:
        if reader is not None:
            reader.close()
        with open(stop_path, "w", encoding="utf-8") as handle:
            handle.write("stop")
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
        for path in (info_path, stop_path, script_path):
            try:
                os.remove(path)
            except OSError:
                pass


def section_host_work() -> None:
    """2. Host-side work on bytes: struct construction and the string-table decode."""

    print()
    print("== 2. host-side work (struct parse, the string table's decode) ==")

    header_size = ctypes.sizeof(GWArray)
    record_size = ctypes.sizeof(AgentStruct)
    header = bytes(header_size)
    record = bytes(record_size)
    _row(
        f"GWArray.from_buffer_copy ({header_size} B header)",
        _time(lambda: GWArray.from_buffer_copy(header), 2000),
    )
    _row(
        f"AgentStruct.from_buffer_copy ({record_size} B record)",
        _time(lambda: AgentStruct.from_buffer_copy(record), 2000),
    )

    # The decode, on the two shapes a real string file holds: a plain UTF-16 entry, and one stored
    # as a bit-packed char stream (which is what `bpc` names).
    plain = entry("Random Arenas".encode("utf-16-le"), 0, 0x10)
    packed_payload = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    packed = entry(packed_payload, 0x41, 5)
    keyed = entry(plain[6:], 0, 0x10)
    _row("string_table._decode_entry (plain entry)", _time(lambda: string_table._decode_entry(plain, 0), 5000))
    _row("string_table._decode_entry (bit-packed)", _time(lambda: string_table._decode_entry(packed, 0), 5000))
    _row("string_table._postprocess (one name)", _time(lambda: string_table._postprocess("Random Arenas"), 5000))
    codepoints = tuple(int.from_bytes(keyed[index : index + 2], "little") for index in range(0, 4, 2))
    _row("string_table._parse_codepoints (2 units)", _time(lambda: string_table._parse_codepoints(codepoints), 5000))
    _row(
        "one name, cached decode path",
        _time(lambda: string_table.decode(plain), 20000),
        "ms",
        "(cache miss: no table, so the source's own empty answer)",
    )


def section_ring(live: bool) -> None:
    """3. Anything that has to run inside the client: the ring, the hit rate, the dat chain."""

    print()
    print("== 3. inside the client (the command ring; needs a running client and elevation) ==")
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client is running: skipped (start the game and pass --live)")
        return
    if not win32.is_elevated():
        print("this shell is not elevated: connecting asserts elevation, so this section is skipped")
        return
    if not live:
        print("client found; pass --live to connect and measure the ring")
        return

    import py4gw
    from py4gw import dat_reader
    from py4gw.agent import Agent
    from py4gw.context.text_parser_context import TextParser
    from py4gw.game_thread.shared_block import Operation
    from py4gw.player import Player

    started = time.perf_counter()
    client = py4gw.connect(clients[0])
    connect_ms = (time.perf_counter() - started) * 1000.0
    try:
        print(f"{'connect (scan + capability layer)':<44} {connect_ms:9.1f} ms  pid={client.pid}")

        # a. One command end to end: the host publishes, the client's own thread takes it at its
        #    next hook hit, executes it, and the host reads the answer back.
        _row("ring: one command (PING)", _time(lambda: client.bridge.submit(Operation.PING), 20))

        # b. How often the client can take a command at all. One command is taken per hit (the
        #    emitted dispatcher's own bound), so the hit rate is the ceiling on commands per second
        #    and its inverse is the floor on one command's pickup latency.
        before = client.bridge.hits()
        time.sleep(1.0)
        hits = client.bridge.hits() - before
        if hits:
            print(
                f"{'ring: hook hits per second':<44} {hits:5d} hits/s  "
                f"-> one command's pickup floor is {1000.0 / hits:6.1f} ms"
            )
        else:
            print(f"{'ring: hook hits per second':<44}     0 hits/s  (the client did not service the hook)")

        # c. The GW.dat chain phase by phase, on a real string file of the client's language.
        TextParser._update_ptr()
        context = TextParser.get_context()
        file_hash = ""
        if context is not None:
            slot = context.get_file_slot(0, int(context.language_id))
            if slot is not None and int(slot.file_hash_ptr):
                file_hash = slot.file_hash
        if file_hash:
            file_id = dat_reader.file_hash_to_file_id(file_hash)

            def acquire() -> None:
                record = 0
                if file_id and dat_reader._open_ready:
                    record = dat_reader._open_file_by_file_id(
                        client, file_id, dat_reader.READ_STREAM_ID
                    )
                if not record:
                    record = dat_reader._file_hash_to_rec_obj(client, file_hash)
                if record:
                    dat_reader._close_rec_obj(client, record)

            _row("ring: one dat record opened + closed", _time(acquire, 5))
            _row(
                "ring: read_file_by_hash (the whole chain)",
                _time(lambda: dat_reader.read_file_by_hash(file_hash), 3),
            )
            data = dat_reader.read_file_by_hash(file_hash)
            if data:
                print(
                    f"{'   the string file itself':<44} {len(data):9d} bytes "
                    f"(the client decompressed them)"
                )

        # d. A name: the fetch is host-side reads only; the walk is that repeated per agent.
        own_agent = int(Player.GetAgentID())
        ids = [int(agent_id) for agent_id in client.agent_array.get_context().GetAgentArray()]
        named = [
            agent_id
            for agent_id in ids
            if agent_id != own_agent and Agent.GetEncNameByID(agent_id)
        ]
        if named:
            sample = named[0]
            _row(
                f"Agent.GetEncNameByID (one agent of {len(ids)})",
                _time(lambda: Agent.GetEncNameByID(sample), 200),
            )
            _row(
                f"Agent.GetEncNameByID (all {len(ids)} agents)",
                _time(lambda: [Agent.GetEncNameByID(agent_id) for agent_id in ids], 20),
            )

        # e. The table: the first decode reads the one string file its entry names, every later one
        #    is a cache hit. This is the pair the "milliseconds or seconds" question is about.
        if named:
            agent_id = named[0]
            started = time.perf_counter()
            answer = Agent.GetNameByID(agent_id)
            deadline = time.time() + 30.0
            while not answer and time.time() < deadline:
                time.sleep(0.02)
                answer = Agent.GetNameByID(agent_id)
            print(
                f"{'first decode of one slot':<44} {((time.perf_counter() - started) * 1000):9.1f} ms  "
                f"answer={answer!r}"
            )
            _row("cached decode of that name", _time(lambda: Agent.GetNameByID(agent_id), 200))
            print(f"{'   table':<44} {string_table._last_load_status}")

        # f. The array view the categories and the viewer's own rows ride on.
        _row(
            "AgentArray.get_context().GetAgentArray()",
            _time(lambda: client.agent_array.get_context().GetAgentArray(), 20),
        )
    finally:
        py4gw.disconnect()
        print(f"{'disconnected':<44} yes")


def main() -> int:
    live = "--live" in sys.argv
    print(f"perf: access cost (python {sys.version.split()[0]}, {'elevated' if Win32().is_elevated() else 'not elevated'})")
    print()
    section_read_cost()
    section_host_work()
    section_ring(live)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
