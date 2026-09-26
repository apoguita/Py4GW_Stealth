"""Probe: target one enemy, call it, and attack it. Five steps, then it stops.

Not a suite. This does exactly what it says and nothing else:

1. scan for living enemies within **1000 units**;
2. pick the nearest one;
3. **target** it;
4. **call** it;
5. **interact** with it — which for an enemy is attacking it.

Then it prints what happened and exits.

**What it deliberately does not do**, because the operator is watching the client
and has to be able to tell the library's behaviour apart from this file's:

- it does not move the character anywhere — no stepped move, no walk back;
- it does not clear the target afterwards;
- it does not abort on health, retry a step, or restore a position;
- it does not stop the fight it starts.

Every action below is one of the three members. The only other writes are the
library's own: connecting installs its hooks and `disconnect()` takes them out,
which is reported at the end. Reads — the agent array, the client's own messages —
change nothing.

Run it from an **elevated** shell, in an explorable map, with Guild Wars running::

    python tests/probe_enemy_actions.py

Then watch the client. What you should see, in order: the target ring move to the
enemy, a party call on it, and the character start attacking it. If something else
happens, that something came from the library and not from here.
"""

from __future__ import annotations

import math
import sys
import time

import py4gw
from py4gw.context.agent_array import AgentAllegiance
from py4gw.game_thread.shared_block import CommandState, EventKind, EventRecord
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

HOOK_RESOLVER = "game_thread.leave_game_thread_func"
DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")

#: How far out to look for an enemy. The operator asked for this number.
SCAN_RANGE = 1000.0

#: ``UIMessage::kChangeTarget``: the client's own notice that its target changed.
#: Watched so the target step can be reported from the client's side as well as
#: from the call completing. Reading it changes nothing.
CHANGE_TARGET_MESSAGE = 0x10000020

#: How many candidates to list, and how long to wait for the client's own notice
#: after the target step. Both are for the report only; nothing is gated on them.
LIST_LIMIT = 8
NOTICE_WAIT_S = 1.5


def read_entry(win32: Win32, pid: int, address: int) -> bytes:
    """Read the hooked function's entry bytes through a fresh read-only handle."""

    with ProcessMemoryReader(win32, pid) as reader:
        return reader.read(address, len(DISPLACED))


def resolve(win32: Win32, pid: int, name: str) -> int:
    """Find one address the way every other read in this project does."""

    module = win32.get_main_module(pid)
    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        result = PatternCatalog.from_directory("offsets").resolve(name, scanner)
    if not result.ok:
        raise SystemExit(f"{name} did not resolve: {result.message}")
    return int(result.value)


def scan_enemies(
    client: py4gw.ConnectedClient, xy: tuple[float, float], own_agent: int
) -> tuple[int, list[tuple[float, int, int, float]]]:
    """Return ``(total living enemies in the array, those in range)``.

    Each in-range entry is ``(distance, agent id, level, health fraction)``, nearest
    first. The array is scanned by reference first and only the enemies in range are
    read in full, so this is a scan and not a walk through every agent record.
    """

    snapshot = client.read_agent_array()
    if snapshot is None:
        return 0, []

    total = 0
    found: list[tuple[float, int, int, float]] = []
    for reference in snapshot.all:
        if reference.allegiance is not AgentAllegiance.ENEMY:
            continue
        if reference.agent_id in (0, own_agent) or not reference.is_living:
            continue
        total += 1
        record = client.read_agent_by_id(int(reference.agent_id))
        if record is None or record.GetAsAgentLiving() is None:
            continue
        if float(record.hp) <= 0.0:
            continue
        distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
        if distance > SCAN_RANGE:
            continue
        found.append(
            (distance, int(reference.agent_id), int(record.level), float(record.hp))
        )
    found.sort(key=lambda entry: entry[0])
    return total, found


def run_step(
    label: str,
    call,
    completions: list[EventRecord],
    previous: int,
    timeout_s: float = 5.0,
) -> int:
    """Run one member and report the completion the client's own code published.

    Returns the highest completion sequence seen, so the next step can tell its own
    completion apart from this one's — a command's sequence number is the block's
    write counter *before* it advances, so the first command of a connection is
    sequence **0** and "nothing seen yet" has to be ``-1``.
    """

    started = time.monotonic()
    call()
    elapsed_ms = (time.monotonic() - started) * 1000.0

    deadline = time.monotonic() + timeout_s
    event: EventRecord | None = None
    while time.monotonic() < deadline:
        event = next(
            (item for item in completions if item.sequence > previous), None
        )
        if event is not None:
            break
        time.sleep(0.02)

    if event is None:
        print(f"  {label:9} published a call, but no completion event arrived")
        return previous

    state = CommandState(event.arg1)
    print(
        f"  {label:9} {state.name:6} result {event.arg2:<4} "
        f"({elapsed_ms:.0f} ms round trip)"
    )
    return event.sequence


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("Start Guild Wars first.")
        return 1
    if not win32.is_elevated():
        print("Run this from an elevated shell: connecting asserts it.")
        return 1

    pid = int(clients[0]["pid"])
    module = win32.get_main_module(pid)
    hook_target = resolve(win32, pid, HOOK_RESOLVER)
    if read_entry(win32, pid, hook_target) != DISPLACED:
        print(f"0x{hook_target:08X} does not hold the entry bytes this probe declares.")
        return 1

    client = py4gw.connect(clients[0])
    completions: list[EventRecord] = []
    notices: list[EventRecord] = []
    client.callbacks.register(EventKind.COMMAND_COMPLETE, completions.append)
    client.callbacks.register(EventKind.UI_MESSAGE, notices.append)
    client.watch(CHANGE_TARGET_MESSAGE)

    print(
        f"client     = pid {pid}, module 0x{int(module['base_address']):08X} + "
        f"0x{int(module['size']):X}"
    )
    print(f"hook       = 0x{hook_target:08X}")
    print("actions    = Player.ChangeTarget, Player.CallTarget, Player.Interact")

    own_agent = int(Player.GetAgentID())
    xy = Player.GetXY()
    if not own_agent or xy == (0.0, 0.0):
        print("Log a character into a map first.")
        py4gw.disconnect()
        return 1
    print(f"character  = agent {own_agent} at ({xy[0]:.1f}, {xy[1]:.1f})")

    # 1. Scan.
    total, found = scan_enemies(client, xy, own_agent)
    print(
        f"\n1. scan     = {total} living enemies in the array, {len(found)} within "
        f"{SCAN_RANGE:.0f} units"
    )
    for distance, agent_id, level, health in found[:LIST_LIMIT]:
        print(
            f"              agent {agent_id:<5} level {level:<3} health {health:>4.0%}"
            f"  {distance:>7.1f} units away"
        )
    if len(found) > LIST_LIMIT:
        print(f"              ... and {len(found) - LIST_LIMIT} more")

    if not found:
        print("\nNothing within range, so there is nothing to target. Stopping.")
        py4gw.disconnect()
        return 0

    # 2. Pick.
    distance, enemy, level, health = found[0]
    print(
        f"\n2. pick     = agent {enemy} (level {level}, health {health:.0%}, "
        f"{distance:.1f} units away) — the nearest"
    )

    # 3. Target. The client's own notice is read back as well, because the notice is
    #    the client confirming it, and this is the one step where that is available.
    print("\n3. target")
    notices.clear()
    previous = max((event.sequence for event in completions), default=-1)
    completions.clear()
    previous = run_step(
        "target", lambda: Player.ChangeTarget(enemy), completions, previous
    )
    deadline = time.monotonic() + NOTICE_WAIT_S
    confirmed = False
    while time.monotonic() < deadline and not confirmed:
        confirmed = any(
            event.sequence == CHANGE_TARGET_MESSAGE and event.arg0 == enemy
            for event in notices
        )
        time.sleep(0.02)
    print(
        "             the client's own kChangeTarget notice "
        + (
            f"reports target {enemy}"
            if confirmed
            else "did not arrive within "
            f"{NOTICE_WAIT_S:.1f}s — watch the ring to judge this step"
        )
    )

    # 4. Call.
    print("\n4. call")
    previous = run_step(
        "call", lambda: Player.CallTarget(enemy), completions, previous
    )

    # 5. Interact.
    print("\n5. interact")
    previous = run_step(
        "interact", lambda: Player.Interact(enemy), completions, previous
    )

    print(
        "\nthe three calls are done. The probe stops here and changes nothing else:\n"
        f"the target is left on agent {enemy}, the character is where the client put\n"
        "it, and whatever it does next is the client acting on the interaction."
    )

    py4gw.disconnect()
    restored = read_entry(win32, pid, hook_target)
    print(f"\nentry after disconnect = {restored.hex(' ')}")
    print(f"hooks removed          = {restored == DISPLACED}")
    print("finished               = five steps, nothing left running")
    return 0


if __name__ == "__main__":
    sys.exit(main())
