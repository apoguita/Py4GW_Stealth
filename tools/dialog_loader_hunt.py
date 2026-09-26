"""Offline hunt for this client build's ``DialogLoader_GetText``, from ``Gw.exe`` on disk.

The native source resolves that function from one hardcoded value,
``DialogMemory::DIALOG_LOADER_GETTEXT = 0x0079EEF0`` (``dialog.h:99``), rebased by
``ToRuntimeAddress`` (``dialog_patterns.cpp:23-31``). That constant is right for the build Native
was written against and wrong for every other build, and this port runs against the client on this
machine. Live probes have established what is *not* there (``RESEARCH.md``), so the next question is
a static one — and a static question about a file does not need a running client, a hook, or an
elevated shell: ``Gw.exe`` is on disk, and ``tools/pe_image.py`` reads it.

Two subcommands, one per kind of evidence:

``constants <Gw.exe> ...``
    What Native's two dialog constants describe in each file given. ``RVA 0x39EEF0`` is the loader
    on Native's build, and the flags column of the metadata table is at ``RVA 0x513920`` — the one
    column ``ValidateDialogMetadataBases`` can check from the values alone. A build where the first
    is mid-function and the second is not a table is not the build those constants describe.

``strings <Gw.exe>``
    The loader **returns a pointer to an encoded string**, so the hunt does not have to guess what
    the function looks like: it looks for what it hands out. Every run of code units the source's
    own validator accepts (``is_valid_enc_str`` — the port of ``EncStrValidate``) is a candidate, and
    then two questions are asked of the file: which code holds one of those addresses as an
    immediate, and does a **table of them** exist in the data — because a getter indexes a table.
    That is the shape ``DialogLoader_GetText`` would have, and a table of four-or-more pointers at a
    constant stride is not something that happens by accident.

``rows <Gw.exe>``
    The dialog metadata table itself, resolved by **the port's own** ``ResolveFlagsBase``
    (``dialog.py``, the port of ``dialog_patterns.cpp:94-133``) over the file, with every row's
    fields and the name string each row points at, plus the data that follows the table. This is the
    offline counterpart of the live reading in ``DIALOG_PORT.md``: if the two agree, the file is the
    same binary the port has been reading, and the table's neighbourhood can be examined without a
    client.

Read-only, no client, no elevation, no writes.

Usage: ``python tools/dialog_loader_hunt.py <constants|strings|rows> <Gw.exe> [<Gw.exe> ...]``
"""

from __future__ import annotations

import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(Path(__file__).resolve().parent), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gw_scan import (  # noqa: E402
    EncodedString,
    encoded_strings,
    find_immediates,
    find_pointer_tables,
    is_entry,
    preceding_entry,
)
from pe_image import PeImage  # noqa: E402

#: ``DialogMemory`` (``dialog.h:94-99``): the constants Native hardcodes, as file virtual addresses.
NATIVE_IMAGE_BASE = 0x00400000
NATIVE_LOADER_GETTEXT = 0x0079EEF0
NATIVE_FLAGS_BASE = 0x00913920

#: ``DialogMemory::MAX_DIALOG_ID`` and the stride its table uses (``dialog.h:89-92``).
MAX_DIALOG_ID = 0x39
FLAGS_STRIDE = 0x24

#: How many strings to report in full, and how many references to show per string.
MAX_REPORTED_STRINGS = 40
MAX_SITES_SHOWN = 3


# ── constants ────────────────────────────────────────────────────────────────


def describe_loader_site(image: PeImage) -> dict[str, object]:
    """What sits at Native's loader address in this file."""

    rva = NATIVE_LOADER_GETTEXT - NATIVE_IMAGE_BASE
    report: dict[str, object] = {"rva": f"{rva:#010x}"}
    section = image.section_for_rva(rva)
    report["section"] = section.name if section else ""
    head = image.read_rva(rva, 16)
    report["bytes"] = head.hex(" ")
    report["is_entry"] = is_entry(head)
    entry = preceding_entry(image, rva)
    report["entry_at_or_before"] = f"{entry:#010x}" if entry is not None else ""
    report["offset_from_entry"] = f"{rva - entry:#x}" if entry is not None else ""
    return report


def describe_flags_table(image: PeImage) -> dict[str, object]:
    """Whether Native's flags table address holds a dialog metadata table in this file."""

    rva = NATIVE_FLAGS_BASE - NATIVE_IMAGE_BASE
    report: dict[str, object] = {"rva": f"{rva:#010x}"}
    section = image.section_for_rva(rva - 8)
    report["section"] = section.name if section else ""

    text = image.section(".text")
    enabled = 0
    handlers_in_text = 0
    handlers_nonzero = 0
    flags_within = 0
    readable = True
    rows: list[str] = []
    for index in range(MAX_DIALOG_ID + 1):
        try:
            flags = image.read_u32(rva + index * FLAGS_STRIDE)
            handler = image.read_u32(rva - 8 + index * FLAGS_STRIDE)
            frame_type = image.read_u32(rva - 4 + index * FLAGS_STRIDE)
            content_id = image.read_u32(rva + 4 + index * FLAGS_STRIDE)
            property_id = image.read_u32(rva + 8 + index * FLAGS_STRIDE)
        except ValueError:
            readable = False
            break
        if flags <= 0xFFFF:
            flags_within += 1
        if flags & 0x1:
            enabled += 1
        if handler:
            handlers_nonzero += 1
            if text.contains(handler - NATIVE_IMAGE_BASE):
                handlers_in_text += 1
        if index < 3:
            rows.append(
                f"id {index}: handler {handler:#010x} flags {flags:#06x} "
                f"frame {frame_type:#06x} content {content_id:#06x} property {property_id:#06x}"
            )
    report.update(
        {
            "rows_read": MAX_DIALOG_ID + 1 if readable else "truncated",
            "flags_within_0xffff": flags_within,
            "rows_enabled": enabled,
            "handlers_nonzero": handlers_nonzero,
            "handlers_in_text": handlers_in_text,
            "looks_like_the_table": bool(
                readable and flags_within == MAX_DIALOG_ID + 1 and enabled > 0
            ),
            "first_rows": rows,
        }
    )
    return report


def command_constants(paths: list[str]) -> int:
    for path in paths:
        image = PeImage(path)
        print(f"=== {path}")
        print(f"    size {len(image.data):#x}  image base {image.image_base:#010x}")
        for section in image.sections:
            print(
                f"    {section.name:<8} rva {section.virtual_address:#010x} "
                f"vsize {section.virtual_size:#x}"
            )
        loader = describe_loader_site(image)
        print(
            f"    loader site (Native {NATIVE_LOADER_GETTEXT:#010x}): rva {loader['rva']} "
            f"in {loader['section'] or 'no section'} -> {loader['bytes']}"
        )
        print(
            f"      is a function entry: {loader['is_entry']}, nearest entry "
            f"{loader['entry_at_or_before'] or 'none'}"
            + (
                f" ({loader['offset_from_entry']} bytes before)"
                if loader["offset_from_entry"]
                else ""
            )
        )
        table = describe_flags_table(image)
        print(
            f"    flags table (Native {NATIVE_FLAGS_BASE:#010x}): rva {table['rva']} "
            f"in {table['section'] or 'no section'} -> {table['rows_read']} rows read, "
            f"{table['flags_within_0xffff']} flags <= 0xffff, {table['rows_enabled']} enabled, "
            f"{table['handlers_in_text']}/{table['handlers_nonzero']} handlers in .text -> "
            f"looks like the table: {table['looks_like_the_table']}"
        )
        for row in table["first_rows"]:  # type: ignore[union-attr]
            print(f"      {row}")
    return 0


# ── rows ─────────────────────────────────────────────────────────────────────


class FileRange:
    """What ``RemoteScanner.get_section_range`` returns, for a file."""

    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end


class FileMemory:
    """The reader interface ``DialogTables`` asks for, answered from a file.

    ``dialog.py`` reads the client through two objects — ``reader.read`` and
    ``scanner.get_section_range`` / ``read_uint32`` — and both work in the client's virtual address
    space. A file's addresses are the same space with the image base the file declares, so one object
    serves both roles and the port's own scan runs unchanged. A range the file does not hold raises
    ``OSError``, which is what the port's scan already catches.
    """

    def __init__(self, image: PeImage) -> None:
        self._image = image

    def read(self, address: int, size: int) -> bytes:
        try:
            return self._image.read_va(address, size)
        except ValueError as error:
            raise OSError(str(error)) from error

    def read_uint32(self, address: int) -> int:
        return self._image.read_u32(address - self._image.image_base)

    def get_section_range(self, section: str) -> FileRange:
        area = self._image.section(f".{section}")
        start = self._image.image_base + area.virtual_address
        return FileRange(start, start + area.virtual_size)

    def w_string(self, address: int, limit: int = 64) -> str:
        """The wide string at ``address``, which is what this client's tables hold.

        The first attempt at this read the field as ANSI and every name came back as a single
        letter: the table's ``+0x04`` pointer is a ``wchar_t*`` literal, so reading it bytewise stops
        at the high byte of its first character.
        """

        try:
            data = self.read(address, limit * 2)
        except OSError:
            return ""
        return data.decode("utf-16-le", "replace").split("\x00", 1)[0]


def command_rows(path: str) -> int:
    from py4gw.dialog import DialogTables

    image = PeImage(path)
    memory = FileMemory(image)
    tables = DialogTables(memory, memory, None)  # type: ignore[arg-type]
    flags_base = tables._resolve_flags_base()
    print(f"=== {path}")
    if not flags_base:
        print("    ResolveFlagsBase found nothing in this file")
        return 0
    section = image.section_for_va(flags_base)
    print(
        f"    ResolveFlagsBase (the port's own scan) -> flags {flags_base:#010x} "
        f"(rva {flags_base - image.image_base:#010x}, in {section.name if section else '?'})"
    )

    #: A row is 0x24 bytes: handler, name pointer, flags, content_id, property_id, then four words
    #: the sources do not name. The flags column is at +0x08, which is why the scan's base is the
    #: row's start plus eight.
    row_start = flags_base - 8
    for index in range(MAX_DIALOG_ID + 1):
        try:
            cells = struct.unpack("<9I", memory.read(row_start + index * FLAGS_STRIDE, 0x24))
        except OSError:
            print(f"    id {index}: unreadable")
            break
        handler, name_ptr, flags, content_id, property_id = cells[:5]
        tail = " ".join(f"{value:#x}" for value in cells[5:])
        name = memory.w_string(name_ptr) if name_ptr else ""
        print(
            f"    id {index:2}: handler {handler:#010x} flags {flags:#06x} "
            f"content {content_id:#06x} property {property_id:#06x} tail [{tail}] name {name!r}"
        )

    tail_start = row_start + (MAX_DIALOG_ID + 1) * FLAGS_STRIDE
    print(
        f"    data after the table, from {tail_start:#010x} "
        f"(rva {tail_start - image.image_base:#010x}):"
    )
    for step in range(0, 0x100, 0x10):
        try:
            chunk = memory.read(tail_start + step, 0x10)
        except OSError:
            break
        values = struct.unpack("<4I", chunk)
        rendered = " ".join(f"{value:#010x}" for value in values)
        print(f"      {tail_start + step:#010x}  {rendered}")
    return 0


# ── table users ──────────────────────────────────────────────────────────────


def command_table_users(path: str) -> int:
    """Who reads the dialog metadata table: as an immediate in code, and as a pointer in data.

    A getter that indexes the table has to *find* it, and there are only two ways to: the address as
    an immediate, or the address loaded from a pointer the module carries. A search that only looks
    for immediates therefore misses a table reached through a global — which is one of the two ways
    the loader could be invisible to the earlier probes.
    """

    from py4gw.dialog import DialogTables

    image = PeImage(path)
    memory = FileMemory(image)
    flags_base = DialogTables(memory, memory, None)._resolve_flags_base()  # type: ignore[arg-type]
    print(f"=== {path}")
    if not flags_base:
        print("    ResolveFlagsBase found nothing in this file")
        return 0
    table_start = flags_base - 8
    table_end = table_start + (MAX_DIALOG_ID + 1) * FLAGS_STRIDE
    print(f"    table {table_start:#010x} .. {table_end:#010x}")

    #: The table's own addresses, every dword boundary in it — a reader may name a row's field.
    targets = list(range(table_start, table_end, 4))
    text = image.section(".text")
    code = image.read_rva(text.virtual_address, text.raw_size)

    by_function: dict[int, set[int]] = {}
    immediate_sites = 0
    for target in targets:
        needle = struct.pack("<I", target)
        start = 0
        while True:
            at = code.find(needle, start)
            if at < 0:
                break
            immediate_sites += 1
            site = text.virtual_address + at
            entry = preceding_entry(image, site) or 0
            by_function.setdefault(entry, set()).add(target)
            start = at + 1

    print(f"    {immediate_sites} immediate site(s) naming the table, in {len(by_function)} function(s):")
    for entry, named in sorted(by_function.items(), key=lambda item: -len(item[1])):
        rows = sorted((value - table_start) // FLAGS_STRIDE for value in named)
        print(
            f"      {entry:#010x}: {len(named)} address(es), row(s) "
            f"{rows[:8]}{' ...' if len(rows) > 8 else ''}"
        )

    held: list[tuple[int, int]] = []
    for name in (".rdata", ".data"):
        area = image.section(name)
        data = image.read_rva(area.virtual_address, area.raw_size)
        for target in (table_start, table_start + 4, table_end - FLAGS_STRIDE):
            needle = struct.pack("<I", target)
            start = 0
            while True:
                at = data.find(needle, start)
                if at < 0:
                    break
                held.append((area.virtual_address + at, target))
                start = at + 1
    print(f"    {len(held)} dword(s) in the data sections holding the table start, +4, or last row:")
    for rva, target in held[:16]:
        print(f"      rva {rva:#010x} holds {target:#010x}")
    return 0


# ── immediates ───────────────────────────────────────────────────────────────


def command_immediates(path: str, values: list[int]) -> int:
    """Every code site holding one of these values as a 4-byte immediate, and its function.

    A sentinel is a signature. ``0x187CA`` is the value this build's floating-dialog table uses for
    "this dialog has no text" (``dialog.py``'s window builder compares the row's ``+0x14`` word with
    it), so a function carrying that constant is doing something with that column — which is the
    closest thing to a name for a getter nobody has labelled.
    """

    image = PeImage(path)
    text = image.section(".text")
    code = image.read_rva(text.virtual_address, text.raw_size)
    print(f"=== {path}")
    for value in values:
        needle = struct.pack("<I", value)
        sites: list[int] = []
        start = 0
        while True:
            at = code.find(needle, start)
            if at < 0:
                break
            sites.append(text.virtual_address + at)
            start = at + 1
        by_function: dict[int, list[int]] = {}
        for site in sites:
            entry = preceding_entry(image, site) or 0
            by_function.setdefault(entry, []).append(site)
        print(f"    {value:#x}: {len(sites)} site(s) in {len(by_function)} function(s)")
        for entry, entry_sites in sorted(by_function.items(), key=lambda item: -len(item[1])):
            shown = ", ".join(f"{site:#010x}" for site in entry_sites[:6])
            print(
                f"      in {entry:#010x}: {len(entry_sites)} site(s) "
                f"{shown}{' ...' if len(entry_sites) > 6 else ''}"
            )
    return 0


# ── strings ──────────────────────────────────────────────────────────────────


def command_strings(path: str, limit: int, min_index: int = 0) -> int:
    image = PeImage(path)
    print(f"=== {path}")
    found = encoded_strings(image, limit=limit)
    print(f"    {len(found)} encoded strings accepted by is_valid_enc_str")
    if min_index:
        found = [item for item in found if item.index >= min_index]
        print(
            f"    {len(found)} of them name a table index >= {min_index} "
            f"(the band the client's dialog text was measured in: 99942, 99994, 99946, "
            f"with the strings' own code units 8103 0a66 ... / 8103 0a9a ... / 8103 0a6a ...)"
        )
    if not found:
        return 0

    by_va = {item.va: item for item in found}
    find_immediates(image, by_va)
    tables = find_pointer_tables(image, by_va)

    referenced = [item for item in found if item.code_sites]
    print(
        f"    {len(referenced)} of them are referenced as an immediate in .text "
        f"(a data reference is not countable from the address alone)"
    )
    print(f"    index buckets (index // 0x1000): {dict(Counter(i.index // 0x1000 for i in found).most_common(8))}")

    for item in found[:MAX_REPORTED_STRINGS]:
        print(f"    {item}")
        if item.code_sites:
            entries = []
            for site in item.code_sites[:MAX_SITES_SHOWN]:
                entry = preceding_entry(image, site)
                entries.append(f"{site:#010x} (in {entry:#010x})" if entry else f"{site:#010x}")
            print(
                f"        code: {len(item.code_sites)} site(s): "
                + ", ".join(entries)
                + (" ..." if len(item.code_sites) > MAX_SITES_SHOWN else "")
            )
    if len(found) > MAX_REPORTED_STRINGS:
        print(f"    ... and {len(found) - MAX_REPORTED_STRINGS} more")

    print(f"    pointer tables of encoded strings (stride, rows >= 4): {len(tables)}")
    for table in tables:
        targets: list[EncodedString] = [by_va[value] for value in table["targets"]]  # type: ignore[index]
        print(
            f"      rva {table['rva']:#010x} stride {table['stride']} rows {table['rows']} "
            f"-> index {targets[0].index} (and {targets[1].index} next)"
            if len(targets) > 1
            else f"      rva {table['rva']:#010x} stride {table['stride']} rows {table['rows']}"
        )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in (
        "constants",
        "strings",
        "rows",
        "table-users",
        "immediates",
    ):
        print(__doc__)
        return 2

    command, targets = argv[0], argv[1:]
    if command == "constants":
        return command_constants(targets)
    if command == "rows":
        for path in targets:
            command_rows(path)
        return 0
    if command == "table-users":
        for path in targets:
            command_table_users(path)
        return 0
    if command == "immediates":
        values: list[int] = []
        paths = []
        for value in targets:
            if value.startswith("0x"):
                values.append(int(value, 16))
            else:
                paths.append(value)
        for path in paths:
            command_immediates(path, values)
        return 0
    limit = 4000
    if command == "strings":
        min_index = 0
        paths: list[str] = []
        for value in targets:
            if value.startswith("--min-index="):
                min_index = int(value.split("=", 1)[1], 0)
            else:
                paths.append(value)
        for path in paths:
            command_strings(path, limit, min_index)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
