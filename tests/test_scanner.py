"""Offline tests for the reusable scanner's matching contract."""

from __future__ import annotations

import unittest

from py4gw import Pattern, Scanner


class ScannerTests(unittest.TestCase):
    """Verify matching without opening a process."""

    def test_decodes_reforged_literal_and_finds_address(self) -> None:
        """Escaped offsets literals produce the expected target address."""

        scanner = Scanner(b"\x90\x8b\x0c\x90\x85\xc9\x74\x19\x90", 0x1000)
        pattern = Pattern.from_literal(
            r"\x8b\x0c\x90\x85\xc9\x74\x19", "xxxxxxx"
        )

        self.assertEqual(scanner.find(pattern), 0x1001)

    def test_wildcards_and_offset_are_applied(self) -> None:
        """Wildcard bytes match and the native-style offset is returned."""

        scanner = Scanner(b"\x90\x8b\x12\x90\x85\xc9\x74\x19\x90", 0x2000)
        pattern = Pattern.from_literal(
            r"\x8b\x00\x90\x85\xc9\x74\x19", "x?xxxxx", offset=-2
        )

        self.assertEqual(scanner.find(pattern), 0x1FFF)

    def test_find_all_supports_overlapping_matches(self) -> None:
        """All matches include overlapping occurrences."""

        scanner = Scanner(b"aaaa", 0x3000)
        pattern = Pattern.from_literal("aa")

        self.assertEqual(scanner.find_all(pattern), [0x3000, 0x3001, 0x3002])

    def test_find_nth_uses_zero_based_occurrences(self) -> None:
        """The first occurrence is number zero, matching native usage."""

        scanner = Scanner(b"xxABxxAB", 0x4000)
        pattern = Pattern.from_literal("AB")

        self.assertEqual(scanner.find_nth(pattern, 0), 0x4002)
        self.assertEqual(scanner.find_nth(pattern, 1), 0x4006)
        self.assertIsNone(scanner.find_nth(pattern, 2))

    def test_range_is_half_open(self) -> None:
        """A match ending at the range boundary is included."""

        scanner = Scanner(b"xxAByyAB", 0x5000)
        pattern = Pattern.from_literal("AB")

        self.assertEqual(scanner.find(pattern, start=2, end=4), 0x5002)
        self.assertIsNone(scanner.find(pattern, start=3, end=4))

    def test_invalid_pattern_is_rejected(self) -> None:
        """Malformed data and masks fail before scanning begins."""

        with self.assertRaises(ValueError):
            Pattern(data=b"\x90", mask="xx")

        with self.assertRaises(ValueError):
            Pattern.from_literal(r"\x90", "z")

    def test_literal_loader_preserves_native_c_string_behavior(self) -> None:
        """Offsets masks retain the native implicit-NUL and length rules."""

        with_terminator = Pattern.from_literal("AB", "xxx")
        self.assertEqual(with_terminator.data, b"AB\x00")

        shorter_mask = Pattern.from_literal("ABC", "xx")
        self.assertEqual(shorter_mask.data, b"AB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
