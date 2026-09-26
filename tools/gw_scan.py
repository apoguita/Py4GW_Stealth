"""Guild Wars client shapes, read from ``Gw.exe`` on disk.

``tools/pe_image.py`` knows what a PE file is; it knows nothing about Guild Wars. This module holds
the other half — the things that are true of *this* client rather than of PE files in general —
and it holds them in one place so a tool does not grow its own copy:

- **what a function entry looks like on this client.** Measured read-only, not assumed: the dialog
  event handlers the metadata table points at (``0x0070B8D0``, ``0x007103C0``) and the two
  functions this project hooks (``0x00845880``, ``0x008441A0``) all begin ``55 8B EC``, some with
  the hot-patch ``8B FF`` padding in front. It is a shape check, not a proof — it says an address
  *looks like* an entry, never which function it is.
- **the client's encoded strings.** The game does not store translatable text as text: it stores
  codepoint arrays in base ``0x7F00``, and the structural check they must pass is the source's own
  ``EncStrValidate``. This project ported it (``py4gw.ui.encoded_str``), so a scan for encoded
  strings uses the port rather than a second opinion about what one looks like.
- **where a value is referenced**, in code (a 4-byte immediate) and in data (a pointer in a table).

Everything here takes a :class:`~pe_image.PeImage`, so it works on any build's file with no client
running, no hook, no elevation and no writes.

**Source:** the entry shapes and the validator are the same evidence as ``dialog.py``'s
``_FUNCTION_ENTRY_PREFIXES`` and ``ui/encoded_str.py``; this module reads them off a file instead of
off a process.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py4gw.internals.string_table import _parse_codepoints  # noqa: E402
from py4gw.ui.encoded_str import is_valid_enc_str  # noqa: E402

from pe_image import PeImage  # noqa: E402

#: The two prefixes a function entry carries on this client, longest first.
ENTRY_PREFIXES = (b"\x8b\xff\x55\x8b\xec", b"\x55\x8b\xec")

#: ``cc`` is what the compiler pads between functions, so an entry usually follows a run of it.
PADDING = b"\xcc\xcc"


def is_entry(head: bytes) -> bool:
    """Whether these bytes begin the way this client's functions begin."""

    return any(head.startswith(prefix) for prefix in ENTRY_PREFIXES)


def preceding_entry(image: PeImage, rva: int, window: int = 0x400) -> int | None:
    """The nearest function entry at or before ``rva``, looking back ``window`` bytes.

    The walk keeps the last candidate a padding run precedes, and falls back to the last prologue
    it saw when no padding is there (a leaf function with no prologue is not found at all, and this
    returns a *plausible* entry rather than a proven one — the caller decides what that is worth).
    """

    start = max(image.section(".text").virtual_address, rva - window)
    data = image.read_rva(start, rva - start + 1)
    last_prologue: int | None = None
    for offset in range(len(data) - 1, -1, -1):
        if not is_entry(data[offset : offset + 5]):
            continue
        if last_prologue is None:
            last_prologue = start + offset
        if offset >= 2 and data[offset - 2 : offset] == PADDING:
            return start + offset
    return last_prologue


# ── encoded strings ──────────────────────────────────────────────────────────


@dataclass
class EncodedString:
    """One run of code units that the source's validator accepts."""

    rva: int
    va: int
    words: tuple[int, ...]
    index: int
    key: int
    #: Filled in by :func:`find_immediates`: code sites that hold this address as an immediate.
    code_sites: list[int] = field(default_factory=list)

    @property
    def length(self) -> int:
        """Code units, not counting the terminator."""

        return len(self.words) - 1

    def __str__(self) -> str:
        words = " ".join(f"{word:04x}" for word in self.words[:12])
        return (
            f"rva {self.rva:#010x} index {self.index} key {self.key} "
            f"{self.length} units: {words}"
            + (" ..." if len(self.words) > 12 else "")
        )


def encoded_strings(
    image: PeImage,
    sections: tuple[str, ...] = (".rdata", ".data"),
    min_words: int = 3,
    max_words: int = 128,
    limit: int | None = None,
) -> list[EncodedString]:
    """Every run of code units in ``sections`` that ``is_valid_enc_str`` accepts.

    The scan is one pass per section, over the section's file bytes. A candidate starts wherever a
    code unit can begin a base-``0x7F00`` digit (anything whose low 15 bits reach
    ``WORD_VALUE_BASE``), it ends at the first zero code unit, and the run is only looked at
    further when it is long enough and terminates within ``max_words`` — which is what keeps this
    affordable on a two-megabyte section.
    """

    found: list[EncodedString] = []
    for name in sections:
        section = image.section(name)
        data = image.read_rva(section.virtual_address, section.raw_size)
        count = len(data) // 2
        words = struct.unpack(f"<{count}H", data[: count * 2])
        index = 0
        last_start = count - min_words
        while index <= last_start:
            if (words[index] & 0x7FFF) < 0x100:
                index += 1
                continue
            try:
                term = words.index(0, index, index + max_words)
            except ValueError:
                index += 1
                continue
            if term - index + 1 < min_words:
                index += 1
                continue
            run = words[index : term + 1]
            if not is_valid_enc_str(run):
                index += 1
                continue
            parsed_index, key = _parse_codepoints(run)
            rva = section.virtual_address + index * 2
            index = term + 1
            if not parsed_index:
                continue
            found.append(
                EncodedString(
                    rva=rva,
                    va=image.image_base + rva,
                    words=run,
                    index=parsed_index,
                    key=key,
                )
            )
            if limit is not None and len(found) >= limit:
                return found
    return found


# ── where a value is referenced ──────────────────────────────────────────────


def find_immediates(
    image: PeImage, addresses: dict[int, EncodedString], section: str = ".text"
) -> None:
    """Fill in ``code_sites`` for every address that appears as a 4-byte immediate in a section."""

    area = image.section(section)
    code = image.read_rva(area.virtual_address, area.raw_size)
    for value, payload in addresses.items():
        needle = struct.pack("<I", value)
        start = 0
        while True:
            at = code.find(needle, start)
            if at < 0:
                break
            payload.code_sites.append(area.virtual_address + at)
            start = at + 1


def find_pointer_tables(
    image: PeImage,
    addresses: dict[int, EncodedString],
    sections: tuple[str, ...] = (".rdata", ".data"),
    min_rows: int = 4,
) -> list[dict[str, object]]:
    """Runs of consecutive pointers to the addresses given, which is what a table looks like.

    A table is the shape a getter indexes: the addresses it hands out sit at a fixed stride, in
    order. The stride is read from the file rather than assumed, and a run shorter than ``min_rows``
    is not reported — two pointers in a row happen by accident, four in a row at a constant stride
    do not.
    """

    #: rva of a dword -> the address it holds, for values that are one of the addresses given.
    sites: dict[int, int] = {}
    for name in sections:
        area = image.section(name)
        data = image.read_rva(area.virtual_address, area.raw_size)
        for value in addresses:
            needle = struct.pack("<I", value)
            start = 0
            while True:
                at = data.find(needle, start)
                if at < 0:
                    break
                sites[area.virtual_address + at] = value
                start = at + 1

    ordered = sorted(sites)
    tables: list[dict[str, object]] = []
    run_start = 0
    while run_start < len(ordered):
        run_end = run_start + 1
        stride: int | None = None
        while run_end < len(ordered):
            gap = ordered[run_end] - ordered[run_end - 1]
            if stride is None:
                stride = gap
            elif gap != stride:
                break
            run_end += 1
        rows = run_end - run_start
        if rows >= min_rows:
            tables.append(
                {
                    "rva": ordered[run_start],
                    "stride": stride,
                    "rows": rows,
                    "targets": [sites[rva] for rva in ordered[run_start:run_end]],
                }
            )
        run_start = run_end
    tables.sort(key=lambda table: -int(table["rows"]))  # type: ignore[arg-type]
    return tables
