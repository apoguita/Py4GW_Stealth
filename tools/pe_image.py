"""Read a PE file's sections offline, so build questions can be answered from disk.

**Why this exists.** Every "where is this function on *this* build" question so far was answered
against the *live* client, through the capability layer, with an elevated shell and a UAC prompt
each time. But ``Gw.exe`` is a file, and a file can be read without any of that: the headers give
the sections, the sections give the bytes, and a virtual address the sources quote (``0x0079EEF0``,
``0x00913920``) is an offset into that file. So a build can be examined, and two builds compared,
with no client running at all.

**What it is.** A section table and the arithmetic that turns a virtual address into a file offset.
Nothing else: no signatures, no offsets, no Guild Wars knowledge — a caller keeps that
(``AGENTS.md``: target knowledge stays out of generic mechanics).

**What it is not.** It is not a loader: ``read_va`` never invents bytes. A virtual address whose
bytes are not in the file (an uninitialised tail, a range spanning two sections) raises rather
than returning zeros, because a zero that was never in the file is a wrong answer that reads like
a real one.

Read-only, pure Python, no dependencies.

Usage: (no client, no elevation) ``python tools/pe_image.py <exe> [virtual-address [length]]``
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

#: ``IMAGE_FILE_MACHINE_I386``. The only machine this project reads.
IMAGE_FILE_MACHINE_I386 = 0x014C

#: The PE signature that follows the DOS stub's ``e_lfanew`` pointer.
PE_SIGNATURE = b"PE\x00\x00"


@dataclass(frozen=True)
class Section:
    """One section header, in the units the file stores it in."""

    name: str
    virtual_address: int
    virtual_size: int
    raw_offset: int
    raw_size: int
    characteristics: int

    @property
    def virtual_end(self) -> int:
        """One past the last virtual address the section covers."""

        return self.virtual_address + max(self.virtual_size, self.raw_size)

    def contains(self, va: int) -> bool:
        """Whether ``va`` falls inside this section's virtual range."""

        return self.virtual_address <= va < self.virtual_end

    def __str__(self) -> str:
        return (
            f"{self.name:<8} va {self.virtual_address:#010x} "
            f"vsize {self.virtual_size:#08x} raw {self.raw_offset:#08x} "
            f"rawsize {self.raw_size:#08x} characteristics {self.characteristics:#010x}"
        )


class PeImage:
    """One PE file's headers, sections and file bytes."""

    def __init__(self, path: str | Path) -> None:
        """Read ``path`` and parse its headers."""

        self.path = Path(path)
        self.data = self.path.read_bytes()
        if len(self.data) < 0x40:
            raise ValueError(f"{self.path} is too small to be a PE file")

        pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe_offset : pe_offset + 4] != PE_SIGNATURE:
            raise ValueError(f"{self.path} has no PE signature at {pe_offset:#x}")

        coff = pe_offset + 4
        machine, section_count, _, _, _, optional_size, _ = struct.unpack_from(
            "<HHIIIHH", self.data, coff
        )
        if machine != IMAGE_FILE_MACHINE_I386:
            raise ValueError(f"{self.path} is machine {machine:#06x}, not i386")

        optional = coff + 20
        magic = struct.unpack_from("<H", self.data, optional)[0]
        if magic != 0x010B:
            raise ValueError(f"{self.path} optional header magic is {magic:#06x}, not PE32")

        self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
        self.entry_point = struct.unpack_from("<I", self.data, optional + 16)[0]
        self.section_alignment = struct.unpack_from("<I", self.data, optional + 32)[0]
        self.file_alignment = struct.unpack_from("<I", self.data, optional + 36)[0]
        self.size_of_image = struct.unpack_from("<I", self.data, optional + 56)[0]

        table = optional + optional_size
        self.sections: list[Section] = []
        for index in range(section_count):
            header = table + index * 40
            name = self.data[header : header + 8].rstrip(b"\x00").decode("ascii", "replace")
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", self.data, header + 8
            )
            characteristics = struct.unpack_from("<I", self.data, header + 36)[0]
            self.sections.append(
                Section(
                    name=name,
                    virtual_address=virtual_address,
                    virtual_size=virtual_size,
                    raw_offset=raw_offset,
                    raw_size=raw_size,
                    characteristics=characteristics,
                )
            )

    def section(self, name: str) -> Section:
        """Return the section called ``name``, or raise ``KeyError``."""

        for section in self.sections:
            if section.name == name:
                return section
        raise KeyError(f"{self.path} has no section {name!r}")

    def section_for_rva(self, rva: int) -> Section | None:
        """Return the section holding the relative virtual address ``rva``, or ``None``."""

        for section in self.sections:
            if section.contains(rva):
                return section
        return None

    def section_for_va(self, va: int) -> Section | None:
        """Return the section holding the virtual address ``va``, or ``None``."""

        return self.section_for_rva(va - self.image_base)

    def read_rva(self, rva: int, size: int) -> bytes:
        """Return the ``size`` bytes at ``rva``, or raise.

        A range that leaves the file — past a section's raw size, across a section boundary, or
        outside every section — raises ``ValueError`` rather than being padded with zeros.
        """

        if size <= 0:
            raise ValueError("size must be positive")
        section = self.section_for_rva(rva)
        if section is None:
            raise ValueError(f"{rva:#010x} is outside every section of {self.path}")
        offset_in_section = rva - section.virtual_address
        if offset_in_section + size > section.raw_size:
            raise ValueError(
                f"{rva:#010x}+{size:#x} leaves {section.name}'s file bytes "
                f"({section.raw_size:#x} of them, {section.virtual_size:#x} virtual)"
            )
        start = section.raw_offset + offset_in_section
        return self.data[start : start + size]

    def read_va(self, va: int, size: int) -> bytes:
        """Return the ``size`` bytes at the virtual address ``va``, or raise.

        A virtual address is what the sources quote (``0x0079EEF0``), and it is a relative virtual
        address plus ``ImageBase`` — so this converts and calls :meth:`read_rva`.
        """

        return self.read_rva(va - self.image_base, size)

    def read_u32(self, rva: int) -> int:
        """Return the little-endian ``uint32`` at the relative virtual address ``rva``."""

        return struct.unpack("<I", self.read_rva(rva, 4))[0]

    def rva_of_section_offset(self, name: str, offset: int) -> int:
        """Return the relative virtual address at ``offset`` bytes into a section."""

        return self.section(name).virtual_address + offset

    def va_of_section_offset(self, name: str, offset: int) -> int:
        """Return the virtual address at ``offset`` bytes into a section."""

        return self.image_base + self.rva_of_section_offset(name, offset)

    def is_in(self, name: str, rva: int) -> bool:
        """Whether the relative virtual address ``rva`` falls inside section ``name``."""

        return self.section(name).contains(rva)

    def __str__(self) -> str:
        lines = [
            f"{self.path}",
            f"  size on disk  {len(self.data):#x}",
            f"  image base    {self.image_base:#010x}",
            f"  entry point   {self.entry_point:#010x}",
            f"  size of image {self.size_of_image:#x}",
            f"  alignments    section {self.section_alignment:#x} / file {self.file_alignment:#x}",
        ]
        lines.extend(f"  {section}" for section in self.sections)
        return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2

    image = PeImage(argv[0])
    print(image)
    if len(argv) > 2:
        va = int(argv[1], 0)
        size = int(argv[2], 0) if len(argv) > 3 else 64
        data = image.read_va(va, size)
        for offset in range(0, len(data), 16):
            chunk = data[offset : offset + 16]
            hexed = " ".join(f"{byte:02x}" for byte in chunk)
            print(f"  {va + offset:#010x}  {hexed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
