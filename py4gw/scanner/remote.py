"""Read-only scanning of a selected process module."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Protocol

from .scanner import Pattern, Scanner


class _memory_reader(Protocol):
    """The small read-only transport required by ``RemoteScanner``."""

    def read(self, address: int, size: int) -> bytes: ...


@dataclass(frozen=True)
class SectionRange:
    """One virtual section range in a target module."""

    name: str
    start: int
    end: int

    @property
    def size(self) -> int:
        """Return the number of bytes in the section."""

        return self.end - self.start


class RemoteScanner:
    """Scan one external process module through a read-only memory reader."""

    _DOS_SIGNATURE = 0x5A4D
    _PE_SIGNATURE = b"PE\x00\x00"
    _I386_MACHINE = 0x014C
    _PE32_MAGIC = 0x010B
    _SECTION_SIZE = 40
    _DEFAULT_CHUNK_SIZE = 0x10000

    def __init__(
        self,
        reader: _memory_reader,
        module_base: int,
        module_size: int,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Create a scanner for one x86 module in a selected process."""

        if module_base <= 0:
            raise ValueError("module_base must be positive.")
        if module_size <= 0:
            raise ValueError("module_size must be positive.")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        self._reader = reader
        self._module_base = module_base
        self._module_size = module_size
        self._chunk_size = chunk_size
        self._sections: dict[str, SectionRange] = {}

    @property
    def module_base(self) -> int:
        """Return the target module's base address."""

        return self._module_base

    @property
    def module_end(self) -> int:
        """Return the exclusive end of the target module range."""

        return self._module_base + self._module_size

    def initialize(self) -> dict[str, SectionRange]:
        """Read and validate the module PE headers and section table."""

        header_size = min(self._module_size, 0x1000)
        header = self._read(self._module_base, header_size)
        if len(header) < 0x40 or struct.unpack_from("<H", header, 0)[0] != self._DOS_SIGNATURE:
            raise ValueError("Target module does not have a valid DOS header.")

        pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
        if pe_offset + 24 > self._module_size:
            raise ValueError("Target module PE header is outside the module.")
        if pe_offset + 24 > len(header):
            header = self._read(self._module_base, pe_offset + 24)
        if header[pe_offset : pe_offset + 4] != self._PE_SIGNATURE:
            raise ValueError("Target module does not have a valid PE signature.")

        coff_offset = pe_offset + 4
        machine, section_count = struct.unpack_from("<HH", header, coff_offset)
        optional_size = struct.unpack_from("<H", header, coff_offset + 16)[0]
        if machine != self._I386_MACHINE:
            raise ValueError(f"Target module is not x86 (machine=0x{machine:04X}).")
        if section_count == 0:
            raise ValueError("Target module contains no sections.")

        optional_offset = coff_offset + 20
        if optional_offset + optional_size > self._module_size:
            raise ValueError("Target module optional header is outside the module.")
        if optional_offset + optional_size > len(header):
            header = self._read(self._module_base, optional_offset + optional_size)
        optional_magic = struct.unpack_from("<H", header, optional_offset)[0]
        if optional_magic != self._PE32_MAGIC:
            raise ValueError("Target module does not contain a PE32 optional header.")

        section_offset = optional_offset + optional_size
        section_table_size = section_count * self._SECTION_SIZE
        if section_offset + section_table_size > self._module_size:
            raise ValueError("Target module section table is outside the module.")
        if section_offset + section_table_size > len(header):
            header = self._read(
                self._module_base,
                section_offset + section_table_size,
            )

        sections: dict[str, SectionRange] = {}
        for index in range(section_count):
            offset = section_offset + index * self._SECTION_SIZE
            raw_name = header[offset : offset + 8]
            name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")
            virtual_size, virtual_address, raw_size = struct.unpack_from(
                "<III", header, offset + 8
            )
            section_size = max(virtual_size, raw_size)
            start = self._module_base + virtual_address
            end = start + section_size
            if not name or section_size == 0:
                continue
            if start < self._module_base or end > self.module_end:
                raise ValueError(f"Section {name!r} is outside the target module.")
            sections[name] = SectionRange(name, start, end)

        if ".text" not in sections:
            raise ValueError("Target module has no .text section.")
        self._sections = sections
        return dict(sections)

    def get_section_range(self, section: str) -> SectionRange:
        """Return one initialized section range by name."""

        if not self._sections:
            raise RuntimeError("RemoteScanner.initialize() has not been called.")
        normalized = section if section.startswith(".") else f".{section}"
        try:
            return self._sections[normalized]
        except KeyError as error:
            raise ValueError(f"Unknown module section: {section}") from error

    def find(self, pattern: Pattern, section: str = "text") -> int | None:
        """Return the first matching target address in one section."""

        matches = self.find_all(pattern, section=section, limit=1)
        return matches[0] if matches else None

    def find_all(
        self,
        pattern: Pattern,
        section: str = "text",
        limit: int | None = None,
    ) -> list[int]:
        """Return matching addresses from one section using bounded reads."""

        section_range = self.get_section_range(section)
        return self.find_in_range(
            pattern,
            section_range.start,
            section_range.end,
            limit=limit,
        )

    def find_in_range(
        self,
        pattern: Pattern,
        start: int,
        end: int,
        limit: int | None = None,
    ) -> list[int]:
        """Return matches in the half-open target address range."""

        self._validate_target_range(start, end)
        if limit is not None and limit <= 0:
            return []

        if start > end:
            return self._find_descending(pattern, start, end, limit)

        overlap = len(pattern.data) - 1
        matches: list[int] = []
        seen: set[int] = set()
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + self._chunk_size, end)
            read_end = min(chunk_end + overlap, end)
            data = self._read(cursor, read_end - cursor)
            local_scanner = Scanner(data, base_address=cursor)
            local_matches = local_scanner.find_all(pattern)
            for match in local_matches:
                match_start = match - pattern.offset
                if match_start >= chunk_end or match in seen:
                    continue
                seen.add(match)
                matches.append(match)
                if limit is not None and len(matches) >= limit:
                    return matches
            cursor = chunk_end
        return matches

    def _find_descending(
        self,
        pattern: Pattern,
        start: int,
        end: int,
        limit: int | None,
    ) -> list[int]:
        """Scan a half-open range from high addresses toward low addresses."""

        overlap = len(pattern.data) - 1
        matches: list[int] = []
        seen: set[int] = set()
        high = start
        while high > end:
            low = max(end, high - self._chunk_size)
            read_low = max(end, low - overlap)
            read_high = min(start, high + overlap)
            data = self._read(read_low, read_high - read_low)
            local_scanner = Scanner(data, base_address=read_low)
            local_matches = local_scanner.find_all(pattern)
            for match in reversed(local_matches):
                match_start = match - pattern.offset
                if match_start < low or match_start >= high or match in seen:
                    continue
                seen.add(match)
                matches.append(match)
                if limit is not None and len(matches) >= limit:
                    return matches
            high = low
        return matches

    def is_valid_ptr(self, address: int, section: str = "data") -> bool:
        """Return whether an address lies inside an initialized section."""

        section_range = self.get_section_range(section)
        return section_range.start <= address < section_range.end

    def find_use_of_address(
        self,
        address: int,
        offset: int = 0,
        section: str = "text",
    ) -> int | None:
        """Find the first x86 little-endian use of a target address."""

        pattern = Pattern(address.to_bytes(4, "little"), "xxxx", offset)
        return self.find(pattern, section)

    def find_nth_use_of_address(
        self,
        address: int,
        occurrence: int,
        offset: int = 0,
        section: str = "text",
    ) -> int | None:
        """Find a zero-based occurrence of a target address use."""

        if occurrence < 0:
            raise ValueError("occurrence cannot be negative.")
        pattern = Pattern(address.to_bytes(4, "little"), "xxxx", offset)
        matches = self.find_all(pattern, section, limit=occurrence + 1)
        return matches[occurrence] if len(matches) > occurrence else None

    def find_use_of_string(
        self,
        value: str,
        offset: int = 0,
        section: str = "text",
        wide: bool = False,
    ) -> int | None:
        """Find the first code use of an ANSI or UTF-16 string literal."""

        return self.find_nth_use_of_string(value, 0, offset, section, wide)

    def find_nth_use_of_string(
        self,
        value: str,
        occurrence: int,
        offset: int = 0,
        section: str = "text",
        wide: bool = False,
    ) -> int | None:
        """Find a zero-based code use of a string stored in ``.rdata``."""

        if occurrence < 0:
            raise ValueError("occurrence cannot be negative.")
        literal_addresses = self._find_rdata_literal_addresses(value, wide)
        if not literal_addresses:
            return None
        literal_address = literal_addresses[0]
        matches = self.find_all(
            Pattern(literal_address.to_bytes(4, "little"), "xxxx", offset),
            section,
            limit=occurrence + 1,
        )
        return matches[occurrence] if len(matches) > occurrence else None

    def find_assertion(
        self,
        assertion_file: str,
        assertion_message: str,
        line_number: int = 0,
        offset: int = 0,
    ) -> int | None:
        """Find the x86 assertion call sequence used by Reforged Native."""

        if line_number < 0 or line_number > 0xFFFFFFFF:
            raise ValueError("line_number must fit in an unsigned 32-bit value.")
        file_addresses = self._find_assertion_file_addresses(assertion_file)
        message_addresses = self._find_rdata_literal_addresses(assertion_message, False)
        if not file_addresses or not message_addresses:
            return None

        line_prefixes = [b""]
        if line_number:
            line_prefixes = []
            if line_number <= 0xFF:
                line_prefixes.append(b"\x6A" + bytes((line_number,)))
            line_prefixes.append(b"\x68" + line_number.to_bytes(4, "little"))

        matches: list[int] = []
        for file_address in file_addresses:
            for message_address in message_addresses:
                file_bytes = file_address.to_bytes(4, "little")
                message_bytes = message_address.to_bytes(4, "little")
                for line_prefix in line_prefixes:
                    pattern_data = (
                        line_prefix + b"\xBA" + file_bytes + b"\xB9" + message_bytes
                    )
                    found = self.find(
                        Pattern(pattern_data, "x" * len(pattern_data), offset)
                    )
                    if found is not None:
                        matches.append(found)
        return min(matches) if matches else None

    def _find_assertion_file_addresses(self, assertion_file: str) -> list[int]:
        """Find assertion file addresses using the native suffix behavior."""

        matches = self._find_rdata_literal_addresses(assertion_file, False)
        if not matches:
            return []

        rdata = self.get_section_range("rdata")
        addresses: list[int] = []
        for match in matches:
            # Native FileScanner accepts a filename suffix and walks backward
            # to the drive-colon in a full source path before building the
            # assertion reference. Keep the direct match when no colon exists,
            # which also preserves short synthetic test strings.
            start = max(rdata.start, match - 128)
            colon = self.find_in_range(
                Pattern(b":", "x"), match, start, limit=1
            )
            # Native FindInRange applies an offset of -1 to that colon,
            # producing the first character of the drive-qualified path.
            addresses.append(colon[0] - 1 if colon else match)
        return addresses

    def read_uint32(self, address: int) -> int:
        """Read one little-endian x86 pointer-sized integer."""

        return int.from_bytes(self._read(address, 4), "little")

    def function_from_near_call(
        self,
        call_address: int,
        check_valid_ptr: bool = True,
        max_depth: int = 32,
    ) -> int | None:
        """Resolve x86 near-call/jump chains to their final target."""

        if not self.is_valid_ptr(call_address, "text"):
            return None
        if max_depth <= 0:
            raise ValueError("max_depth must be positive.")
        current = call_address
        visited: set[int] = set()
        for _ in range(max_depth):
            if current in visited:
                return None
            visited.add(current)
            opcode = self._read(current, 1)[0]
            if opcode in (0xE8, 0xE9):
                displacement = struct.unpack("<i", self._read(current + 1, 4))[0]
                target = current + 5 + displacement
            elif opcode == 0xEB:
                displacement = struct.unpack("<b", self._read(current + 1, 1))[0]
                target = current + 2 + displacement
            else:
                return current if current != call_address else None
            if check_valid_ptr and not self.is_valid_ptr(target, "text"):
                return None
            current = target
        return None

    def to_function_start(self, address: int, scan_range: int = 0xFF) -> int | None:
        """Find the last x86 ``push ebp; mov ebp, esp`` before an address."""

        if address <= 0:
            return None
        if scan_range < 0:
            raise ValueError("scan_range cannot be negative.")
        section = self.get_section_range("text")
        start = max(section.start, min(section.end, address + 3))
        end = max(section.start, min(section.end, address - scan_range))
        if start <= end:
            return None
        pattern = Pattern(b"\x55\x8B\xEC", "xxx")
        matches = self.find_in_range(pattern, start, end)
        return matches[0] if matches else None

    def _validate_target_range(self, start: int, end: int) -> None:
        """Reject ranges outside the selected module."""

        if (
            start < self._module_base
            or start > self.module_end
            or end < self._module_base
            or end > self.module_end
        ):
            raise ValueError("Scan range endpoints must be inside the target module.")

    def _find_rdata_literal_addresses(self, value: str, wide: bool) -> list[int]:
        """Return literal addresses, preferring native null-terminated data."""

        encoded = value.encode("utf-16-le" if wide else "mbcs")
        if not encoded:
            return []
        terminator = b"\x00\x00" if wide else b"\x00"
        with_terminator = Pattern(
            encoded + terminator,
            "x" * (len(encoded) + len(terminator)),
        )
        addresses = self.find_all(with_terminator, "rdata")
        if addresses:
            return addresses
        # Some mapped/synthetic images expose only the literal bytes. Keep a
        # bounded fallback so the scanner remains useful for those images.
        return self.find_all(Pattern(encoded, "x" * len(encoded)), "rdata")

    def _read(self, address: int, size: int) -> bytes:
        """Read bytes and preserve the address context on failure."""

        try:
            data = self._reader.read(address, size)
        except OSError as error:
            raise OSError(
                error.errno,
                f"Remote read failed at 0x{address:X} for 0x{size:X} bytes: {error}",
            ) from error
        if len(data) != size:
            raise OSError(
                299,
                f"Remote read returned 0x{len(data):X} of 0x{size:X} bytes "
                f"at 0x{address:X}.",
            )
        return data
