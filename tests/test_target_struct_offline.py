"""Offline checks for readable target-structure values and printing.

These use local ``ctypes`` values only.  No process is opened or read.
"""

from __future__ import annotations

import ctypes
import sys
import unittest
from ctypes import c_char, c_float, c_uint8, c_uint16, c_uint32
from typing import Any, cast

from py4gw.helpers.target_struct import Describable, TargetStruct, describe_value, format_value


class _Inner(TargetStruct):
    _pack_ = 1
    _fields_ = [("item_id", c_uint32), ("ratio", c_float)]


class _Outer(TargetStruct):
    _pack_ = 1
    _fields_ = [
        ("name", c_uint16 * 8),
        ("tag", c_char * 4),
        ("counts", c_uint32 * 3),
        ("blob", c_uint8 * 20),
        ("inner", _Inner),
        ("inners", _Inner * 2),
        ("flag", c_uint32),
    ]


def _sample() -> _Outer:
    value = _Outer()
    for index, code in enumerate("Fezzik"):
        value.name[index] = ord(code)
    value.tag = b"GW\x00\x00"
    value.counts = (c_uint32 * 3)(7, 8, 9)
    value.blob = (c_uint8 * 20)(*range(20))
    value.inner = _Inner(item_id=449, ratio=1.5)
    value.inners[0] = _Inner(item_id=1, ratio=0.5)
    value.inners[1] = _Inner(item_id=2, ratio=0.25)
    value.flag = 200
    return value


class DescribeValueTests(unittest.TestCase):
    """Verify each value form is decoded to data."""

    def test_scalars_pass_through(self) -> None:
        self.assertEqual(describe_value(449), 449)
        self.assertEqual(describe_value(1.5), 1.5)

    def test_wide_character_array_becomes_text(self) -> None:
        buffer = (c_uint16 * 8)()
        for index, code in enumerate("Fezzik"):
            buffer[index] = ord(code)
        self.assertEqual(describe_value(buffer), "Fezzik")

    def test_narrow_character_bytes_become_text(self) -> None:
        # ctypes returns c_char array fields as bytes, so bytes is the input.
        self.assertEqual(describe_value(b"GW\x00\x00"), "GW")

    def test_non_text_byte_array_becomes_numbers(self) -> None:
        value = (c_uint8 * 20)(*range(20))
        self.assertEqual(describe_value(value), list(range(20)))

    def test_binary_bytes_stay_bytes(self) -> None:
        self.assertEqual(describe_value(b"\x01\x02\x03\x04"), b"\x01\x02\x03\x04")

    def test_zero_leading_byte_array_is_not_an_empty_string(self) -> None:
        self.assertEqual(describe_value((c_uint8 * 3)(0, 1, 2)), [0, 1, 2])

    def test_numeric_array_becomes_a_list(self) -> None:
        self.assertEqual(
            describe_value((c_uint32 * 3)(7, 8, 9)),
            [7, 8, 9],
        )

    def test_embedded_record_becomes_a_dict(self) -> None:
        self.assertEqual(
            describe_value(_Inner(item_id=449, ratio=1.5)),
            {"item_id": 449, "ratio": 1.5},
        )

    def test_array_of_records_becomes_a_list_of_dicts(self) -> None:
        items = _Inner * 2
        values = items(_Inner(item_id=1, ratio=0.5), _Inner(item_id=2, ratio=0.25))
        self.assertEqual(
            describe_value(values),
            [{"item_id": 1, "ratio": 0.5}, {"item_id": 2, "ratio": 0.25}],
        )


class TargetStructApiTests(unittest.TestCase):
    """Verify the public helpers on a structure."""

    def test_to_dict_decodes_every_field_completely(self) -> None:
        data = _sample().to_dict()
        self.assertEqual(data["name"], "Fezzik")
        self.assertEqual(data["tag"], "GW")
        self.assertEqual(data["counts"], [7, 8, 9])
        self.assertEqual(data["blob"], list(range(20)))
        self.assertEqual(data["inner"], {"item_id": 449, "ratio": 1.5})
        self.assertEqual(data["flag"], 200)
        self.assertEqual(len(data["inners"]), 2)

    def test_items_yields_fields_in_layout_order(self) -> None:
        names = [name for name, _ in _sample().iter_fields()]
        self.assertEqual(names, [entry[0] for entry in _Outer._fields_])

    def test_iter_fields_does_not_collide_with_an_items_field(self) -> None:
        class _HasItemsField(TargetStruct):
            _pack_ = 1
            _fields_ = cast(Any, [("items", c_uint32), ("other", c_uint32)])

        value = _HasItemsField()
        value.items = 5
        value.other = 6
        self.assertEqual(value.to_dict(), {"items": 5, "other": 6})
        self.assertEqual([n for n, _ in value.iter_fields()], ["items", "other"])

    def test_describe_matches_to_dict(self) -> None:
        value = _sample()
        self.assertEqual(value.describe(), value.to_dict())

    def test_raw_attributes_keep_their_source_types(self) -> None:
        value = _sample()
        self.assertIsInstance(value.name, ctypes.Array)
        self.assertEqual(value.flag, 200)


class DescribableTests(unittest.TestCase):
    """Verify plain records get the same API as target structures."""

    def test_slots_dataclass_reports_its_fields(self) -> None:
        from dataclasses import dataclass

        @dataclass(slots=True, repr=False)
        class _Record(Describable):
            agent_id: int
            name: str
            flags: tuple[int, ...]

        record = _Record(agent_id=7, name="Fezzik", flags=(1, 2, 3))
        self.assertEqual(
            record.to_dict(),
            {"agent_id": 7, "name": "Fezzik", "flags": (1, 2, 3)},
        )
        self.assertEqual(
            [n for n, _ in record.iter_fields()], ["agent_id", "name", "flags"]
        )
        self.assertIn("agent_id = 7", repr(record))
        self.assertTrue(repr(record).startswith("_Record("))

    def test_frozen_dataclass_reports_its_fields(self) -> None:
        from dataclasses import dataclass

        @dataclass(frozen=True, repr=False)
        class _Frozen(Describable):
            value: int

        self.assertEqual(_Frozen(value=5).to_dict(), {"value": 5})

    def test_slots_record_keeps_slot_only_storage(self) -> None:
        from dataclasses import dataclass

        @dataclass(slots=True, repr=False)
        class _Slotted(Describable):
            value: int

        self.assertFalse(hasattr(_Slotted(value=1), "__dict__"))

    def test_nested_record_is_described(self) -> None:
        from dataclasses import dataclass

        @dataclass(frozen=True, repr=False)
        class _NestedRecord(Describable):
            item_id: int

        @dataclass(frozen=True, repr=False)
        class _WrapperRecord(Describable):
            inner: _NestedRecord

        wrapped = _WrapperRecord(inner=_NestedRecord(item_id=449))
        self.assertEqual(wrapped.to_dict(), {"inner": {"item_id": 449}})
        self.assertIn("inner = {item_id=449}", repr(wrapped))


class ConsoleSafetyTests(unittest.TestCase):
    """Verify printed output survives a console that cannot encode it.

    Game text contains characters a Windows console cannot represent, and
    writing those raises ``UnicodeEncodeError``. The escaping lives in the
    library so no caller has to configure stdout.
    """

    def _with_encoding(self, encoding: str | None, text: str) -> str:
        class _FakeStdout:
            pass

        fake = _FakeStdout()
        fake.encoding = encoding  # type: ignore[attr-defined]
        held = sys.stdout
        sys.stdout = cast(Any, fake)
        try:
            return format_value(text)
        finally:
            sys.stdout = held

    def test_unencodable_characters_are_escaped(self) -> None:
        rendered = self._with_encoding("cp1252", "sue\u00f1o \ufffd end")
        self.assertTrue(rendered.isascii())
        self.assertIn("sue", rendered)
        self.assertIn("end", rendered)

    def test_readable_characters_are_left_alone(self) -> None:
        rendered = self._with_encoding("utf-8", "sue\u00f1o")
        self.assertIn("\u00f1", rendered)
        self.assertFalse(rendered.isascii())

    def test_encoding_that_can_represent_the_text_is_unchanged(self) -> None:
        rendered = self._with_encoding("cp1252", "Coran Ironclaw")
        self.assertIn("Coran Ironclaw", rendered)

    def test_unknown_encoding_is_not_fatal(self) -> None:
        rendered = self._with_encoding("not-a-codec", "sue\u00f1o")
        self.assertTrue(rendered.isascii())

    def test_missing_encoding_is_not_fatal(self) -> None:
        rendered = self._with_encoding(None, "sue\u00f1o")
        self.assertIn("sue", rendered)

    def test_escaped_output_actually_prints(self) -> None:
        import io

        buffer = io.StringIO()
        held = sys.stdout
        sys.stdout = buffer
        try:
            print(self._with_encoding("cp1252", "\ufffd"))
        finally:
            sys.stdout = held
        self.assertTrue(buffer.getvalue().strip())

    def test_to_dict_keeps_the_real_text(self) -> None:
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class _TextRecord(Describable):
            text: str

        real = "sue\u00f1o \ufffd a\u00f1os"
        self.assertEqual(_TextRecord(text=real).to_dict(), {"text": real})


class ReprTests(unittest.TestCase):
    """Verify the printed form lists every field and stays readable."""

    def test_repr_names_every_field(self) -> None:
        text = repr(_sample())
        for entry in _Outer._fields_:
            self.assertIn(entry[0], text)

    def test_repr_decodes_values(self) -> None:
        text = repr(_sample())
        self.assertIn("'Fezzik'", text)
        self.assertIn("'GW'", text)
        self.assertIn("item_id=449", text)

    def test_repr_shortens_long_sequences_only(self) -> None:
        value = _sample()
        self.assertIn("+12 more", repr(value))
        self.assertEqual(len(value.to_dict()["blob"]), 20)

    def test_long_tuples_are_shortened_too(self) -> None:
        self.assertEqual(
            format_value(tuple(range(20))),
            "(0, 1, 2, 3, 4, 5, 6, 7, ... +12 more)",
        )
        self.assertEqual(format_value(tuple(range(3))), "(0, 1, 2)")
        self.assertEqual(format_value([1, 2, 3]), "[1, 2, 3]")

    def test_repr_is_multiline_and_named(self) -> None:
        lines = repr(_sample()).splitlines()
        self.assertEqual(lines[0], "_Outer(")
        self.assertEqual(lines[-1], ")")
        self.assertGreater(len(lines), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
