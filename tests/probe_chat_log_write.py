"""Live probe: write one line into the client's own chat log, and read it back.

This is the first bounded test of the chat-log write path — `GW::chat::WriteChat` /
`WriteChatEnc` (`chat_methods.cpp:156-202`), reached from `Player.SendFakeChat`. It exists because
that path's first live use crashed the client on 2026-09-26, and the crash named the fault exactly:
the port passed a *pointer to* a `UIChatMessage` where the UI-message form hands the client two
payload **words** (``payload.py:645-669``), so the client read ``0`` as the message and asserted its
own null check (`CtChatLog.cpp:765`, inside `AddToChatLog` — `FUN_00825830`). The crash trace also
settled the field order: the client took payload word 0 as the channel and word 1 as the message, so
the call now passes ``(channel, message_address)``.

What it does, in order: connect (which installs the capability layer and restores it on exit), read
the chat log's length, call ``Player.SendFakeChat(channel, marker)`` **once**, wait for the marker to
appear in the client's own log, and report what the client holds. Nothing is sent to the server —
`SendFakeChat` writes to this client's log only — and the channel is 1 rather than 7, because the
client's own `AddToChatLog` skips the append for channel 7.

Usage: (elevated) python tests/probe_chat_log_write.py [report-path]
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import py4gw
from py4gw.player import Player
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The line to write, and the channel to write it on. The channel is 1 because the client's own
#: ``AddToChatLog`` does not append a line whose channel is 7 (``if (param_2 != 7)``).
MARKER = "py4gw port smoke test"
CHANNEL = 1

#: How long to wait for the client's log to hold the line, and how often to look.
WAIT_S = 5.0
POLL_S = 0.25


def _log_texts(client: Any) -> list[str]:
    """The messages the client's own chat log holds, newest last.

    The log is the ``0x80C`` ring buffer the ported context reads: ``ChatBufferStruct.messages`` is
    the slot table, ``message_records`` walks the non-null slots into ``ChatMessageStruct`` headers,
    and the payload itself is read by ``ChatMessageStruct.message_str`` — it is a variable-length
    encoded UTF-16 string that follows the header in the target
    (``py4gw/context/chat_buffer_context.py``).
    """

    buffer = client.read_chat_buffer()
    if buffer is None:
        return []
    texts: list[str] = []
    for record in buffer.message_records:
        try:
            texts.append(record.message_str)
        except (RuntimeError, OSError):
            texts.append("")
    return texts


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
        report["module_base"] = hex(client._module_base)  # type: ignore[attr-defined]
        before = _log_texts(client)
        report["log_before"] = len(before)

        started = time.monotonic()
        Player.SendFakeChat(CHANNEL, MARKER)
        report["call_seconds"] = round(time.monotonic() - started, 3)

        found = False
        deadline = time.monotonic() + WAIT_S
        after: list[str] = before
        while time.monotonic() < deadline:
            after = _log_texts(client)
            if any(MARKER in text for text in after):
                found = True
                break
            time.sleep(POLL_S)

        report["marker_in_log"] = found
        report["log_after"] = len(after)
        report["newest_lines"] = [text for text in after[len(before) :]][-4:]
        report["note"] = (
            "read from the client's own chat log through its chat-buffer context. The line is "
            "written locally; SendFakeChat sends nothing to the server. `with py4gw.connect(...)` "
            "restores the client on exit (listener stopped, both hooked entries back, block freed)."
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
