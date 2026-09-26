"""Read-only probe: what every call target actually is, before anything is called.

On 2026-09-25 the client died with ``eip=462fd617`` while this port was calling
``chat.send_chat_func``: the dispatcher called an address that is not code, and the address it
called had been written into the call table by the host. The host now refuses a target outside the
client's code section (``ConnectedClient._descriptor_slot``), which stops that crash from being
possible — but a refusal is not a diagnosis, and the diagnosis is a **read**: which address does
each resolver answer with, which section is it in, and does it look like a function.

That is all this probe does. It resolves names, prints the resolver's own step-by-step trace, and
reads the bytes at the answer. **No client function is called, nothing is written into the
client, and no hook is placed**: the connection is the read-only one (``game_thread=False``), so
this probe cannot put code in the client even by accident.

Usage: (elevated) python tests/probe_resolver_targets.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The names to look at: the chat senders this port now calls, and the ones the dialog module
#: uses, so a wrong one shows up beside a right one.
NAMES = (
    "chat.send_chat_func",
    "chat.add_to_chat_log_func",
    "chat.recv_whisper_func",
    "ui.send_ui_message_func",
    "ui.validate_async_decode_str_func",
    "agent.send_agent_dialog_func",
    "game_thread.leave_game_thread_func",
)

#: The entry shapes a client function has on this build, and how many bytes to read at a target.
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")
HEAD_BYTES = 32


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    with py4gw.connect(process, game_thread=False) as client:
        scanner = client._scanner  # type: ignore[attr-defined]
        text = scanner.get_section_range("text")
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}

        rows = []
        for name in NAMES:
            row: dict[str, Any] = {"name": name}
            try:
                result = client._patterns.resolve(name, scanner)  # type: ignore[attr-defined]
            except Exception as error:  # noqa: BLE001 - reported, not raised
                row["error"] = f"{type(error).__name__}: {error}"
                rows.append(row)
                continue

            row["ok"] = bool(result.ok)
            row["value"] = hex(int(result.value))
            row["in_text"] = bool(text.start <= int(result.value) < text.end)
            row["trace"] = [
                {
                    "step": step.name,
                    "op": step.operation,
                    "in": hex(step.input_value),
                    "out": hex(step.output_value),
                    "ok": bool(step.ok),
                    "detail": step.detail,
                }
                for step in result.trace
            ]
            if result.value:
                head = client.reader.read(int(result.value), HEAD_BYTES)
                row["head"] = head.hex(" ")
                row["looks_like_a_function"] = any(
                    head.startswith(prefix) for prefix in ENTRY_PREFIXES
                )
                row["starts_with_jmp"] = head[:1] == b"\xe9"
            rows.append(row)

        report["targets"] = rows
        report["note"] = (
            "read-only: no client function was called and nothing was written. A target whose "
            "in_text is false, or whose head is not a prologue or a jmp, is a resolver finding."
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
