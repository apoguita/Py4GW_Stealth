"""Read-only live probe for phase 1: the frame lookup and the encoded-string grammar.

Two things cannot be settled offline, and this probe settles them against the running
client:

1. **``is_dialog_active``** — the port finds the ``"NPC Dialog"`` frame by hash in the
   frame array (``GetFrameIDByHash``'s scan) and reads two state bits. Whether the hash and
   the scan find *the client's* dialog frame is a live question, so the probe reports the
   answer before and after an interaction opens a dialog.
2. **``IsValidEncStr``** — the grammar is ported from the source, but the only proof it
   matches the game's own format is that it accepts **real encoded strings**. The probe
   takes the text pointers straight out of the client's own dialog messages
   (``DialogBodyInfo.message_enc`` is word 2, ``DialogButtonInfo.message`` is word 1), reads
   the codepoints at them, and reports what the ported validator says.

It reads only: the connection installs the layer because the dialog messages arrive through
its observer, and nothing is sent. The interaction is the same one
``probe_dialog_open.py`` makes — closest NPC, then wait — because a dialog has to be open for
any of this to exist.
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
from py4gw.player import Player
from py4gw.ui.encoded_str import is_valid_enc_str

OPEN_WAIT_S = 30.0
POLL_S = 0.25
SCAN_LIMIT = 400

#: ``UIMessage::kDialogBody`` / ``kDialogButton`` (``constants/ui.h:74-75``).
DIALOG_BODY_MESSAGE = dialog.DIALOG_BODY_MESSAGE
DIALOG_BUTTON_MESSAGE = dialog.DIALOG_BUTTON_MESSAGE

#: How many codepoints to read at each text pointer. A dialog body is a sentence or two, so
#: this is generous; the read stops at the array's own terminator anyway.
CODEPOINT_LIMIT = 256


class _Tee:
    """Write to the console and to a report file at once."""

    def __init__(self, stream: Any, path: str) -> None:
        self._stream = stream
        self._file = open(path, "w", encoding="utf-8")

    def write(self, text: str) -> int:
        self._stream.write(text)
        self._file.write(text)
        return len(text)

    def flush(self) -> None:
        self._stream.flush()
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class _MessageSpy:
    """Keep the text pointers the client's dialog messages carry.

    The dialog module reads ``DialogBodyInfo``'s agent and ``DialogButtonInfo``'s id; the
    *text* pointers in those same packets are what this probe needs, and word 2 of the body
    and word 1 of a button are where the client puts them.
    """

    def __init__(self) -> None:
        self.body_pointer = 0
        self.body_agent = 0
        self.button_pointers: list[int] = []
        self.button_ids: list[int] = []
        self.delivered = 0
        self.bodies = 0
        self.buttons = 0

    def __call__(self, event: EventRecord) -> None:
        """Keep the text pointers from one event.

        ``EventRecord.kind`` is a plain ``int`` (``shared_block.py:482``) while
        ``EventKind`` is an ``IntEnum``, so the comparison is by value: an identity test
        against the enum member is false for every real record.
        """

        if int(event.kind) != int(EventKind.UI_MESSAGE):
            return
        self.delivered += 1
        if event.sequence == DIALOG_BODY_MESSAGE:
            self.body_agent = int(event.arg1)
            self.body_pointer = int(event.arg2)
            self.bodies += 1
        elif event.sequence == DIALOG_BUTTON_MESSAGE:
            self.button_pointers.append(int(event.arg1))
            self.button_ids.append(int(event.arg2))
            self.buttons += 1


def _read_codepoints(read_u32: Any, address: int, limit: int) -> list[int] | None:
    """Read a wide string's codepoints, stopping at the terminator.

    The client stores these as UTF-16 code units; the port reads them one at a time because
    that is the read primitive it has. An unreadable address is reported, not guessed at.
    """

    if not address:
        return None
    codepoints: list[int] = []
    for index in range(limit):
        value = read_u32(address + index * 2)
        if value is None:
            return None
        # One UTF-16 code unit, low half of the word the reader returned.
        unit = int(value) & 0xFFFF
        codepoints.append(unit)
        if unit == 0:
            break
    return codepoints


def _closest_npc(client: py4gw.ConnectedClient, xy: tuple[float, float]) -> int:
    """Return the closest NPC, as ``probe_dialog_open.py`` does."""

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


def _run() -> int:
    processes = [
        process
        for process in py4gw.win32.list_processes()
        if str(process.get("name", "")).lower().endswith("gw.exe")
    ]
    if not processes:
        print("no Gw.exe found. Start the client and run this again.")
        return 1

    process = processes[0]
    pid = int(process["pid"])
    print(f"connecting to pid {pid} ({process.get('name')}) with the capability layer")

    client = py4gw.connect(pid)
    try:
        read_u32 = client.dialog_tables.read_uint32
        spy = _MessageSpy()
        client.callbacks.register(EventKind.UI_MESSAGE, spy)

        print("\n--- is_dialog_active, before anything is done ---")
        before = dialog.PyDialog.is_dialog_active()
        print(f"  is_dialog_active() = {before}")
        frame_array = client.frame_array
        frame_id = frame_array.frame_id_by_hash(dialog.NPC_DIALOG_HASH)
        print(f"  frame_id_by_hash({dialog.NPC_DIALOG_HASH}) = {frame_id}")
        print(f"  frame array size = {frame_array.size()}")
        if frame_id:
            frame = frame_array.get(frame_id)
            if frame is not None:
                print(
                    f"  frame {frame_id}: state 0x{int(frame.frame_state):08X}"
                    f"  created={frame.is_created}  visible={frame.is_visible}"
                    f"  hash=0x{int(frame.relation.frame_hash_id):08X}"
                )

        start = Player.GetXY()
        agent_id = _closest_npc(client, start)
        if not agent_id:
            print("\nno NPC found in the scanned records; nothing to interact with.")
            return 2
        already_open = dialog.get_active_dialog() is not None
        if already_open:
            print(
                "\na dialog is already open. The client only announces a body when it "
                "opens one, so if it is already up no fresh text pointer arrives in this "
                "run — press Escape in the client and run this again for the text half."
            )
        print(f"\ninteracting with agent {agent_id} (closest NPC)")
        Player.Interact(agent_id)

        # A fresh body is what carries the text pointer, so wait for that rather than for
        # any dialog: an already-open one would satisfy the weaker condition immediately.
        waited = 0.0
        while waited < OPEN_WAIT_S and not spy.bodies:
            time.sleep(POLL_S)
            waited += POLL_S

        active = dialog.get_active_dialog()
        print(f"\n--- after {waited:.1f}s ---")
        print(
            f"  the spy saw {spy.delivered} UI messages:"
            f" {spy.bodies} body, {spy.buttons} button"
        )
        if active is None:
            print("no dialog opened; the text pointers cannot be read without one.")
            return 3
        print(f"  dialog captured for agent {active.agent_id}")
        after = dialog.PyDialog.is_dialog_active()
        print(f"  is_dialog_active() = {after}   (was {before})")

        print("\n--- the client's own encoded strings ---")
        print(f"  body pointer 0x{spy.body_pointer:08X} (agent {spy.body_agent})")
        body = _read_codepoints(read_u32, spy.body_pointer, CODEPOINT_LIMIT)
        if body is None:
            print("  body pointer could not be read")
        else:
            print(f"  body codepoints ({len(body)}): {[hex(c) for c in body[:16]]}...")
            print(f"  is_valid_enc_str(body) = {is_valid_enc_str(body)}")

        for index, (pointer, dialog_id) in enumerate(
            zip(spy.button_pointers, spy.button_ids)
        ):
            label = _read_codepoints(read_u32, pointer, CODEPOINT_LIMIT)
            if label is None:
                print(f"  button {index} (id {dialog_id}) pointer unreadable")
                continue
            print(
                f"  button {index} (id {dialog_id}) pointer 0x{pointer:08X}:"
                f" {len(label)} codepoints, first {[hex(c) for c in label[:8]]},"
                f" valid={is_valid_enc_str(label)}"
            )

        print(
            "\nthe dialog is still open so you can look at it; press Escape to close it. "
            "This probe sent nothing."
        )
        return 0
    finally:
        client.close()
        print("\nclosed; the client's own bytes are back.")


def main() -> int:
    """Run the probe, writing the report to the path given as the first argument."""

    report = sys.argv[1] if len(sys.argv) > 1 else ""
    tee = _Tee(sys.stdout, report) if report else None
    if tee is not None:
        sys.stdout = tee  # type: ignore[assignment]
    try:
        return _run()
    finally:
        if tee is not None:
            sys.stdout = sys.__stdout__
            tee.close()


if __name__ == "__main__":
    sys.exit(main())
