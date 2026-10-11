"""Offline tests for `py4gw/gwa3/data_attribute.py` -- GwAu3's attribute reader, whole file.

No client. The file's seven members read two structures this project already has, so what is pinned here
is the **mapping**: five fields of the attribute-constant record, the party block's five attribute fields
at GwAu3's own offsets, the two point words after the 45 records, and the source's own guard order --
including the two keys the source reads as **signed**, which is a difference a caller sees.
"""

from __future__ import annotations

import ctypes
import unittest
from unittest import mock

from py4gw.context.world_context import AttributeInfoStruct, AttributeStruct, PartyAttributeStruct
from py4gw.gwa3 import data_attribute


class _World:
    """A world context with the party-attribute blocks a caller asks about."""

    def __init__(self, blocks: list[PartyAttributeStruct]) -> None:
        self.party_attributes = blocks


class _Client:
    def __init__(self, world: _World | None) -> None:
        self._world = world

    def read_world_context(self) -> _World | None:
        return self._world


def _block(
    agent_id: int,
    records: dict[int, tuple[int, int, int, int]] | None = None,
    unused_points: int = 0,
    total_points: int = 0,
) -> PartyAttributeStruct:
    """A party block, with the attribute records and the two trailing point words set."""

    block = PartyAttributeStruct()
    block.agent_id = agent_id
    for index, (base, level, decrement, increment) in (records or {}).items():
        block.attribute_array[index].attribute_id = index
        block.attribute_array[index].level_base = base
        block.attribute_array[index].level = level
        block.attribute_array[index].decrement_points = decrement
        block.attribute_array[index].increment_points = increment
    ctypes.memmove(ctypes.addressof(block) + 0x434, ctypes.byref(ctypes.c_uint32(unused_points)), 4)
    ctypes.memmove(
        ctypes.addressof(block) + 0x438, ctypes.byref(ctypes.c_uint32(total_points)), 4
    )
    return block


class AttributeNameTests(unittest.TestCase):
    def test_the_name_table_answers_inside_the_sources_range(self) -> None:
        self.assertEqual(data_attribute.Attribute_GetAttributeName(0), "Fast Casting")
        self.assertEqual(data_attribute.Attribute_GetAttributeName(44), "Mysticism")

    def test_outside_the_range_answers_unknown(self) -> None:
        """``If $a_i_AttributeID >= 0 And $a_i_AttributeID < 45`` -- and ``"Unknown"`` otherwise."""

        for attribute in (-1, 45, 999):
            with self.subTest(attribute=attribute):
                self.assertEqual(data_attribute.Attribute_GetAttributeName(attribute), "Unknown")


class AttributeInfoTests(unittest.TestCase):
    """`Attribute_GetAttributePtr` and `Attribute_GetAttributeInfo`, over the constant table."""

    def _serve(self, record: AttributeInfoStruct | None) -> None:
        patch = mock.patch.object(
            data_attribute, "Attribute_GetAttributePtr", lambda attribute_id: record
        )
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_five_fields_are_the_records_own(self) -> None:
        record = AttributeInfoStruct()
        record.profession_id = 5
        record.attribute_id = 0
        record.name_id = 1234
        record.desc_id = 5678
        record.is_pve = 1
        self._serve(record)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(0, "ProfessionID"), 5)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(0, "AttributeID"), 0)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(0, "NameID"), 1234)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(0, "DescID"), 5678)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(0, "IsPVE"), 1)

    def test_an_empty_field_name_answers_zero_before_the_table_is_read(self) -> None:
        """``:22`` -- and unlike the party form, it does **not** answer the record for an empty name."""

        with mock.patch.object(data_attribute, "Attribute_GetAttributePtr") as accessor:
            self.assertEqual(data_attribute.Attribute_GetAttributeInfo(3, ""), 0)
            accessor.assert_not_called()

    def test_no_record_answers_zero_and_an_unknown_field_does_too(self) -> None:
        self._serve(None)
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(3, "ProfessionID"), 0)
        self._serve(AttributeInfoStruct())
        self.assertEqual(data_attribute.Attribute_GetAttributeInfo(3, "Nonsense"), 0)


class PartyAttributeTests(unittest.TestCase):
    """`Attribute_GetPartyAttributeInfo` and `Attribute_GetPartyAttributePointInfo`."""

    AGENT = 35

    def _serve(self, blocks: list[PartyAttributeStruct], agent_id: int = AGENT) -> None:
        patches = [
            mock.patch.object(data_attribute, "Agent_GetMyID", lambda: agent_id),
            mock.patch.object(
                data_attribute, "Party_GetMyPartyHeroInfo", lambda hero, key="": 777
            ),
            mock.patch.object(
                data_attribute,
                "require_client",
                lambda: _Client(_World(blocks)),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def _one_block(self) -> PartyAttributeStruct:
        return _block(
            self.AGENT,
            records={5: (12, 14, 0xFFFFFFFF, 3)},
            unused_points=9,
            total_points=200,
        )

    def test_the_five_attribute_fields_are_at_the_sources_offsets(self) -> None:
        self._serve([self._one_block()])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "AttributeID"), 5)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "BaseLevel"), 12)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "Level"), 14)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "LevelBase"), 12)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "CurrentLevel"), 14)

    def test_the_computed_keys_are_the_sources_arithmetic(self) -> None:
        self._serve([self._one_block()])
        self.assertTrue(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "HasAttribute"))
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "BonusLevel"), 2)
        self.assertTrue(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "IsMaxed"))
        self.assertTrue(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "IsRaisable"))
        self.assertFalse(data_attribute.Attribute_GetPartyAttributeInfo(1, 0, "HasAttribute"))

    def test_the_two_point_keys_are_read_as_signed_like_the_source(self) -> None:
        """``DecrementPoints`` is ``-1`` here, which the source's ``"long"`` read answers ``False`` for."""

        self._serve([self._one_block()])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "DecrementPoints"), -1)
        self.assertFalse(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "IsDecreasable"))

    def test_an_empty_field_name_answers_the_block(self) -> None:
        """``:56`` -- the pointer the source answers, as the record here."""

        block = self._one_block()
        self._serve([block])
        self.assertIs(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, ""), block)

    def test_an_agent_the_array_does_not_hold_answers_zero(self) -> None:
        self._serve([_block(999)])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "Level"), 0)

    def test_a_hero_number_resolves_that_heros_agent_id_first(self) -> None:
        self._serve([_block(777, records={2: (4, 6, 0, 1)})])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(2, 3, "Level"), 6)

    def test_the_point_words_sit_after_the_forty_five_records(self) -> None:
        """``0x14 * 45 + 0xB0`` for ``UnusedPoints`` and four bytes on for ``TotalPoints`` (``:116-127``)."""

        self._serve([self._one_block()])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributePointInfo(0, "UnusedPoints"), 9)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributePointInfo(0, "TotalPoints"), 200)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributePointInfo(0, "Nonsense"), 0)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributePointInfo(4, "UnusedPoints"), 0)

    def test_the_party_form_forwards_the_two_point_keys(self) -> None:
        self._serve([self._one_block()])
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "UnusedPoints"), 9)
        self.assertEqual(data_attribute.Attribute_GetPartyAttributeInfo(5, 0, "TotalPoints"), 200)


class ProfessionAttributeTests(unittest.TestCase):
    def test_the_ten_cases_are_the_sources_own_numbers(self) -> None:
        expected = {1: 17, 2: 23, 3: 16, 4: 6, 5: 0, 6: 12, 7: 35, 8: 36, 9: 40, 10: 44}
        for profession, attribute in expected.items():
            with self.subTest(profession=profession):
                self.assertEqual(
                    data_attribute.Attribute_GetProfPrimaryAttribute(profession), attribute
                )

    def test_a_profession_outside_the_switch_answers_zero(self) -> None:
        """The source has **no** ``Case Else``: the ``EndFunc`` answers nothing, which is AutoIt's zero."""

        self.assertEqual(data_attribute.Attribute_GetProfPrimaryAttribute(0), 0)
        self.assertEqual(data_attribute.Attribute_GetProfPrimaryAttribute(11), 0)


class LastModifiedTests(unittest.TestCase):
    def test_the_member_is_not_applicable_and_keeps_the_pairs_shape(self) -> None:
        """The state behind GwAu3's own attribute setter, which is a write this layer does not perform."""

        module_doc = data_attribute.__doc__ or ""
        self.assertIn("NOT APPLICABLE", module_doc)
        self.assertEqual(data_attribute.Attribute_GetLastModified(), [0, 0])


class SurfaceTests(unittest.TestCase):
    def test_the_whole_file_is_exported(self) -> None:
        """``GwAu3_Data_Attribute.au3`` declares seven functions and this module exports seven."""

        self.assertEqual(
            sorted(data_attribute.__all__),
            [
                "Attribute_GetAttributeInfo",
                "Attribute_GetAttributeName",
                "Attribute_GetAttributePtr",
                "Attribute_GetLastModified",
                "Attribute_GetPartyAttributeInfo",
                "Attribute_GetPartyAttributePointInfo",
                "Attribute_GetProfPrimaryAttribute",
            ],
        )

    def test_the_party_block_is_the_source_own_stride(self) -> None:
        """``0x43C`` per block and ``0x14`` per record: the source's arithmetic, asserted on the struct."""

        self.assertEqual(ctypes.sizeof(PartyAttributeStruct), 0x43C)
        self.assertEqual(ctypes.sizeof(AttributeStruct), 0x14)
        self.assertEqual(PartyAttributeStruct.attribute_array.offset, 0x4)
        self.assertEqual(AttributeStruct.decrement_points.offset, 0x0C)


if __name__ == "__main__":
    unittest.main()
