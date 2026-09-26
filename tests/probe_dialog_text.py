"""Live probe: display what the open dialog **says**, without decoding anything.

The port cannot render encoded text yet — that is Route A (the ``gw.dat`` string table) and
it is the next phase. But the client has already rendered it: a frame's context holds the
**decoded** label immediately after the encoded one, and ``TextLabelFrame::GetDecodedLabel``
(``ui_methods.cpp:2224-2234``) is a plain read of it.

So this probe answers the question directly and honestly:

- find the ``"NPC Dialog"`` frame by its hash (the port's ``frame_id_by_hash``),
- walk its subtree with the ported frame tree,
- print each frame's **decoded** label, and its encoded label's codepoints where the
  decoded copy is not published (buttons expose only the encoded one through the source's
  own accessor, and their decoded text arrives with the dialog decode),
- print the dialog module's captured state beside it, so the two views can be compared.

Read-only: the connection installs the layer because the dialog state arrives through its
observer, the interaction is the same one the other probes make, and nothing is sent.
"""

from __future__ import annotations

import math
import sys
import time
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.context.agent_array import AgentAllegiance
from py4gw.player import Player
from py4gw.ui.encoded_str import is_valid_enc_str
from py4gw.ui.frame_tree import FrameTree

OPEN_WAIT_S = 30.0

#: How long the client gets to announce the dialog buttons after the dialog itself is up.
#: They arrive on their own and can take seconds (measured: 2.1 s and 6.1 s in one run).
BUTTON_WAIT_S = 20.0
POLL_S = 0.25
SCAN_LIMIT = 400

#: How deep to walk the dialog's subtree, and how many frames to print. A dialog is a
#: handful of frames; the bounds exist so a mis-identified root cannot dump the UI.
MAX_DEPTH = 4
MAX_FRAMES = 40


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


def _walk(tree: FrameTree, root: Any, depth: int = 0) -> list[tuple[int, Any]]:
    """Return ``(depth, frame)`` for the root and its descendants, breadth-first and bounded."""

    out: list[tuple[int, Any]] = []
    queue: list[tuple[int, Any]] = [(depth, root)]
    while queue and len(out) < MAX_FRAMES:
        level, frame = queue.pop(0)
        out.append((level, frame))
        if level >= MAX_DEPTH:
            continue
        for child in tree.children_of(frame):
            queue.append((level + 1, child))
    return out


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
        frame_array = client.frame_array
        tree = FrameTree(frame_array)

        # A dialog exists only while an interaction is in flight, so this probe drives it: the
        # closest NPC, one interaction, and a bounded wait for the client to walk there and open
        # its dialog. Nothing here is done by hand in the client (``AGENTS.md``, "Live
        # verification").
        if dialog.get_active_dialog() is None:
            agent_id = _closest_npc(client, Player.GetXY())
            if not agent_id:
                print("\nno NPC found in the scanned records; nothing to interact with.")
                return 2
            print(f"\nno dialog open; interacting with agent {agent_id} (closest NPC)")
            Player.Interact(agent_id)

        waited = 0.0
        while waited < OPEN_WAIT_S and not dialog.PyDialog.is_dialog_active():
            time.sleep(POLL_S)
            waited += POLL_S
        print(f"\nwaited {waited:.1f}s; is_dialog_active() = {dialog.PyDialog.is_dialog_active()}")

        # The buttons are not announced with the body: they arrive on their own, and seconds
        # later rather than milliseconds, so the wait does not stop when the dialog appears.
        buttons_waited = 0.0
        while buttons_waited < BUTTON_WAIT_S and not dialog.PyDialog.get_active_dialog_buttons():
            time.sleep(POLL_S)
            buttons_waited += POLL_S
        buttons = dialog.PyDialog.get_active_dialog_buttons()
        print(
            f"the client announced {len(buttons)} buttons "
            f"after a further {buttons_waited:.1f}s"
        )
        for button in buttons:
            print(
                f"  dialog id {button.dialog_id}: caption {ascii(button.message_decoded)}, "
                f"pending {button.message_decode_pending}"
            )

        waited = 0.0
        while waited < OPEN_WAIT_S and not dialog.PyDialog.is_dialog_active():
            time.sleep(POLL_S)
            waited += POLL_S
        print(f"\nwaited {waited:.1f}s; is_dialog_active() = {dialog.PyDialog.is_dialog_active()}")

        frame_id = frame_array.frame_id_by_hash(dialog.NPC_DIALOG_HASH)
        print(f"the NPC Dialog frame is frame {frame_id}")
        if not frame_id:
            print(
                "\nthe client does not have that frame up. It exists only while a dialog is "
                "open, so interact with a dialog NPC and run this again."
            )
            return 3

        root = frame_array.get(frame_id)
        if root is None:
            print("the frame could not be read.")
            return 4

        print(f"\n--- what the client renders under frame {frame_id} ---")
        for depth, frame in _walk(tree, root):
            marker = " " * depth
            try:
                decoded = frame_array.decoded_label(frame)
                encoded = frame_array.encoded_label(frame)
            except (OSError, ValueError) as error:
                print(f"{marker}[unreadable] frame {int(frame.frame_id)}: {error}")
                continue
            context = frame_array.frame_context_address(frame)
            kind = "text" if decoded else ("label" if encoded else "frame")
            print(
                f"{marker}[{kind}] frame {int(frame.frame_id)}"
                f" hash 0x{int(frame.relation.frame_hash_id):08X}"
                f" type {int(frame.type)} state 0x{int(frame.frame_state):08X}"
                f" ctx 0x{context:08X}"
            )
            if decoded:
                print(f"{marker}    says: {ascii(decoded)}")
            elif encoded:
                codepoints = [ord(char) for char in encoded]
                print(
                    f"{marker}    encoded only ({len(codepoints)} codepoints),"
                    f" valid enc-str: {is_valid_enc_str(codepoints + [0])}"
                )
            # The context's own words, so a frame whose text is rendered by a layout we do
            # not model can still be recognised: ``[+4]`` is the label pointer and
            # ``[+0xC]`` the size word the two accessors read.
            if context:
                try:
                    words = [
                        frame_array.read_u32(context + offset)
                        for offset in (0x0, 0x4, 0x8, 0xC)
                    ]
                except OSError as error:
                    print(f"{marker}    context unreadable: {error}")
                    continue
                print(
                    f"{marker}    ctx words: "
                    + " ".join(f"+{offset:X}=0x{value:08X}" for offset, value in zip((0, 4, 8, 12), words))
                )

        # The tree walk above follows the parent relation and can stop short of a frame
        # whose parent field does not point at its parent's address. A full-array sweep for
        # frames that carry a label finds the text regardless of where the walk got to,
        # which is the point of this probe: show what the client has rendered, not what the
        # tree happens to reach.
        print(f"\n--- every labelled frame in the array ({frame_array.size()} slots) ---")
        labelled = 0
        unreadable = 0
        unreadable_frames = 0
        for candidate_id, _pointer in frame_array.iter_slots():
            try:
                candidate = frame_array.get(candidate_id)
            except (OSError, ValueError):
                # ``iter_frames`` reads each frame record, so a slot whose pointer no
                # longer resolves raises from the iteration itself. Outside the process a
                # stale pointer is an error to skip, where in-process it would be a fault.
                unreadable_frames += 1
                continue
            if candidate is None:
                continue
            try:
                decoded = frame_array.decoded_label(candidate)
                encoded = frame_array.encoded_label(candidate)
            except (OSError, ValueError):
                # ``ValueError`` as well as ``OSError``: this port bounds the callback and
                # label array headers it reads, and a frame whose header is junk is
                # reported that way rather than read as a string.
                unreadable += 1
                continue
            if not (decoded or encoded):
                continue
            labelled += 1
            parent = int(candidate.relation.parent)
            print(
                f"  frame {candidate_id}: parent 0x{parent:08X}"
                f" type {int(candidate.type)}"
                f" state 0x{int(candidate.frame_state):08X}"
            )
            if decoded:
                print(f"      rendered: {ascii(decoded)}")
            if encoded:
                codepoints = [ord(char) for char in encoded]
                print(
                    f"      encoded : {len(codepoints)} codepoints,"
                    f" first {[hex(c) for c in codepoints[:10]]}"
                    f" valid={is_valid_enc_str(codepoints + [0])}"
                )
        print(
            f"  {labelled} frame(s) carry a label, {unreadable} unreadable label(s),"
            f" {unreadable_frames} unreadable frame record(s)"
        )

        active = dialog.get_active_dialog()
        if active is not None:
            print("\n--- the dialog module's own state, for comparison ---")
            print(f"  agent {active.agent_id}, message {active.message!r}")
            for index, button in enumerate(dialog.get_active_dialog_buttons()):
                print(
                    f"  button {index}: dialog_id {button.dialog_id}"
                    f" icon {button.button_icon}"
                    f" message {button.message!r}"
                    f" decode_pending {button.message_decode_pending}"
                )

        print(
            "\nthe dialog is still open so you can compare the two; press Escape to close "
            "it. This probe sent nothing."
        )
        return 0
    finally:
        client.close()
        print("\nclosed; the client's own bytes are back.")


def main() -> int:
    """Run the probe, writing the report to the path given as the first argument."""

    report = sys.argv[1] if len(sys.argv) > 1 else ""
    tee = _Tee(sys.stdout, report) if report else None
    error_tee = _Tee(sys.stderr, report + ".err") if report else None
    if tee is not None:
        sys.stdout = tee  # type: ignore[assignment]
    if error_tee is not None:
        sys.stderr = error_tee  # type: ignore[assignment]
    try:
        return _run()
    finally:
        if tee is not None:
            sys.stdout = sys.__stdout__
            tee.close()
        if error_tee is not None:
            sys.stderr = sys.__stderr__
            error_tee.close()


if __name__ == "__main__":
    sys.exit(main())
