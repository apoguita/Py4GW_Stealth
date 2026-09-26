"""Offline tests for the ported ``Skill`` class (``py4gw/skill.py``) and its record.

Three things are pinned here, and none of them needs a running client.

**The surface is the source's.** Reforged's ``Py4GWCoreLib/Skill.py`` is read at test time and every
member it declares — across the class and its five nested namespaces — must exist here with the same
nesting, so a member that is dropped, renamed or added fails here. Native's ``PySkill`` binding
surface (``skill_bindings.cpp``) is pinned the same way: the fields Reforged's members read must all
be present on the ported binding object.

**The record is the client's.** ``SkillStruct`` is checked field by field against native's own
declaration (``include/GW/context/skill.h``, which carries an offset comment on every line and a
``static_assert(sizeof(Skill) == 0xA4)``): every field's offset is asserted against the header's
comment, and the client's own bytes — read from ``Gw.exe`` on disk, at the address the port's
resolver answers — are decoded for skills whose data is known (Healing Signet's 2-second activation
and 5 energy, Meteor Shower's 25 energy and 60-second recharge, Blood Renewal's 15% health cost,
Power Block's elite bit, and the exhaustion skills' overcast). That is the same offline method
``tools/resolve_offline.py`` uses: no process, no elevation, no risk.

**The values are the source's.** Every implemented member is driven against a synthetic binding
object built from a record the test chooses, and the two name tables native generates in code are
compared with the switches in ``skill_names.cpp``.
"""

from __future__ import annotations

import ast
import re
import ctypes
import struct
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw.context.skill_context import (
    SKILL_ARRAY_LENGTH,
    SKILL_RECORD_SIZE,
    UNUSED_SKILL_IDS,
    SkillConstantArray,
    SkillStruct,
)
from py4gw.skill import (
    PROFESSION_NAMES,
    SKILL_TYPE_NAMES,
    PySkill,
    Skill,
    SkillID,
    SkillProfession,
    SkillType,
)
from py4gw.skill_names import (
    ID_TO_NAME,
    NAME_TO_ID,
    SKILL_NAME_TABLE,
    GetSkillIDByName,
    GetSkillNameByID,
)

#: Reforged's own file, and the native sources the binding and the record come from.
SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Skill.py")
NATIVE_SKILL_H = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\skill.h")
NATIVE_BINDINGS = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skill_bindings.cpp")
NATIVE_NAMES = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\src\GW\skillbar\skill_names.cpp")

#: The client image the record was verified against, and the address the port's resolver answers
#: for ``skillbar.skill_array_addr`` on it (``tools/resolve_offline.py skillbar``).
CLIENT = Path(r"F:\GW\GW1\Gw.exe")
SKILL_ARRAY_ADDRESS = 0x98A370

#: ``(field, offset)`` for every member of the client's record, from ``skill.h``'s own comments.
RECORD_LAYOUT: tuple[tuple[str, int], ...] = (
    ("skill_id", 0x00),
    ("h0004", 0x04),
    ("campaign", 0x08),
    ("type", 0x0C),
    ("special", 0x10),
    ("combo_req", 0x14),
    ("effect1", 0x18),
    ("condition", 0x1C),
    ("effect2", 0x20),
    ("weapon_req", 0x24),
    ("profession", 0x28),
    ("attribute", 0x29),
    ("title", 0x2A),
    ("skill_id_pvp", 0x2C),
    ("combo", 0x30),
    ("target", 0x31),
    ("h0032", 0x32),
    ("skill_equip_type", 0x33),
    ("overcast", 0x34),
    ("energy_cost", 0x35),
    ("health_cost", 0x36),
    ("h0037", 0x37),
    ("adrenaline", 0x38),
    ("activation", 0x3C),
    ("aftercast", 0x40),
    ("duration0", 0x44),
    ("duration15", 0x48),
    ("recharge", 0x4C),
    ("h0050", 0x50),
    ("skill_arguments", 0x58),
    ("scale0", 0x5C),
    ("scale15", 0x60),
    ("bonus_scale0", 0x64),
    ("bonus_scale15", 0x68),
    ("aoe_range", 0x6C),
    ("const_effect", 0x70),
    ("caster_overhead_animation_id", 0x74),
    ("caster_body_animation_id", 0x78),
    ("target_body_animation_id", 0x7C),
    ("target_overhead_animation_id", 0x80),
    ("projectile_animation_1_id", 0x84),
    ("projectile_animation_2_id", 0x88),
    ("icon_file_id", 0x8C),
    ("icon_file_id_2", 0x90),
    ("icon_file_id_hi_res", 0x94),
    ("name", 0x98),
    ("concise", 0x9C),
    ("description", 0xA0),
)


def _record(**fields: Any) -> SkillStruct:
    """Build one record with the fields a test names, the rest zero."""

    record = SkillStruct()
    for name, value in fields.items():
        setattr(record, name, value)
    return record


def _binding(record: SkillStruct | None, skill_id: int = 1) -> PySkill:
    """Build a binding object over one record, the way ``PySkill.__init__`` does."""

    client = mock.Mock()
    client.read_skill = mock.Mock(return_value=record)
    with mock.patch("py4gw.client._current_client", client):
        return PySkill(skill_id)


class SkillSurfaceTests(unittest.TestCase):
    """The port declares the source's class, its nested namespaces, and every member in them."""

    def _source_tree(self) -> ast.Module:
        if not SOURCE.is_file():
            self.skipTest(f"Reforged's Skill.py is not at {SOURCE}")
        return ast.parse(SOURCE.read_text(encoding="utf-8"))

    def _source_classes(self) -> dict[str, ast.ClassDef]:
        classes: dict[str, ast.ClassDef] = {}
        for node in self._source_tree().body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node
                for child in node.body:
                    if isinstance(child, ast.ClassDef):
                        classes[f"{node.name}.{child.name}"] = child
        return classes

    @staticmethod
    def _member_names(node: ast.ClassDef) -> list[str]:
        return [
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    def test_the_class_and_its_namespaces_exist(self) -> None:
        """``Skill`` with ``Data``/``Attribute``/``Flags``/``Animations``/``ExtraData`` nested."""

        classes = self._source_classes()
        self.assertIn("Skill", classes)
        self.assertEqual(
            sorted(name for name in classes if "." in name),
            [
                "Skill.Animations",
                "Skill.Attribute",
                "Skill.Data",
                "Skill.ExtraData",
                "Skill.Flags",
            ],
        )
        self.assertTrue(hasattr(Skill, "Data"))
        self.assertTrue(hasattr(Skill, "Attribute"))
        self.assertTrue(hasattr(Skill, "Flags"))
        self.assertTrue(hasattr(Skill, "Animations"))
        self.assertTrue(hasattr(Skill, "ExtraData"))

    def test_every_member_is_declared_in_the_sources_order(self) -> None:
        """Every ``def`` of the source's class and namespaces, in the source's own order."""

        classes = self._source_classes()
        for path, source_node in classes.items():
            owner: Any = Skill
            for part in path.split(".")[1:]:
                owner = getattr(owner, part)
            with self.subTest(namespace=path):
                ported = [
                    name
                    for name, value in vars(owner).items()
                    if isinstance(value, staticmethod)
                ]
                self.assertEqual(ported, self._member_names(source_node))

    def test_the_description_cache_attribute_is_the_sources(self) -> None:
        """``_desc_cache = None`` (``Skill.py:7``) is the declared class attribute."""

        self.assertIsNone(Skill._desc_cache)

    def test_the_binding_object_carries_every_field_the_source_reads(self) -> None:
        """Native's bound ``PySkill.Skill`` surface (``skill_bindings.cpp:236-294``)."""

        fields = (
            "id", "campaign", "type", "special", "combo_req", "effect1", "condition", "effect2",
            "weapon_req", "profession", "attribute", "title", "id_pvp", "combo", "target",
            "skill_equip_type", "overcast", "energy_cost", "health_cost", "adrenaline",
            "activation", "aftercast", "duration_0pts", "duration_15pts", "recharge",
            "skill_arguments", "scale_0pts", "scale_15pts", "bonus_scale_0pts", "bonus_scale_15pts",
            "aoe_range", "const_effect", "caster_overhead_animation_id", "caster_body_animation_id",
            "target_body_animation_id", "target_overhead_animation_id", "projectile_animation1_id",
            "projectile_animation2_id", "icon_file_id", "icon_file2_id", "icon_file_hi_res_id",
            "name_id", "concise", "description_id", "is_touch_range", "is_elite", "is_half_range",
            "is_pvp", "is_pve", "is_playable", "is_stacking", "is_non_stacking", "is_unused",
            "adrenaline_a", "adrenaline_b", "recharge2", "h0004", "h0032", "h0037",
        )
        obj = _binding(_record())
        for field in fields:
            with self.subTest(field=field):
                self.assertTrue(hasattr(obj, field), field)


class SkillRecordLayoutTests(unittest.TestCase):
    """``SkillStruct`` matches native's declaration, field for field."""

    def test_the_record_is_the_declared_size(self) -> None:
        """``static_assert(sizeof(Skill) == 0xA4)`` (``skill.h:87``)."""

        self.assertEqual(ctypes.sizeof(SkillStruct), 0xA4)
        self.assertEqual(SKILL_RECORD_SIZE, 0xA4)
        self.assertEqual(SKILL_ARRAY_LENGTH, 0xD94)

    def test_every_field_sits_at_the_headers_offset(self) -> None:
        """Each offset is asserted against ``skill.h``'s own comment for that field."""

        for field, offset in RECORD_LAYOUT:
            with self.subTest(field=field):
                self.assertEqual(getattr(SkillStruct, field).offset, offset)

    def test_the_header_declares_the_same_layout(self) -> None:
        """The header is read, not quoted: its comments name the same fields and offsets."""

        if not NATIVE_SKILL_H.is_file():
            self.skipTest(f"native skill.h is not at {NATIVE_SKILL_H}")
        text = NATIVE_SKILL_H.read_text(encoding="utf-8")
        self.assertIn("static_assert(sizeof(Skill) == 0xA4", text)
        for field, offset in RECORD_LAYOUT:
            with self.subTest(field=field):
                self.assertIn(f"+h{offset:04X}", text)
        for native_name in ("skill_id", "skill_id_pvp", "energy_cost", "health_cost", "overcast"):
            self.assertIn(native_name, text)


class SkillFlagTests(unittest.TestCase):
    """The flag fields are derived from the record's ``special`` word (``skill.h:75-85``)."""

    def test_the_special_bits(self) -> None:
        """Each bit native tests, and the ``is_playable`` inversion."""

        cases: tuple[tuple[int, dict[str, bool]], ...] = (
            (0x2, {"is_touch_range": True}),
            (0x4, {"is_elite": True}),
            (0x8, {"is_half_range": True}),
            (0x400000, {"is_pvp": True}),
            (0x80000, {"is_pve": True}),
            (0x10000, {"is_stacking": True}),
            (0x20000, {"is_non_stacking": True}),
            (0x2000000, {"is_playable": False}),
            (0, {"is_playable": True}),
        )
        for special, expected in cases:
            with self.subTest(special=hex(special)):
                obj = _binding(_record(special=special))
                for name, value in expected.items():
                    self.assertEqual(getattr(obj, name), value, name)

    def test_is_unused_reads_the_native_id_list(self) -> None:
        """``Skill::IsUnused`` (``skill.cpp:11-18``) over ``unused_skill_ids``."""

        self.assertEqual(len(UNUSED_SKILL_IDS), 64)
        for skill_id in (2511, 2539, 1380, 1581, 2303, 2325, 11, 1299, 1125, 775):
            with self.subTest(skill_id=skill_id):
                self.assertTrue(_binding(_record(skill_id=skill_id), skill_id).is_unused)
        for skill_id in (0, 1, 2, 2510, 2540, 1582, 2302, 2326, 1126):
            with self.subTest(skill_id=skill_id):
                self.assertFalse(_binding(_record(skill_id=skill_id), skill_id).is_unused)

    def test_the_energy_cost_encoding_is_the_clients(self) -> None:
        """``Skill::GetEnergyCost`` (``skill.h:67-73``): ``11 → 15``, ``12 → 25``, else the byte."""

        for stored, expected in ((0, 0), (5, 5), (10, 10), (11, 15), (12, 25), (15, 15), (99, 99)):
            with self.subTest(stored=stored):
                self.assertEqual(_binding(_record(energy_cost=stored)).energy_cost, expected)


class SkillNameTableTests(unittest.TestCase):
    """The three tables native generates in code are transcribed, not invented."""

    def _names_source(self) -> str:
        if not NATIVE_NAMES.is_file():
            self.skipTest(f"native skill_names.cpp is not at {NATIVE_NAMES}")
        return NATIVE_NAMES.read_text(encoding="utf-8")

    def test_the_skill_name_table_is_the_sources_pairs(self) -> None:
        """``kSkillNameTable`` (``skill_names.cpp:16-3048``), pair for pair and in source order."""

        text = self._names_source()
        start = text.index("const SkillNameEntry kSkillNameTable[] = {")
        block = text[start : text.index("};", start)]
        expected = [
            (int(entry), name)
            for entry, name in re.findall(r'\{\s*(\d+),\s*"([^"]+)"\s*\}', block)
        ]
        self.assertEqual(len(expected), 3031)
        self.assertEqual(list(SKILL_NAME_TABLE), expected)
        self.assertEqual(GetSkillNameByID(1), "Healing_Signet")
        self.assertEqual(GetSkillIDByName("Healing_Signet"), 1)
        self.assertEqual(GetSkillNameByID(99999), "")
        self.assertEqual(GetSkillIDByName("no such skill"), 0)

    def test_both_name_maps_are_built_from_the_table(self) -> None:
        """``IdToName``/``NameToId`` (``skill_names.cpp:3050-3066``)."""

        self.assertEqual(ID_TO_NAME[1], "Healing_Signet")
        self.assertEqual(NAME_TO_ID["Healing_Signet"], 1)
        self.assertEqual(len(ID_TO_NAME), len(SKILL_NAME_TABLE))
        self.assertEqual(len(NAME_TO_ID), len(SKILL_NAME_TABLE))

    def test_the_skill_type_names_are_the_sources_cases(self) -> None:
        """``GetSkillTypeNameByID`` (``skill_names.cpp:3081-3114``): 29 cases, ``""`` otherwise."""

        text = self._names_source()
        block = text[text.index("const char* GetSkillTypeNameByID") : text.index("const char* GetProfessionNameById")]
        expected = {
            int(case): name
            for case, name in re.findall(r'case\s+(\d+):\s*return\s+"([^"]*)"', block)
        }
        self.assertEqual(SKILL_TYPE_NAMES, expected)
        self.assertEqual(len(SKILL_TYPE_NAMES), 29)
        self.assertEqual(SkillType(4).GetName(), "Hex")
        self.assertEqual(SkillType(29).GetName(), "Disguise")
        self.assertEqual(SkillType(30).GetName(), "")
        self.assertEqual(SkillType(0).GetName(), "")

    def test_the_profession_names_are_the_sources_cases(self) -> None:
        """``GetProfessionNameById`` (``skill_names.cpp:3116-3131``): 11 cases."""

        text = self._names_source()
        block = text[text.index("const char* GetProfessionNameById") :]
        expected = {
            int(case): name
            for case, name in re.findall(r'case\s+(\d+):\s*return\s+"([^"]*)"', block)
        }
        self.assertEqual(PROFESSION_NAMES, expected)
        self.assertEqual(SkillProfession(5).GetName(), "Mesmer")
        self.assertEqual(SkillProfession(5).ToInt(), 5)
        self.assertEqual(SkillProfession(11).GetName(), "")


class SkillMemberTests(unittest.TestCase):
    """Every implemented member answers the source's value for a chosen record."""

    #: One record with distinctive, exactly-representable values in every field a member reads.
    RECORD = {
        "campaign": 2,
        "type": 4,
        "special": 0x5,
        "combo_req": 7,
        "effect1": 11,
        "condition": 12,
        "effect2": 13,
        "weapon_req": 2,
        "profession": 6,
        "attribute": 3,
        "title": 9,
        "skill_id_pvp": 42,
        "combo": 1,
        "target": 2,
        "skill_equip_type": 1,
        "overcast": 10,
        "energy_cost": 12,
        "health_cost": 15,
        "adrenaline": 80,
        "activation": 2.0,
        "aftercast": 0.75,
        "duration0": 5,
        "duration15": 20,
        "recharge": 60,
        "skill_arguments": 3,
        "scale0": 1,
        "scale15": 2,
        "bonus_scale0": 3,
        "bonus_scale15": 4,
        "aoe_range": 1.5,
        "const_effect": 0.5,
        "caster_overhead_animation_id": 21,
        "caster_body_animation_id": 22,
        "target_body_animation_id": 23,
        "target_overhead_animation_id": 24,
        "projectile_animation_1_id": 25,
        "projectile_animation_2_id": 26,
        "icon_file_id": 31,
        "icon_file_id_2": 32,
        "icon_file_id_hi_res": 33,
        "name": 3476,
        "concise": 41,
        "description": 42,
    }

    def _with_record(self, member: str, *args: Any) -> Any:
        client = mock.Mock()
        client.read_skill = mock.Mock(return_value=_record(**self.RECORD))
        with mock.patch("py4gw.client._current_client", client):
            owner: Any = Skill
            for part in member.split(".")[:-1]:
                owner = getattr(owner, part)
            return getattr(owner, member.split(".")[-1])(*args)

    def test_the_record_readers(self) -> None:
        """Each member returns the field the source reads, with the source's own default."""

        cases: tuple[tuple[str, Any], ...] = (
            ("Data.GetCombo", 1),
            ("Data.GetComboReq", 7),
            ("Data.GetWeaponReq", 2),
            ("Data.GetOvercast", 10),
            ("Data.GetEnergyCost", 25),
            ("Data.GetHealthCost", 15),
            ("Data.GetAdrenaline", 80),
            ("Data.GetActivation", 2.0),
            ("Data.GetAftercast", 0.75),
            ("Data.GetRecharge", 60),
            ("Data.GetRecharge2", 0),
            ("Data.GetAoERange", 1.5),
            ("Data.GetAdrenalineA", 0),
            ("Data.GetAdrenalineB", 0),
            ("Attribute.GetAttribute", 3),
            ("Attribute.GetScale", (1, 2)),
            ("Attribute.GetBonusScale", (3, 4)),
            ("Attribute.GetDuration", (5, 20)),
            ("Flags.IsElite", True),
            ("Flags.IsTouchRange", False),
            ("Flags.IsHex", True),
            ("Flags.IsSignet", False),
            ("Animations.GetEffects", (11, 13)),
            ("Animations.GetSpecial", 0x5),
            ("Animations.GetConstEffect", 0.5),
            ("Animations.GetCasterOverheadAnimationID", 21),
            ("Animations.GetCasterBodyAnimationID", 22),
            ("Animations.GetTargetBodyAnimationID", 23),
            ("Animations.GetTargetOverheadAnimationID", 24),
            ("Animations.GetProjectileAnimationID", (25, 26)),
            ("Animations.GetIconFileID", (31, 32)),
            ("ExtraData.GetCondition", 12),
            ("ExtraData.GetTitle", 9),
            ("ExtraData.GetIDPvP", 42),
            ("ExtraData.GetTarget", 2),
            ("ExtraData.GetSkillEquipType", 1),
            ("ExtraData.GetSkillArguments", 3),
            ("ExtraData.GetNameID", 3476),
            ("ExtraData.GetConcise", 41),
            ("ExtraData.GetDescriptionID", 42),
        )
        for member, expected in cases:
            with self.subTest(member=member):
                self.assertEqual(self._with_record(member, 1), expected)

    def test_get_type_and_get_profession_are_tuples_of_id_and_name(self) -> None:
        """``Skill.py:82-97``: the id and the name table's answer for it."""

        self.assertEqual(self._with_record("GetType", 1), (4, "Hex"))
        self.assertEqual(self._with_record("GetProfession", 1), (6, "Elementalist"))

    def test_the_overcast_member_guards_on_the_special_flag(self) -> None:
        """``Skill.py:115-121``: without ``special & 1`` the member answers ``0``, not the byte."""

        client = mock.Mock()
        client.read_skill = mock.Mock(return_value=_record(overcast=10, special=0))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Skill.Data.GetOvercast(1), 0)

    def test_a_missing_record_leaves_the_bindings_defaults(self) -> None:
        """``skill_bindings.cpp:134-136``: no record, no fields — the defaults stay."""

        obj = _binding(None, 5)
        self.assertEqual(obj.id.id, 5)
        self.assertEqual(obj.campaign, 0)
        self.assertEqual(obj.type.id, 10)
        self.assertEqual(obj.profession.id, 0)
        self.assertFalse(obj.is_elite)
        self.assertFalse(obj.is_playable)

    def test_the_id_type_reads_and_compares_the_way_native_does(self) -> None:
        """``PySkillID`` equality is against another id or a plain integer."""

        self.assertEqual(SkillID(7), SkillID(7))
        self.assertEqual(SkillID(7), 7)
        self.assertNotEqual(SkillID(7), 8)
        self.assertEqual(hash(SkillID(7)), hash(7))


class SkillRaisingTests(unittest.TestCase):
    """The members that are not built yet name the table each one needs.

    Each of these members reaches its missing table *through* the binding object — the source's own
    order is ``Skill.skill_instance(skill_id).id.GetName()`` — so the tests supply a record the way a
    connection would, and the raise that surfaces is the missing table's. Without a connection the
    first failure is the usage error, which is the port's behaviour for every reader.
    """

    def setUp(self) -> None:
        client = mock.Mock()
        client.read_skill = mock.Mock(return_value=_record(skill_id=1, type=4))
        self._patch = mock.patch("py4gw.client._current_client", client)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _assert_names(self, call: Any, requirement: str) -> None:
        with self.assertRaises(NotImplementedError) as caught:
            call()
        message = str(caught.exception)
        self.assertIn(requirement, message)
        self.assertIn("The source's member works", message)

    def test_get_name_and_get_id_read_the_generated_table(self) -> None:
        """``Skill.GetName``/``Skill.GetID`` over native's ``kSkillNameTable``, both directions."""

        client = mock.Mock()
        client.read_skill = mock.Mock(return_value=_record(skill_id=1, type=7))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Skill.GetName(1), "Healing_Signet")
            self.assertEqual(Skill.GetName(192), "Meteor_Shower")
            self.assertEqual(Skill.GetID("Illusionary_Weaponry"), 33)
            self.assertEqual(Skill.GetID("Not_A_Skill"), 0)

    def test_get_campaign_names_the_region_enums(self) -> None:
        self._assert_names(lambda: Skill.GetCampaign(1), "CampaignName")

    def test_get_texture_path_names_the_texture_enums(self) -> None:
        self._assert_names(lambda: Skill.ExtraData.GetTexturePath(1), "SkillTextureMap")

    def test_the_description_members_name_the_bundled_json(self) -> None:
        for call in (
            lambda: Skill.GetDescription(1),
            lambda: Skill.GetConciseDescription(1),
            lambda: Skill.GetURL(1),
            lambda: Skill.GetProgressionData(1),
            lambda: Skill.GetNameFromWiki(1),
        ):
            with self.subTest(call=call):
                self._assert_names(call, "skill_descriptions.json")

    def test_the_binding_needs_a_connection_before_it_can_answer(self) -> None:
        """With no client the failure is the port's usage error, not a wrong value."""

        with mock.patch("py4gw.client._current_client", None):
            with self.assertRaises(RuntimeError) as caught:
                Skill.Data.GetEnergyCost(1)
            self.assertIn("connect()", str(caught.exception))


class SkillArrayReaderTests(unittest.TestCase):
    """The table reader indexes the way the client's own accessor does."""

    class _Reader:
        def __init__(self, base: int, fault_at: int | None = None) -> None:
            self.base = base
            self.fault_at = fault_at
            self.reads: list[tuple[int, int]] = []
            self.record = bytearray(SKILL_RECORD_SIZE)
            struct.pack_into("<I", self.record, 0, 0x99)

        def read(self, address: int, size: int) -> bytes:
            self.reads.append((address, size))
            if self.fault_at is not None and address >= self.fault_at:
                raise OSError(f"{address:#010x} is unreadable")
            return bytes(self.record[:size])

    def _array(self, fault_at: int | None = None) -> tuple[SkillConstantArray, Any]:
        reader = self._Reader(0x100000, fault_at)
        patterns = mock.Mock()
        patterns.resolve = mock.Mock(
            return_value=mock.Mock(ok=True, value=0x100000, message="")
        )
        return SkillConstantArray(reader, mock.Mock(), patterns), reader

    def test_the_stride_and_the_base_are_the_clients(self) -> None:
        """``address + skill_id * 0xA4``, the accessor's own arithmetic."""

        array, reader = self._array()
        record = array.read(3)
        assert record is not None
        self.assertEqual(reader.reads[-1], (0x100000 + 3 * 0xA4, 0xA4))
        self.assertEqual(record.skill_id, 0x99)

    def test_the_clients_bound_is_enforced(self) -> None:
        """``cmp esi, 0xD94``: at the bound and past it the reader answers ``None``."""

        array, reader = self._array()
        self.assertIsNotNone(array.read(SKILL_ARRAY_LENGTH - 1))
        self.assertIsNone(array.read(SKILL_ARRAY_LENGTH))
        self.assertIsNone(array.read(-1))
        self.assertEqual(len(reader.reads), 1)

    def test_a_missing_array_and_an_unreadable_record_are_the_sources_null(self) -> None:
        """No table, or a read that faults, is ``None`` — which the binding turns into defaults."""

        array, _ = self._array()
        with mock.patch.object(array, "resolve_address", lambda: None):
            self.assertIsNone(array.read(1))

        array, _ = self._array(fault_at=0x100000)
        self.assertIsNone(array.read(1))


class SkillClientBytesTests(unittest.TestCase):
    """The port decodes the client's own bytes, offline, into the fields the members answer.

    This is the strongest check the change can make without a running client: ``Gw.exe`` on disk is
    the same image with its sections at their file offsets, so the port's own resolver, the record
    layout, the binding copy and every member are exercised over the real table at the address the
    client's own accessor uses.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if not CLIENT.is_file():
            raise unittest.SkipTest(f"no client image at {CLIENT}")
        tools = str(Path(__file__).resolve().parents[1] / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from pe_image import PeImage  # type: ignore[import-not-found]  # noqa: PLC0415
        from resolve_offline import FileModule  # type: ignore[import-not-found]  # noqa: PLC0415

        from py4gw.scanner.patterns import PatternCatalog  # noqa: PLC0415
        from py4gw.scanner.remote import RemoteScanner  # noqa: PLC0415

        cls.image = PeImage(str(CLIENT))
        cls.reader = FileModule(cls.image)
        scanner = RemoteScanner(cls.reader, cls.image.image_base, cls.image.size_of_image)
        scanner.initialize()
        cls.catalog = PatternCatalog.from_directory(
            Path(__file__).resolve().parents[1] / "offsets"
        )
        cls.scanner = scanner
        result = cls.catalog.resolve("skillbar.skill_array_addr", scanner)
        if not result.ok or not result.value:
            raise unittest.SkipTest("skillbar.skill_array_addr does not resolve on this image")
        cls.base = result.value

    def _record(self, skill_id: int) -> SkillStruct:
        raw = self.reader.read(self.base + skill_id * SKILL_RECORD_SIZE, SKILL_RECORD_SIZE)
        return SkillStruct.from_buffer_copy(raw)

    def _client(self) -> Any:
        """A stand-in client whose ``read_skill`` answers from the file, as the real one would."""

        constants = SkillConstantArray(self.reader, self.scanner, self.catalog)
        client = mock.Mock()
        client.read_skill = constants.read
        return client

    def test_the_resolver_answers_the_table_the_accessor_uses(self) -> None:
        """The address is the one the client's own function adds (verified in the module docstring)."""

        self.assertEqual(self.base, SKILL_ARRAY_ADDRESS)
        ids = [self._record(index).skill_id for index in range(12)]
        self.assertEqual(ids, list(range(12)))

    def test_known_skills_decode_to_their_known_data(self) -> None:
        """Field values checked against the game's own data for skills whose numbers are stable.

        Every expectation below was read out of the client's table first, so the test pins what the
        client holds rather than a remembered number: Healing Signet is a 2-second, 4-second-recharge
        Signet with no energy cost, Power Block is an elite 15-energy Spell (the client's own ``11``
        encoding), Meteor Shower is 25 energy (``12``) with a 60-second recharge, Blood Renewal costs
        1 energy and 15% health, and Distortion and Mantra of Earth are Stances.
        """

        client = self._client()
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Skill.GetType(1)[1], "Signet")
            self.assertEqual(Skill.Data.GetEnergyCost(1), 0)
            self.assertEqual(Skill.Data.GetActivation(1), 2.0)
            self.assertEqual(Skill.Data.GetRecharge(1), 4)
            self.assertFalse(Skill.Flags.IsElite(1))

            self.assertTrue(Skill.Flags.IsSpell(5))
            self.assertTrue(Skill.Flags.IsElite(5))
            self.assertEqual(Skill.Data.GetEnergyCost(5), 15)

            self.assertEqual(Skill.Data.GetEnergyCost(192), 25)
            self.assertEqual(Skill.Data.GetRecharge(192), 60)
            self.assertEqual(Skill.Data.GetActivation(192), 5.0)
            self.assertEqual(Skill.Data.GetOvercast(192), 10)

            self.assertEqual(Skill.Data.GetEnergyCost(115), 1)
            self.assertEqual(Skill.Data.GetHealthCost(115), 15)
            self.assertEqual(Skill.GetType(115)[1], "Enchantment")

            self.assertTrue(Skill.Flags.IsStance(11))
            self.assertFalse(Skill.Flags.IsHex(11))
            self.assertEqual(Skill.Data.GetEnergyCost(6), 10)
            self.assertEqual(Skill.GetType(6)[1], "Stance")

    def test_the_exhaustion_skills_are_exactly_the_flagged_ones(self) -> None:
        """``special & 1`` is the overcast flag (``skill.h:36``): 25 records carry it."""

        flagged = [
            index for index in range(SKILL_ARRAY_LENGTH) if self._record(index).special & 0x1
        ]
        self.assertEqual(len(flagged), 25)
        with mock.patch("py4gw.client._current_client", self._client()):
            for skill_id in flagged:
                with self.subTest(skill_id=skill_id):
                    self.assertNotEqual(Skill.Data.GetOvercast(skill_id), 0)
            # A skill without the flag answers 0 even though its byte holds something else.
            self.assertEqual(Skill.Data.GetOvercast(1), 0)

    def test_the_pvp_id_member_reads_the_records_own_word(self) -> None:
        """``Skill.ExtraData.GetIDPvP`` — the member ``Utils``'s Balthazar conversion calls."""

        with mock.patch("py4gw.client._current_client", self._client()):
            for skill_id in (1, 5, 11, 115, 192):
                with self.subTest(skill_id=skill_id):
                    self.assertEqual(
                        Skill.ExtraData.GetIDPvP(skill_id),
                        int(self._record(skill_id).skill_id_pvp),
                    )

    def test_the_unused_list_matches_the_clients_own_records(self) -> None:
        """``IsUnused`` over the client's table: the list's ids answer true, others false."""

        with mock.patch("py4gw.client._current_client", self._client()):
            self.assertTrue(Skill.Flags.IsUnused(2303))
            self.assertTrue(Skill.Flags.IsUnused(2539))
            self.assertFalse(Skill.Flags.IsUnused(1))
            self.assertFalse(Skill.Flags.IsUnused(2302))

