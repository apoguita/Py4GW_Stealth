"""Offline tests for copied offsets definitions and resolver chains."""

from __future__ import annotations

import contextlib
import json
import shutil
import unittest
from collections.abc import Iterator
from pathlib import Path

from py4gw import PatternCatalog


@contextlib.contextmanager
def fixture_directory(name: str) -> Iterator[Path]:
    """Yield a scratch catalog directory beside this test file.

    Nothing is written to a temporary or hidden location. The fixture is created
    in this test's own folder, so it is visible while the test runs, and removed
    when the test finishes. Each fixture gets its own directory because
    ``PatternCatalog.from_directory`` loads every ``*.json`` it finds.
    """

    directory = Path(__file__).resolve().parent / name
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


class _TestScanner:
    """Small scanner double for resolver execution tests."""

    def find(self, pattern: object, section: str = "text") -> int | None:
        """Return one deterministic scan address."""

        return 0x1000

    def find_in_range(
        self,
        pattern: object,
        start: int,
        end: int,
        limit: int | None = None,
    ) -> list[int]:
        """Return one deterministic range match."""

        return [start] if start < end else []

    def find_assertion(
        self,
        assertion_file: str,
        assertion_message: str,
        line_number: int = 0,
        offset: int = 0,
    ) -> int | None:
        """Return no assertion for this focused test double."""

        return None

    def find_nth_use_of_string(
        self,
        value: str,
        occurrence: int,
        offset: int = 0,
        section: str = "text",
        wide: bool = False,
    ) -> int | None:
        """Return no string use for this focused test double."""

        return None

    def function_from_near_call(
        self,
        call_address: int,
        check_valid_ptr: bool = True,
    ) -> int | None:
        """Return no call target for this focused test double."""

        return None

    def to_function_start(self, address: int, scan_range: int = 0xFF) -> int | None:
        """Return no function start for this focused test double."""

        return None

    def is_valid_ptr(self, address: int, section: str = "data") -> bool:
        """Accept one deterministic pointer for the test."""

        return address != 0

    def read_uint32(self, address: int) -> int:
        """Return one deterministic pointer-sized value."""

        return address + 4


class _AssertionScanner(_TestScanner):
    """Record the offset passed to a native-style assertion search."""

    def __init__(self) -> None:
        self.assertion_offset: int | None = None

    def find_assertion(
        self,
        assertion_file: str,
        assertion_message: str,
        line_number: int = 0,
        offset: int = 0,
    ) -> int | None:
        self.assertion_offset = offset
        return 0x1000 + offset


class PatternCatalogTests(unittest.TestCase):
    """Verify the copied schema and resolver trace behavior."""

    def test_loads_copied_offsets_directory(self) -> None:
        """All copied pattern and resolver files load through one catalog."""

        catalog = PatternCatalog.from_directory("offsets")

        self.assertIsNotNone(catalog.get_pattern("agent.agent_array_ref"))
        self.assertIsNotNone(catalog.get_resolver("agent.agent_array_addr"))

    def test_resolves_a_chain_and_keeps_trace(self) -> None:
        """A resolver applies its steps and records each operation."""

        with fixture_directory("pattern_fixture_demo") as directory:
            path = directory / "demo.json"
            path.write_text(
                json.dumps(
                    {
                        "namespace": "demo",
                        "patterns": {"anchor": {"pattern": "AB"}},
                        "resolvers": {
                            "value": {
                                "steps": [
                                    {
                                        "name": "scan",
                                        "op": "scan",
                                        "pattern": "anchor",
                                        "out": "scan",
                                    },
                                    {
                                        "name": "adjust",
                                        "op": "add",
                                        "in": "scan",
                                        "value": "0x20",
                                        "out": "final",
                                    },
                                ]
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            catalog = PatternCatalog.from_directory(directory)

        result = catalog.resolve("demo.value", _TestScanner())

        self.assertTrue(result.ok)
        self.assertEqual(result.value, 0x1020)
        self.assertEqual([step.name for step in result.trace], ["scan", "adjust"])

    def test_passes_assertion_offset_from_json(self) -> None:
        """Assertion resolvers preserve the native JSON result offset."""

        with fixture_directory("pattern_fixture_assertion") as directory:
            path = directory / "assertion.json"
            path.write_text(
                json.dumps(
                    {
                        "namespace": "demo",
                        "patterns": {
                            "assertion": {
                                "assertion_file": "UiPregame.cpp",
                                "assertion_message": "!s_scene",
                                "offset": "0x32",
                            }
                        },
                        "resolvers": {
                            "value": {
                                "steps": [
                                    {
                                        "name": "scan",
                                        "op": "scan",
                                        "pattern": "assertion",
                                        "out": "final",
                                    }
                                ]
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            catalog = PatternCatalog.from_directory(directory)

        scanner = _AssertionScanner()
        result = catalog.resolve("demo.value", scanner)

        self.assertTrue(result.ok)
        self.assertEqual(result.value, 0x1032)
        self.assertEqual(scanner.assertion_offset, 0x32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
