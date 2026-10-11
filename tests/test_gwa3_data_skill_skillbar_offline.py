"""Offline tests for the **skillbar** reader `tools/gwa3_snippets/data_skill_skillbar.py` carries.

No client: the accessor reads the world's skillbar array and the client's skill timer, so a test serves
a stand-in client and checks GwAu3's own guards and key set (`GwAu3_Data_Skill.au3:210-304`) --
including the two reversals, whose *skill id* travels in the **slot** parameter, and the two recharge
keys, which are the source's signed subtraction against the client's own clock.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from types import SimpleNamespace
from typing import Any
from unittest import mock

from py4gw.gwa3 import data_skill

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Modules"
    / "Data"
    / "GwAu3_Data_Skill.au3"
)


class _Client:
    def __init__(self, world: Any, timer: int) -> None:
        self._world = world
        self.memory_manager = SimpleNamespace(GetSkillTimer=lambda: timer)

    def read_world_context(self) -> Any:
        return self._world


def _slot(skill_id: int = 0, recharge: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        adrenaline_a=1,
        adrenaline_b=2,
        recharge=recharge,
        skill_id=skill_id,
        event=9,
    )


def _skillbar(agent_id: int, skills: list[Any] | None = None) -> SimpleNamespace:
    slots = skills if skills is not None else [_slot(skill_id=1000 + index) for index in range(8)]
    return SimpleNamespace(
        agent_id=agent_id,
        skills=slots,
        disabled=0x11,
        cast_array=SimpleNamespace(m_buffer=0xAA, m_capacity=8, m_size=0, m_param=0xBB),
        h00B8=0xCC,
    )


def _world(bars: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(
        skillbars=bars,
        party_skillbar_array=SimpleNamespace(m_size=len(bars)),
    )


def _serve(test: unittest.TestCase, bars: list[Any], timer: int = 1000, player_id: int = 42) -> None:
    client = _Client(_world(bars), timer)
    patcher = mock.patch.object(data_skill, "require_client", lambda: client)
    patcher.start()
    test.addCleanup(patcher.stop)
    agent = mock.patch.object(data_skill, "Agent_GetMyID", lambda: player_id)
    agent.start()
    test.addCleanup(agent.stop)


class SurfaceTests(unittest.TestCase):
    def test_the_file_declares_the_two_accessors(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        for name in ("Skill_GetSkillbarInfo", "Skill_GetSkillTimer"):
            self.assertIn(name, declared)
            self.assertIn(name, data_skill.__all__)
            self.assertTrue(callable(getattr(data_skill, name)))


class SkillTimerTests(unittest.TestCase):
    def test_it_answers_the_clients_own_timer(self) -> None:
        _serve(self, [_skillbar(42)], timer=123456)
        self.assertEqual(data_skill.Skill_GetSkillTimer(), 123456)


class SkillbarTests(unittest.TestCase):
    def test_the_bar_keys_answer_the_matched_skillbar(self) -> None:
        _serve(self, [_skillbar(7), _skillbar(42)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID"), 42)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "Disabled"), 0x11)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "Casting"), 0)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "h00A8[2]"), 0xAA)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "h00B4[2]"), 0xBB)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "Queued"), 0xCC)

    def test_the_slot_keys_answer_the_numbered_slot(self) -> None:
        _serve(self, [_skillbar(42)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(3, "SkillID"), 1002)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(3, "Adrenaline"), 1)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(3, "AdrenalineB"), 2)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(3, "Event"), 9)
        self.assertTrue(data_skill.Skill_GetSkillbarInfo(3, "HasSkill"))

    def test_the_recharge_keys_use_the_sources_signed_subtraction(self) -> None:
        _serve(self, [_skillbar(42, [_slot(skill_id=1000, recharge=1500)] + [_slot()] * 7)], timer=1000)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "RechargeTime"), 500)
        self.assertFalse(data_skill.Skill_GetSkillbarInfo(1, "IsRecharged"))

        # Elapsed (the timestamp is behind the timer): `RechargeTime` clamps at 0 while `IsRecharged`
        # is only true when the two are exactly equal -- the source's own asymmetry (`:271-287`).
        _serve(self, [_skillbar(42, [_slot(skill_id=1000, recharge=900)] + [_slot()] * 7)], timer=1000)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "RechargeTime"), 0)
        self.assertFalse(data_skill.Skill_GetSkillbarInfo(1, "IsRecharged"))

        _serve(self, [_skillbar(42, [_slot(skill_id=1000, recharge=1000)] + [_slot()] * 7)], timer=1000)
        self.assertTrue(data_skill.Skill_GetSkillbarInfo(1, "IsRecharged"))

    def test_a_zero_timestamp_answers_zero_and_true(self) -> None:
        _serve(self, [_skillbar(42, [_slot(skill_id=1000, recharge=0)] + [_slot()] * 7)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "RechargeTime"), 0)
        self.assertTrue(data_skill.Skill_GetSkillbarInfo(1, "IsRecharged"))

    def test_the_two_reversals_are_unreachable_and_that_is_the_sources_own_guard(self) -> None:
        """``SlotBySkillID``/``HasSkillID`` want a **skill id in the slot parameter**, and the guard
        above the ``Switch`` rejects anything outside ``1..8`` (``GwAu3_Data_Skill.au3:217``) -- so with
        a real skill id they answer ``0``, in GwAu3 exactly as here. Only a value ``1..8`` reaches their
        loops, which is where the slot number itself would go.
        """

        _serve(self, [_skillbar(42)])
        for skill_id in (1003, 9999):
            with self.subTest(skill_id=skill_id):
                self.assertEqual(data_skill.Skill_GetSkillbarInfo(skill_id, "SlotBySkillID"), 0)
                self.assertEqual(data_skill.Skill_GetSkillbarInfo(skill_id, "HasSkillID"), 0)

        # A value inside the slot range does reach the loop, and answers the slot whose skill id equals
        # it -- which is the source's own arithmetic, not a useful lookup.
        _serve(self, [_skillbar(42, [_slot(skill_id=4)] + [_slot()] * 7)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(4, "SlotBySkillID"), 1)
        self.assertTrue(data_skill.Skill_GetSkillbarInfo(4, "HasSkillID"))

    def test_a_hero_bar_is_matched_by_the_heros_agent_id(self) -> None:
        _serve(self, [_skillbar(42), _skillbar(77)])
        with mock.patch.object(data_skill, "Party_GetMyPartyHeroInfo", lambda number, info: 77):
            self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID", 1), 77)
            self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "SkillID", 1), 1000)

    def test_the_guards_answer_zero_in_the_sources_order(self) -> None:
        _serve(self, [_skillbar(42)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(0, "AgentID"), 0)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(9, "AgentID"), 0)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID", 5), 0)
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID", -1), 0)

    def test_no_matching_bar_answers_zero_and_an_unknown_key_answers_zero(self) -> None:
        _serve(self, [_skillbar(7)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID"), 0)

        _serve(self, [_skillbar(42)])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "NoSuchKey"), 0)

    def test_a_bar_array_the_client_does_not_hold_answers_zero(self) -> None:
        _serve(self, [])
        self.assertEqual(data_skill.Skill_GetSkillbarInfo(1, "AgentID"), 0)


if __name__ == "__main__":
    unittest.main()
