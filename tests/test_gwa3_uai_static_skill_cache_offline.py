"""Offline tests for `py4gw/gwa3/uai_static_skill_cache.py` -- the skillbar's skill data.

No client: the two accessors read the live skillbar slot and the live skill record, so a test stubs
those two reads and checks GwAu3's own columns, guards and conversions:

* the surface is `UtilityAI_StaticSkillCache.au3`'s four functions, and the column table is GwAu3's own
  ``Global Enum`` rather than a transcription -- every name in the generated constants module is in it;
* `UAI_GetStaticSkillInfo`'s guards, in the source's order, and the **empty slot** that answers ``0``;
* the three conversions the source performs while caching -- ``Overcast`` (5 and 10, else 0),
  ``EnergyCost`` (11 -> 15, 12 -> 25) and ``Aftercast`` (x1000) -- because a port that reads live has to
  make them too;
* the two source quirks: the last enum name (``Description``, column 43) is refused by the guard, and the
  plugin's ``Name`` column is read through the data module's ``NameID`` key;
* `UAI_SlotIsPriority`'s three groups of flags;
* `UAI_CacheSkillBar`'s two failure paths and its success answer.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from unittest import mock

from py4gw.gwa3 import constants, uai_static_skill_cache as cache

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Plugins"
    / "UtilityAI"
    / "Cache"
    / "UtilityAI_StaticSkillCache.au3"
)


class _Skill:
    """A stand-in for `Skill_GetSkillInfo`: answers a table of ``{key: value}`` for one skill id."""

    def __init__(self, rows: dict[int, dict[str, object]]) -> None:
        self.rows = rows
        self.asked: list[tuple[int, str]] = []

    def __call__(self, skill_id: object, key: str = "") -> object:
        self.asked.append((int(skill_id), key))
        if key == "":
            return 0
        return self.rows.get(int(skill_id), {}).get(key, 0)


class SurfaceTests(unittest.TestCase):
    def test_the_surface_is_the_sources_own(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(sorted(declared), sorted(cache.__all__))
        for name in cache.__all__:
            self.assertTrue(callable(getattr(cache, name)), name)

    def test_the_column_table_is_gwaus_own_enum(self) -> None:
        """Every ``$GC_UAI_STATIC_SKILL_*`` name in the generated constants module, by its own value."""

        names = [n for n in constants.__all__ if n.startswith("GC_UAI_STATIC_SKILL_")]
        self.assertEqual(len(names), 44, "the enum declares forty-four names")
        for name in names:
            with self.subTest(name=name):
                self.assertIn(getattr(constants, name), cache._STATIC_SKILL_FIELDS)

        self.assertEqual(cache._LAST_COLUMN, 42, "the source's table is [9][43]")

    def test_the_plugin_name_column_reads_the_data_modules_name_id(self) -> None:
        self.assertEqual(
            cache._column_key(constants.GC_UAI_STATIC_SKILL_Name), "NameID"
        )
        self.assertEqual(cache._column_key(constants.GC_UAI_STATIC_SKILL_SkillID), "SkillID")


class GetStaticSkillInfoTests(unittest.TestCase):
    def _serve(self, skill_id: int, **fields: object) -> _Skill:
        skill = _Skill({skill_id: {"SkillID": skill_id, **fields}})
        patches = [
            mock.patch.object(cache, "Skill_GetSkillbarInfo", lambda slot, info, *a: skill_id),
            mock.patch.object(cache, "Skill_GetSkillInfo", skill),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return skill

    def test_a_column_answers_the_skills_field(self) -> None:
        self._serve(1062, EnergyCost=5, Recharge=20)
        self.assertEqual(
            cache.UAI_GetStaticSkillInfo(3, constants.GC_UAI_STATIC_SKILL_EnergyCost), 5
        )
        self.assertEqual(cache.UAI_GetStaticSkillInfo(3, constants.GC_UAI_STATIC_SKILL_Recharge), 20)

    def test_the_guards_are_the_sources_and_in_its_order(self) -> None:
        skill = self._serve(1062, EnergyCost=5)
        self.assertEqual(cache.UAI_GetStaticSkillInfo(0, constants.GC_UAI_STATIC_SKILL_SkillID), 0)
        self.assertEqual(cache.UAI_GetStaticSkillInfo(9, constants.GC_UAI_STATIC_SKILL_SkillID), 0)
        self.assertEqual(cache.UAI_GetStaticSkillInfo(1, -1), 0)
        # The forty-fourth name (column 43) is refused by the guard (`:210`), so it never reaches a read.
        self.assertEqual(cache.UAI_GetStaticSkillInfo(1, 43), 0)
        self.assertEqual(skill.asked, [])

    def test_an_empty_slot_answers_zero_without_reading_a_skill(self) -> None:
        skill = _Skill({})
        with mock.patch.object(cache, "Skill_GetSkillbarInfo", lambda slot, info, *a: 0), mock.patch.object(
            cache, "Skill_GetSkillInfo", skill
        ):
            self.assertEqual(
                cache.UAI_GetStaticSkillInfo(2, constants.GC_UAI_STATIC_SKILL_SkillID), 0
            )
        self.assertEqual(skill.asked, [])

    def test_overcast_keeps_five_and_ten_and_zeroes_the_rest(self) -> None:
        for raw, expected in ((5, 5), (10, 10), (0, 0), (7, 0), (200, 0)):
            with self.subTest(raw=raw):
                self._serve(1062, Overcast=raw)
                self.assertEqual(
                    cache.UAI_GetStaticSkillInfo(1, constants.GC_UAI_STATIC_SKILL_Overcast), expected
                )

    def test_energy_cost_maps_the_two_pip_costs(self) -> None:
        for raw, expected in ((11, 15), (12, 25), (10, 10), (25, 25)):
            with self.subTest(raw=raw):
                self._serve(1062, EnergyCost=raw)
                self.assertEqual(
                    cache.UAI_GetStaticSkillInfo(1, constants.GC_UAI_STATIC_SKILL_EnergyCost), expected
                )

    def test_aftercast_is_converted_to_milliseconds(self) -> None:
        self._serve(1062, Aftercast=0.25)
        self.assertEqual(
            cache.UAI_GetStaticSkillInfo(1, constants.GC_UAI_STATIC_SKILL_Aftercast), 250.0
        )


class StaticDataSkillTests(unittest.TestCase):
    def test_the_row_has_the_sources_forty_three_columns(self) -> None:
        skill = _Skill({1062: {"SkillID": 1062, "Aftercast": 0.5}})
        with mock.patch.object(cache, "Skill_GetSkillInfo", skill):
            row = cache.UAI_StaticDataSkill(1062)
        self.assertEqual(len(row), 43)

        index = constants.GC_UAI_STATIC_SKILL_Aftercast
        self.assertEqual(row[index], 500.0)
        self.assertEqual(row[constants.GC_UAI_STATIC_SKILL_SkillID], 1062)

    def test_a_skill_the_client_does_not_hold_answers_a_zero_row(self) -> None:
        with mock.patch.object(cache, "Skill_GetSkillInfo", _Skill({})):
            row = cache.UAI_StaticDataSkill(999_999)
        self.assertEqual(row, [0] * 43)


class SlotIsPriorityTests(unittest.TestCase):
    def _slot(self, **fields: object) -> None:
        values = {
            "Special": 0,
            "Effect2": 0,
            "SkillType": 0,
            **fields,
        }
        skill = _Skill({1062: values})

        def info(slot: object, info_type: object) -> object:
            key = cache._column_key(info_type)
            return values.get(key, 0)

        patches = [
            mock.patch.object(cache, "Skill_GetSkillbarInfo", lambda slot, info_, *a: 1062),
            mock.patch.object(cache, "Skill_GetSkillInfo", skill),
            mock.patch.object(cache, "UAI_GetStaticSkillInfo", info),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_special_flag_makes_a_slot_a_priority(self) -> None:
        self._slot(Special=constants.GC_I_SKILL_SPECIAL_FLAG_ELITE)
        self.assertTrue(cache.UAI_SlotIsPriority(1))

    def test_an_effect2_flag_makes_a_slot_a_priority(self) -> None:
        self._slot(Effect2=constants.GC_I_SKILL_EFFECT2_HEX_REMOVAL)
        self.assertTrue(cache.UAI_SlotIsPriority(1))

    def test_a_priority_skill_type_makes_a_slot_a_priority(self) -> None:
        self._slot(SkillType=constants.GC_I_SKILL_TYPE_GLYPH)
        self.assertTrue(cache.UAI_SlotIsPriority(1))

    def test_a_plain_skill_is_not_a_priority(self) -> None:
        self._slot(SkillType=constants.GC_I_SKILL_TYPE_SPELL)
        self.assertFalse(cache.UAI_SlotIsPriority(1))


class CacheSkillBarTests(unittest.TestCase):
    def test_no_skillbar_array_answers_false(self) -> None:
        client = mock.Mock()
        client.read_world_context.return_value = mock.Mock(
            party_skillbar_array=mock.Mock(m_size=0)
        )
        with mock.patch("py4gw.client.require_client", lambda: client):
            self.assertFalse(cache.UAI_CacheSkillBar())

    def test_no_controlled_character_answers_false(self) -> None:
        client = mock.Mock()
        client.read_world_context.return_value = mock.Mock(
            party_skillbar_array=mock.Mock(m_size=1)
        )
        with mock.patch("py4gw.client.require_client", lambda: client), mock.patch.object(
            cache, "Agent_GetMyID", lambda: 0
        ):
            self.assertFalse(cache.UAI_CacheSkillBar())

    def test_a_skillbar_and_a_character_answer_none(self) -> None:
        client = mock.Mock()
        client.read_world_context.return_value = mock.Mock(
            party_skillbar_array=mock.Mock(m_size=1)
        )
        with mock.patch("py4gw.client.require_client", lambda: client), mock.patch.object(
            cache, "Agent_GetMyID", lambda: 42
        ):
            self.assertIsNone(cache.UAI_CacheSkillBar())

    def test_it_does_not_touch_the_skill_table(self) -> None:
        """The cache has nothing to fill, so the member must not read a skill on the way."""

        client = mock.Mock()
        client.read_world_context.return_value = mock.Mock(
            party_skillbar_array=mock.Mock(m_size=1)
        )
        with mock.patch("py4gw.client.require_client", lambda: client), mock.patch.object(
            cache, "Agent_GetMyID", lambda: 42
        ), mock.patch.object(
            cache, "Skill_GetSkillInfo", side_effect=AssertionError("read a skill")
        ), mock.patch.object(
            cache, "Skill_GetSkillbarInfo", side_effect=AssertionError("read the bar")
        ):
            self.assertIsNone(cache.UAI_CacheSkillBar())


if __name__ == "__main__":
    unittest.main()
