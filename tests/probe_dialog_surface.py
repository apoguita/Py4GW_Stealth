"""Probe: what the client tells us when a dialog is open.

Read-only, and it asks the operator to open the dialog. It hooks nothing by hand
and sends nothing: connecting installs the library's layer, the observer records the
client's own ``kDialogBody`` message, and everything else here is a read.

It answers two questions at once, which is why it exists rather than a test:

1. **Is the capture right?** The connection keeps the agent a dialog belongs to, the
   way Reforged's runtime keeps ``g_dialog_agent_id`` (``agent.cpp:133-137``). If the
   operator talks to an npc, does the id the client reports match the npc?

2. **Do we need the client's decoder to read dialog text?** ``DialogBodyInfo`` is
   ``{type, agent_id, message_enc}`` and ``message_enc`` is a pointer to the dialog's
   text *in the client*. Reforged decodes such strings with ``AsyncDecodeStr``, an
   in-client call, and that is what blocks ``Dialog``'s text, ``GetChatHistory`` and
   player names here. But if the encoded text is plain UTF-16 with marker code points
   mixed in, a bounded read may be enough — and then those members want a *reader*,
   not a decode call. This probe prints the code points so that is a measurement
   instead of an assumption.

Run it from an **elevated** shell, stand next to an npc, and talk to it while the
probe waits::

    python tests/probe_dialog_surface.py

It waits ``WAIT_SECONDS`` for a dialog and then stops either way. It changes nothing
in the game — the dialog is the operator's to open and to close.
"""

from __future__ import annotations

import struct
import sys
import time

import py4gw
from py4gw import dialog
from py4gw.game_thread.shared_block import EventKind, EventRecord
from py4gw.memory import ProcessMemoryReader
from py4gw.player import Player
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

HOOK_RESOLVER = "game_thread.leave_game_thread_func"
DISPLACED = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")

#: ``UIMessage::kDialogBody`` (``constants/ui.h:75``), whose packet is
#: ``DialogBodyInfo {type, agent_id, message_enc}`` (``context/ui.h:54-58``).
DIALOG_BODY_MESSAGE = 0x100000A6

#: How long to wait for the operator to open a dialog, and how much of the encoded
#: text to look at. 256 bytes is 128 UTF-16 code units, which is enough for a dialog
#: body and its first markers.
WAIT_SECONDS = 90.0
TEXT_BYTES = 256


def read_entry(win32: Win32, pid: int, address: int) -> bytes:
    with ProcessMemoryReader(win32, pid) as reader:
        return reader.read(address, len(DISPLACED))


def describe_text(raw: bytes) -> str:
    """Render raw bytes as code points, so markers are visible rather than hidden.

    ``repr`` of the decoded string is not enough here: the whole question is which
    code points the client stores, and a marker like ``U+0108`` disappears into a
    character that looks like a letter.
    """

    units = struct.unpack(f"<{len(raw) // 2}H", raw[: len(raw) // 2 * 2])
    text = []
    for unit in units:
        if unit == 0:
            break
        if 32 <= unit < 127:
            text.append(chr(unit))
        else:
            text.append(f"\\u{unit:04x}")
    rendered = "".join(text)
    return rendered if rendered else "(nothing before the first null)"


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
    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        result = PatternCatalog.from_directory("offsets").resolve(
            HOOK_RESOLVER, scanner
        )
    if not result.ok:
        print(f"{HOOK_RESOLVER} did not resolve: {result.message}")
        return 1
    hook_target = int(result.value)
    if read_entry(win32, pid, hook_target) != DISPLACED:
        print(f"0x{hook_target:08X} does not hold the entry bytes this probe declares.")
        return 1

    client = py4gw.connect(clients[0])
    seen: list[EventRecord] = []
    client.callbacks.register(EventKind.UI_MESSAGE, seen.append)
    client.watch(DIALOG_BODY_MESSAGE)
    print(
        f"client  = pid {pid}\n"
        f"agent   = {int(Player.GetAgentID())}\n"
        f"watch   = kDialogBody 0x{DIALOG_BODY_MESSAGE:08X}\n"
        f"\nTalk to an npc now. Waiting {WAIT_SECONDS:.0f}s for the client to report a "
        "dialog body.\n"
    )

    event: EventRecord | None = None
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline and event is None:
        event = next(
            (item for item in seen if item.sequence == DIALOG_BODY_MESSAGE), None
        )
        time.sleep(0.05)

    if event is None:
        print("No dialog body arrived. Nothing was read, and nothing was changed.")
        py4gw.disconnect()
        return 0

    words = (event.arg0, event.arg1, event.arg2, event.arg3)
    active = dialog.get_active_dialog()
    agent_id = 0 if active is None else active.agent_id
    print(
        "the client reported a dialog body:\n"
        f"  packet words      = type {words[0]}, agent {words[1]}, "
        f"message_enc 0x{words[2]:08X}, spare 0x{words[3]:08X}\n"
        f"  dialog module     = agent {agent_id}, dialog id "
        f"{0 if active is None else active.dialog_id}, context id "
        f"{0 if active is None else active.context_dialog_id}\n"
        f"  capture agrees    = {agent_id == words[1]}\n"
        f"  buttons so far    = "
        f"{[button.dialog_id for button in dialog.get_active_dialog_buttons()]}"
    )

    if not words[2]:
        print("  the packet carries no text pointer, so there is nothing more to read.")
    else:
        try:
            with ProcessMemoryReader(win32, pid) as reader:
                raw = reader.read(words[2], TEXT_BYTES)
        except OSError as error:
            print(f"  the text pointer is not readable: {error}")
        else:
            print(
                f"  text (first {TEXT_BYTES} bytes at the pointer), code points:\n"
                f"    {describe_text(raw)}\n"
                f"  raw head          = {raw[:32].hex(' ')}"
            )
            if any(0x0100 <= unit <= 0x01FF for unit in struct.unpack(
                f"<{len(raw) // 2}H", raw[: len(raw) // 2 * 2]
            )):
                print(
                    "  note: control-range code points are present, which is what "
                    "Reforged's\n  AsyncDecodeStr removes — the text is a read away, "
                    "but it needs cleaning."
                )

    py4gw.disconnect()
    restored = read_entry(win32, pid, hook_target)
    print(f"\nentry after disconnect = {restored.hex(' ')}")
    print(f"hooks removed          = {restored == DISPLACED}")
    print("finished               = read only, nothing sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
