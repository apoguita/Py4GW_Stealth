"""Live probe: does the client's own chat sender accept the buffer this port builds?

``GW::chat::SendChat`` builds a ``wchar_t buffer[140]`` on its own stack and hands its address to
``g_send_chat_func`` (``chat_methods.cpp:88-142``). Nothing of this project's runs in the client,
so ``py4gw/chat.py`` builds the same buffer in the block's data region and calls the same
function through the capability layer. The offline suite pins the buffer's bytes; what no offline
test can show is that **the client accepts it**.

The command it sends is ``/age``. That matters: the client answers it itself, in its own chat log,
with no server traffic and no effect on the game — a line the owner can read and nothing else
changes. A channel message would go to other players, which is not something a test should do.

What it reports, in order:

1. whether ``chat.send_chat_func`` resolves on this client at all;
2. the buffer this port places, read back out of the block word for word;
3. the call's own report — the state the dispatcher left the command in.

Read-only in what it asks of the client apart from that one command, which the client processes
locally. Run it with a character in a map.

Usage: (elevated) python tests/probe_chat_send.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw import chat
from py4gw.player import Player
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

COMMAND = "age"


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    with py4gw.connect(process) as client:
        report["resolver_present"] = client.resolves(chat.SEND_CHAT_FUNC)
        if not report["resolver_present"]:
            report["note"] = (
                "chat.send_chat_func did not resolve, so nothing can be sent: the source's "
                "own first guard (chat_methods.cpp:89)"
            )
            return write_report(report)

        # What the sender will be handed, read back out of the client's own memory.
        Player.SendChatCommand(COMMAND)
        placed = client.bridge.read_data(
            chat.BUFFER_OFFSET, (len(COMMAND) + 2) * 2
        )
        report["buffer"] = placed.decode("utf-16-le", "replace")
        report["buffer_hex"] = placed.hex(" ")

        # ``SendChat`` answers whether it sent, which is the source's own answer; the facade
        # member above is ``void`` because the source's is (``player_bindings.cpp:327``).
        report["sent_again_directly"] = chat.SendChat("/", COMMAND)

        report["note"] = (
            "the client answers /age itself, in its own chat log: the owner can read the line "
            "there. No server traffic and no game state change."
        )

    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
