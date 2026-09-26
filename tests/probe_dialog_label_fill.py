"""Live probe: does the string a button's label points at change after the message?

A button's label is the one string this port decodes that the source's own guard accepts and the
client's parser then asserts on (``IsParam(data)``, ``TextParser.cpp:724``), which is why the
handover is withheld. The recorded reading is that a button's announced pointer does not carry a
table reference (``docs/RESEARCH.md``). The repeated live reads complicate that: across four
reads on the record the **first two words are a heap pointer** (``0xC02F4481``, ``0xC143455B``,
``0xC0301DD4``, ``0xC0297D99``) while the words after them are the same every time. A buffer whose
head is an address is not a wide string that has been written yet, which points the other way: the
port is reading a buffer the client has not finished filling, and the source never does that
because its callback runs **after** the client's own send returns (``SendUIMessage``,
``ui_methods.cpp:1390-1404``; the dialog registers at altitude ``0x1``, ``dialog.cpp:1273-1292``).

This probe settles it by watching instead of arguing: it drives one interaction the way the live
tests do, and for each announced button label it reads that pointer **repeatedly** for a couple of
seconds, printing every distinct content with the time it was first seen. A buffer that settles
into something new is a buffer that was being filled; one that stays as announced is read at the
only moment there is.

Read-only: the connection installs the capability layer because the messages arrive through its
observer, and the only thing this probe sends is the interaction itself.

Usage: (elevated) python tests/probe_dialog_label_fill.py
"""

from __future__ import annotations

import math
import sys
import time
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.context.agent_array import AgentAllegiance
from py4gw.game_thread.shared_block import EventKind, EventRecord
from py4gw.internals import string_table
from py4gw.player import Player
from py4gw.ui.encoded_str import is_valid_enc_str
from py4gw.win32 import Win32

#: How long the client gets to announce the dialog, and then its buttons. The buttons can arrive
#: seconds after the body, so the second wait is its own.
OPEN_WAIT_S = 30.0
BUTTON_WAIT_S = 20.0
POLL_S = 0.25

#: How long one pointer is watched, how often it is read, and how many words one read covers.
#: The word bound is the same 256 the live test reads a wide string with.
WATCH_S = 2.0
WATCH_INTERVAL_S = 0.0002
WORD_LIMIT = 256

SCAN_LIMIT = 400


class _LabelWatch:
    """Keep the pointer of every button the client announces, as its message arrives."""

    def __init__(self) -> None:
        self.bodies = 0
        self.body_pointer = 0
        self.body_agent = 0
        self.pointer_at: list[tuple[float, int, int]] = []

    def __call__(self, event: EventRecord) -> None:
        if int(event.kind) != int(EventKind.UI_MESSAGE):
            return
        if event.sequence == dialog.DIALOG_BODY_MESSAGE:
            self.bodies += 1
            self.body_agent = int(event.arg1)
            self.body_pointer = int(event.arg2)
        elif event.sequence == dialog.DIALOG_BUTTON_MESSAGE:
            self.pointer_at.append(
                (time.monotonic() * 1000.0, int(event.arg2), int(event.arg1))
            )


def _closest_npc(client: py4gw.ConnectedClient, xy: tuple[float, float]) -> int:
    """Return the closest NPC, as the other dialog probes do."""

    snapshot = client.read_agent_array()
    if snapshot is None:
        return 0
    own_agent = int(Player.GetAgentID())
    best_id, best_distance = 0, 0.0
    read = 0
    for reference in snapshot.all:
        if reference.agent_id in (0, own_agent):
            continue
        if reference.allegiance in (None, AgentAllegiance.ENEMY):
            continue
        if not (reference.is_living or reference.is_gadget):
            continue
        if read >= SCAN_LIMIT:
            break
        read += 1
        try:
            record = client.read_agent(reference)
        except (OSError, RuntimeError):
            continue
        if record is None or not (record.is_living_type and not int(record.login_number)):
            continue
        distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
        if not best_id or distance < best_distance:
            best_id, best_distance = int(reference.agent_id), distance
    return best_id


def _read_words(read_u32: Any, address: int) -> list[int] | None:
    """Read a wide string at ``address``, stopping at its terminator."""

    if not address:
        return None
    words: list[int] = []
    for index in range(WORD_LIMIT):
        unit = read_u32(address + index * 2)
        if unit is None:
            return None
        words.append(int(unit))
        if int(unit) == 0:
            break
    return words


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
        return 2
    if not win32.is_elevated():
        print("the controller must be elevated: the messages arrive through the capability layer")
        return 3

    watch = _LabelWatch()
    with py4gw.connect(clients[0]) as client:
        client.callbacks.register(EventKind.UI_MESSAGE, watch)
        read_u32 = dialog._dialog_tables().read_uint32

        xy = Player.GetXY()
        agent_id = _closest_npc(client, xy)
        if not agent_id:
            print("no NPC was found to interact with")
            return 4

        print(f"pid {client.pid}: interacting with agent {agent_id} (closest NPC at {xy})")
        Player.Interact(agent_id)

        waited = 0.0
        while waited < OPEN_WAIT_S and not watch.bodies:
            time.sleep(POLL_S)
            waited += POLL_S
        print(f"the client announced {watch.bodies} dialog bodies in {waited:.1f}s")
        if not watch.bodies:
            print("no dialog opened, so there is no label to watch")
            return 5

        buttons = 0.0
        while waited < OPEN_WAIT_S + BUTTON_WAIT_S and not watch.pointer_at:
            time.sleep(POLL_S)
            waited += POLL_S
            buttons += POLL_S
        print(
            f"{len(watch.pointer_at)} button message(s) after a further {buttons:.1f}s"
        )

        body = _read_words(read_u32, watch.body_pointer)
        print(
            f"\nbody pointer 0x{watch.body_pointer:08X} (agent {watch.body_agent}): "
            f"{[hex(word) for word in body[:8]] if body else 'unreadable'}"
        )

        for at, dialog_id, pointer in watch.pointer_at:
            print(f"\n--- button {dialog_id}, label pointer 0x{pointer:08X} ---")
            print(f"  announced at +{at - watch.pointer_at[0][0]:.1f} ms after the first")

            # Every distinct content this pointer holds while it is watched, with the time it
            # was first seen. A buffer still being written changes here; one that is finished
            # does not.
            seen: list[tuple[float, list[int]]] = []
            deadline = time.monotonic() + WATCH_S
            while time.monotonic() < deadline:
                words = _read_words(read_u32, pointer)
                if words is None:
                    seen.append((time.monotonic() * 1000.0, []))
                    break
                if not seen or seen[-1][1] != words:
                    seen.append((time.monotonic() * 1000.0, words))
                time.sleep(WATCH_INTERVAL_S)

            first = seen[0][0]
            for at_ms, words in seen:
                print(f"  +{at_ms - first:7.2f} ms  {[hex(word) for word in words]}")
            print(f"  distinct contents over {WATCH_S:.0f}s: {len(seen)}")

            final = seen[-1][1]
            if final:
                index, key = string_table._parse_codepoints(tuple(final))
                print(
                    f"  final: valid={is_valid_enc_str(final)} index={index} key=0x{key:X}"
                )

        print("\nthe interaction is the only thing this probe sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
