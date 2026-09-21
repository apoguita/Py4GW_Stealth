"""The offline core of the reusable pattern scanner.

This module deliberately scans a byte snapshot instead of opening a process.
The same matching contract will later be used by the external memory reader.
"""

from __future__ import annotations

from dataclasses import dataclass


def _decode_pattern_literal(literal: str) -> bytes:
    """Decode the escaped byte-string format used by the offsets JSON files."""

    result = bytearray()
    index = 0
    while index < len(literal):
        character = literal[index]
        if character != "\\":
            code_point = ord(character)
            if code_point > 0xFF:
                raise ValueError(
                    "Pattern literals may only contain single-byte characters."
                )
            result.append(code_point)
            index += 1
            continue

        index += 1
        if index >= len(literal):
            raise ValueError("Pattern literal ends with an incomplete escape.")

        escape = literal[index]
        if escape == "x":
            if index + 2 >= len(literal):
                raise ValueError("Hex pattern escape must contain two digits.")
            digits = literal[index + 1 : index + 3]
            try:
                result.append(int(digits, 16))
            except ValueError as error:
                raise ValueError(
                    f"Invalid hex pattern escape: \\x{digits}"
                ) from error
            index += 3
            continue

        escaped_bytes = {
            "0": b"\x00",
            "\\": b"\\",
            "n": b"\n",
            "r": b"\r",
            "t": b"\t",
        }
        if escape in escaped_bytes:
            result.extend(escaped_bytes[escape])
        else:
            result.append(ord(escape))
        index += 1

    return bytes(result)


@dataclass(frozen=True)
class Pattern:
    """One byte pattern in the Reforged pattern/mask format.

    ``x`` in the mask means that the corresponding byte must match. ``?``
    means that the byte is a wildcard. ``offset`` is applied to a match
    address after the pattern has been found.
    """

    data: bytes
    mask: str
    offset: int = 0

    def __post_init__(self) -> None:
        """Reject malformed patterns before they reach the scanner."""

        if not self.data:
            raise ValueError("A pattern must contain at least one byte.")
        if len(self.mask) != len(self.data):
            raise ValueError("Pattern data and mask must have equal lengths.")
        if any(character not in "xX?" for character in self.mask):
            raise ValueError("Pattern masks may contain only 'x' and '?'.")

    @classmethod
    def from_literal(
        cls,
        literal: str,
        mask: str | None = None,
        offset: int = 0,
    ) -> Pattern:
        """Create a pattern from an escaped offsets-file literal."""

        data = _decode_pattern_literal(literal)
        selected_mask = "x" * len(data) if mask is None else mask
        if mask is not None and len(mask) == len(data) + 1:
            # The native loader passes pattern.c_str() to the scanner. The
            # final mask position can therefore match that implicit NUL.
            data += b"\x00"
        elif mask is not None and len(mask) < len(data):
            # Native FileScanner uses the mask length as the scan length.
            data = data[: len(mask)]
        return cls(data=data, mask=selected_mask, offset=offset)


class Scanner:
    """Search one validated byte snapshot for scanner patterns.

    The snapshot is addressed as if it began at ``base_address``. This keeps
    the matching logic independent from the future process-memory transport.
    """

    def __init__(self, data: bytes, base_address: int = 0) -> None:
        """Create a scanner over ``data`` at a target-relative base address."""

        if base_address < 0:
            raise ValueError("base_address cannot be negative.")
        self._data = bytes(data)
        self._base_address = base_address

    def find(
        self,
        pattern: Pattern,
        start: int = 0,
        end: int | None = None,
    ) -> int | None:
        """Return the first matching address, or ``None`` when not found."""

        matches = self.find_all(pattern, start=start, end=end, limit=1)
        return matches[0] if matches else None

    def find_all(
        self,
        pattern: Pattern,
        start: int = 0,
        end: int | None = None,
        limit: int | None = None,
    ) -> list[int]:
        """Return matching addresses in the requested half-open byte range."""

        range_start, range_end = self._validate_range(start, end)
        pattern_length = len(pattern.data)
        last_start = range_end - pattern_length
        if last_start < range_start:
            return []

        matches: list[int] = []
        exact_indexes = [
            index
            for index, mask_character in enumerate(pattern.mask)
            if mask_character.casefold() == "x"
        ]
        anchor_index = exact_indexes[0] if exact_indexes else None
        candidate = range_start
        while candidate <= last_start:
            if anchor_index is not None:
                anchor = pattern.data[anchor_index]
                found = self._data.find(
                    bytes((anchor,)),
                    candidate + anchor_index,
                    last_start + anchor_index + 1,
                )
                if found < 0:
                    break
                candidate = found - anchor_index

            if self._matches_at(pattern, candidate):
                matches.append(self._base_address + candidate + pattern.offset)
                if limit is not None and len(matches) >= limit:
                    break
            candidate += 1

        return matches

    def find_nth(
        self,
        pattern: Pattern,
        occurrence: int,
        start: int = 0,
        end: int | None = None,
    ) -> int | None:
        """Return the zero-based occurrence address, or ``None``."""

        if occurrence < 0:
            raise ValueError("occurrence cannot be negative.")
        matches = self.find_all(pattern, start=start, end=end, limit=occurrence + 1)
        return matches[occurrence] if len(matches) > occurrence else None

    def _matches_at(self, pattern: Pattern, position: int) -> bool:
        """Check one candidate position against a pattern and mask."""

        for index, mask_character in enumerate(pattern.mask):
            if (
                mask_character.casefold() == "x"
                and self._data[position + index] != pattern.data[index]
            ):
                return False
        return True

    def _validate_range(self, start: int, end: int | None) -> tuple[int, int]:
        """Validate and normalize a half-open range within the snapshot."""

        selected_end = len(self._data) if end is None else end
        if start < 0 or selected_end < start or selected_end > len(self._data):
            raise ValueError("Scan range must be inside the byte snapshot.")
        return start, selected_end
