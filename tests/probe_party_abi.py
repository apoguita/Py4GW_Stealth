"""Read-only probe: what each party action's own function looks like, and how it cleans its stack.

Every member this round has to write ends in one call to a function the catalog already names, and the
port's emitted call forms are **typed by how many words the callee takes and who releases them**. The
sources declare those prototypes (``party_methods.cpp:19-26``), but a declaration is a claim about the
client's own code, and this project has been burned by one before: ``SendFrameUIMessage`` had to be
*live-read as ``ret 0xc``* rather than assumed. So each function is read here — entry bytes, and the
``ret imm16`` at its end — before any stub calls it.

Reads, nothing else: a direct ``ProcessMemoryReader``, no connection, no elevation, nothing called.

Usage: python tests/probe_party_abi.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else "tests/live_reports/party_abi.json"

#: Each resolver the party actions call, with the prototype the sources declare for it.
#: ``(resolver name, declared prototype, source line)``.
FUNCTIONS = (
    (
        "party.set_difficulty_func",
        "void __cdecl(uint32_t flag)",
        "party_methods.cpp:20, 109-117",
    ),
    (
        "party.set_ready_status_func",
        "void __cdecl(uint32_t identifier)",
        "party_methods.cpp:21, 44-52",
    ),
    (
        "party.party_search_seek_func",
        "void __cdecl(uint32_t search_type, const wchar_t* advertisement, uint32_t unk)",
        "party_methods.cpp:19, 467-472",
    ),
    (
        "party.party_search_button_callback_func",
        "void __fastcall(void* context, uint32_t edx, uint32_t* wparam)",
        "party_methods.cpp:20, 213-279",
    ),
    (
        "party.party_window_button_callback_func",
        "void __fastcall(void* context, uint32_t edx, uint32_t* wparam)",
        "party_methods.cpp:30, 200-211",
    ),
    (
        "party.flag_hero_agent_func",
        "void __cdecl(uint32_t agent_id, GamePos* pos)",
        "party_methods.cpp:22, 325-332",
    ),
    (
        "party.flag_all_func",
        "void __cdecl(GamePos* pos)",
        "party_methods.cpp:23, 338-340",
    ),
    (
        "party.set_hero_behavior_func",
        "void __cdecl(uint32_t agent_id, HeroBehavior behavior)",
        "party_methods.cpp:24, 346-359",
    ),
    (
        "party.lock_pet_target_func",
        "bool __cdecl(uint32_t pet_agent_id, uint32_t target_id)",
        "party_methods.cpp:25, 391-413",
    ),
    (
        "party.command_hotkey_disable_ai_func",
        "void __cdecl(uint32_t hero_agent_id, uint32_t zero_based_skill_slot)",
        "party_methods.cpp:26, 361-389",
    ),
)

#: How far into a function to look for the ``ret`` that ends its body. These are short handlers; the
#: scan is bounded so a wrong address cannot make this read a whole section.
SCAN = 0x200


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    module = win32.get_main_module(pid)
    report["module"] = {
        "base": hex(int(module["base_address"])),
        "size": hex(int(module["size"])),
    }

    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(
            reader, int(module["base_address"]), int(module["size"])
        )
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")
        text = scanner.get_section_range("text")
        report["text"] = {"start": hex(text.start), "end": hex(text.end)}

        rows = []
        for name, prototype, source in FUNCTIONS:
            row: dict[str, Any] = {
                "resolver": name,
                "declared": prototype,
                "source": source,
            }
            result = catalog.resolve(name, scanner)
            row["resolved"] = bool(result.ok)
            if not result.ok:
                row["message"] = result.message
                rows.append(row)
                continue
            address = int(result.value)
            row["address"] = hex(address)
            row["in_text"] = bool(text.start <= address < text.end)
            code = reader.read(address, SCAN)
            row["entry"] = code[:16].hex(" ")
            row["ret"] = _epilogue(code)
            row["has_frame_pointer"] = code[:3] == b"\x55\x8b\xec"
            rows.append(row)
        report["functions"] = rows
        report["note"] = (
            "read-only: nothing was called and nothing was written. 'ret' is the first "
            "'ret imm16' (C2 xx xx) or bare 'ret' (C3) in the first "
            f"{SCAN} bytes; a C2 argues for a __fastcall/__thiscall callee that cleans its own "
            "stack, and C3 for one whose caller does."
        )
    finally:
        reader.close()

    return write_report(report)


def _epilogue(code: bytes) -> dict[str, Any]:
    """Return every return-candidate in range, with the bytes before it, so a reader can judge.

    A ``C2``/``C3`` byte is *not* an epilogue by itself: ``e8 18 8b c2 ff`` is a ``call`` whose
    displacement happens to contain ``c2``, and the first version of this probe reported that as a
    ``ret imm16`` with 65535 pops. What tells a real epilogue from a byte in an immediate is what is
    in front of it (``5d``, ``c9``, a restored register) and what follows it (padding, or another
    function's prologue), so all of them are reported rather than the first one being picked.
    """

    candidates = []
    for index, byte in enumerate(code):
        if byte == 0xC2 and index + 2 < len(code):
            pops = int.from_bytes(code[index + 1 : index + 3], "little")
            candidates.append(
                {
                    "kind": "ret imm16",
                    "pops": pops,
                    "at": index,
                    "before": code[max(0, index - 6) : index].hex(" "),
                    "after": code[index + 3 : index + 9].hex(" "),
                }
            )
        elif byte == 0xC3:
            candidates.append(
                {
                    "kind": "ret",
                    "pops": 0,
                    "at": index,
                    "before": code[max(0, index - 6) : index].hex(" "),
                    "after": code[index + 1 : index + 7].hex(" "),
                }
            )
    # A real epilogue is usually the last one before the padding that ends the function, and its
    # `after` is `cc` padding or the next prologue rather than more code.
    likely = [
        candidate
        for candidate in candidates
        if candidate["after"].startswith("cc")
        or candidate["after"].startswith("55 8b")
        or candidate["after"] == ""
    ]
    return {
        "likely": likely[-1] if likely else None,
        "candidates": candidates[:8],
        "count": len(candidates),
    }


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
