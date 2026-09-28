"""Read-only probe: the render entry's own bytes, which the capture hook needs.

The DX-context capture (`docs/TARGET_SIDE_WORK.md`) hooks the client's ``EndScene`` and keeps its first
argument — native's own ``Context::g_dx_context = ctx`` (``render.cpp:88``). A hook here displaces at least
five bytes of **whole instructions** at the entry (``hooker.py:615-619``), and the trampoline replays exactly
those bytes from another address — so the displaced span is a property of this client build and is not
something to guess. This port pins its other three hooks the same way (``55 8B EC 81 EC 20 02 00 00`` for the
game thread, ``55 8B EC 8B 45 08 83 F8 56`` for the message sender), and a probe like this one is how those
numbers were obtained: resolve the target, read its head, and show it.

**Nothing is called, nothing is written and no hook is placed**: the connection is the read-only one
(``game_thread=False``), so this probe cannot put code in the client even by accident.

The three render names are looked at together because they share a pattern family (``offsets/render.json``):
``end_scene_func`` is the capture's target, ``reset_func`` the same capture's second target in native, and
``screen_capture_func`` is there so a wrong answer shows up beside the right ones.

Usage: (elevated) python tests/probe_render_entry.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The render targets, as the catalog names them.
NAMES = (
    "render.end_scene_func",
    "render.reset_func",
    "render.screen_capture_func",
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
            "read-only: no client function was called and nothing was written. The bytes at "
            "render.end_scene_func are what its hook must displace — at least five of them, ending on an "
            "instruction boundary — and they are pinned as a constant the way the other three hooks' are."
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
