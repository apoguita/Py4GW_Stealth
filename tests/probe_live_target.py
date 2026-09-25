"""Probe: make the client change its target, so a human can watch it happen.

Not a test. This exists because the first live call picked the wrong half of the
mechanism: it *sent* ``kSendChangeTarget``, which is the message the client emits
when its target changes, and sending a notification changes nothing. Native's own
handler says so — it observes that message and then calls ``ChangeTargetFn``
(``agent.cpp:143-155``), which is where the target actually changes.

So this calls the function, alternating between the player's own character and
"no target", and the answer is whether the target ring appears and disappears. A
person watching the client is the only sensor available: the current target is
``g_current_target_id``, a global Native maintains from a hook, and no readable
context holds it (which is why ``Player.GetTargetID`` refuses in this library).

Run it from an **elevated** shell, in a map, and watch the client::

    python tests/probe_live_target.py
"""

from __future__ import annotations

import sys
import time

import py4gw
from py4gw.game_thread.bridge import Bridge
from py4gw.game_thread.shared_block import CallForm, CommandState, Descriptor
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

HOOK_RESOLVER = "game_thread.leave_game_thread_func"
CALL_RESOLVER = "agent.change_target_func"
DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
SLOT_CHANGE_TARGET = 0

#: How many times to alternate, and how long each state is held. **Each round is
#: two calls**, so the default is six target changes over about nine seconds.
#: Raise it on the command line only when a longer look is actually wanted: an
#: earlier run used 20 rounds and held somebody's target for a minute, which was
#: far more than the question needed.
ROUNDS = 3
HOLD_SECONDS = 1.5

#: A ceiling, so a typo cannot hold a player's target hostage for minutes.
MAX_ROUNDS = 20


def read_arguments() -> tuple[int, float]:
    """Return ``(rounds, hold_seconds)``, from the command line if given."""

    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else ROUNDS
    hold = float(sys.argv[2]) if len(sys.argv) > 2 else HOLD_SECONDS
    if not 1 <= rounds <= MAX_ROUNDS:
        raise SystemExit(f"rounds must be 1..{MAX_ROUNDS}; {rounds} was given.")
    if not 0.2 <= hold <= 10.0:
        raise SystemExit(f"hold must be 0.2..10.0 seconds; {hold} was given.")
    return rounds, hold


def resolve(win32: Win32, pid: int, name: str) -> int:
    """Find one address the way every other read in this project does."""

    module = win32.get_main_module(pid)
    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        result = PatternCatalog.from_directory("offsets").resolve(name, scanner)
    if not result.ok:
        raise SystemExit(f"{name} did not resolve: {result.message}")
    return int(result.value)


def read_entry(win32: Win32, pid: int, address: int) -> bytes:
    with ProcessMemoryReader(win32, pid) as reader:
        return reader.read(address, len(DISPLACED))


def main() -> int:
    rounds, hold_seconds = read_arguments()
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
    module_base, module_size = int(module["base_address"]), int(module["size"])
    hook_target = resolve(win32, pid, HOOK_RESOLVER)
    change_target = resolve(win32, pid, CALL_RESOLVER)

    if read_entry(win32, pid, hook_target) != DISPLACED:
        print(f"0x{hook_target:08X} does not hold the entry bytes this probe declares.")
        return 1

    client = py4gw.connect(clients[0])
    try:
        agent_id = int(Player.GetAgentID())
    finally:
        py4gw.disconnect()
    if not agent_id:
        print("Log a character into a map first: the probe needs an agent to target.")
        return 1

    print(f"client           = pid {pid}, module 0x{module_base:08X} + 0x{module_size:X}")
    print(f"hook             = 0x{hook_target:08X}")
    print(f"{CALL_RESOLVER} = 0x{change_target:08X}")
    print(f"player agent     = {agent_id}")
    print(f"\nwatch the client: the target should appear on your character and clear.")
    print(
        f"{rounds} rounds = {rounds * 2} target changes over about "
        f"{rounds * 2 * hold_seconds:.0f} seconds, and then it stops.\n"
    )

    access = WriteAccess(pid)
    bridge = Bridge(access, pid, timeout_ms=5000)
    try:
        bridge.install(
            hook_target,
            DISPLACED,
            calls={
                SLOT_CHANGE_TARGET: Descriptor(
                    target=change_target, form=CallForm.U32_U32
                )
            },
            module_base=module_base,
            module_size=module_size,
        )
        hits = bridge.wait_for_hits(2, 5000)
        print(f"hook hits        = {hits}")

        for round_index in range(rounds):
            targeted = bridge.call(SLOT_CHANGE_TARGET, agent_id, 0)
            print(
                f"  {round_index + 1}: target self -> {targeted.state.name} "
                f"(result {targeted.result})"
            )
            time.sleep(hold_seconds)
            cleared = bridge.call(SLOT_CHANGE_TARGET, 0, 0)
            print(
                f"  {round_index + 1}: clear       -> {cleared.state.name} "
                f"(result {cleared.result})"
            )
            time.sleep(hold_seconds)

            if targeted.state is not CommandState.DONE:
                print("  a call did not complete; stopping here.")
                break
    finally:
        if bridge.installed:
            bridge.remove()
        restored = read_entry(win32, pid, hook_target)
        access.close()

    print(f"\nentry after remove = {restored.hex(' ')}")
    print(f"restored           = {restored == DISPLACED}")
    print(f"finished           = {rounds} rounds, hook removed, nothing left running")
    print(
        "\nIf the target ring moved, the call path works end to end and the first\n"
        "live call was simply on the wrong side of the mechanism. If it did not,\n"
        "the function resolves to something other than the target setter, and the\n"
        "next step is to observe the client's own messages instead of guessing."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
