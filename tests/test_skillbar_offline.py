"""Offline tests for the ported ``SkillBar`` class (``py4gw/skillbar.py``).

Three things are pinned here, and none of them needs a running client.

**The surface is the source's.** Reforged's ``Py4GWCoreLib/Skillbar.py`` is read at test time and its
18 member names must exist here in the source's order, and native's binding surface
(``PySkillbar.Skillbar`` and ``PySkillbar.SkillbarSkill``, ``skillbar_bindings.cpp:88-192``) must be
present on the ported binding object field for field.

**The values are the source's.** Every implemented member is driven against a synthetic client whose
skillbar array is made of real ``SkillbarStruct`` records, so the field reads, the slot arithmetic,
the two skill bitsets, the hero walk and the tooltip branch are all exercised — including native's
own edges: a slot outside ``1..8`` is refused (``skillbar_bindings.cpp:44-49``), a hero index above
``7`` answers an empty list (``skillbar_methods.cpp:479``), and a tooltip whose payload is not
``0x14`` bytes is not a skill tooltip (``skillbar_bindings.cpp:492``).

**The members that raise name what they need**, and ``ChangeHeroSecondary`` — the one action whose
mechanism exists — is checked by its arguments.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import party as party_module
from py4gw import skillbar as skillbar_module
from py4gw.context.world_context import SkillbarSkillStruct, SkillbarStruct
from py4gw.game_thread.shared_block import CallForm
from py4gw.map import Map
from py4gw.player import Player
from py4gw.skillbar import (
    SKILL_TOOLTIP_PAYLOAD_LENGTH,
    PySkillbar,
    SkillBar,
    SkillbarSkill,
)

#: Reforged's own file, and the native sources the binding and its hovered-skill read come from.
SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Skillbar.py")
NATIVE_BINDINGS = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skillbar_bindings.cpp")
NATIVE_METHODS = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skillbar_methods.cpp")

#: The agent id the synthetic skillbar belongs to.
AGENT_ID = 1234

#: The eight slots of the synthetic skillbar.
SLOT_SKILL_IDS = (5, 0, 42, 0, 0, 0, 0, 7)


def _skillbar(
    agent_id: int = AGENT_ID,
    skill_ids: tuple[int, ...] = SLOT_SKILL_IDS,
    disabled: int = 0,
    casting: int = 0,
) -> SkillbarStruct:
    """Build one real ``SkillbarStruct`` record with the slots a test chooses."""

    skillbar = SkillbarStruct()
    skillbar.agent_id = agent_id
    for index, skill_id in enumerate(skill_ids):
        skillbar.skills[index].skill_id = skill_id
        skillbar.skills[index].adrenaline_a = index + 1
        skillbar.skills[index].adrenaline_b = index + 10
        skillbar.skills[index].recharge = 100 + index
        skillbar.skills[index].event = index
    skillbar.disabled = disabled
    skillbar.cast_array.m_size = casting
    return skillbar


class _FakeWorld:
    """The world-context reads the skillbar members make."""

    def __init__(self, skillbars: list[SkillbarStruct], skill_words: list[int] | None = None) -> None:
        self.skillbars = skillbars
        self.unlocked_character_skills = skill_words


class _FakeAccount:
    """The account-context read ``IsSkillUnlocked`` makes."""

    def __init__(self, unlocked: set[int]) -> None:
        self.unlocked = unlocked

    def is_account_skill_unlocked(self, skill_id: int) -> bool:
        return int(skill_id) in self.unlocked


class _FakeTooltip:
    """A tooltip record with the two fields the hovered-skill read uses."""

    def __init__(self, payload: int = 0, payload_len: int = 0) -> None:
        self.payload = payload
        self.payload_len = payload_len


class _FakeTooltipReader:
    """The tooltip reader the client exposes, answering one payload word."""

    def __init__(self, word: int | None) -> None:
        self.word = word
        self.reads: list[Any] = []

    def read_payload_word(self, tooltip: Any) -> int | None:
        self.reads.append(tooltip)
        return self.word


class _FakeClient:
    """A client answering the reads the skillbar members make."""

    def __init__(
        self,
        world: _FakeWorld | None = None,
        account: _FakeAccount | None = None,
        tooltip: _FakeTooltip | None = None,
        tooltip_word: int | None = None,
        skill_ids: tuple[int, ...] = (),
    ) -> None:
        self.world = world
        self.account = account
        self.tooltip = tooltip
        self.tooltip_reader = _FakeTooltipReader(tooltip_word)
        self.skill_ids = skill_ids
        self.calls: list[tuple[Any, ...]] = []

    def read_world_context(self) -> Any:
        return self.world

    def read_account_context(self) -> Any:
        return self.account

    def read_current_tooltip(self) -> Any:
        return self.tooltip

    @property
    def current_tooltip(self) -> _FakeTooltipReader:
        return self.tooltip_reader

    def read_skill(self, skill_id: int) -> Any:
        if skill_id not in self.skill_ids:
            return None
        record = mock.Mock()
        record.skill_id = skill_id
        return record

    def call_function(self, name: str, form: int, *args: Any) -> Any:
        self.calls.append((name, form, *args))
        return None


def _patch_client(client: _FakeClient) -> Any:
    """Patch the connection the members resolve, the map gate and the agent ids."""

    return mock.patch.multiple(
        "py4gw.client",
        _current_client=client,
    )


class SkillBarSurfaceTests(unittest.TestCase):
    """The port declares the source's class and native's binding surface."""

    def _source_members(self) -> list[str]:
        if not SOURCE.is_file():
            self.skipTest(f"Reforged's Skillbar.py is not at {SOURCE}")
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "SkillBar":
                return [
                    child.name
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
        return []

    def test_the_port_declares_every_source_member_in_order(self) -> None:
        """18 members, the source's names, the source's order — none missing, none added."""

        source_members = self._source_members()
        self.assertEqual(len(source_members), 18)
        ported = [
            name for name, value in vars(SkillBar).items() if isinstance(value, staticmethod)
        ]
        self.assertEqual(ported, source_members)

    def test_every_member_is_a_staticmethod(self) -> None:
        """Match Reforged, where ``SkillBar`` is a namespace of static methods."""

        for name in self._source_members():
            self.assertIsInstance(vars(SkillBar).get(name), staticmethod, msg=name)

    def test_the_binding_object_carries_native_s_bound_members(self) -> None:
        """``PySkillbar.Skillbar`` (``skillbar_bindings.cpp:168-192``)."""

        obj = PySkillbar.__new__(PySkillbar)
        obj.data = None
        for name in (
            "GetContext",
            "GetSkill",
            "GetSkills",
            "LoadSkillTemplate",
            "LoadHeroSkillTemplate",
            "UseSkill",
            "UseSkillTargetless",
            "HeroUseSkill",
            "ChangeHeroSecondary",
            "GetHeroSkillbar",
            "GetHoveredSkill",
            "IsSkillUnlocked",
            "IsSkillLearnt",
            "agent_id",
            "disabled",
            "casting",
        ):
            with self.subTest(member=name):
                self.assertTrue(hasattr(obj, name), name)

    def test_the_slot_type_carries_native_s_bound_members(self) -> None:
        """``PySkillbar.SkillbarSkill`` (``skillbar_bindings.cpp:153-163``).

        The properties are checked on the class rather than on an instance: ``get_recharge`` is one
        of the members this port has not built yet, so reading it raises by design.
        """

        slot = SkillbarSkill(SkillbarSkillStruct())
        for name in ("id", "adrenaline_a", "adrenaline_b", "recharge", "event", "get_recharge"):
            with self.subTest(member=name):
                self.assertTrue(hasattr(SkillbarSkill, name), name)
        self.assertEqual(int(slot.id.id), 0)
        # Skill 0 is native's own name table entry, which the port now carries.
        self.assertEqual(slot.id.GetName(), "No_Skill")

    def test_the_tooltip_payload_length_is_native_s(self) -> None:
        """``skillbar_methods.cpp:492``: ``payload_len == 0x14``."""

        self.assertEqual(SKILL_TOOLTIP_PAYLOAD_LENGTH, 0x14)
        if NATIVE_METHODS.is_file():
            self.assertIn(
                "payload_len == 0x14",
                NATIVE_METHODS.read_text(encoding="utf-8"),
            )


class SkillBarReadTests(unittest.TestCase):
    """Every implemented read answers the source's value over a synthetic skillbar."""

    def setUp(self) -> None:
        self.world = _FakeWorld([_skillbar()])
        self.client = _FakeClient(world=self.world, account=_FakeAccount({42}))
        self._client_patch = _patch_client(self.client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)
        self._map_patch = mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True))
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)
        self._agent_patch = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: AGENT_ID)
        )
        self._agent_patch.start()
        self.addCleanup(self._agent_patch.stop)

    def test_the_skillbar_reads_its_eight_slots(self) -> None:
        """``GetSkillbar`` (``Skillbar.py:28-39``) drops the empty slots, the dict form keeps them."""

        self.assertEqual(SkillBar.GetSkillbar(), [5, 42, 7])
        self.assertEqual(
            SkillBar.GetZeroFilledSkillbar(),
            {1: 5, 2: 0, 3: 42, 4: 0, 5: 0, 6: 0, 7: 0, 8: 7},
        )

    def test_a_slot_answers_its_id_and_its_record(self) -> None:
        """``GetSkillIDBySlot``/``GetSkillData`` (``Skillbar.py:109-146``)."""

        self.assertEqual(SkillBar.GetSkillIDBySlot(1), 5)
        self.assertEqual(SkillBar.GetSkillIDBySlot(3), 42)
        self.assertEqual(SkillBar.GetSkillIDBySlot(4), 0)

        skill = SkillBar.GetSkillData(1)
        self.assertIsInstance(skill, SkillbarSkill)
        self.assertEqual(int(skill.id.id), 5)
        self.assertEqual(skill.adrenaline_a, 1)
        self.assertEqual(skill.adrenaline_b, 10)
        self.assertEqual(skill.recharge, 100)
        self.assertEqual(skill.event, 0)

    def test_the_slot_lookup_by_skill_id(self) -> None:
        """``GetSlotBySkillID`` (``Skillbar.py:121-135``): the first match, else ``0``."""

        self.assertEqual(SkillBar.GetSlotBySkillID(5), 1)
        self.assertEqual(SkillBar.GetSlotBySkillID(42), 3)
        self.assertEqual(SkillBar.GetSlotBySkillID(999), 0)

    def test_a_slot_outside_the_range_is_refused(self) -> None:
        """``ValidateSlot`` (``skillbar_bindings.cpp:44-49``) raises rather than reading a neighbour."""

        instance = PySkillbar()
        for slot in (0, 9, -1):
            with self.subTest(slot=slot):
                with self.assertRaises(IndexError) as caught:
                    instance.GetSkill(slot)
                self.assertIn("must be between 1 and 8", str(caught.exception))

    def test_the_owner_and_the_state_words(self) -> None:
        """``GetAgentID``/``GetDisabled``/``GetCasting`` (``Skillbar.py:181-209``)."""

        self.assertEqual(SkillBar.GetAgentID(), AGENT_ID)
        self.assertEqual(SkillBar.GetDisabled(), 0)
        self.assertEqual(SkillBar.GetCasting(), 0)

        # The casting word is native's data.casting, the word at 0xB0 of the record.
        self.world.skillbars = [_skillbar(casting=2)]
        self.assertEqual(SkillBar.GetCasting(), 2)
        self.world.skillbars = [_skillbar(disabled=0x10)]
        self.assertEqual(SkillBar.GetDisabled(), 0x10)

    def test_the_two_skill_bitsets(self) -> None:
        """``IsSkillUnlocked``/``IsSkillLearnt`` (``skillbar_methods.cpp:546-570``)."""

        # The world bitset: 42 is in word 1, bit 10.
        words = [0] * 4
        words[1] = 1 << 10
        self.world.unlocked_character_skills = words
        self.assertTrue(SkillBar.IsSkillLearnt(42))
        self.assertFalse(SkillBar.IsSkillLearnt(43))
        # Past the array's end the source answers false rather than reading past it.
        self.assertFalse(SkillBar.IsSkillLearnt(32 * 8))

        # The account bitset: 42 unlocked, 7 not.
        self.assertTrue(SkillBar.IsSkillUnlocked(42))
        self.assertFalse(SkillBar.IsSkillUnlocked(7))

    def test_a_missing_context_answers_the_sources_defaults(self) -> None:
        """No skillbar record is native's default: an empty ``GetSkillbar`` and a zeroed slot."""

        self.world.skillbars = []
        # ``GetSkillbar`` drops the zero slots, so an empty skillbar answers an empty list.
        self.assertEqual(SkillBar.GetSkillbar(), [])
        self.assertEqual(SkillBar.GetZeroFilledSkillbar(), dict.fromkeys(range(1, 9), 0))
        self.assertEqual(SkillBar.GetAgentID(), 0)
        self.assertEqual(SkillBar.GetDisabled(), 0)
        self.assertEqual(SkillBar.GetCasting(), 0)
        self.assertEqual(int(SkillBar.GetSkillData(1).id.id), 0)

        empty = _FakeClient(world=None, account=None)
        with _patch_client(empty):
            self.assertFalse(SkillBar.IsSkillUnlocked(42))
            self.assertFalse(SkillBar.IsSkillLearnt(42))

    def test_the_map_gate_stops_the_snapshot(self) -> None:
        """``skillbar_bindings.cpp:30-38``: a loading map leaves native's data at its defaults."""

        with mock.patch.object(Map, "IsMapReady", staticmethod(lambda: False)):
            instance = PySkillbar()
            self.assertIsNone(instance.data)
            self.assertEqual(instance.agent_id, 0)

    def test_the_hero_skillbar_walks_the_same_array(self) -> None:
        """``GetHeroSkillbar`` (``skillbar_methods.cpp:478-488``)."""

        self.world.skillbars = [_skillbar(agent_id=555)]
        with mock.patch.object(
            party_module.Party.Heroes,
            "GetHeroAgentIDByPartyPosition",
            staticmethod(lambda position: 555),
        ):
            slots = SkillBar.GetHeroSkillbar(1)
            self.assertEqual([int(slot.id.id) for slot in slots], list(SLOT_SKILL_IDS))
            # Native's own guard: an index above 7 is an empty list.
            self.assertEqual(SkillBar.GetHeroSkillbar(8), [])

    def test_the_hovered_skill_reads_the_tooltip_payload(self) -> None:
        """``GetHoveredSkill`` (``skillbar_bindings.cpp:130-133``, ``skillbar_methods.cpp:490``)."""

        skill_tooltip = _FakeTooltip(payload=0x200000, payload_len=0x14)
        client = _FakeClient(
            world=self.world,
            tooltip=skill_tooltip,
            tooltip_word=42,
            skill_ids=(42,),
        )
        with _patch_client(client):
            self.assertEqual(SkillBar.GetHoveredSkillID(), 42)

        # A tooltip that is not a skill tooltip answers 0 without reading its payload.
        other = _FakeTooltip(payload=0x200000, payload_len=0xC)
        client = _FakeClient(world=self.world, tooltip=other, tooltip_word=42, skill_ids=(42,))
        with _patch_client(client):
            self.assertEqual(SkillBar.GetHoveredSkillID(), 0)
            self.assertEqual(client.tooltip_reader.reads, [])

        # No tooltip at all is 0 as well.
        client = _FakeClient(world=self.world, tooltip=None, skill_ids=(42,))
        with _patch_client(client):
            self.assertEqual(SkillBar.GetHoveredSkillID(), 0)


class SkillBarActionTests(unittest.TestCase):
    """``ChangeHeroSecondary`` is the one action whose mechanism this port has."""

    def setUp(self) -> None:
        self.client = _FakeClient(world=_FakeWorld([_skillbar()]))
        self._client_patch = _patch_client(self.client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)
        self._map_patch = mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True))
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)
        self._agent_patch = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: AGENT_ID)
        )
        self._agent_patch.start()
        self.addCleanup(self._agent_patch.stop)

    def test_it_calls_the_resolver_with_the_agent_and_the_profession(self) -> None:
        """``skillbar_methods.cpp:85-93``: agent id, then the profession."""

        with mock.patch.object(
            party_module.Party.Heroes,
            "GetHeroAgentIDByPartyPosition",
            staticmethod(lambda position: 555),
        ):
            instance = PySkillbar()
            self.assertTrue(instance.ChangeHeroSecondary(1, 6))

        self.assertEqual(
            self.client.calls,
            [("skillbar.change_secondary_func", int(CallForm.U32_U32), 555, 6)],
        )

    def test_a_missing_hero_answers_false_without_calling(self) -> None:
        """``skillbar_methods.cpp:88-90``: no agent id, no call."""

        with mock.patch.object(
            party_module.Party.Heroes,
            "GetHeroAgentIDByPartyPosition",
            staticmethod(lambda position: 0),
        ):
            instance = PySkillbar()
            self.assertFalse(instance.ChangeHeroSecondary(1, 6))

        self.assertEqual(self.client.calls, [])


class SkillBarRaisingTests(unittest.TestCase):
    """The members that are not built yet name themselves and what they need."""

    def setUp(self) -> None:
        client = _FakeClient(world=_FakeWorld([_skillbar()]))
        self._client_patch = _patch_client(client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)
        self._map_patch = mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True))
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)
        self._agent_patch = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: AGENT_ID)
        )
        self._agent_patch.start()
        self.addCleanup(self._agent_patch.stop)

    def _assert_names(self, member: str, call: Any, requirement: str) -> None:
        with self.assertRaises(NotImplementedError) as caught:
            call()
        message = str(caught.exception)
        self.assertIn(member, message)
        self.assertIn(requirement, message)
        self.assertIn("The source's member works", message)

    def test_the_action_members_name_their_mechanism(self) -> None:
        """The three control-action members name ``ui::Keypress``."""

        for member, call in (
            ("UseSkill", lambda: SkillBar.UseSkill(1)),
            ("UseSkillTargetless", lambda: SkillBar.UseSkillTargetless(1)),
            ("HeroUseSkill", lambda: SkillBar.HeroUseSkill(1, 1, 1)),
        ):
            with self.subTest(member=member):
                self._assert_names(member, call, "ui::Keypress")

    def test_the_template_members_name_the_decode(self) -> None:
        """The two loaders name native's ``DecodeSkillTemplate`` and its gating."""

        self._assert_names(
            "LoadSkillTemplate",
            lambda: SkillBar.LoadSkillTemplate("OQAAAA"),
            "DecodeSkillTemplate",
        )
        self._assert_names(
            "LoadHeroSkillTemplate",
            lambda: SkillBar.LoadHeroSkillTemplate(1, "OQAAAA"),
            "DecodeSkillTemplate",
        )

    def test_the_slot_recharge_names_the_skill_timer(self) -> None:
        """``get_recharge`` names ``MemoryManager::GetSkillTimer``."""

        slot = SkillBar.GetSkillData(1)
        self._assert_names(
            "get_recharge",
            lambda: slot.get_recharge,
            "GetSkillTimer",
        )
