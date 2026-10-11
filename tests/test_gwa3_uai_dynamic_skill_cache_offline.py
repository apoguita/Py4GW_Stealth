"""Offline tests for `py4gw/gwa3/uai_dynamic_skill_cache.py`.

No client: a slot's words come from the client's skillbar, so a test serves a stand-in client whose
world holds one skillbar, and checks the source's own guards and arithmetic
(`UtilityAI_DynamicSkillCache.au3:29-72`):

* the two guard clauses answer ``0`` **before** the record is touched, in the source's order;
* the four read columns are the slot record's own fields -- and they are the *same* fields
  `Skill_GetSkillbarInfo` reads, which the struct's own offsets establish;
* the two recharge columns are the source's signed subtraction, clamped at zero, with the timestamp-zero
  case answering ``True``/``0`` without consulting the timer;
* the two NOT APPLICABLE members say so and touch nothing, and the one that reports can answer ``False``.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from types import SimpleNamespace
from typing import Any
from unittest import mock

from py4gw.gwa3 import constants, uai_dynamic_skill_cache as cache

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Cache"
    / "UtilityAI_DynamicSkillCache.au3"
)


def _slot(adrenaline_a: int = 1, adrenaline_b: int = 2, recharge: int = 0, skill_id: int = 0, event: int = 9) -> Any:
    return SimpleNamespace(
        adrenaline_a=adrenaline_a,
        adrenaline_b=adrenaline_b,
        recharge=recharge,
        skill_id=skill_id,
        event=event,
    )


class _World:
    def __init__(self, slots: list[Any], bar_agent_id: int) -> None:
        # An empty slot list is the client holding **no skillbar**, which is the case the reader answers
        # `0` for -- so the bar is only there when there are slots.
        self.skillbars = [SimpleNamespace(agent_id=bar_agent_id, skills=slots)] if slots else []


def _serve(
    test: unittest.TestCase,
    slots: list[Any],
    agent_id: int = 42,
    timer: int = 1000,
    bar_agent_id: int | None = None,
) -> None:
    client = SimpleNamespace(
        read_world_context=lambda: _World(slots, agent_id if bar_agent_id is None else bar_agent_id)
    )
    # **The timer is patched where the module looks it up.** `uai_dynamic_skill_cache` imports
    # `Skill_GetSkillTimer` at module scope, so patching `data_skill`'s attribute would leave the real one
    # in place -- which is what the first version of this file did, and the client-less failure it
    # produced was the fixture's, not the module's.
    patches = [
        mock.patch("py4gw.client.require_client", lambda: client),
        mock.patch("py4gw.gwa3.data_agent.Agent_GetMyID", lambda: agent_id),
        mock.patch.object(cache, "Skill_GetSkillTimer", lambda: timer),
    ]
    for patch in patches:
        patch.start()
        test.addCleanup(patch.stop)


class SurfaceTests(unittest.TestCase):
    def test_the_surface_is_the_sources_own(self) -> None:
        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(sorted(declared), sorted(cache.__all__))
        self.assertEqual(len(cache.__all__), 3)

    def test_the_column_table_is_gwaus_own_enum(self) -> None:
        self.assertEqual(
            cache._READ_COLUMNS[constants.GC_UAI_DYNAMIC_SKILL_SkillID], "skill_id"
        )
        self.assertEqual(
            cache._READ_COLUMNS[constants.GC_UAI_DYNAMIC_SKILL_Adrenaline], "adrenaline_a"
        )
        self.assertNotIn(constants.GC_UAI_DYNAMIC_SKILL_COUNT, cache._READ_COLUMNS)
        self.assertEqual(constants.GC_UAI_DYNAMIC_SKILL_SLOTS, 8)


class DynamicSkillInfoTests(unittest.TestCase):
    def test_the_read_columns_are_the_slot_records_own_fields(self) -> None:
        _serve(self, [_slot(skill_id=1062) for _ in range(8)])
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_SkillID), 1062
        )
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_Adrenaline), 1
        )
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_AdrenalineB), 2
        )
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_Event), 9
        )

    def test_the_slot_number_selects_the_record(self) -> None:
        slots = [_slot(skill_id=1000 + index) for index in range(8)]
        _serve(self, slots)
        for slot in range(1, 9):
            with self.subTest(slot=slot):
                self.assertEqual(
                    cache.UAI_GetDynamicSkillInfo(slot, constants.GC_UAI_DYNAMIC_SKILL_SkillID),
                    1000 + slot - 1,
                )

    def test_the_guards_answer_zero_before_the_record_is_touched(self) -> None:
        with mock.patch("py4gw.client.require_client", side_effect=AssertionError("read")):
            self.assertEqual(cache.UAI_GetDynamicSkillInfo(0, 0), 0)
            self.assertEqual(cache.UAI_GetDynamicSkillInfo(9, 0), 0)
            self.assertEqual(cache.UAI_GetDynamicSkillInfo(1, -1), 0)
            self.assertEqual(
                cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_COUNT), 0
            )

    def test_a_zero_timestamp_is_recharged_and_answers_the_timer_not_at_all(self) -> None:
        _serve(self, [_slot(recharge=0) for _ in range(8)])
        with mock.patch.object(cache, "Skill_GetSkillTimer", side_effect=AssertionError("timer")):
            self.assertTrue(
                cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_IsRecharged)
            )
            self.assertEqual(
                cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_RechargeTime), 0
            )

    def test_a_future_timestamp_is_the_signed_remaining_time(self) -> None:
        _serve(self, [_slot(recharge=1500) for _ in range(8)], timer=1000)
        self.assertFalse(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_IsRecharged)
        )
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_RechargeTime), 500
        )

    def test_an_elapsed_timestamp_is_recharged_and_clamps_at_zero(self) -> None:
        _serve(self, [_slot(recharge=900) for _ in range(8)], timer=1000)
        self.assertTrue(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_IsRecharged)
        )
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_RechargeTime), 0
        )

    def test_no_skillbar_answers_zero(self) -> None:
        _serve(self, [])
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_SkillID), 0
        )

    def test_a_skillbar_belonging_to_another_agent_answers_zero(self) -> None:
        _serve(self, [_slot(skill_id=1062) for _ in range(8)], agent_id=42, bar_agent_id=99)
        self.assertEqual(
            cache.UAI_GetDynamicSkillInfo(1, constants.GC_UAI_DYNAMIC_SKILL_SkillID), 0
        )


class NotApplicableTests(unittest.TestCase):
    def test_the_fill_member_is_not_applicable_and_reports_a_missing_bar(self) -> None:
        _serve(self, [_slot() for _ in range(8)])
        self.assertTrue(cache.UAI_CacheDynamicSkillbarInfo())

        _serve(self, [])
        self.assertFalse(cache.UAI_CacheDynamicSkillbarInfo())

    def test_the_struct_member_answers_none(self) -> None:
        self.assertIsNone(cache.UAI_GetDynamicSkillStruct())


if __name__ == "__main__":
    unittest.main()
