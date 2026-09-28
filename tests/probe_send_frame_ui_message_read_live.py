"""Live, **read-only** pre-flight for ``Frame.send_message`` — the five-word frame message call.

``Frame.send_message`` (round 58) resolves the client's own callbacks-based UI sender
(``ui.send_frame_ui_message_func`` — native holds it as ``g_send_frame_ui_message_original``) and calls it
with native's own five words: ``&frame->frame_callbacks``, a null second word, the message id and the
caller's two words (``ui_methods.cpp:1332-1345``). Two parts of that can only be checked against the running
client, and this probe reads both **without writing anything** (``game_thread=False`` — no hook, no patch,
no call):

1. **the resolver answers on this build**, and where the catalog's ``+0x67`` near-call target lands;
2. **the first word's arithmetic is the record's own field** — the bytes at
   ``frame_pointer + FrameStruct.frame_callbacks.offset`` must equal the bytes of the frame record's
   ``frame_callbacks`` field as the record itself reports them. If those two disagree, the address handed to
   the client is not the field native passes, and the write probe must not run.

It also reports the *candidate* ``ret`` sites in the resolved function's first bytes. That is evidence, not
proof — an argument count read by eye out of unaligned bytes is exactly the kind of guess this project does
not act on. The write probe (``tests/probe_send_frame_ui_message_write_live.py``) is what settles the shape:
it makes the call and then checks the client is still healthy.

Usage: python tests/probe_send_frame_ui_message_read_live.py [report-path]
"""

from __future__ import annotations

import json
import sys
from typing import Any

import py4gw
from py4gw.ui.frame import FrameStruct, is_valid_frame_pointer
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: ``Frame.send_message``'s resolver (``offsets/ui.json``, from ``ui_patterns.cpp``).
_SEND_FRAME_UI_MESSAGE_FUNC = "ui.send_frame_ui_message_func"

#: How much of the resolved function to read while looking for its own ``ret``.
_CODE_SCAN_BYTES = 0x200

#: How many frames to open while looking for one that registers callbacks.
_FRAME_SAMPLE = 80


def _ret_sites(code: bytes) -> list[dict[str, Any]]:
    """Return the ``ret`` candidates in a function's first bytes.

    ``C3`` is a plain ``ret`` (cdecl: the caller cleans) and ``C2 imm16`` is ``ret imm16`` (stdcall: the
    callee pops that many bytes, so ``imm16 / 4`` is its argument count). Bytes are not decoded here, so a
    ``C2`` inside another instruction is reported too — the point is to show the evidence, not to conclude
    from it.
    """

    sites: list[dict[str, Any]] = []
    for index in range(len(code) - 2):
        byte = code[index]
        if byte == 0xC3:
            sites.append({"offset": hex(index), "kind": "ret"})
        elif byte == 0xC2:
            immediate = code[index + 1] | (code[index + 2] << 8)
            sites.append(
                {
                    "offset": hex(index),
                    "kind": "ret imm16",
                    "immediate": hex(immediate),
                    "words_if_stdcall": immediate // 4,
                }
            )
        if len(sites) >= 6:
            break
    return sites


def _frames_with_callbacks(client: Any) -> dict[str, Any]:
    """Open a bounded sample of the live frame array and describe the frames that register callbacks."""

    array = client.frame_array
    pointers = array.read_slot_pointers()
    report: dict[str, Any] = {
        "array_size": len(pointers),
        "valid_slots": sum(1 for p in pointers if is_valid_frame_pointer(p)),
        "sampled": 0,
        "with_callbacks": [],
    }
    for frame_id, pointer in enumerate(pointers):
        if not is_valid_frame_pointer(pointer):
            continue
        if report["sampled"] >= _FRAME_SAMPLE:
            break
        report["sampled"] += 1
        frame = array.get(frame_id)
        if frame is None:
            continue
        size = int(frame.frame_callbacks.m_size)
        if size <= 0:
            continue
        # The field's own bytes, read from the record, against the same bytes read at the address
        # `send_message` hands the client (`frame_pointer + FrameStruct.frame_callbacks.offset`).
        field_bytes = bytes(frame.frame_callbacks)
        at_address = client.reader.read(
            pointer + FrameStruct.frame_callbacks.offset, len(field_bytes)
        )
        report["with_callbacks"].append(
            {
                "frame_id": frame_id,
                "pointer": hex(pointer),
                "frame_hash": hex(int(frame.relation.frame_hash_id)),
                "callbacks_size": size,
                "callbacks_buffer": hex(int(frame.frame_callbacks.m_buffer)),
                "first_word": hex(pointer + FrameStruct.frame_callbacks.offset),
                "address_matches_field": at_address == field_bytes,
            }
        )
        if len(report["with_callbacks"]) >= 5:
            break
    return report


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["image"] = process.get("path")
    report["controller_elevated"] = bool(win32.is_elevated())
    report["game_thread"] = False

    with py4gw.connect(process, game_thread=False) as client:
        report["resolves"] = bool(client.resolves(_SEND_FRAME_UI_MESSAGE_FUNC))
        if not report["resolves"]:
            report["error"] = f"{_SEND_FRAME_UI_MESSAGE_FUNC} does not resolve on this build"
            return write_report(report)

        address = int(client._resolve(_SEND_FRAME_UI_MESSAGE_FUNC))
        report["address"] = hex(address)
        code = client.reader.read(address, _CODE_SCAN_BYTES)
        report["first_bytes"] = code[:16].hex(" ")
        report["ret_sites"] = _ret_sites(code)

        report["frames"] = _frames_with_callbacks(client)
        report["note"] = (
            "read-only: game_thread=False installed no hook, no patch and made no call. The write probe is "
            "the run that makes the call itself."
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
