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
from py4gw.py4gwcorelib_src.utils import Utils
from py4gw.skillbar import (
    SKILL_TOOLTIP_PAYLOAD_LENGTH,
    PySkillbar,
    SkillBar,
    SkillbarSkill,
    decode_skill_template,
    is_primary_attribute_required,
    is_profession_required,
)
from py4gw.ui_manager import UIManager

#: Reforged's own file, and the native sources the binding and its hovered-skill read come from.
SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Skillbar.py")
NATIVE_BINDINGS = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skillbar_bindings.cpp")
NATIVE_METHODS = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skillbar_methods.cpp")

#: The agent id the synthetic skillbar belongs to.
AGENT_ID = 1234

#: The eight slots of the synthetic skillbar.
SLOT_SKILL_IDS = (5, 0, 42, 0, 0, 0, 0, 7)

#: Two ids the template decoder must refuse: one past ``SKILL_MAX`` (``3431``) and one at the
#: attribute table's own bound (``0x33``, ``skillbar.cpp:41``). Both still fit the bit widths the
#: encoder chooses for them, so the decoder's range checks are what refuse them and not the reader.
SKILL_OVER_MAX = 3432
ATTRIBUTE_PAST_TABLE = 0x33


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


class _FakeMemoryManager:
    """The ported skill timer, answering a fixed value (``memory_manager.cpp:69-71``)."""

    def __init__(self, timer: int = 0) -> None:
        self.timer = timer

    def GetSkillTimer(self) -> int:
        return self.timer


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
        #: The ported skill timer, for the slot member that subtracts it: ``get_recharge``.
        self.memory_manager: Any = _FakeMemoryManager()

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


class SkillBarControlActionTests(unittest.TestCase):
    """The three control-action members press the client's own keys, in native's own order.

    ``PySkillbar::UseSkill``/``UseSkillTargetless`` (``skillbar_bindings.cpp:70-86``) validate the slot,
    make it zero-based and hand it to ``GW::skillbar::UseSkill``/``PointBlankUseSkill``
    (``skillbar_methods.cpp:439-447``), which press ``ControlAction_UseSkill1`` (``0xA4``) plus that
    zero-based slot. ``HeroUseSkill`` (``skillbar_bindings.cpp:88-115``) is the **switch** of the seven
    ``ControlAction_Hero{N}Skill1`` bases — not an arithmetic series — with the target saved and
    restored around the press.

    Three quirks of the source are pinned here because a rewrite would quietly lose them: the player's
    previous target is **not** restored, the hero's **is** (even on the path where no change was made),
    and ``skill_number`` is not validated the way ``slot`` is.
    """

    def setUp(self) -> None:
        client = _FakeClient(world=_FakeWorld([_skillbar()]))
        self._client_patch = _patch_client(client)
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)

        # ``PySkillbar()`` snapshots through ``Map.IsMapReady()``, the same gate the raising class
        # above patches, so the construction path under test is the real one.
        self._map_patch = mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True))
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)
        self._agent_patch = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: AGENT_ID)
        )
        self._agent_patch.start()
        self.addCleanup(self._agent_patch.stop)

        self.calls: list[tuple[Any, ...]] = []
        for name, handler in (
            ("GetTargetID", staticmethod(lambda: 111)),
            ("ChangeTarget", staticmethod(lambda agent_id: self.calls.append(("target", agent_id)))),
        ):
            patch = mock.patch.object(Player, name, handler)
            patch.start()
            self.addCleanup(patch.stop)

        keypress = mock.patch.object(
            UIManager,
            "Keypress",
            staticmethod(lambda key, frame_id: self.calls.append(("key", key, frame_id))),
        )
        keypress.start()
        self.addCleanup(keypress.stop)

    def test_use_skill_presses_the_base_plus_the_zero_based_slot(self) -> None:
        """``skillbar_bindings.cpp:70-77`` → ``skillbar_methods.cpp:439-442``.

        ``0xA4`` is ``ControlAction_UseSkill1``; the binding makes the slot zero-based before the
        method adds it, so slot ``1`` presses ``0xA4`` and slot ``8`` presses ``0xAB``.
        """

        instance = PySkillbar()
        self.assertTrue(instance.UseSkill(1))
        self.assertTrue(instance.UseSkill(8))

        pressed = [call[1] for call in self.calls if call[0] == "key"]
        self.assertEqual(pressed, [0xA4, 0xA4 + 7])
        self.assertEqual([call[2] for call in self.calls if call[0] == "key"], [0, 0])

    def test_use_skill_changes_the_target_only_when_it_must(self) -> None:
        """``if (target && target != agent::GetTargetId())`` — and never restores it."""

        instance = PySkillbar()

        instance.UseSkill(1, 0)
        self.assertEqual([call for call in self.calls if call[0] == "target"], [])

        self.calls.clear()
        instance.UseSkill(1, 111)  # already the target
        self.assertEqual([call for call in self.calls if call[0] == "target"], [])

        self.calls.clear()
        instance.UseSkill(1, 999)
        targets = [call[1] for call in self.calls if call[0] == "target"]
        self.assertEqual(targets, [999], "the target is changed once")
        self.assertNotIn(111, targets, "the player's previous target is not put back")
        self.assertEqual([call[1] for call in self.calls if call[0] == "key"], [0xA4])

    def test_use_skill_targetless_presses_without_touching_the_target(self) -> None:
        """``skillbar_methods.cpp:445-447`` is the keypress alone."""

        instance = PySkillbar()
        self.assertTrue(instance.UseSkillTargetless(3))

        self.assertEqual(self.calls, [("key", 0xA4 + 2, 0)])

    def test_the_player_members_refuse_a_slot_outside_one_to_eight(self) -> None:
        """``ValidateSlot`` (``skillbar_bindings.cpp:44-49``): ``std::out_of_range``, and no press."""

        instance = PySkillbar()
        for slot in (0, 9, -1, 100):
            for member in ("UseSkill", "UseSkillTargetless"):
                with self.subTest(slot=slot, member=member):
                    with self.assertRaises(IndexError) as caught:
                        getattr(instance, member)(slot)
                    self.assertIn("Skill slot out of range (must be between 1 and 8)", str(caught.exception))
        self.assertEqual(self.calls, [], "a refused slot must not press anything")

    def test_hero_use_skill_presses_the_switch_base_plus_the_skill_index(self) -> None:
        """``skillbar_bindings.cpp:92-101,107-108``: the seven bases, then ``base + skill_idx``.

        The bases are the reason the source writes a switch — ``0xE5``, ``0xED``, ``0xF5``, then
        ``0x106`` — so hero ``3`` with skill ``1`` presses ``0xF5`` and hero ``1`` with skill ``2``
        presses ``0xE6``.
        """

        instance = PySkillbar()

        self.assertTrue(instance.HeroUseSkill(0, 1, 3))
        self.calls.clear()
        self.assertTrue(instance.HeroUseSkill(0, 2, 1))

        self.assertEqual([call for call in self.calls if call[0] == "key"], [("key", 0xE6, 0)])

    def test_hero_use_skill_restores_the_previous_target(self) -> None:
        """``:110-112``: the hero's target **is** put back, unlike the player's."""

        instance = PySkillbar()
        instance.HeroUseSkill(999, 1, 1)

        self.assertEqual(
            self.calls,
            [("target", 999), ("key", 0xE5, 0), ("target", 111)],
        )

    def test_hero_use_skill_restores_even_when_nothing_changed(self) -> None:
        """``:110`` tests ``curr_target_id && target_agent_id != curr_target_id`` — the source's own quirk.

        With no target asked for (``0``) and a live previous target, the guard is still true, so the
        client is told to target what it already has. Kept as the source has it.
        """

        instance = PySkillbar()
        instance.HeroUseSkill(0, 1, 1)

        self.assertEqual([call for call in self.calls if call[0] == "target"], [("target", 111)])

    def test_hero_use_skill_answers_false_for_a_hero_outside_one_to_seven(self) -> None:
        """``default: return false`` (``:100``) — and nothing is pressed."""

        instance = PySkillbar()
        for hero_index in (0, 8, 99):
            with self.subTest(hero_index=hero_index):
                self.assertFalse(instance.HeroUseSkill(0, 1, hero_index))
        self.assertEqual(self.calls, [])

    def test_hero_use_skill_does_not_validate_the_skill_number(self) -> None:
        """The source validates the hero and not the slot, so the press still goes out."""

        instance = PySkillbar()
        self.assertTrue(instance.HeroUseSkill(0, 9, 1))

        self.assertEqual([call for call in self.calls if call[0] == "key"], [("key", 0xE5 + 8, 0)])


class SkillTemplateTests(unittest.TestCase):
    """The build-template decoder, its gating and its two loaders.

    ``DecodeSkillTemplate`` (``skillbar_methods.cpp:190-312``) is a pure function over the template
    string plus two tables — the client's attribute constants and its skill constants — so it can be
    driven offline in full. The two tables are patched here rather than read, and the strongest check
    in this class runs the template through the source's **own encoder**
    (``py4gwcorelib_src/utils.py``, Reforged's ``Utils.GenerateSkillbarTemplate``) and back through the
    decoder: a round trip that agrees is evidence for the bit order, both bit-width fields and the
    profession/attribute/skill gating at once.
    """

    #: A stand-in for the client's attribute-constant table, as ``get_attribute_profession`` reads it:
    #: attribute id -> ``(profession, is_primary)``. The professions are arbitrary but inside the
    #: decoder's own ``1..8`` range, and the primary flags are the source's ten (``skillbar.cpp:107-119``).
    ATTRIBUTES = {
        0: (1, True),    # a primary attribute of the first profession
        1: (1, False),
        17: (2, True),   # a primary attribute of a *different* profession
        18: (2, False),
    }

    class _SkillRecord:
        """What ``GetSkillConstantData`` answers: a record with a ``profession`` word."""

        def __init__(self, profession: int) -> None:
            self.profession = profession

    def _tables(self, attribute=None, skill_profession=0):
        """Patch the decoder's two tables for the duration of a ``with`` block."""

        attribute = self.ATTRIBUTES if attribute is None else attribute
        return mock.patch.multiple(
            skillbar_module,
            get_attribute_profession=mock.Mock(
                side_effect=lambda value, want_primary=False: attribute.get(
                    int(value), (skillbar_module.PROFESSION_NONE, False)
                )
            ),
            _skill_constant_record=mock.Mock(
                side_effect=lambda skill_id: self._SkillRecord(skill_profession)
            ),
        )

    def test_the_alphabet_and_its_reverse_are_the_sources(self) -> None:
        """``kBase64Table``/``kBase64ToValue`` (``skillbar_methods.cpp:26-38``)."""

        self.assertEqual(len(skillbar_module.BASE64_TABLE), 64)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["A"], 0)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["Z"], 25)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["a"], 26)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["0"], 52)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["+"], 62)
        self.assertEqual(skillbar_module.BASE64_TO_VALUE["/"], 63)
        self.assertIsNone(skillbar_module.BASE64_TO_VALUE.get("="))
        self.assertEqual(sorted(skillbar_module.BASE64_TO_VALUE.values()), list(range(64)))

    def test_read_bits_is_least_significant_bit_first(self) -> None:
        """``ReadBits`` (``:47-55``) over the order ``WriteBits`` (``:40-45``) wrote."""

        # ``WriteBits(5, ..., 6)`` is 1,0,1,0,0,0 — LSB first — and reads back as 5.
        bits = [1, 0, 1, 0, 0, 0]
        value, cursor = skillbar_module._read_bits(bits, 0, 6)
        self.assertEqual(value, 5)
        self.assertEqual(cursor, 6)

        # A later window is read at the cursor, not from the start.
        value, cursor = skillbar_module._read_bits([0, 0, 1, 1], 0, 2)
        self.assertEqual(value, 0)
        value, cursor = skillbar_module._read_bits([0, 0, 1, 1], 2, 2)
        self.assertEqual(value, 3)
        self.assertEqual(cursor, 4)

    def test_a_template_the_source_encoded_decodes_back_to_the_same_build(self) -> None:
        """The round trip through Reforged's own ``Utils.GenerateSkillbarTemplate`` encoder."""

        template = Utils.encode_skill_template(
            prof_primary=1,
            prof_secondary=2,
            attributes={0: 12, 18: 8},
            skills=[1, 2, 3, 4, 5, 6, 7, 8],
        )
        with self._tables():
            decoded = decode_skill_template(template)

        self.assertIsNotNone(decoded, f"the decoder refused {template!r}")
        assert decoded is not None
        self.assertEqual(decoded.primary, 1)
        self.assertEqual(decoded.secondary, 2)
        self.assertEqual(decoded.skills, [1, 2, 3, 4, 5, 6, 7, 8])
        filled = [
            (attribute.attribute, attribute.points)
            for attribute in decoded.attributes
            if attribute.attribute != skillbar_module.ATTRIBUTE_NONE
        ]
        self.assertEqual(filled, [(0, 12), (18, 8)])
        # The decoder writes ``Attribute::None`` into every slot it did not fill.
        self.assertEqual(len(decoded.attributes), skillbar_module.TEMPLATE_ATTRIBUTE_COUNT)
        self.assertEqual(
            sum(
                1
                for attribute in decoded.attributes
                if attribute.attribute == skillbar_module.ATTRIBUTE_NONE
            ),
            skillbar_module.TEMPLATE_ATTRIBUTE_COUNT - 2,
        )

    def test_a_profession_zero_or_past_dervish_is_refused(self) -> None:
        """``skillbar_methods.cpp:228``: ``prof1 <= None`` or either past ``Dervish`` answers false."""

        for primary, secondary in ((0, 1), (9, 1), (1, 9), (9, 9)):
            with self.subTest(primary=primary, secondary=secondary):
                template = Utils.encode_skill_template(primary, secondary, {}, [1])
                with self._tables():
                    self.assertIsNone(decode_skill_template(template))

        # ``prof2 == Profession::None`` is a legitimate build: no secondary. The source's own
        # asymmetry is kept here: ``prof1 <= None`` is fatal while ``prof2 < None`` is not.
        template = Utils.encode_skill_template(1, 0, {}, [1])
        with self._tables():
            decoded = decode_skill_template(template)
        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(decoded.primary, 1)
        self.assertEqual(decoded.secondary, 0)

    def test_a_character_outside_the_alphabet_is_refused(self) -> None:
        """``kBase64ToValue``'s ``-1`` (``:204-210``)."""

        with self._tables():
            self.assertIsNone(decode_skill_template("OQAA*A"))
            self.assertIsNone(decode_skill_template("OQAA\nA"))
            self.assertIsNone(decode_skill_template(""))

    def test_a_bad_header_is_refused(self) -> None:
        """``if (header != 0 && header != 14)`` (``:217-223``)."""

        with self._tables():
            # A leading 'B' is value 1, so the first four bits are 1,0,0,0 — a header of 1.
            self.assertIsNone(decode_skill_template("B" + "A" * 30))

    def test_a_skill_id_past_the_ceiling_is_refused(self) -> None:
        """``SKILL_MAX`` (``:191``) and the check at ``:284-289``."""

        self.assertEqual(skillbar_module.SKILL_MAX, 3431)
        template = Utils.encode_skill_template(1, 2, {}, [SKILL_OVER_MAX])
        with self._tables():
            self.assertIsNone(decode_skill_template(template))

    def test_a_skill_of_neither_profession_is_refused(self) -> None:
        """``:297-302``: the record's profession must be one of the template's two."""

        template = Utils.encode_skill_template(1, 2, {}, [1, 2, 3])
        with self._tables(skill_profession=3):
            self.assertIsNone(decode_skill_template(template))
        with self._tables(skill_profession=1):
            self.assertIsNotNone(decode_skill_template(template))

    def test_an_attribute_id_past_the_table_is_refused(self) -> None:
        """``attrib_id >= g_attribute_array_count`` (``:244-249``), the bound the source hardcodes."""

        self.assertEqual(skillbar_module.ATTRIBUTE_ARRAY_COUNT, 0x33)
        # ``0x33`` is the first id past the table, so the encoder's id is inside the 4-bit field and
        # the decoder's own range check is what refuses it.
        template = Utils.encode_skill_template(1, 2, {ATTRIBUTE_PAST_TABLE: 4}, [1])
        with self._tables():
            self.assertIsNone(decode_skill_template(template))

    def test_a_primary_attribute_of_the_wrong_profession_is_refused(self) -> None:
        """``:259-271``: the owner must be a template profession, and a primary must be the first."""

        # Attribute 17 is primary and owned by profession 2, but the template's secondary is 2 — so
        # ``is_primary_attribute && profession != prof1`` refuses it.
        template = Utils.encode_skill_template(1, 2, {17: 6}, [1])
        with self._tables():
            self.assertIsNone(decode_skill_template(template))
        # The same attribute with the template's *first* profession is accepted.
        template = Utils.encode_skill_template(2, 1, {17: 6}, [1])
        with self._tables():
            self.assertIsNotNone(decode_skill_template(template))

    def test_an_attribute_of_neither_profession_is_refused(self) -> None:
        """``:260-265``: an owner that is neither ``prof1`` nor ``prof2`` is fatal."""

        template = Utils.encode_skill_template(1, 2, {3: 5}, [1])
        with self._tables():
            self.assertIsNone(decode_skill_template(template))

    def test_the_gating_helpers_answer_the_sources_way(self) -> None:
        """``IsPrimaryAttributeRequired``/``IsProfessionRequired`` (``skillbar.cpp:128-152``)."""

        template = skillbar_module.SkillTemplate()
        self.assertEqual(template.primary, skillbar_module.PROFESSION_NONE)
        template.attributes[0].attribute = 0
        template.skills[0] = 7

        with self._tables():
            # ``Profession::None`` answers false from both, before anything is examined.
            self.assertFalse(is_primary_attribute_required(template, skillbar_module.PROFESSION_NONE))
            self.assertFalse(is_profession_required(template, skillbar_module.PROFESSION_NONE))
            # Attribute 0 is a primary of profession 1.
            self.assertTrue(is_primary_attribute_required(template, 1))
            self.assertTrue(is_profession_required(template, 1))
            # A non-primary attribute of the same profession is not a *primary* requirement.
            template.attributes[0].attribute = 1
            self.assertFalse(is_primary_attribute_required(template, 1))
            self.assertTrue(is_profession_required(template, 1))
            # Neither question is true for a profession the build does not use.
            self.assertFalse(is_primary_attribute_required(template, 7))
            self.assertFalse(is_profession_required(template, 7))

    def test_the_primary_attribute_set_is_the_sources_switch(self) -> None:
        """The ten ids ``GetAttributeProfession`` sets its flag for (``skillbar.cpp:107-119``)."""

        self.assertEqual(
            sorted(skillbar_module.PRIMARY_ATTRIBUTES),
            [0, 6, 12, 16, 17, 23, 35, 36, 40, 44],
        )
        self.assertEqual(len(skillbar_module.PRIMARY_ATTRIBUTES), 10)

    def test_a_missing_attribute_record_answers_the_sources_none(self) -> None:
        """``GetAttributeProfession`` (``skillbar.cpp:103-105``): no record, ``Profession::None``."""

        with mock.patch.object(skillbar_module, "get_attribute_constant_data", lambda value: None):
            self.assertEqual(
                skillbar_module.get_attribute_profession(0, want_primary=True),
                (skillbar_module.PROFESSION_NONE, False),
            )

    def test_get_attribute_constant_data_bounds_the_id_before_reading(self) -> None:
        """``skillbar_methods.cpp:80-81``: an id at or past the count is refused before the array."""

        with mock.patch.object(skillbar_module, "_attribute_info_array") as table:
            self.assertIsNone(
                skillbar_module.get_attribute_constant_data(skillbar_module.ATTRIBUTE_ARRAY_COUNT)
            )
            self.assertIsNone(
                skillbar_module.get_attribute_constant_data(skillbar_module.ATTRIBUTE_ARRAY_COUNT + 5)
            )
            table.assert_not_called()

    def test_the_two_template_loaders_gate_on_the_instance_type(self) -> None:
        """``skillbar_methods.cpp:317`` and ``:360``: not an outpost, not a load."""

        with mock.patch.object(Map, "GetInstanceType", staticmethod(lambda: 1)):
            self.assertFalse(skillbar_module.load_skill_template("OQAAAA"))
            self.assertFalse(skillbar_module.load_hero_skill_template(1, "OQAAAA"))

    def test_hero_index_zero_is_the_player_and_delegates(self) -> None:
        """``:363-364``: ``if (hero_index == 0) return LoadSkillTemplate(temp);``"""

        with mock.patch.object(Map, "GetInstanceType", staticmethod(lambda: 0)), mock.patch.object(
            skillbar_module, "load_skill_template", mock.Mock(return_value="delegated")
        ) as inner:
            self.assertEqual(
                skillbar_module.load_hero_skill_template(0, "OQAAAA"), "delegated"
            )
            inner.assert_called_once_with("OQAAAA")

    def test_the_loaders_answer_false_when_the_template_does_not_decode(self) -> None:
        """The decode stands directly in front of everything else in both loaders."""

        with mock.patch.object(Map, "GetInstanceType", staticmethod(lambda: 0)):
            self.assertFalse(skillbar_module.load_skill_template("!!!!"))
            self.assertFalse(skillbar_module.load_hero_skill_template(1, "!!!!"))


class SkillBarSlotTests(unittest.TestCase):
    """``get_recharge`` over the ported skill timer."""

    def setUp(self) -> None:
        self._map_patch = mock.patch.object(Map, "IsMapReady", staticmethod(lambda: True))
        self._map_patch.start()
        self.addCleanup(self._map_patch.stop)
        self._agent_patch = mock.patch.object(
            Player, "GetAgentID", staticmethod(lambda: AGENT_ID)
        )
        self._agent_patch.start()
        self.addCleanup(self._agent_patch.stop)

    def test_the_slot_recharge_is_the_source_s_subtraction(self) -> None:
        """``get_recharge`` is ``recharge - GetSkillTimer()`` (``skill.cpp:20-25``).

        It raised until 2026-09-26 for want of the timer; the timer is ported now
        (``py4gw/memory/memory_manager.py``), so what is pinned here is the source's own two
        branches: a zero recharge answers ``0`` without asking for the timer, and a real one is the
        ``DWORD`` subtraction — masked, because the register is.
        """

        client = _FakeClient(world=_FakeWorld([_skillbar(skill_ids=(1,))]))
        client.memory_manager = _FakeMemoryManager(500)
        with mock.patch("py4gw.client._current_client", client):
            slot = SkillBar.GetSkillData(1)
            # ``_skillbar`` fills only the slots it is given: slot 1 carries recharge 100.
            self.assertEqual(int(slot.recharge), 100)
            self.assertEqual(slot.get_recharge, (100 - 500) & 0xFFFFFFFF)

            empty = SkillBar.GetSkillData(2)
            self.assertEqual(int(empty.recharge), 0)
            self.assertEqual(empty.get_recharge, 0)
