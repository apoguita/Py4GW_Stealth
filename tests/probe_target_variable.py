"""Probe: which client variable follows the target as the target changes.

The previous version of this probe asked "which dwords equal this agent id" and got
4522 hits for id 1, because small ids are everywhere in client data. It also used a
stale agent list, so two "targets" were not findable and the client substituted the
controlled character instead — and the probe reported that substitution as data.

Both mistakes are fixed here:

* **every candidate is verified before it is used.** The client is asked to target
  it, and the id it reports back must be the id that was asked for. Anything else is
  the client doing something other than what we said, which is a failed candidate,
  not a measurement. Every candidate is also checked against a live agent snapshot
  so its kind and allegiance are known.
* **the match is differential.** Each round clears the target, snapshots ``.data``,
  sets the candidate, and snapshots again. An address qualifies only if its dword
  went **0 -> that id** in step with the client's own notice. The addresses that did
  that for *every* candidate are the global current target; ones that did it for
  only some are allegiance- or type-related state. That is the question this probe
  exists to answer.

Not a test. Run it from an **elevated** shell, in a map::

    python tests/probe_target_variable.py
"""

from __future__ import annotations

import struct
import sys
import time

import py4gw
from py4gw.game_thread.bridge import Bridge
from py4gw.game_thread.shared_block import (
    CallForm,
    CommandState,
    Descriptor,
    EventKind,
)
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

HOOK_RESOLVER = "game_thread.leave_game_thread_func"
CALL_RESOLVER = "agent.change_target_func"
OBSERVE_RESOLVER = "ui.send_ui_message_func"

DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
UI_DISPLACED = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")
CHANGE_TARGET_MESSAGE = 0x10000020
#: ``ChangeTargetUIMsg`` names no string (``context/ui.h:78-84``): nothing for the observer to copy.
CHANGE_TARGET_STRING_OFFSET = 0
SLOT_CHANGE_TARGET = 0

CHUNK = 0x10000
WORD = 4
SETTLE_SECONDS = 0.15
MAX_CANDIDATES = 6
MAX_PRINTED = 8


def resolve(win32: Win32, pid: int, name: str) -> int:
    module = win32.get_main_module(pid)
    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        result = PatternCatalog.from_directory("offsets").resolve(name, scanner)
    if not result.ok:
        raise SystemExit(f"{name} did not resolve: {result.message}")
    return int(result.value)


def reported_id(bridge: Bridge, timeout: float = 2.0) -> int | None:
    """Return the id from the next target-change notice, or None."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in bridge.events():
            if (
                event.kind == EventKind.UI_MESSAGE
                and event.sequence == CHANGE_TARGET_MESSAGE
            ):
                return int(event.arg0)
        time.sleep(0.01)
    return None


def set_target(bridge: Bridge, agent_id: int) -> int | None:
    """Ask for one target and return what the client reported, if anything."""

    record = bridge.call(SLOT_CHANGE_TARGET, agent_id, 0)
    if record.state is not CommandState.DONE:
        return None
    return reported_id(bridge)


def snapshot(reader: ProcessMemoryReader, start: int, end: int) -> bytes:
    """Read a whole section, in chunks, aligned to whole words."""

    parts: list[bytes] = []
    address = start
    while address < end:
        chunk = min(CHUNK, end - address)
        chunk -= chunk % WORD
        parts.append(reader.read(address, chunk))
        address += chunk
    return b"".join(parts)


def followed(
    before: bytes, after: bytes, was: int, now: int, start: int
) -> set[int]:
    """Return addresses whose dword went ``was`` -> ``now`` between two snapshots."""

    was_bytes = struct.pack("<I", was)
    now_bytes = struct.pack("<I", now)
    hits: set[int] = set()
    for offset in range(0, len(before) - WORD + 1, WORD):
        if before[offset : offset + WORD] == was_bytes and (
            after[offset : offset + WORD] == now_bytes
        ):
            hits.add(start + offset)
    return hits


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("Start Guild Wars first.")
        return 1
    if not win32.is_elevated():
        print("Run this from an elevated shell.")
        return 1

    pid = int(clients[0]["pid"])
    module = win32.get_main_module(pid)
    base, size = int(module["base_address"]), int(module["size"])
    hook_target = resolve(win32, pid, HOOK_RESOLVER)
    change_target = resolve(win32, pid, CALL_RESOLVER)
    observe_target = resolve(win32, pid, OBSERVE_RESOLVER)

    client = py4gw.connect(clients[0])
    try:
        player_id = int(Player.GetAgentID())
        snapshot_agents = client.read_agent_array()
        pool: list[tuple[int, str]] = [(player_id, f"self (agent {player_id})")]
        if snapshot_agents is not None:
            # One representative per kind and allegiance, so the candidates span
            # agent types instead of being the first six of whatever the array
            # happens to list first.
            seen: set[tuple[object, object]] = set()
            for reference in snapshot_agents.all:
                if reference.agent_id in (0, player_id):
                    continue
                key = (reference.kind, reference.allegiance)
                if key in seen:
                    continue
                seen.add(key)
                pool.append(
                    (
                        int(reference.agent_id),
                        f"{reference.kind.name}/allegiance {reference.allegiance}",
                    )
                )
    finally:
        py4gw.disconnect()
    if not player_id:
        print("Log a character into a map first.")
        return 1

    print(f"client             = pid {pid}, module 0x{base:08X} + 0x{size:X}")
    print(f"candidate pool     = {len(pool)} entries, player agent {player_id}")

    access = WriteAccess(pid)
    bridge = Bridge(access, pid, timeout_ms=5000)
    restored = b""
    try:
        bridge.install(
            hook_target,
            DISPLACED,
            calls={
                SLOT_CHANGE_TARGET: Descriptor(
                    target=change_target, form=CallForm.U32_U32
                )
            },
            module_base=base,
            module_size=size,
            watch=[(CHANGE_TARGET_MESSAGE, CHANGE_TARGET_STRING_OFFSET)],
            observing=(observe_target, UI_DISPLACED),
        )
        bridge.wait_for_hits(2, 5000)

        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(reader, base, size)
            sections = scanner.initialize()
            data = sections[".data"]
            print(f".data              = 0x{data.start:08X} .. 0x{data.end:08X}")
            print()
            print(f"{'target':<34} {'asked':>6} {'reported':>8}  tracked addresses")
            print("-" * 78)

            survivors: set[int] | None = None
            tested = 0
            for agent_id, label in pool:
                if tested >= MAX_CANDIDATES:
                    break
                # Clear first, so the change is a change the client will report.
                set_target(bridge, 0)
                before = snapshot(reader, data.start, data.end)
                reported = set_target(bridge, agent_id)
                if reported is None or reported != agent_id:
                    print(
                        f"{label:<34} {agent_id:>6} {str(reported):>8}  "
                        f"rejected (not findable as asked)"
                    )
                    continue
                after = snapshot(reader, data.start, data.end)
                hits = followed(before, after, 0, reported, data.start)
                survivors = hits if survivors is None else (survivors & hits)
                tested += 1
                shown = " ".join(f"{a:#010x}" for a in sorted(hits)[:MAX_PRINTED])
                more = "" if len(hits) <= MAX_PRINTED else f" (+{len(hits) - MAX_PRINTED})"
                print(
                    f"{label:<34} {agent_id:>6} {reported:>8}  "
                    f"{len(hits):>3} hits  {shown}{more}"
                )

            print("-" * 78)
            if not tested:
                print("no candidate could be targeted as asked; nothing to conclude.")
            elif survivors:
                print(f"followed EVERY candidate ({tested} of them):")
                for address in sorted(survivors)[:MAX_PRINTED]:
                    value = struct.unpack(
                        "<I", reader.read(address, WORD)
                    )[0]
                    print(f"   {address:#010x}  now {value}")
            else:
                print(
                    f"no address followed all {tested} candidates: the target is not "
                    "kept in one global, or it was never one of the addresses that "
                    "merely held the right value."
                )
    finally:
        if bridge.installed:
            bridge.remove()
        restored = read_entry(win32, pid, hook_target)
        access.close()

    print(f"\nhook restored      = {restored == DISPLACED} ({restored.hex(' ')})")
    print("finished           = hooks removed, nothing left running")
    return 0


def read_entry(win32: Win32, pid: int, address: int) -> bytes:
    with ProcessMemoryReader(win32, pid) as reader:
        return reader.read(address, len(DISPLACED))


if __name__ == "__main__":
    sys.exit(main())
