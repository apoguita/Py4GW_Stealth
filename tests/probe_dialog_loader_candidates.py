"""Read-only probe: identify this build's ``DialogLoader_GetText`` from the client's own bytes.

``ResolveDialogLoaderGetText`` rebases one hardcoded address (``DIALOG_LOADER_GETTEXT``,
``dialog.h:99``) and calls it without reading anything at it. On build 38888 that address is
**stale**: rebased it lands inside another function, and calling it faulted the client on
2026-09-25 (``docs/RESEARCH.md``). The port therefore refuses it and answers the sources' own
"no loader" value, which leaves a catalog dialog's ``content`` empty.

Everything gathered so far is in ``RESEARCH.md``: 58 handler pointers and 481 call targets did not
identify it, and the client's own assertion strings are there but **none is referenced by a
``push imm32``**. That last one is where this probe starts, because ``find_use_of_string`` looks
for the literal's *address* in a code section rather than for one instruction form — the mechanism
the eight DAT resolvers already use (``docs/RESEARCH.md``, 2026-09-25).

Three signals, all read-only, and each is independent:

1. **Which function references a dialog anchor.** The anchors are the client's own assertion
   expressions and source paths from its dialog module (``dialog < DIALOGS``,
   ``dialog < arrsize(s_floatingDialogs)``, ``DialogGetFrame(frame, dialog)``, ``DlgKey.cpp`` …).
   The function that asserts a dialog index is in range while looking one up is dialog code, and
   this names it.
2. **Which function touches the resolved dialog table.** The table the port already resolves —
   0x24-byte rows of ``event_handler, name, flags, content_id, property_id`` — has its base
   embedded in whatever code indexes it. A function whose immediates land on that base is a
   candidate for the loader whatever its entry looks like.
3. **What sits around the stale address.** ``0x0079EEF0`` rebased is inside a function; if the
   dialog module merely moved, the loader is among that function's neighbours, so every prologue
   within a window of it is listed.

Nothing is called, nothing is written, and no address is executed.

Usage: (elevated) python tests/probe_dialog_loader_candidates.py [report-path]
"""

from __future__ import annotations

import json
import re
import struct
import sys
from typing import Any

import py4gw
from py4gw import dialog
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The addresses the sources carry for the dialog module, module-relative (``dialog.h:94-99``).
SOURCES_IMAGE_BASE = 0x00400000
DIALOG_LOADER_GETTEXT = 0x0079EEF0

#: The client's own dialog strings, as the previous probe found them. The assertion expressions
#: are the distinctive ones: a function that asserts a dialog index is dialog code.
ANCHORS = (
    "dialog < DIALOGS",
    "dialog < arrsize(s_floatingDialogs)",
    "dialog < GM_INT_TEMPLATES_DIALOGS",
    "DialogGetFrame(frame, dialog)",
    "ArenaNet_Dialog_Class",
    "P:\\Code\\Gw\\Ui\\Dialog\\DlgKey.cpp",
    "P:\\Code\\Gw\\Ui\\Dialog\\DlgCustomize.cpp",
)

#: How many uses of each anchor to look for, how much of a function to scan for immediates, and
#: how far around the stale address to look for prologues.
ANCHOR_USES = 16
FUNCTION_BYTES = 0x600
NEIGHBOUR_WINDOW = 0x600

ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")

#: The prologue the neighbours are found by, and how many of them to list.
PROLOGUE = b"\x55\x8b\xec"
PROLOGUE_LIMIT = 40

#: How much of a section to read at a time, and what a client source path looks like.
CHUNK = 0x100000
PATH = re.compile(rb"P:\\Code\\[ -~]{3,96}?\.(?:cpp|h)")
#: A class- or type-like name that mentions loading or dialog text: what the sources call the
#: module's own ``DialogLoader``, and anything named for a dialog's text.
NAME = re.compile(
    rb"[A-Za-z_][A-Za-z0-9_]{2,40}(?:Loader|Load|Dialog|Dlg)[A-Za-z0-9_]{0,40}"
    rb"|(?:Loader|Dialog|Dlg)[A-Za-z0-9_]{2,40}"
)

#: The band of string-table indices every dialog text this project has measured falls in: the
#: live body at 99942, its two buttons at 99994 and 99946. A run of dwords in it is a table of
#: dialog text references.
BAND_LOW = 99000
BAND_HIGH = 101000
RUN_LENGTH = 8


def rebase(module_base: int, address: int) -> int:
    """Return a module-relative address as this build's runtime address."""

    return module_base + (address - SOURCES_IMAGE_BASE)


def immediates(code: bytes, base: int) -> list[tuple[int, int]]:
    """Every four-byte value in ``code`` that could be an address, as ``(offset, value)``."""

    found: list[tuple[int, int]] = []
    for index in range(0, max(0, len(code) - 4)):
        value = struct.unpack_from("<I", code, index)[0]
        if 0x00400000 <= value < 0x10000000:
            found.append((base + index, int(value)))
    return found


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
        module = win32.get_main_module(client.pid)
        module_base = int(module["base_address"])
        module_size = int(module["size"])
        report["module"] = {"base": hex(module_base), "size": hex(module_size)}

        reader = client.reader
        scanner = client._scanner  # type: ignore[attr-defined]
        sections = scanner.initialize()
        report["sections"] = {
            name: {"start": hex(area.start), "end": hex(area.end)}
            for name, area in sorted(sections.items())
        }
        text = scanner.get_section_range("text")
        rdata = scanner.get_section_range("rdata")

        tables = client.dialog_tables
        addrs = tables.get()
        if not addrs.event_handler_base:
            report["error"] = "the dialog tables did not resolve"
            return write_report(report)

        rows = (dialog.MAX_DIALOG_ID + 1) * dialog.FLAGS_STRIDE
        table = {
            "event_handler_base": hex(addrs.event_handler_base),
            "flags_base": hex(addrs.flags_base),
            "rows": dialog.MAX_DIALOG_ID + 1,
            "stride": dialog.FLAGS_STRIDE,
            "range": [
                hex(addrs.event_handler_base - 0x1000),
                hex(addrs.event_handler_base + rows + 0x1000),
            ],
        }
        report["dialog_table"] = table
        table_start = addrs.event_handler_base - 0x1000
        table_end = addrs.event_handler_base + rows + 0x1000

        # -- signal 1: the functions that reference the client's own dialog strings -----------
        anchors: dict[str, Any] = {}
        functions: dict[int, dict[str, Any]] = {}
        for anchor in ANCHORS:
            uses: list[dict[str, Any]] = []
            for occurrence in range(ANCHOR_USES):
                site = scanner.find_nth_use_of_string(anchor, occurrence)
                if site is None:
                    break
                if not (text.start <= site < text.end):
                    continue
                entry = scanner.to_function_start(site)
                if entry is None:
                    continue
                function = functions.setdefault(
                    entry, {"anchors": [], "entries": []}
                )
                function["anchors"].append(anchor)
                function["entries"].append(hex(entry))
                uses.append({"site": hex(site), "function": hex(entry)})
            anchors[anchor] = {"uses": uses}
        report["anchors"] = anchors

        # -- signal 2: the functions whose immediates land on the resolved dialog table --------
        table_functions: dict[int, list[str]] = {}
        for entry in sorted(functions):
            code = read_code(reader, entry, FUNCTION_BYTES)
            for at, value in immediates(code, entry):
                if table_start <= value < table_end:
                    table_functions.setdefault(entry, []).append(
                        f"{hex(at)} -> {hex(value)}"
                    )
        report["anchor_functions"] = [
            {
                "entry": hex(entry),
                "head": head(reader, entry),
                "anchors": sorted(set(info["anchors"])),
                "table_immediates": table_functions.get(entry, []),
                "near_stale_address": abs(entry - rebase(module_base, DIALOG_LOADER_GETTEXT))
                <= NEIGHBOUR_WINDOW,
            }
            for entry, info in sorted(functions.items())
        ]

        # -- signal 2, widened: every function in the text section is too much, so the table
        # reference is looked for directly by the *value* the code would embed, which is the
        # table's own base. Its users are the functions that index dialogs.
        table_users: list[dict[str, Any]] = []
        for name, base in (
            ("event_handler_base", addrs.event_handler_base),
            ("flags_base", addrs.flags_base),
            ("frame_type_base", addrs.frame_type_base),
        ):
            for occurrence in range(8):
                site = scanner.find_nth_use_of_address(base, occurrence)
                if site is None:
                    break
                entry = scanner.to_function_start(site)
                table_users.append(
                    {
                        "column": name,
                        "site": hex(site),
                        "function": hex(entry) if entry else None,
                        "head": head(reader, entry) if entry else None,
                        "in_text": bool(text.start <= site < text.end),
                    }
                )
        report["table_users"] = table_users

        # -- signal 3: the neighbours of the stale address -------------------------------------
        stale = rebase(module_base, DIALOG_LOADER_GETTEXT)
        stale_entry = scanner.to_function_start(stale)
        window_start = max(text.start, stale - NEIGHBOUR_WINDOW)
        window_end = min(text.end, stale + NEIGHBOUR_WINDOW)
        code = read_code(reader, window_start, window_end - window_start)
        prologues: list[dict[str, Any]] = []
        index = 0
        while len(prologues) < PROLOGUE_LIMIT:
            found = code.find(PROLOGUE, index)
            if found < 0:
                break
            address = window_start + found
            prologues.append(
                {
                    "address": hex(address),
                    "head": head(reader, address),
                    "contains_stale": bool(
                        stale_entry and address == stale_entry
                    ),
                }
            )
            index = found + 1
        report["stale"] = {
            "rebased": hex(stale),
            "function": hex(stale_entry) if stale_entry else None,
            "window": [hex(window_start), hex(window_end)],
            "prologues": prologues,
        }
        if stale_entry:
            stale_code = read_code(reader, stale_entry, FUNCTION_BYTES)
            report["stale"]["function_head"] = head(reader, stale_entry)
            report["stale"]["function_immediates"] = [
                {"at": hex(at), "value": hex(value)}
                for at, value in immediates(stale_code, stale_entry)
                if table_start <= value < table_end or rdata.start <= value < rdata.end
            ][:24]

        # -- signal 5: every dialog source path the client carries, and what references it -----
        # ``probe_dialog_strings.py`` found the paths but only looked for ``push imm32``, and none
        # of the assertions is loaded that way. This asks the question the other way round: for
        # *every* ``P:\Code\`` path in the data section, which code references it at all. A file
        # named after loading a dialog would answer this work item on its own.
        paths = source_paths(reader, rdata)
        report["source_paths"] = paths
        path_anchors: dict[str, Any] = {}
        for path in paths:
            uses: list[dict[str, Any]] = []
            for occurrence in range(ANCHOR_USES):
                site = scanner.find_nth_use_of_string(path, occurrence)
                if site is None:
                    break
                if not (text.start <= site < text.end):
                    continue
                entry = scanner.to_function_start(site)
                if entry is None:
                    continue
                uses.append({"site": hex(site), "function": hex(entry)})
                info = functions.setdefault(entry, {"anchors": [], "entries": []})
                info["anchors"].append(path)
                info["entries"].append(hex(entry))
            if uses:
                path_anchors[path] = uses
        report["path_anchors"] = path_anchors

        # -- signal 6: the client's own names for things, and who references them ---------------
        # The dialog source paths turned out to be UI dialogs (options, key bindings, timeout) and
        # the login screen, none of which is a text loader. What has not been asked is the other
        # direction: the client carries its own **class and type names** (``ArenaNet_Dialog_Class``
        # is one), so the name of the module the sources call ``DialogLoader`` may be in the image
        # as a string, with the functions that use it next to it.
        names: dict[str, Any] = {}
        for value in name_strings(reader, rdata):
            uses: list[dict[str, Any]] = []
            for occurrence in range(8):
                site = scanner.find_nth_use_of_string(value, occurrence)
                if site is None:
                    break
                if not (text.start <= site < text.end):
                    continue
                entry = scanner.to_function_start(site)
                uses.append(
                    {"site": hex(site), "function": hex(entry) if entry else None}
                )
            names[value] = uses
        report["name_strings"] = names

        # -- signal 7: the code that indexes a dialog row -------------------------------------
        # Whatever the loader is, it turns a dialog id into that dialog's row, and a row is
        # ``0x24`` bytes: the compiler emits either ``imul r, r, 0x24`` or the shift pair
        # ``lea r, [r+r*8]`` / ``shl r, 2``. Both are searched for by their bytes, and each hit
        # is reported with the function it lands in — the shortlist a caller can then test.
        report["stride_users"] = stride_users(reader, scanner, text)

        # -- signal 8: a table of dialog *text* references ------------------------------------
        # The loader is not reached from the 58-row table (nothing in `.text` but the dialog
        # window reads it), so the text must be indexed by something else. Every dialog text this
        # project has measured sits in one narrow band of the string table — the live body at
        # 99942, its two buttons at 99994 and 99946 — so a table of those references would show
        # up as a run of dwords in that band, and the code that indexes it is the loader.
        report["text_reference_runs"] = text_reference_runs(reader, sections)

        # -- signal 9: what indexes such a table ----------------------------------------------
        # A run of text references is only useful if something reads it: whatever embeds the
        # run's own address is the code that indexes dialogs by their text, and that is the
        # loader or its neighbour.
        run_users: list[dict[str, Any]] = []
        for run in report["text_reference_runs"]:
            address = int(run["start"], 16)
            for occurrence in range(4):
                site = scanner.find_nth_use_of_address(address, occurrence)
                if site is None:
                    break
                entry = scanner.to_function_start(site)
                run_users.append(
                    {
                        "run": run["start"],
                        "site": hex(site),
                        "in_text": bool(text.start <= site < text.end),
                        "function": hex(entry) if entry else None,
                        "head": head(reader, entry) if entry else None,
                    }
                )
        report["text_reference_users"] = run_users

        # -- signal 4: the bodies of the candidates, annotated -------------------------------
        # There is no disassembler here and none is wanted: what identifies a function is what it
        # *reaches*, so every call target and every immediate that lands on data is printed with
        # the string or the table it names. A function that takes one id and returns a pointer to
        # an encoded string is what is being looked for, and its body will show it.
        candidates = {
            *functions,
            *table_functions,
            *(
                scanner.to_function_start(int(row["site"], 16)) or 0
                for row in table_users
            ),
            *(int(row["entry"], 16) for row in report["stride_users"]),
            *(
                int(row["function"], 16)
                for row in run_users
                if row["function"] is not None
            ),
        }
        report["bodies"] = [
            body(reader, scanner, entry, table_start, table_end)
            for entry in sorted(candidates - {0})
        ]

    return write_report(report)


def text_reference_runs(reader: Any, sections: dict[str, Any]) -> list[dict[str, Any]]:
    """Runs of dwords in the data sections that look like dialog string-table indices."""

    runs: list[dict[str, Any]] = []
    for name in ("rdata", "data"):
        area = sections.get(name)
        if area is None:
            continue
        address = area.start
        current: list[int] = []
        start = 0
        while address < area.end:
            size = min(CHUNK, area.end - address)
            try:
                chunk = reader.read(address, size)
            except OSError:
                break
            for index in range(0, len(chunk) - 3, 4):
                value = struct.unpack_from("<I", chunk, index)[0]
                if BAND_LOW <= value <= BAND_HIGH:
                    if not current:
                        start = address + index
                    current.append(value)
                else:
                    if len(current) >= RUN_LENGTH:
                        runs.append(
                            {
                                "section": name,
                                "start": hex(start),
                                "count": len(current),
                                "indices": current[:24],
                            }
                        )
                    current = []
            address += size
        if len(current) >= RUN_LENGTH:
            runs.append(
                {
                    "section": name,
                    "start": hex(start),
                    "count": len(current),
                    "indices": current[:24],
                }
            )
    return runs


def stride_users(reader: Any, scanner: Any, text: Any) -> list[dict[str, Any]]:
    """Every function that scales a value by the dialog row size, with how it does it."""

    code = read_code(reader, text.start, text.end - text.start)
    found: dict[int, list[dict[str, Any]]] = {}
    for index in range(len(code) - 4):
        how = None
        if code[index] == 0x6B and code[index + 2] == 0x24:
            how = "imul r, r, 0x24"
        elif code[index] == 0xC1 and code[index + 2] == 0x02:
            # ``shl r, 2``, whose ``r`` is the ModRM's reg field: only a hit if the instruction
            # four bytes before it is the matching ``lea r, [r + r*8]``.
            register = (code[index + 1] >> 3) & 7
            if code[index - 4] == 0x8D:
                modrm = code[index - 3]
                sib = code[index - 2]
                if (
                    modrm & 0xC7 == 0x04
                    and (modrm >> 3) & 7 == register
                    and (sib & 7) == register
                    and (sib >> 3) & 7 == register
                    and sib >> 6 == 3
                ):
                    how = "lea r, [r+r*8]; shl r, 2"
        if how is None:
            continue
        site = text.start + index
        entry = scanner.to_function_start(site)
        if entry is None:
            continue
        found.setdefault(entry, []).append({"at": hex(site), "how": how})
    return [
        {
            "entry": hex(entry),
            "head": head(reader, entry),
            "sites": sites[:6],
        }
        for entry, sites in sorted(found.items())
    ]


def body(
    reader: Any, scanner: Any, entry: int, table_start: int, table_end: int
) -> dict[str, Any]:
    """One candidate function: its bytes, the calls it makes, and the data it names."""

    code = read_code(reader, entry, FUNCTION_BYTES)
    calls: list[dict[str, Any]] = []
    for index in range(len(code) - 5):
        if code[index] != 0xE8:
            continue
        displacement = struct.unpack_from("<i", code, index + 1)[0]
        target = entry + index + 5 + displacement
        calls.append({"at": hex(entry + index), "target": hex(target)})
    data: list[dict[str, Any]] = []
    for at, value in immediates(code, entry):
        if table_start <= value < table_end:
            data.append({"at": hex(at), "value": hex(value), "what": "dialog table"})
        elif scanner.is_valid_ptr(value, "rdata"):
            data.append(
                {"at": hex(at), "value": hex(value), "what": string_at(reader, value)}
            )
    return {
        "entry": hex(entry),
        "head": head(reader, entry),
        "bytes": code.hex(" "),
        "calls": calls[:32],
        "data": data[:32],
    }


def string_at(reader: Any, address: int) -> str:
    """The NUL-terminated text at an address, for naming what an immediate points at."""

    try:
        raw = reader.read(address, 96)
    except OSError:
        return "?"
    end = raw.find(b"\x00")
    text = raw[: end if end >= 0 else len(raw)]
    try:
        return text.decode("ascii")
    except UnicodeDecodeError:
        return text.decode("latin-1")


def source_paths(reader: Any, rdata: Any) -> list[str]:
    """Every ``P:\\Code\\`` path the data section carries, sorted, for use as an anchor."""

    found: set[str] = set()
    address = rdata.start
    while address < rdata.end:
        size = min(CHUNK, rdata.end - address)
        try:
            chunk = reader.read(address, size)
        except OSError:
            break
        for match in PATH.finditer(chunk):
            found.add(match.group(0).decode("ascii"))
        address += size
    return sorted(found)


def name_strings(reader: Any, rdata: Any) -> list[str]:
    """Every class- or type-like name in the data section that mentions a loader or dialog text.

    A name here is a bare identifier: no spaces, no path separators, at least four characters of
    letters, digits and underscores. Those are the names a compiler leaves behind for RTTI, for a
    class registered with the engine, or for an assertion that names a type.
    """

    found: set[str] = set()
    address = rdata.start
    while address < rdata.end:
        size = min(CHUNK, rdata.end - address)
        try:
            chunk = reader.read(address, size)
        except OSError:
            break
        for match in NAME.finditer(chunk):
            found.add(match.group(0).decode("ascii"))
        address += size
    return sorted(found)


def read_code(reader: Any, address: int, size: int) -> bytes:
    """Read code bytes, answering an empty read rather than raising."""

    try:
        return reader.read(address, size)
    except OSError:
        return b""


def head(reader: Any, address: int) -> str | None:
    """The first bytes at an address, as text."""

    code = read_code(reader, address, 16)
    return code.hex(" ") if code else None


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
