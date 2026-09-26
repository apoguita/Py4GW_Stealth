"""Live probe: open a real dialog and read what the dialog module captured.

The metadata tables (``probe_dialog_tables.py``) are static and read without a dialog.
The **state** is not: ``kDialogBody`` and ``kDialogButton`` only arrive while a dialog is
open, so the only way to see them is to open one. Nothing in the client offers a dialog
on request, so this probe does what a player does: it picks the closest NPC, interacts
with it, and waits — the client walks the character there and opens the dialog when it
arrives.

It reads the dialog the port captured and prints it. It sends nothing, so the dialog
stays open for you to look at; Escape closes it.

Run it from an elevated shell. This one *does* install the capability layer, because the
dialog state arrives through the hook's observer: ``game_thread=False`` would capture
nothing. The layer puts the client's own bytes back when the probe closes.
"""

from __future__ import annotations

import math
import os
import sys
import time
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.context.agent_array import AgentAllegiance
from py4gw.player import Player

#: How long to wait for the walk and the dialog that follows it.
OPEN_WAIT_S = 30.0

#: How often to look, and how often to say where the character is.
POLL_S = 0.25
REPORT_EVERY_S = 2.0

#: How many agent records to read while looking for the closest NPC. A busy outpost has
#: thousands of references and every one is a remote read.
SCAN_LIMIT = 400


class _Tee:
    """Write to the console and to a report file at once.

    An elevated child's console is not the one the caller can read, and it does not
    inherit the caller's environment either, so the report path arrives as an argument.
    """

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


def _closest_npc(client: py4gw.ConnectedClient, xy: tuple[float, float]) -> tuple[int, float]:
    """Return the closest NPC and its distance, excluding what must not be touched.

    The exclusions are the live suite's, for the reasons it records: never the player's
    own agent, never an enemy or an unknown allegiance, and only something that can
    answer with a dialog. Unlike the suite this probe does **not** cap the distance,
    because the whole point is the walk: the client takes the character to the NPC.
    """

    snapshot = client.read_agent_array()
    if snapshot is None:
        return 0, 0.0

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
        if record is None:
            continue
        # An NPC is a living agent with no login number: a player has one, a gadget is
        # not living. Preferring NPCs is the suite's ordering, and a dialog is what an
        # NPC answers with.
        if not (record.is_living_type and not int(record.login_number)):
            continue
        distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
        if not best_id or distance < best_distance:
            best_id, best_distance = int(reference.agent_id), distance
    return best_id, best_distance


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
        start = Player.GetXY()
        print(f"character at {start}, agent {int(Player.GetAgentID())}")

        agent_id, distance = _closest_npc(client, start)
        if not agent_id:
            print("no NPC found in the scanned records; nothing to interact with.")
            return 2

        record = client.read_agent_by_id(agent_id)
        position = (
            (float(record.pos.x), float(record.pos.y)) if record is not None else (0.0, 0.0)
        )
        print(
            f"\nclosest NPC: agent {agent_id} at {position}, {distance:.1f} units away"
        )

        active = dialog.get_active_dialog()
        print(
            "dialog already open before we act: "
            + ("none" if active is None else f"agent {active.agent_id}")
        )

        print(f"\ninteracting with agent {agent_id} (the client walks there)")
        Player.Interact(agent_id)

        seen_since = 0.0
        last_report = 0.0
        opened = None
        while seen_since < OPEN_WAIT_S:
            time.sleep(POLL_S)
            seen_since += POLL_S

            candidate = dialog.get_active_dialog()
            if candidate is not None:
                opened = candidate
                break

            if seen_since - last_report >= REPORT_EVERY_S:
                last_report = seen_since
                now = Player.GetXY()
                try:
                    near = math.dist(Player.GetXY(), position)
                except (OSError, RuntimeError):
                    near = 0.0
                print(
                    f"  t+{seen_since:4.1f}s  character at {now}, "
                    f"{near:.1f} units from the NPC, no dialog yet"
                )

        if opened is None:
            print(f"\nno dialog opened within {OPEN_WAIT_S:.0f}s.")
            print(f"character is at {Player.GetXY()}")
            return 3

        walked = math.dist(Player.GetXY(), position)
        print(
            f"\ndialog opened after {seen_since:.1f}s; character is {walked:.1f} units "
            f"from the NPC"
        )
        print("\nthe captured dialog:")
        print(f"  agent_id              {opened.agent_id}")
        print(f"  dialog_id             {opened.dialog_id} (0x{opened.dialog_id:08X})")
        print(f"  context_dialog_id     {opened.context_dialog_id}")
        print(f"  id_authoritative      {opened.dialog_id_authoritative}")
        print(f"  message               {opened.message!r}")

        buttons = dialog.get_active_dialog_buttons()
        print(f"\nbuttons: {len(buttons)}")
        for index, button in enumerate(buttons):
            print(
                f"  [{index}] dialog_id {button.dialog_id} (0x{button.dialog_id:08X})"
                f"  icon {button.button_icon}"
                f"  message {button.message!r}"
                f"  decode_pending {button.message_decode_pending}"
            )

        print(f"\nlast_selected_dialog_id: {dialog.PyDialog.get_last_selected_dialog_id()}")
        for button in buttons:
            print(
                f"  is_dialog_displayed({button.dialog_id}) "
                f"= {dialog.PyDialog.is_dialog_displayed(button.dialog_id)}"
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
    """Run the probe, writing the report to the path given as the first argument.

    An elevated child does not inherit the environment of the shell that started it, and
    its console is not the one the caller can read, so the report path is an argument:
    ``python -m tests.probe_dialog_open <report-path>``.
    """

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
