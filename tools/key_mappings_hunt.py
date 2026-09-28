"""Offline derivation of the client's key-remap table resolver (``s_remapTable``).

**Why.** Reforged's ``UIManager.GetKeyMappings``/``SetKeyMappings`` wrap a binding native's current
revision does not have at all; the older runtime's implementation finds the table through GWCA's
``FindAssertion("FrKey.cpp", "count == arrsize(s_remapTable)", 0, 0x13)``
(``C:\\Users\\Apo\\Py4GW\\include\\py_ui.h:4757-4790``). That route is **not** reproducible here — the
assertion's own offset does not land on the table on this build — so the table needs a resolver
derived from the file. That is a question about ``Gw.exe``, not about a running client.

**Method.** Read the assertion message's address out of ``.rdata``, find where ``.text`` uses it,
and read the instructions around that use: this client's ``FrKey`` entry asserts
``count == arrsize(s_remapTable)`` against ``0x75`` and then loads the table's address as an
immediate right after it. The distance from the message's use to that immediate is what the resolver
needs, and it is printed both ways here so the number is measured, not guessed.

Offline, read-only, no client and no elevation:

    python tools/key_mappings_hunt.py [path-to-Gw.exe]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pe_image import PeImage  # noqa: E402

DEFAULT_CLIENT = r"F:\GW\GW1\Gw.exe"
MESSAGE = "count == arrsize(s_remapTable)"
SOURCE_FILE = "FrKey.cpp"

#: How many words the table holds, from the assertion itself (``count == arrsize(s_remapTable)``)
#: and from the count the entry compares against (``cmp [ebp+8], 0x75``).
TABLE_WORDS = 0x75


def section_of(pe: PeImage, file_offset: int) -> str:
    for section in pe.sections:
        if section.raw_offset <= file_offset < section.raw_offset + section.raw_size:
            return section.name
    return ""


def address_of(pe: PeImage, file_offset: int) -> int:
    for section in pe.sections:
        if section.raw_offset <= file_offset < section.raw_offset + section.raw_size:
            return (
                pe.image_base
                + section.virtual_address
                + (file_offset - section.raw_offset)
            )
    raise ValueError(f"file offset {file_offset:#x} is in no section")


def file_offset_of(pe: PeImage, address: int) -> int:
    for section in pe.sections:
        start = pe.image_base + section.virtual_address
        if start <= address < start + section.virtual_size:
            return section.raw_offset + (address - start)
    raise ValueError(f"{address:#x} is in no section")


def find_literals(pe: PeImage, text: str) -> list[int]:
    """Every address where an ANSI literal appears, which is what the catalog's op uses."""

    needle = text.encode("ascii") + b"\x00"
    out: list[int] = []
    start = 0
    while True:
        found = pe.data.find(needle, start)
        if found < 0:
            return out
        out.append(address_of(pe, found))
        start = found + 1


def find_uses(pe: PeImage, address: int) -> list[int]:
    """Every ``.text`` address holding ``address`` as a 4-byte little-endian immediate."""

    section = pe.section(".text")
    raw = pe.data[section.raw_offset : section.raw_offset + section.raw_size]
    needle = struct.pack("<I", address)
    out: list[int] = []
    start = 0
    while True:
        found = raw.find(needle, start)
        if found < 0:
            return out
        out.append(pe.image_base + section.virtual_address + found)
        start = found + 1


def dump(pe: PeImage, address: int, before: int = 16, after: int = 32) -> None:
    start = file_offset_of(pe, address) - before
    for row in range(start, start + before + after, 8):
        chunk = pe.data[row : row + 8]
        print(f"    {address_of(pe, row):#010x}  {chunk.hex(' ')}")


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else DEFAULT_CLIENT
    pe = PeImage(path)
    print(f"{path}: image base {pe.image_base:#x}, {len(pe.data)} bytes")

    for label, text in (("message", MESSAGE), ("file", SOURCE_FILE)):
        literals = find_literals(pe, text)
        print(f'\n{label} literal "{text}": {len(literals)} copy/copies')
        for address in literals:
            print(f"    {address:#010x}  {section_of(pe, file_offset_of(pe, address))}")

    message_address = find_literals(pe, MESSAGE)[0]
    uses = find_uses(pe, message_address)
    print(f"\n.text uses of {message_address:#010x}: {len(uses)}")
    for index, use in enumerate(uses):
        print(f"  use {index} at {use:#010x}:")
        dump(pe, use)

    for index, use in enumerate(uses):
        for distance in range(0, 0x20):
            candidate = int.from_bytes(pe.read_va(use + distance, 4), "little")
            if candidate and section_of_address(pe, candidate) == ".data":
                print(
                    f"  use {index}: +{distance:#x} reads {candidate:#010x}, inside .data"
                )

    return 0


def section_of_address(pe: PeImage, address: int) -> str:
    """The section an address falls in, by name (``.data`` is what GWCA validates against)."""

    for section in pe.sections:
        start = pe.image_base + section.virtual_address
        if start <= address < start + section.virtual_size:
            return section.name
    return ""


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
