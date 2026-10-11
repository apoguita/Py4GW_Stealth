"""Offline tests for the GwAu3 accessor families built by `tools/generate_gwa3_family.py`.

Covers `py4gw/gwa3/data_skill.py` (`Skill_GetSkillInfo`, 63 keys) and `py4gw/gwa3/data_party.py`
(`Party_GetPartyContextInfo`, 14 keys). No client and no elevation: the accessors read a
*materialized* record -- this project copies the client's bytes into a `ctypes.Structure` -- so a test
fills a byte buffer with known values, materializes the same structure over it, and asserts what the
accessor answers.

The integrity tests are the important ones, and they are the reason this file exists: they compare the
generated table against the source's own `Case` list **read independently of the parser**. That check
caught two real defects while this generator was being written -- `Flags` resolved to
`henchmen_array.m_buffer` and the member counts answered `player_party_ptr` -- both of which were
wrong values of the right type, undetectable by a caller.
"""

from __future__ import annotations

import ctypes
import importlib
import importlib.util
import re
import struct
import sys
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

from py4gw.gwa3 import data_item, data_map, data_party, data_quest, data_skill, data_world  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "generate_gwa3_family", REPO_ROOT / "tools" / "generate_gwa3_family.py"
)
if _spec is None or _spec.loader is None:  # pragma: no cover - the file is in the tree
    raise RuntimeError("could not load tools/generate_gwa3_family.py")
GENERATOR = importlib.util.module_from_spec(_spec)
sys.modules["generate_gwa3_family"] = GENERATOR
_spec.loader.exec_module(GENERATOR)

FAMILY_CASES = {
    family.module: (family, module)
    for family, module in (
        (family, importlib.import_module(f"py4gw.gwa3.{family.module}"))
        for family in GENERATOR.FAMILIES
    )
}


def _build_record(family, **values):
    """A record whose bytes hold the given values, materialized the way this project materializes one.

    ``values`` are named GwAu3 keys (``EnergyCost=5``), resolved through the same case table the
    generator used, so a test states a value in GwAu3's own vocabulary rather than in offsets.
    """

    import importlib

    module = importlib.import_module(f"py4gw.{family.structure[0]}")
    structure = getattr(module, family.structure[1])
    size = ctypes.sizeof(structure)
    buffer = (ctypes.c_uint8 * size)()

    cases = {key: case for case in GENERATOR.parse_cases(family) for key in case.keys}
    for key, value in values.items():
        case = cases.get(key)
        if case is None:
            raise KeyError(f"{family.function} declares no field case for {key!r}")
        fmt = GENERATOR.WIDTHS[case.type_text.split("[")[0]]
        struct.pack_into(f"<{fmt}", buffer, case.offset, value)
    return structure.from_buffer_copy(bytes(buffer))


def call_family(family, module, key):
    """Call a family's accessor the way its own signature requires.

    Every reader takes the record's id and the field name, except `World_GetWorldInfo`, whose only
    parameter is the field name -- the world context is a singleton. Calling that one with `(1, key)`
    raises `TypeError`, which the integrity test would report as a key that failed for an unstated
    reason rather than as the test's own mistake.
    """

    if family.record_arg:
        return module.__dict__[family.function](1, key)
    return module.__dict__[family.function](key)


class _ServeRecord:
    """Make the family's accessor read a record built here, instead of reaching the client."""

    def __init__(self, family, record) -> None:
        self.family = family
        self.record = record

    def __enter__(self) -> "_ServeRecord":
        module = FAMILY_CASES[self.family.module][1]
        self._patch = mock.patch.object(module, "_record", return_value=self.record)
        self._patch.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._patch.stop()


class SkillFieldTests(unittest.TestCase):
    """`Skill_GetSkillInfo` against a skill record holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_skill")
    module = data_skill

    def _info(self, key: str) -> object:
        record = _build_record(
            self.family, SkillID=1062, Campaign=2, SkillType=3, Profession=1, Attribute=17,
            EnergyCost=10, Recharge=30, Activation=1,
        )
        with _ServeRecord(self.family, record):
            return self.module.Skill_GetSkillInfo(1062, key)

    def test_named_attributes(self) -> None:
        self.assertEqual(self._info("SkillID"), 1062)
        self.assertEqual(self._info("Campaign"), 2)
        self.assertEqual(self._info("SkillType"), 3)
        self.assertEqual(self._info("Profession"), 1)
        self.assertEqual(self._info("Attribute"), 17)
        self.assertEqual(self._info("EnergyCost"), 10)
        self.assertEqual(self._info("Recharge"), 30)
        self.assertEqual(self._info("Activation"), 1)

    def test_an_empty_field_name_answers_zero(self) -> None:
        record = _build_record(self.family, SkillID=1062)
        with _ServeRecord(self.family, record):
            self.assertEqual(self.module.Skill_GetSkillInfo(1062, ""), 0)

    def test_an_unknown_field_name_answers_zero(self) -> None:
        record = _build_record(self.family, SkillID=1062)
        with _ServeRecord(self.family, record):
            self.assertEqual(self.module.Skill_GetSkillInfo(1062, "NotAKey"), 0)

    def test_a_skill_the_client_does_not_hold_answers_zero(self) -> None:
        with _ServeRecord(self.family, None):
            self.assertEqual(self.module.Skill_GetSkillInfo(9999, "Campaign"), 0)


class PartyFieldTests(unittest.TestCase):
    """`Party_GetPartyContextInfo` against a party-context record holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_party")
    module = data_party

    def test_the_total_party_size_is_the_sum_of_its_parts(self) -> None:
        """`TotalPartySize` combines three counts, two of which this layer refuses.

        So it is tested against the accessor rather than a record: GwAu3's expression is a sum of three
        named keys, and stubbing them proves the sum is the source's and not a different arithmetic.
        """

        answers = {"PlayerCount": 4, "HenchmenCount": 3, "HeroCount": 2}

        def fake(key: str) -> int:
            return answers[key]

        record = _build_record(self.family, Flags=0)
        with _ServeRecord(self.family, record):
            with mock.patch.object(self.module, self.family.function, side_effect=fake):
                self.assertEqual(self.module._READERS["TotalPartySize"](record, None), 9)

    def test_flags_and_counts(self) -> None:
        record = _build_record(self.family, Flags=0x38, InvitationRequestsCount=2, InvitationSendingCount=1)
        with _ServeRecord(self.family, record):
            self.assertEqual(self.module.Party_GetPartyContextInfo("Flags"), 0x38)
            self.assertEqual(self.module.Party_GetPartyContextInfo("InvitationRequestsCount"), 2)
            self.assertEqual(self.module.Party_GetPartyContextInfo("InvitationSendingCount"), 1)

    def test_the_masked_booleans_read_the_flags_word(self) -> None:
        # GwAu3_Data_Party.au3:16-28 -- 0x10 hard mode, 0x20 defeated, 0x80 party leader, 0x08 waiting.
        record = _build_record(self.family, Flags=0x10 | 0x80)
        with _ServeRecord(self.family, record):
            self.assertTrue(self.module.Party_GetPartyContextInfo("IsHardMode"))
            self.assertTrue(self.module.Party_GetPartyContextInfo("IsPartyLeader"))
            self.assertFalse(self.module.Party_GetPartyContextInfo("IsDefeated"))
            self.assertFalse(self.module.Party_GetPartyContextInfo("IsWaitingForMission"))

    def test_a_zero_flags_word_is_all_false(self) -> None:
        record = _build_record(self.family, Flags=0)
        with _ServeRecord(self.family, record):
            for key in ("IsHardMode", "IsDefeated", "IsPartyLeader", "IsWaitingForMission"):
                with self.subTest(key=key):
                    self.assertFalse(self.module.Party_GetPartyContextInfo(key))

    def test_the_member_counts_read_through_the_party_pointer_or_answer_zero(self) -> None:
        """GwAu3 reads these through `player_party_ptr`; the pointer is followed, and a zero one is `0`.

        This is the regression test for the defect the generator's first version shipped -- all five
        keys resolved to `record.player_party_ptr` because it occupies offset 0x54, which is the offset
        GwAu3 reads *through*, not the count -- and it is also the check on the fix that followed the
        pointer: with the record's pointer zero (what the served record holds, and GwAu3's own "no
        party" case at ``:71``), every one of the five answers ``0`` rather than a pointer.
        `MyPartyPtr` is still refused, because it *is* that pointer.
        """

        record = _build_record(self.family, Flags=0)
        with _ServeRecord(self.family, record):
            for key in ("PlayerCount", "HenchmenCount", "HeroCount", "OtherCount", "PlayerPartyID"):
                with self.subTest(key=key):
                    self.assertEqual(self.module.Party_GetPartyContextInfo(key), 0)

            with self.assertRaises(NotImplementedError) as raised:
                self.module.Party_GetPartyContextInfo("MyPartyPtr")
            message = str(raised.exception)
            self.assertIn("GwAu3_Data_Party.au3", message)
            self.assertIn("py4gw/", message)


class ItemFieldTests(unittest.TestCase):
    """`Item_GetItemInfoByItemID` against an item record holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_item")
    module = data_item

    def _info(self, key: str) -> object:
        record = _build_record(
            self.family, ItemID=777, AgentID=4242, ModelFileID=1234, ItemType=5,
            Value=250, Quantity=3, Interaction=0x1 | 0x2,
        )
        with _ServeRecord(self.family, record):
            return self.module.Item_GetItemInfoByItemID(777, key)

    def test_named_attributes(self) -> None:
        self.assertEqual(self._info("ItemID"), 777)
        self.assertEqual(self._info("AgentID"), 4242)
        self.assertEqual(self._info("ModelFileID"), 1234)
        self.assertEqual(self._info("ItemType"), 5)
        self.assertEqual(self._info("Value"), 250)
        self.assertEqual(self._info("Quantity"), 3)

    def test_the_masked_interaction_keys(self) -> None:
        """`IsIdentified` and `IsStackable` are bits of the interaction word, not the word."""

        self.assertTrue(self._info("IsIdentified"))
        self.assertTrue(self._info("IsStackable"))

        plain = _build_record(self.family, ItemID=777, Interaction=0)
        with _ServeRecord(self.family, plain):
            self.assertFalse(self.module.Item_GetItemInfoByItemID(777, "IsIdentified"))
            self.assertFalse(self.module.Item_GetItemInfoByItemID(777, "IsStackable"))

    def test_is_material_is_a_comparison_not_the_type_word(self) -> None:
        """`Item_GetItemInfoByPtr`'s `IsMaterial` compares the type byte to 11.

        A reader that returned the byte would answer `5` where GwAu3 answers `False` -- a wrong value
        of a plausible type, and the reason the generator carries a table for this case shape.
        """

        not_material = _build_record(self.family, ItemID=777, ItemType=5)
        with _ServeRecord(self.family, not_material):
            self.assertIs(self.module.Item_GetItemInfoByItemID(777, "IsMaterial"), False)

        material = _build_record(self.family, ItemID=777, ItemType=11)
        with _ServeRecord(self.family, material):
            self.assertIs(self.module.Item_GetItemInfoByItemID(777, "IsMaterial"), True)

    def test_the_name_keys_run_the_ports_handshake_in_order(self) -> None:
        """A decode is not a read: request, then ready, then take the value.

        The three steps are the port's own (`py4gw/item.py:773`, `:779`, `:785`). Taking the value
        without requesting it answers `""`, which a caller cannot tell from a nameless item -- so the
        order is asserted rather than assumed, and the sequence is recorded.
        """

        calls: list[str] = []

        def request(item_id: int) -> None:
            calls.append(f"request:{item_id}")

        def ready(item_id: int) -> bool:
            calls.append(f"ready:{item_id}")
            return True

        def get(item_id: int) -> str:
            calls.append(f"get:{item_id}")
            return "Superior Vigor Rune"

        record = _build_record(self.family, ItemID=777)
        with _ServeRecord(self.family, record):
            with (
                mock.patch.object(data_item.Item, "RequestName", side_effect=request),
                mock.patch.object(data_item.Item, "IsNameReady", side_effect=ready),
                mock.patch.object(data_item.Item, "GetName", side_effect=get),
            ):
                value = self.module.Item_GetItemInfoByItemID(777, "Name")

        self.assertEqual(value, "Superior Vigor Rune")
        self.assertEqual(calls, ["request:777", "ready:777", "get:777"])

    def test_the_name_keys_are_answered_now_that_the_handshake_is_wired(self) -> None:
        """The regression guard for the layer's largest gap.

        Thirteen keys across two families used to refuse because a decode is a handshake rather than a
        read. The handshake is now run, so these are in the table and not in the refusals.
        """

        for key in ("Name", "CompleteName", "SingleItemName"):
            with self.subTest(key=key):
                self.assertIn(key, self.module._READERS)
                self.assertNotIn(key, self.module._UNIMPLEMENTED)

    def test_the_dye_bytes_refuse_rather_than_read_inside_a_structure(self) -> None:
        record = _build_record(self.family, ItemID=777)
        with _ServeRecord(self.family, record):
            for key in ("Dye1", "Dye2", "Dye3", "ExtraID"):
                with self.subTest(key=key):
                    with self.assertRaises(NotImplementedError) as raised:
                        self.module.Item_GetItemInfoByItemID(777, key)
                    self.assertIn("py4gw/", str(raised.exception))

    def test_the_encoded_name_spellings_are_not_refused_because_they_are_plain_reads(self) -> None:
        """The `*Enc` spellings are offset reads of the encoded pointer, and answer that pointer.

        They are in the table like any other field; they are *not* decoded, and GwAu3 does not decode
        them either -- its `NameEnc` returns the pointer. A caller that wants text asks for `Name`.
        """

        for key in ("NameEnc", "CompleteNameEnc", "SingleItemNameEnc"):
            with self.subTest(key=key):
                self.assertIn(key, self.module._READERS)
                self.assertNotIn(key, self.module._UNIMPLEMENTED)

    def test_info_string_is_not_a_key_gwau3_declares(self) -> None:
        """A name GwAu3 does not declare answers `0`, which is its own `Case Else`."""

        self.assertNotIn("InfoString", GENERATOR.declared_keys(self.family))
        record = _build_record(self.family, ItemID=777)
        with _ServeRecord(self.family, record):
            self.assertEqual(self.module.Item_GetItemInfoByItemID(777, "InfoString"), 0)

    def test_an_item_the_client_does_not_hold_answers_zero(self) -> None:
        with _ServeRecord(self.family, None):
            self.assertEqual(self.module.Item_GetItemInfoByItemID(9999, "ItemID"), 0)


class QuestFieldTests(unittest.TestCase):
    """`Quest_GetQuestInfo` against a quest-log entry holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_quest")
    module = data_quest

    def _info(self, key: str) -> object:
        # `Quest_GetQuestInfo` has no `ID` key -- the quest id is the argument, not a field
        # (`GwAu3_Data_Quest.au3:4`). The first version of this test asked for one and the case table
        # said so.
        record = _build_record(
            self.family, LogState=0x2 | 0x20, MapFrom=1, MapTo=2,
            MarkerX=100.5, MarkerY=-200.25,
        )
        with _ServeRecord(self.family, record):
            return self.module.Quest_GetQuestInfo(900, key)

    def test_named_attributes(self) -> None:
        self.assertEqual(self._info("LogState"), 0x2 | 0x20)
        self.assertEqual(self._info("MapFrom"), 1)
        self.assertEqual(self._info("MapTo"), 2)

    def test_the_marker_is_read_inside_the_marker_pointer(self) -> None:
        """GwAu3 reads floats at ``+0x18``/``+0x1C``, inside this project's `marker_ptr`."""

        self.assertAlmostEqual(cast(float, self._info("MarkerX")), 100.5, places=3)
        self.assertAlmostEqual(cast(float, self._info("MarkerY")), -200.25, places=3)

    def test_the_log_state_bits(self) -> None:
        """`IsCompleted` and `IsPrimary` are bits of the state word, not the word itself.

        GwAu3_Data_Quest.au3:28-37 reads ``BitAND(log_state, 0x1 / 0x2 / 0x10 / 0x20 / 0x40)``. A
        reader that returned the word would answer `34` where GwAu3 answers `True`.
        """

        self.assertTrue(self._info("IsCompleted"))
        self.assertTrue(self._info("IsPrimary"))
        self.assertFalse(self._info("IsCurrentQuest"))
        self.assertFalse(self._info("IsAreaPrimary"))

        plain = _build_record(self.family, LogState=0)
        with _ServeRecord(self.family, plain):
            for key in ("HasInfo", "IsCompleted", "IsCurrentQuest", "IsPrimary", "IsAreaPrimary"):
                with self.subTest(key=key):
                    self.assertFalse(self.module.Quest_GetQuestInfo(900, key))

    def test_a_quest_not_in_the_log_answers_false_for_has_quest(self) -> None:
        """GwAu3's own no-match guard answers `False` for this key and `0` for the rest.

        ``GwAu3_Data_Quest.au3:16-21``. An AutoIt caller testing `If Not $x` sees both the same; one
        comparing against `False` does not, which is why the distinction is kept.
        """

        with _ServeRecord(self.family, None):
            self.assertIs(self.module.Quest_GetQuestInfo(900, "HasQuest"), False)
            self.assertEqual(self.module.Quest_GetQuestInfo(900, "LogState"), 0)

    def test_the_four_text_keys_run_the_ports_handshake(self) -> None:
        """`Name`, `Location`, `LocationStr` and `Description` decode through the port's own handshake.

        GwAu3 hands each pointer to the client's decoder; this project's route is
        request/poll/take (`py4gw/quest.py:110`, `:116`, `:122`). Taking the value without requesting
        it answers `""`, which a caller cannot tell from a quest with no name.
        """

        calls: list[str] = []

        def request(quest_id: int) -> None:
            calls.append(f"request:{quest_id}")

        def ready(quest_id: int) -> bool:
            calls.append(f"ready:{quest_id}")
            return True

        def get(quest_id: int) -> str:
            calls.append(f"get:{quest_id}")
            return "The Villainy of Galrath"

        record = _build_record(self.family)
        with _ServeRecord(self.family, record):
            with (
                mock.patch.object(data_quest.Quest, "RequestQuestName", side_effect=request),
                mock.patch.object(data_quest.Quest, "IsQuestNameReady", side_effect=ready),
                mock.patch.object(data_quest.Quest, "GetQuestName", side_effect=get),
            ):
                value = self.module.Quest_GetQuestInfo(900, "Name")

        self.assertEqual(value, "The Villainy of Galrath")
        self.assertEqual(calls, ["request:900", "ready:900", "get:900"])

    def test_the_keys_with_no_port_route_still_refuse(self) -> None:
        """`NPCName`, `Objectives` and the two encoded spellings have no route here yet.

        `py4gw/quest.py` carries no request/ready/get trio for the NPC name or the objectives, so
        those refuse rather than answering an empty string that a caller could not detect as a gap.
        """

        record = _build_record(self.family)
        with _ServeRecord(self.family, record):
            for key in ("NPCName", "Objectives", "NameEnc", "NPCNameEnc", "DescriptionEnc", "ObjectivesEnc"):
                with self.subTest(key=key):
                    with self.assertRaises(NotImplementedError) as raised:
                        self.module.Quest_GetQuestInfo(900, key)
                    self.assertIn("py4gw/", str(raised.exception))

    def test_the_text_keys_are_in_the_table_and_not_the_refusals(self) -> None:
        for key in ("Name", "Location", "LocationStr", "Description"):
            with self.subTest(key=key):
                self.assertIn(key, self.module._READERS)
                self.assertNotIn(key, self.module._UNIMPLEMENTED)


class WorldFieldTests(unittest.TestCase):
    """`World_GetWorldInfo` against a world-context record holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_world")
    module = data_world

    def _info(self, key: str) -> object:
        record = _build_record(
            self.family, Experience=1234567, CurrentKurzick=5000, TotalEarnedKurzick=9000,
            Level=20, Morale=100, PlayerNumber=7, ActiveQuestID=42,
        )
        with _ServeRecord(self.family, record):
            return self.module.World_GetWorldInfo(key)

    def test_the_record_fields_match_gwau3_offsets(self) -> None:
        """GwAu3 reads these at ``+0x740``, ``+0x748``, ``+0x788``; the record names them."""

        self.assertEqual(self._info("Experience"), 1234567)
        self.assertEqual(self._info("CurrentKurzick"), 5000)
        self.assertEqual(self._info("TotalEarnedKurzick"), 9000)
        self.assertEqual(self._info("Level"), 20)
        self.assertEqual(self._info("Morale"), 100)
        self.assertEqual(self._info("PlayerNumber"), 7)
        self.assertEqual(self._info("ActiveQuestID"), 42)

    def test_an_empty_field_name_answers_zero(self) -> None:
        record = _build_record(self.family, Level=20)
        with _ServeRecord(self.family, record):
            self.assertEqual(self.module.World_GetWorldInfo(""), 0)

    def test_the_array_addresses_refuse_rather_than_answer_a_pointer(self) -> None:
        """Thirty keys are an array's address or its count, and this layer walks neither.

        Answering the address would be a value a caller could not tell from data -- and the count would
        be a number read out of an array this layer did not walk.
        """

        record = _build_record(self.family, Level=20)
        with _ServeRecord(self.family, record):
            # Only the *address* keys refuse. The `*Size` keys answer, because GwAu3 reads them at the
            # array's offset plus 8 and that is exactly where this project's `GW_Array` wrapper keeps
            # `m_size` -- an answer, not a gap. The address is the one that is not: `m_buffer` sits at
            # the array's own offset, so resolving it would answer a value of the right type naming the
            # wrong thing, which no caller can detect.
            #
            # The keys are GwAu3's own spellings too: `QuestLog`, not `QuestLogArray`.
            for key in ("PlayerArray", "QuestLog"):
                with self.subTest(key=key):
                    with self.assertRaises(NotImplementedError) as raised:
                        self.module.World_GetWorldInfo(key)
                    self.assertIn("py4gw/", str(raised.exception))

    def test_the_array_counts_answer_from_the_wrapper(self) -> None:
        """`PlayerArraySize` is `players_array.m_size` -- the wrapper's own member, so an answer."""

        import inspect

        for key, expected in (
            ("PlayerArraySize", "players_array.m_size"),
            ("QuestLogSize", "quest_log_array.m_size"),
        ):
            with self.subTest(key=key):
                self.assertNotIn(key, self.module._UNIMPLEMENTED)
                self.assertIn(expected, inspect.getsource(self.module._READERS[key]))

    def test_every_declared_key_is_in_the_table(self) -> None:
        """All 79, including the ones that refuse -- a key absent from the table answers `0`."""

        declared = GENERATOR.declared_keys(self.family)
        self.assertEqual(len(declared), 79)
        self.assertEqual(sorted(declared - set(self.module._READERS)), [])


class MapFieldTests(unittest.TestCase):
    """`Map_GetAreaInfo` against an area-info record holding known values."""

    family = next(f for f in GENERATOR.FAMILIES if f.module == "data_map")
    module = data_map

    def _info(self, key: str) -> object:
        record = _build_record(
            self.family, Campaign=1, Continent=2, MinPartySize=1, MaxPartySize=8,
            FileID=0x0102, Flags=0x20,
        )
        with _ServeRecord(self.family, record):
            return self.module.Map_GetAreaInfo(100, key)

    def test_the_record_fields_match_gwau3_offsets(self) -> None:
        """GwAu3 indexes the same table with the same ``0x7C`` stride, so the offsets line up."""

        self.assertEqual(self._info("Campaign"), 1)
        self.assertEqual(self._info("Continent"), 2)
        self.assertEqual(self._info("MinPartySize"), 1)
        self.assertEqual(self._info("MaxPartySize"), 8)
        self.assertEqual(self._info("FileID"), 0x0102)

    def test_is_on_world_map_is_the_negation_of_its_neighbours(self) -> None:
        """GwAu3's case is ``BitAND(flags, 0x20) = 0`` -- *false* when the bit is set.

        Every other flag key in this family tests a bit for non-zero, so a reader that treated them
        uniformly would invert this one and be believed.
        """

        with _ServeRecord(self.family, _build_record(self.family, Flags=0x20)):
            self.assertFalse(self.module.Map_GetAreaInfo(100, "IsOnWorldMap"))
        with _ServeRecord(self.family, _build_record(self.family, Flags=0x0)):
            self.assertTrue(self.module.Map_GetAreaInfo(100, "IsOnWorldMap"))

    def test_has_enter_button_tests_two_bits(self) -> None:
        """``BitAND(flags, 0x100) <> 0 Or BitAND(flags, 0x40000) <> 0`` -- either bit answers true."""

        for flags in (0x100, 0x40000):
            with self.subTest(flags=hex(flags)):
                with _ServeRecord(self.family, _build_record(self.family, Flags=flags)):
                    self.assertTrue(self.module.Map_GetAreaInfo(100, "HasEnterButton"))
        with _ServeRecord(self.family, _build_record(self.family, Flags=0x200)):
            self.assertFalse(self.module.Map_GetAreaInfo(100, "HasEnterButton"))

    def test_the_other_flag_keys_read_their_own_bit(self) -> None:
        for key, bit in (
            ("IsPvP", 0x40001),
            ("IsGuildHall", 0x800000),
            ("IsVanquishableArea", 0x10000000),
            ("IsUnlockable", 0x10000),
            ("HasMissionMapsTo", 0x8000000),
        ):
            with self.subTest(key=key):
                with _ServeRecord(self.family, _build_record(self.family, Flags=bit)):
                    self.assertTrue(self.module.Map_GetAreaInfo(100, key))
                with _ServeRecord(self.family, _build_record(self.family, Flags=0)):
                    self.assertFalse(self.module.Map_GetAreaInfo(100, key))

    def test_the_file_id_split_is_gwau3s_arithmetic(self) -> None:
        """`FileID1`/`FileID2` split the id (`GwAu3_Data_Map.au3:373-379`)."""

        with _ServeRecord(self.family, _build_record(self.family, FileID=0x0102)):
            self.assertEqual(self.module.Map_GetAreaInfo(100, "FileID1"), (0x0102 - 1) % 0xFF00 + 0x100)
            self.assertEqual(self.module.Map_GetAreaInfo(100, "FileID2"), int((0x0102 - 1) / 0xFF00) + 0x100)

    def test_every_declared_key_is_in_the_table(self) -> None:
        declared = GENERATOR.declared_keys(self.family)
        self.assertEqual(len(declared), 40)
        self.assertEqual(sorted(declared - set(self.module._READERS)), [])


#: The client's own refusal, whole: `require_client` (`py4gw/client.py:1937-1949`) names exactly what is
#: missing instead of failing vaguely, so a family that reaches it has *stated* its outcome.
CONNECTION_REFUSAL = "No Guild Wars client is connected"

#: Families whose answer for a key is reached **through the connection**, so that calling one with no
#: client connected is a stated outcome rather than a key that failed for an unstated reason.
#:
#: **GwAu3 resolves the record before it tests the key, and that resolution is a read of the client.**
#: GwAu3 resolves the account pointer at ``GwAu3_Data_Account.au3:9`` and tests the empty key at ``:10``;
#: the same pair at ``GwAu3_Data_Match.au3:12-13``, ``GwAu3_Data_Title.au3:7-12`` and
#: ``GwAu3_Data_Guild.au3:11-12``. These four are the families where that resolution -- or a key's own
#: read -- is reached with no client behind the record the test serves, in two shapes:
#:
#: * `data_match`, `data_title` and `data_guild` carry the family's **hand-written snippet accessor**,
#:   which is emitted after the generated one and is therefore the effective member
#:   (`py4gw/gwa3/data_match.py:248`, `data_title.py:282`, `data_guild.py:271`). It resolves the record
#:   itself, in the accessor, so the served record -- which replaces `_record` -- is never consulted and
#:   *every* key of those three answers the connection refusal offline;
#: * `data_account` keeps its generated accessor, and it is its `AccountName` reader that is one of the
#:   port's own connection reads: `_read_accountname` answers `Player.GetAccountName`
#:   (`py4gw/gwa3/data_account.py:78-81` -> `py4gw/player.py:573-576` -> `require_client`), so that one
#:   key cannot answer offline while its six siblings answer from the served record.
#:
#: **The generated families answer offline because the template reaches the client in exactly one place,
#: and it is the served one.** It emits `if info == ""` first, then `_UNIMPLEMENTED`, then `_READERS.get`,
#: and only then `_record(...)` (`tools/generate_gwa3_family.py:1395-1409`) -- and `_record` is the whole
#: of the template's client surface, which `_ServeRecord` replaces. So a refusal raises before the client
#: is touched and the served record answers every other key. `data_item`'s three and `data_quest`'s four
#: text keys reach the client as well -- through their decode handshake -- and the loop below replaces
#: those entries before it runs, which is why neither family needs an entry here.
FAMILIES_THAT_REACH_THE_CLIENT = frozenset({"data_account", "data_match", "data_guild", "data_title"})


class FamilyTableIntegrityTests(unittest.TestCase):
    """The generated tables against GwAu3's own `Case` lists, and against the written modules."""

    def test_each_familys_record_call_names_a_real_member(self) -> None:
        """The one project-specific line in each generated module must resolve.

        It is written by hand in the family specification, so it is the part most likely to be wrong:
        `data_party`'s first version called `read_context`, which `PartyContext` does not have, and
        `data_skill`'s referenced a variable name the accessor does not declare. Neither would have
        been caught by a test that replaces `_record` with a stub.

        **The call is checked against the type the property returns, not the connection class.**
        `ConnectedClient.party_context` is a property, so looking for the method on the connection
        asks the wrong object -- which is how the first version of this test failed on a call that is
        correct.
        """

        import importlib

        from py4gw.client import ConnectedClient

        for family in GENERATOR.FAMILIES:
            with self.subTest(family=family.module):
                expression = family.record_call.format(record_id="1")

                # Anything of the form `client.<attribute>.<method>(...)`.
                for owner, method in re.findall(r"client\.(\w+)\.(\w+)\(", expression):
                    descriptor = getattr(ConnectedClient, owner, None)
                    self.assertIsNotNone(descriptor, f"client.{owner} does not exist")
                    # A property's `fget` is the function; its return annotation says what it yields.
                    yielded = getattr(descriptor, "fget", None)
                    annotated = (
                        getattr(yielded, "__annotations__", {}).get("return") if yielded else None
                    )
                    owner_type = annotated
                    if isinstance(owner_type, str):
                        module = importlib.import_module("py4gw.context")
                        owner_type = getattr(module, owner_type, None)
                    self.assertTrue(
                        owner_type is not None and hasattr(owner_type, method),
                        f"{family.module}: {owner}.{method}() is not a member of {owner_type}",
                    )

                # Anything the connection itself is asked for.
                for attribute in re.findall(r"client\.(\w+)\(?", expression):
                    if f"client.{attribute}." in expression:
                        continue
                    self.assertTrue(
                        hasattr(ConnectedClient, attribute),
                        f"{family.module}'s record_call uses client.{attribute}, which does not exist",
                    )

    def test_every_declared_key_is_in_the_table(self) -> None:
        for module_name, (family, module) in FAMILY_CASES.items():
            with self.subTest(module=module_name):
                missing = sorted(GENERATOR.declared_keys(family) - set(module._READERS))
                self.assertEqual(missing, [], f"{len(missing)} keys GwAu3 declares are not in the table")

    def test_no_key_the_table_carries_that_gwau3_does_not(self) -> None:
        for module_name, (family, module) in FAMILY_CASES.items():
            with self.subTest(module=module_name):
                extra = sorted(set(module._READERS) - GENERATOR.declared_keys(family))
                self.assertEqual(extra, [], "these keys are in the table and not declared by GwAu3")

    def test_the_modules_are_current(self) -> None:
        for module_name, (family, _) in FAMILY_CASES.items():
            with self.subTest(module=module_name):
                expected = GENERATOR.render(family, GENERATOR.parse_cases(family))
                actual = (REPO_ROOT / "py4gw" / "gwa3" / f"{module_name}.py").read_text(encoding="utf-8")
                self.assertEqual(
                    actual, expected, f"py4gw/gwa3/{module_name}.py is stale -- re-run the generator"
                )

    def test_every_table_entry_answers_or_refuses_with_a_reason(self) -> None:
        """No key may raise for an unstated reason: a refusal names its GwAu3 line and its gap.

        **The text keys are patched out**, because they drive a decode handshake that needs a client.
        That is not a way of hiding them: their order is asserted by their own tests above, and what is
        checked here is that no *other* key raises something it does not explain.

        **One outcome is stated without a GwAu3 line on it, and it is the client's own refusal.** A record
        that cannot be read for want of a connection names exactly what is missing -- `require_client`'s
        sentence (`py4gw/client.py:1947-1949`) -- so it *is* a stated reason, and the families whose answer
        for a key is resolved through the connection (see `FAMILIES_THAT_REACH_THE_CLIENT`) are allowed to
        answer it rather than report a failure. The acceptance is narrow on purpose: only those four
        modules, only `RuntimeError`, and only with the client's own sentence in the message. Any other
        exception still fails here, and so does the same `RuntimeError` from any other family -- which is
        the whole point, because a family whose served record answers must answer.
        """

        for module_name, (family, module) in FAMILY_CASES.items():
            record = _build_record(family)
            # The table holds direct references to the readers, so patching the module attribute does
            # nothing -- the entry itself has to be replaced. It keeps the two-argument shape, because
            # the accessor dispatches a text key on `_COMPUTED` and would call it with both.
            originals = {
                key: module._READERS[key]
                for key in family.text_handshake
                if key in module._READERS
            }
            with self.subTest(module=module_name):
                for key in originals:
                    module._READERS[key] = lambda record, record_id, _key=key: f"<{_key}>"
                try:
                    with _ServeRecord(family, record):
                        for key in sorted(module._READERS):
                            if key == "TotalPartySize":
                                # Combines keys that refuse; its own test in PartyFieldTests covers it.
                                continue
                            try:
                                call_family(family, module, key)
                            except NotImplementedError as error:
                                message = str(error)
                                self.assertIn("GwAu3_", message, f"{key} refuses without citing GwAu3")
                                self.assertIn("py4gw/", message, f"{key} refuses without naming its gap")
                            except RuntimeError as error:
                                # A missing connection is a stated outcome, but only for a family that
                                # reaches the client for this key -- and the message has to be the
                                # client's own, so a `RuntimeError` from anywhere else still fails here.
                                if module_name not in FAMILIES_THAT_REACH_THE_CLIENT:
                                    raise
                                self.assertIn(
                                    CONNECTION_REFUSAL,
                                    str(error),
                                    f"{key} failed with a RuntimeError that does not name the "
                                    f"missing client",
                                )
                finally:
                    module._READERS.update(originals)


if __name__ == "__main__":
    unittest.main()
