"""Read-only probe: who holds each of the four entry points this project and Reforged share.

Reforged Native hooks the client through MinHook, and the four functions it hooks are the four this
project patches (``game_thread.cpp:76``, ``ui.cpp:725``, ``effects.cpp:142``, ``render.cpp:136``). On
this 32-bit build MinHook's entry patch is a five-byte ``jmp rel32`` straight to its detour — the relay
is x64 only (``third_party/minhook/src/trampoline.c:307-313``) — and that detour is compiled code in
Reforged's own module. So the question "who owns this entry" has three answers, and they are told apart
by reading bytes:

- the client's own prologue (nothing is hooked there),
- this project's generated stub — its jump lands on code that begins ``9C 60 B8`` (``pushfd``,
  ``pushad``, ``mov eax, imm32``; ``hooker.STUB_PROLOGUE``),
- another runtime's hook — its jump lands on compiled code that does not begin that way.

**Nothing is written, nothing is called and no hook is placed.** The reads use a read-only process
handle, so this probe runs unelevated; ``py4gw.connect`` is deliberately not used, because it asserts
elevation even for its read-only connection. The decision it reports is the shipping one: the last test
calls the real ``ConnectedClient._is_our_stale_patch`` on the live bytes, so what it prints is what a
``connect()`` would do, not a model of it.

Usage::

    python tests/probe_two_runtimes_live.py [report-path.json] [--pid PID]
"""

from __future__ import annotations

import ctypes
import json
import struct
import sys
from typing import Any, cast

from py4gw.client import (
    _EFFECTS_HOOK,
    _EFFECTS_HOOK_BYTES,
    _GAME_THREAD_HOOK,
    _GAME_THREAD_HOOK_BYTES,
    _GAME_THREAD_OBSERVE,
    _GAME_THREAD_OBSERVE_BYTES,
    _RENDER_HOOK,
    _RENDER_HOOK_BYTES,
    ConnectedClient,
)
from py4gw.game_thread.hooker import STUB_PROLOGUE, is_generated_stub
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.scanner.scanner import Pattern
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

#: The four entry points, as the connection itself declares them: the catalog name it resolves and the
#: entry bytes it checks before writing anything.
TARGETS = (
    (_GAME_THREAD_HOOK, _GAME_THREAD_HOOK_BYTES),
    (_GAME_THREAD_OBSERVE, _GAME_THREAD_OBSERVE_BYTES),
    (_EFFECTS_HOOK, _EFFECTS_HOOK_BYTES),
    (_RENDER_HOOK, _RENDER_HOOK_BYTES),
)

#: ``jmp rel32``, ``jmp rel8``, and ``jmp dword ptr [imm32]``: the three patches a hooking engine
#: writes at an entry. MinHook uses the first (``hook.c:355``, ``trampoline.h:43-47``).
JMP_REL32 = 0xE9
JMP_REL8 = 0xEB
JMP_ABS32 = (0xFF, 0x25)

#: A compiled function's prologue on this build: ``push ebp; mov ebp, esp``, sometimes behind the
#: ``mov edi, edi`` hot-patch prefix.
COMPILED_PREFIXES = (b"\x55\x8b\xec", b"\x8b\xff\x55\x8b\xec")

HEAD_BYTES = 16

#: How far ahead of a resolver's answer to look for an entry jump another runtime placed there. The
#: resolver answered the function *before* its target, so the target's entry is a short way ahead — the
#: same window ``ConnectedClient._stale_patch_before`` walks.
AHEAD_WINDOW = 0x2000

#: ``kernel32``/``psapi``, for naming the module a jump lands in. Loaded lazily so importing this probe
#: stays cheap, and used read-only: ``EnumProcessModulesEx`` and ``VirtualQueryEx`` need only
#: ``PROCESS_QUERY_INFORMATION | PROCESS_VM_READ``, which an unelevated shell has.
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
LIST_MODULES_ALL = 0x03

#: ``MEMORY_BASIC_INFORMATION``'s type field: which of these a region is.
MEMORY_TYPES = {0x1000000: "MEM_IMAGE (a loaded module)", 0x20000: "MEM_PRIVATE (allocated)"}


class MODULEINFO(ctypes.Structure):
    """``MODULEINFO``, for the base and size of every loaded module."""

    _fields_ = (
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", ctypes.c_uint32),
        ("EntryPoint", ctypes.c_void_p),
    )


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    """``MEMORY_BASIC_INFORMATION``, for what kind of memory an address sits in."""

    _fields_ = (
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    )


psapi.EnumProcessModulesEx.argtypes = (
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_uint32,
)
psapi.GetModuleInformation.argtypes = (
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(MODULEINFO),
    ctypes.c_uint32,
)
psapi.GetModuleFileNameExW.argtypes = (
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_wchar_p,
    ctypes.c_uint32,
)


class ReadOnlyAccess:
    """The one call ``ConnectedClient._is_our_stale_patch`` makes, over a read-only handle."""

    def __init__(self, reader: ProcessMemoryReader) -> None:
        self._reader = reader

    def read(self, address: int, size: int) -> bytes:
        return self._reader.read(address, size)


def module_for(pid: int, address: int, modules: list[tuple[int, int, str]]) -> str:
    """Return the name of the module whose mapped range contains ``address``.

    A range that no module covers is not "unknown": it is memory somebody *allocated*, which is what a
    hook engine's own stub or trampoline buffer looks like. The two are told apart here because they
    mean different things — a jump into a loaded DLL is another runtime's detour, a jump into an
    anonymous allocation is another runtime's generated code.
    """

    for base, size, name in modules:
        if base <= address < base + size:
            return name
    return "no loaded module: an allocated region"


def loaded_modules(pid: int) -> list[tuple[int, int, str]]:
    """Return ``(base, size, path)`` for every module loaded in the target, read-only."""

    import ctypes
    from ctypes import wintypes

    process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not process:
        return []
    try:
        needed = wintypes.DWORD()
        psapi.EnumProcessModulesEx(
            process, None, 0, ctypes.byref(needed), LIST_MODULES_ALL
        )
        count = needed.value // ctypes.sizeof(wintypes.HMODULE)
        if not count:
            return []
        array = (wintypes.HMODULE * count)()
        if not psapi.EnumProcessModulesEx(
            process, array, ctypes.sizeof(array), ctypes.byref(needed), LIST_MODULES_ALL
        ):
            return []
        info = MODULEINFO()
        modules = []
        for handle in array:
            if not psapi.GetModuleInformation(
                process, handle, ctypes.byref(info), ctypes.sizeof(info)
            ):
                continue
            buffer = ctypes.create_unicode_buffer(1024)
            psapi.GetModuleFileNameExW(process, handle, buffer, 1024)
            modules.append(
                (int(info.lpBaseOfDll), int(info.SizeOfImage), buffer.value)
            )
        return modules
    finally:
        kernel32.CloseHandle(process)


def region_for(pid: int, address: int) -> dict[str, Any]:
    """Return what ``VirtualQueryEx`` says about the region containing ``address``.

    ``MEM_IMAGE`` (0x1000000) is a file-backed image, so the address is inside a loaded module;
    ``MEM_PRIVATE`` (0x20000) is memory somebody allocated in the target — which is what a hooking
    engine's own stub, trampoline or relay buffer is.
    """

    import ctypes
    from ctypes import wintypes

    process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not process:
        return {"error": "could not open the target for query"}
    try:
        info = MEMORY_BASIC_INFORMATION()
        written = kernel32.VirtualQueryEx(
            process, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info)
        )
        if not written:
            return {"error": "VirtualQueryEx answered nothing"}
        return {
            "allocation_base": hex(int(info.AllocationBase)),
            "type": MEMORY_TYPES.get(int(info.Type), hex(int(info.Type))),
            "protection": hex(int(info.Protect)),
            "size": int(info.RegionSize),
        }
    finally:
        kernel32.CloseHandle(process)


def classify(head: bytes) -> str:
    """Say what the bytes at an address are, in the terms this project's decision uses."""

    if head[: len(STUB_PROLOGUE)] == STUB_PROLOGUE:
        return "this project's generated stub"
    if head[:1] == bytes((JMP_REL32,)):
        return "a jmp rel32"
    if head[:1] == bytes((JMP_REL8,)):
        return "a jmp rel8"
    if head[:2] == bytes(JMP_ABS32):
        return "a jmp [imm32]"
    if any(head.startswith(prefix) for prefix in COMPILED_PREFIXES):
        return "a compiled function's prologue"
    return "unrecognised"


def jump_destination(address: int, head: bytes) -> int:
    """Return where the ``jmp rel32`` at ``address`` lands."""

    return (address + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF


def decide_entries(
    pid: int,
    reader: ProcessMemoryReader,
    scanner: RemoteScanner,
    catalog: PatternCatalog,
    modules: list[tuple[int, int, str]],
    module_base: int,
    module_size: int,
) -> list[dict[str, Any]]:
    """Drive the connection's own placement decision on the live bytes, one entry at a time.

    The decision is the shipping one, driven method by method on the live bytes, in the order
    ``ConnectedClient._prepare_target`` drives them, so what these rows say is what a ``connect()``
    would do rather than a model of it. A bare instance is enough: the methods consulted read the two
    module words, the pattern catalog, the scanner and the access object, and nothing else.
    """

    decision = object.__new__(ConnectedClient)
    decision._pid = pid
    decision._module_base = module_base
    decision._module_size = module_size
    decision._patterns = catalog
    decision._scanner = scanner

    access = cast("WriteAccess", ReadOnlyAccess(reader))
    rows: list[dict[str, Any]] = []
    for name, entry_bytes in TARGETS:
        row: dict[str, Any] = {"name": name, "expected_entry": entry_bytes.hex(" ")}
        try:
            address, anchor = decision._resolve_placement(name)
        except RuntimeError as error:
            row["resolved"] = False
            row["message"] = str(error)
            rows.append(row)
            continue
        row["resolved"] = True
        row["message"] = ""
        row["walked_back_from"] = hex(anchor) if anchor else None

        row["address"] = hex(address)
        row["in_module"] = bool(module_base <= address < module_base + module_size)
        row["head"] = reader.read(address, HEAD_BYTES).hex(" ")
        head = bytes.fromhex(row["head"])
        row["entry_is"] = classify(head)
        row["entry_is_original"] = head[: len(entry_bytes)] == entry_bytes

        if head[:1] == bytes((JMP_REL32,)):
            landing = jump_destination(address, head)
            landing_head = reader.read(landing, HEAD_BYTES)
            row["landing"] = hex(landing)
            row["landing_inside_the_client_module"] = bool(
                module_base <= landing < module_base + module_size
            )
            row["landing_module"] = module_for(pid, landing, modules)
            row["landing_region"] = region_for(pid, landing)
            row["landing_head"] = landing_head.hex(" ")
            row["landing_is"] = classify(landing_head)

        decision_anchor = anchor
        ahead = decision._entry_jump_ahead(access, address, len(entry_bytes), limit=anchor or 0)
        if ahead is not None:
            patch_address, ahead_is_ours = ahead
            row["entry_jump_ahead"] = {
                "address": hex(patch_address),
                "is_this_project": ahead_is_ours,
            }
            if not ahead_is_ours:
                ahead_head = reader.read(patch_address, len(entry_bytes))
                row["entry_jump_ahead"]["declared_tail_matches"] = (
                    decision._jump_covers_part_of_declared_entry(ahead_head, entry_bytes)
                )

        if row["entry_is_original"]:
            row["this_project_would"] = "place its own patch on the client's own bytes"
        elif decision._is_our_stale_patch(access, address, head):
            row["this_project_would"] = (
                "repair its own stale patch, then place on the client's own bytes"
            )
        elif decision._is_foreign_patch_on_the_declared_function(
            head, entry_bytes, decision_anchor, found_by_the_walk=False
        ):
            row["this_project_would"] = (
                "CHAIN on top of another runtime's entry jump here (in place)"
            )
        elif row.get("entry_jump_ahead") and not row["entry_jump_ahead"]["is_this_project"]:
            ahead_address = int(row["entry_jump_ahead"]["address"], 16)
            ahead_head = reader.read(ahead_address, len(entry_bytes))
            if decision._is_foreign_patch_on_the_declared_function(
                ahead_head, entry_bytes, decision_anchor, found_by_the_walk=True
            ):
                row["this_project_would"] = (
                    "CHAIN on top of another runtime's entry jump, at the declared function "
                    f"found ahead (0x{ahead_address:08X})"
                )
            else:
                row["this_project_would"] = (
                    "REFUSE: a jump ahead of the answer whose bytes do not match this catalog's "
                    "declared entry"
                )
        else:
            row["this_project_would"] = (
                "REFUSE: the entry is not a jump and not the bytes this build's catalog "
                "declares, and no usable entry jump was found ahead of the answer either"
            )
        rows.append(row)
    return rows


def placement_is_safe(rows: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Whether ``py4gw.connect`` would proceed, and what it would do at each entry.

    True when every entry is one the connection places on, repairs, or chains on top of — the outcomes
    ``ConnectedClient._prepare_target`` can reach. A ``REFUSE`` row, or an entry the resolver could not
    answer, is the connection's own refusal; this reports it rather than forming a second opinion.
    """

    decisions = [
        f"{row['name']}: {row.get('this_project_would') or row.get('message') or 'unresolved'}"
        for row in rows
    ]
    refused = [
        row
        for row in rows
        if not row.get("resolved") or str(row.get("this_project_would", "")).startswith("REFUSE")
    ]
    return (not refused, decisions)


def connectable(win32: Win32, pid: int) -> tuple[bool, list[str]]:
    """Answer, read-only, whether ``py4gw.connect`` would proceed on one client.

    This is the gate an acting probe wants before it opens the write path: the arrangement the owner
    runs has Reforged injected, so an entry that is not the client's own bytes is the ordinary case and
    connect chains on it. Only the decisions ``_prepare_target`` would refuse at come back ``False``.
    """

    module = win32.get_main_module(pid)
    module_base = int(module["base_address"])
    module_size = int(module["size"])
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, module_base=module_base, module_size=module_size)
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")
        rows = decide_entries(
            pid, reader, scanner, catalog, loaded_modules(pid), module_base, module_size
        )
        return placement_is_safe(rows)
    finally:
        reader.close()


def main() -> int:
    argv = [argument for argument in sys.argv[1:] if not argument.startswith("--pid")]
    pid_argument = next(
        (argument.split("=", 1)[1] for argument in sys.argv[1:] if argument.startswith("--pid=")),
        "",
    )
    report_path = argv[0] if argv else ""

    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report, report_path)

    process = next(
        (
            candidate
            for candidate in clients
            if pid_argument and int(candidate["pid"]) == int(pid_argument)
        ),
        clients[0],
    )
    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    module_base = int(module["base_address"])
    module_size = int(module["size"])
    report["pid"] = pid
    report["image"] = process.get("path") or process.get("image_path")
    report["module"] = {"base": hex(module_base), "size": hex(module_size)}
    report["probe"] = "read-only: no client function was called and nothing was written"

    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(
            reader, module_base=module_base, module_size=module_size
        )
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")

        modules = loaded_modules(pid)
        report["loaded_modules"] = [
            {"name": name, "base": hex(base), "size": hex(size)}
            for base, size, name in modules
        ]

        # The connection's own decision, driven on the live bytes by the shipping methods — the same
        # function the acting probes gate on before they open the write path (``connectable``).
        rows = decide_entries(
            pid, reader, scanner, catalog, modules, module_base, module_size
        )

        # The declared entry bytes are searched for independently of the resolver. If they are in
        # ``.text`` somewhere else, the resolver's anchor answered the wrong function on this build; if
        # they are nowhere, this client build differs from the one the catalog was pinned against. The
        # two need different work, and only a search tells them apart.
        found = []
        for name, entry_bytes in TARGETS:
            entry: dict[str, Any] = {
                "name": name,
                "declared": entry_bytes.hex(" "),
                "hits": [],
            }
            pattern = Pattern(entry_bytes, "x" * len(entry_bytes))
            for hit in scanner.find_all(pattern, "text", limit=5):
                entry["hits"].append(
                    {"address": hex(hit), "head": reader.read(hit, HEAD_BYTES).hex(" ")}
                )
            entry["count"] = len(entry["hits"])
            found.append(entry)
        report["declared_bytes_search"] = found

        # A resolver whose pattern walks back to a function start (``to_function_start``) answers the
        # function *before* the target when the target's prologue has been replaced by another
        # runtime's entry jump — the same effect this project's own stale patch has on it, documented in
        # ``client.py``'s ``_prepare_target``. So the window ahead of the answer is walked for entry
        # jumps, and each candidate is classified by where it lands. This is the read-only half of the
        # walk ``ConnectedClient`` does, over the live bytes.
        found = []
        for row in rows:
            if "address" not in row:
                continue
            start = int(row["address"], 16)
            window = reader.read(start, AHEAD_WINDOW)
            candidates = []
            for offset in range(len(window) - 5):
                if window[offset] != JMP_REL32:
                    continue
                candidate = start + offset
                head = window[offset : offset + HEAD_BYTES]
                landing = jump_destination(candidate, head)
                try:
                    lands_on_us = is_generated_stub(
                        reader.read(landing, len(STUB_PROLOGUE))
                    )
                except OSError:
                    # A landing that cannot be read is not this project's code, and saying so is the
                    # same answer ``ConnectedClient._is_our_stale_patch`` gives for it.
                    lands_on_us = False
                candidates.append(
                    {
                        "address": hex(candidate),
                        "bytes": head[:5].hex(" "),
                        "landing": hex(landing),
                        "landing_module": module_for(pid, landing, modules),
                        "lands_on_this_project": lands_on_us,
                    }
                )
                if len(candidates) >= 8:
                    break
            found.append({"name": row["name"], "from": hex(start), "candidates": candidates})
        report["jumps_ahead_of_the_answer"] = found

        report["targets"] = rows
        report["verdict"] = verdict(rows)
    finally:
        reader.close()

    return write_report(report, report_path)


def verdict(rows: list[dict[str, Any]]) -> str:
    """Say which of the three states the client is in, from what the rows found."""

    def action(row: dict[str, Any]) -> str:
        return str(row.get("this_project_would", ""))

    chained = [row for row in rows if action(row).startswith("CHAIN")]
    refused = [row for row in rows if action(row).startswith("REFUSE")]
    plain = [
        row
        for row in rows
        if action(row).startswith(("place", "repair"))
    ]
    if refused:
        return (
            f"{len(refused)} of {len(rows)} entries cannot be placed on: this project refuses those "
            "and writes nothing there."
        )
    if chained:
        return (
            f"another runtime holds {len(chained)} of {len(rows)} entries: this project chains on top "
            "of each of them, relocating the jump it displaces, and the restore puts those bytes back."
        )
    if plain:
        return "all four entries hold the bytes this project patches: it may connect first."
    return "no entry can be placed on: see the rows."


def write_report(report: dict[str, Any], path: str) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
