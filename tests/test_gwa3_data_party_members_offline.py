"""Offline tests for the party-**member** accessors `tools/gwa3_snippets/data_party_my_party.py` carries.

No client. The four accessors read through the party pointer the context exposes
(`PartyContextStruct.player_party`), so a test serves a stand-in client whose context answers a
stand-in party record, and then checks the source's own guards and key sets:

* `Party_GetMyPartyInfo`'s five scalar keys against the party record's fields, and the four
  ``Array*PartyMember`` keys refusing with their own reason (a client *address* is what GwAu3 returns
  there, and a caller wants the members);
* the **one-based** member numbers with the source's own bounds tests -- the player accessor subtracts
  first and rejects `0`, the hero accessor rejects it directly;
* the hero accessor's owner filter, which counts the party-wide hero array's entries belonging to the
  controlled character's player number;
* the henchman accessor's three keys;
* `Party_GetHeroFlagInfo` refusing, naming the world array it needs.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from types import SimpleNamespace
from typing import Any
from unittest import mock

from py4gw.gwa3 import data_party

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Modules"
    / "Data"
    / "GwAu3_Data_Party.au3"
)


class _Array(SimpleNamespace):
    """A stand-in for a `GWArray`: the accessors read ``m_size`` and the member list beside it."""


def _member(**values: Any) -> SimpleNamespace:
    return SimpleNamespace(**values)


class _Client:
    def __init__(self, party: Any, world: Any = None) -> None:
        self._party_record = party
        self._world_record = world

    def read_party_context(self) -> Any:
        return SimpleNamespace(player_party=self._party_record)

    def read_world_context(self) -> Any:
        return self._world_record


def _serve(test: unittest.TestCase, party: Any, world: Any = None) -> None:
    """Patch the client and the agent read the accessors reach for."""

    patcher = mock.patch.object(data_party, "require_client", lambda: _Client(party, world))
    patcher.start()
    test.addCleanup(patcher.stop)
    agent = mock.patch.object(data_party, "Agent_GetAgentInfo", lambda agent_id, key: 7)
    agent.start()
    test.addCleanup(agent.stop)


def _party(players: list[Any], heroes: list[Any], henchmen: list[Any], others: list[Any], party_id: int = 42) -> Any:
    return SimpleNamespace(
        party_id=party_id,
        players_array=_Array(m_size=len(players)),
        heroes_array=_Array(m_size=len(heroes)),
        henchmen_array=_Array(m_size=len(henchmen)),
        others_array=_Array(m_size=len(others)),
        players=players,
        heroes=heroes,
        henchmen=henchmen,
        others=others,
    )


class SurfaceTests(unittest.TestCase):
    def test_the_snippet_carries_the_files_member_accessors(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        for name in (
            "Party_GetMyPartyInfo",
            "Party_GetMyPartyPlayerMemberInfo",
            "Party_GetMyPartyHeroInfo",
            "Party_GetMyPartyHenchmanInfo",
            "Party_GetHeroFlagInfo",
        ):
            self.assertIn(name, declared, "GwAu3 declares it")
            self.assertIn(name, data_party.__all__, "the layer exports it")
            self.assertTrue(callable(getattr(data_party, name)))


class MyPartyInfoTests(unittest.TestCase):
    def test_the_scalar_keys_answer_the_party_records_own_fields(self) -> None:
        party = _party([_member()], [_member()], [_member(), _member()], [1, 2, 3, 4])
        _serve(self, party)
        self.assertEqual(data_party.Party_GetMyPartyInfo("PartyID"), 42)
        self.assertEqual(data_party.Party_GetMyPartyInfo("ArrayPlayerPartyMemberSize"), 1)
        self.assertEqual(data_party.Party_GetMyPartyInfo("ArrayHeroPartyMemberSize"), 1)
        self.assertEqual(data_party.Party_GetMyPartyInfo("ArrayHenchmanPartyMemberSize"), 2)
        self.assertEqual(data_party.Party_GetMyPartyInfo("ArrayOthersPartyMemberSize"), 4)

    def test_an_empty_key_and_an_unknown_key_answer_zero(self) -> None:
        _serve(self, _party([], [], [], []))
        self.assertEqual(data_party.Party_GetMyPartyInfo(""), 0)
        self.assertEqual(data_party.Party_GetMyPartyInfo("NoSuchKey"), 0)

    def test_a_missing_party_answers_zero_without_reading_a_member(self) -> None:
        _serve(self, None)
        self.assertEqual(data_party.Party_GetMyPartyInfo("PartyID"), 0)

    def test_the_address_keys_refuse_and_name_the_property_that_answers_them(self) -> None:
        _serve(self, _party([], [], [], []))
        for key in (
            "ArrayPlayerPartyMember",
            "ArrayHenchmanPartyMember",
            "ArrayHeroPartyMember",
            "ArrayOthersPartyMember",
        ):
            with self.subTest(key=key):
                with self.assertRaises(NotImplementedError) as raised:
                    data_party.Party_GetMyPartyInfo(key)
                message = str(raised.exception)
                self.assertIn("GwAu3_Data_Party.au3", message)
                self.assertIn("py4gw/context/party_context.py", message)


class PlayerMemberTests(unittest.TestCase):
    def _serve_one(self) -> None:
        _serve(
            self,
            _party(
                [
                    _member(
                        login_number=11,
                        called_target_id=99,
                        state=3,
                        is_connected=True,
                        is_ticked=True,
                    )
                ],
                [],
                [],
                [],
            ),
        )

    def test_the_keys_answer_the_member_record(self) -> None:
        self._serve_one()
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(1, "LoginNumber"), 11)
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(1, "CalledTargetID"), 99)
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(1, "State"), 3)
        self.assertTrue(data_party.Party_GetMyPartyPlayerMemberInfo(1, "IsConnected"))
        self.assertTrue(data_party.Party_GetMyPartyPlayerMemberInfo(1, "IsTicked"))

    def test_the_number_is_one_based_and_its_bounds_are_the_sources(self) -> None:
        self._serve_one()
        # `$a_i_PartyMemberNumber = $a_i_PartyMemberNumber - 1` then `< 0 or >= size` (`:103-104`).
        # The numbers are numbers: AutoIt coerces a non-numeric string to `0` in that subtraction and
        # would reject it the same way, but nothing GwAu3 declares takes a string here, so the port
        # takes the declared type rather than reproducing the language's own coercion.
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(0, "LoginNumber"), 0)
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(2, "LoginNumber"), 0)
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(-1, "LoginNumber"), 0)

    def test_an_empty_key_answers_zero(self) -> None:
        self._serve_one()
        self.assertEqual(data_party.Party_GetMyPartyPlayerMemberInfo(1, ""), 0)


class HeroMemberTests(unittest.TestCase):
    def _serve(self) -> None:
        # Two of the three heroes belong to player number 7 (what `Agent_GetAgentInfo` answers here),
        # and the third to somebody else: the filter is what makes hero 1 and 2 *mine*.
        _serve(
            self,
            _party(
                [],
                [
                    _member(agent_id=100, owner_player_id=7, hero_id=1, level=20),
                    _member(agent_id=101, owner_player_id=9, hero_id=2, level=20),
                    _member(agent_id=102, owner_player_id=7, hero_id=3, level=22),
                ],
                [],
                [],
            ),
        )

    def test_the_default_filter_keeps_only_my_heroes_in_array_order(self) -> None:
        self._serve()
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(1, "AgentID"), 100)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(2, "AgentID"), 102)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(3, "AgentID"), 0)

    def test_every_key_of_a_matched_hero(self) -> None:
        self._serve()
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(2, "OwnerPlayerNumber"), 7)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(2, "HeroID"), 3)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(2, "Level"), 22)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(2, "NoSuchKey"), 0)

    def test_the_include_other_players_flag_indexes_the_whole_array(self) -> None:
        self._serve()
        self.assertEqual(
            data_party.Party_GetMyPartyHeroInfo(2, "AgentID", True), 101
        )

    def test_the_bounds_test_is_one_based_and_rejects_zero(self) -> None:
        self._serve()
        # `$a_i_HeroNumber < 1 or > size` (`:135`) -- no subtraction first, unlike the player accessor.
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(0, "AgentID"), 0)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(4, "AgentID"), 0)
        self.assertEqual(data_party.Party_GetMyPartyHeroInfo(1, ""), 0)

    def test_a_player_number_of_zero_answers_zero(self) -> None:
        _serve(self, _party([], [_member(agent_id=100, owner_player_id=0, hero_id=1, level=20)], [], []))
        with mock.patch.object(data_party, "Agent_GetAgentInfo", lambda agent_id, key: 0):
            self.assertEqual(data_party.Party_GetMyPartyHeroInfo(1, "AgentID"), 0)


class HenchmanMemberTests(unittest.TestCase):
    def test_the_keys_answer_the_henchman_record(self) -> None:
        _serve(self, _party([], [], [_member(agent_id=200, profession=3, level=18)], []))
        self.assertEqual(data_party.Party_GetMyPartyHenchmanInfo(1, "AgentID"), 200)
        self.assertEqual(data_party.Party_GetMyPartyHenchmanInfo(1, "Profession"), 3)
        self.assertEqual(data_party.Party_GetMyPartyHenchmanInfo(1, "Level"), 18)
        self.assertEqual(data_party.Party_GetMyPartyHenchmanInfo(2, "AgentID"), 0)
        self.assertEqual(data_party.Party_GetMyPartyHenchmanInfo(1, ""), 0)


class PetInfoTests(unittest.TestCase):
    """``GwAu3_Data_Party.au3:267-305``: the world's pet array, at its own ``0x1C`` stride."""

    def _pet(self, **values: Any) -> SimpleNamespace:
        return SimpleNamespace(
            agent_id=values.get("agent_id", 500),
            owner_agent_id=values.get("owner_agent_id", 42),
            pet_name_ptr=values.get("pet_name_ptr", 0x20000),
            model_file_id1=values.get("model_file_id1", 7),
            model_file_id2=values.get("model_file_id2", 8),
            behavior=values.get("behavior", 1),
            locked_target_id=values.get("locked_target_id", 0),
            pet_name_encoded_str=values.get("pet_name_encoded_str", "enc-name"),
            pet_name_str=values.get("pet_name_str", "Fluffy"),
        )

    def _world(self, pets: list[Any]) -> Any:
        return SimpleNamespace(pets=pets, pets_array=_Array(m_size=len(pets)))

    def _serve(self, world: Any) -> None:
        _serve(self, _party([], [], [], []), world)

    def test_the_record_keys_answer_the_pets_own_fields(self) -> None:
        self._serve(self._world([self._pet()]))
        self.assertEqual(data_party.Party_GetPetInfo(1, "AgentID"), 500)
        self.assertEqual(data_party.Party_GetPetInfo(1, "OwnerAgentID"), 42)
        self.assertEqual(data_party.Party_GetPetInfo(1, "PetNamePtr"), 0x20000)
        self.assertEqual(data_party.Party_GetPetInfo(1, "ModelFileID1"), 7)
        self.assertEqual(data_party.Party_GetPetInfo(1, "ModelFileID2"), 8)
        self.assertEqual(data_party.Party_GetPetInfo(1, "Behavior"), 1)
        self.assertEqual(data_party.Party_GetPetInfo(1, "LockedTargetID"), 0)

    def test_the_behavior_keys_are_equalities_on_one_word(self) -> None:
        for behavior, expected in ((0, "IsFighting"), (1, "IsGuarding"), (2, "IsAvoiding")):
            with self.subTest(behavior=behavior):
                self._serve(self._world([self._pet(behavior=behavior)]))
                for key in ("IsFighting", "IsGuarding", "IsAvoiding"):
                    with self.subTest(key=key):
                        self.assertEqual(
                            data_party.Party_GetPetInfo(1, key), key == expected
                        )

    def test_has_locked_target_is_the_word_read_for_truth(self) -> None:
        self._serve(self._world([self._pet(locked_target_id=9)]))
        self.assertTrue(data_party.Party_GetPetInfo(1, "HasLockedTarget"))
        self._serve(self._world([self._pet(locked_target_id=0)]))
        self.assertFalse(data_party.Party_GetPetInfo(1, "HasLockedTarget"))

    def test_the_two_name_keys_keep_the_sources_own_guards(self) -> None:
        self._serve(self._world([self._pet()]))
        self.assertEqual(data_party.Party_GetPetInfo(1, "PetNameEnc"), "enc-name")
        self.assertEqual(data_party.Party_GetPetInfo(1, "PetName"), "Fluffy")

        # Below the sentinel the pointer is missing, and the source answers two different things: `""` for
        # the encoded form and `"Unknown"` for the display one (`:285`, `:289`).
        self._serve(self._world([self._pet(pet_name_ptr=0)]))
        self.assertEqual(data_party.Party_GetPetInfo(1, "PetNameEnc"), "")
        self.assertEqual(data_party.Party_GetPetInfo(1, "PetName"), "Unknown")

    def test_the_guards_are_the_sources(self) -> None:
        self._serve(self._world([self._pet()]))
        self.assertEqual(data_party.Party_GetPetInfo(0, "AgentID"), 0)
        self.assertEqual(data_party.Party_GetPetInfo(2, "AgentID"), 0)
        self.assertEqual(data_party.Party_GetPetInfo(1, ""), 0)
        self.assertEqual(data_party.Party_GetPetInfo(1, "NoSuchKey"), 0)

    def test_no_pet_array_answers_zero(self) -> None:
        self._serve(self._world([]))
        self.assertEqual(data_party.Party_GetPetInfo(1, "AgentID"), 0)


class HeroFlagTests(unittest.TestCase):
    """``GwAu3_Data_Party.au3:368-402``: the world's hero-flag array, matched by hero agent id."""

    def _world(self, flags: list[Any], size: int | None = None) -> Any:
        return SimpleNamespace(
            hero_flags=flags,
            hero_flags_array=_Array(m_size=len(flags) if size is None else size),
        )

    def _flag(self, **values: Any) -> SimpleNamespace:
        return SimpleNamespace(
            hero_id=values.get("hero_id", 5),
            agent_id=values.get("agent_id", 100),
            level=values.get("level", 3),
            hero_behavior=values.get("hero_behavior", 2),
            flag_ptr=SimpleNamespace(
                x=values.get("flag_x", 1234.5), y=values.get("flag_y", -6789.25)
            ),
        )

    def _serve(self, world: Any, heroes: list[Any] | None = None) -> None:
        _serve(
            self,
            _party(
                [],
                heroes if heroes is not None else [_member(agent_id=100, owner_player_id=7, hero_id=5, level=20)],
                [],
                [],
            ),
            world,
        )

    def test_the_six_keys_whose_offsets_agree_answer(self) -> None:
        self._serve(self._world([self._flag()]))
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "HeroID"), 5)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "AgentID"), 100)
        # GwAu3's `InventoryID` is the dword at +0x8, which the port's record names `level`; its
        # `Behavior` is +0xC, which the port names `hero_behavior`. Same offsets, different names.
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "InventoryID"), 3)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "Behavior"), 2)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "FlagX"), 1234.5)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "FlagY"), -6789.25)

    def test_the_match_is_on_the_hero_agent_id_and_the_first_match_wins(self) -> None:
        self._serve(
            self._world([self._flag(agent_id=999, hero_id=9), self._flag(agent_id=100, hero_id=5)])
        )
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "HeroID"), 5)

    def test_the_keys_guard_order_is_the_sources(self) -> None:
        # No array at all, an unknown key with a match, a hero number outside the array, and a hero
        # whose agent id is 0 -- all `0`, and the source reaches them in this order (`:370-384`).
        self._serve(self._world([], 0))
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "HeroID"), 0)

        self._serve(self._world([self._flag()]))
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "NoSuchKey"), 0)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(0, "HeroID"), 0)
        self.assertEqual(data_party.Party_GetHeroFlagInfo(2, "HeroID"), 0)

        self._serve(self._world([self._flag()]), heroes=[])
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "HeroID"), 0)

    def test_no_element_matching_the_agent_id_answers_zero(self) -> None:
        self._serve(self._world([self._flag(agent_id=999)]))
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "HeroID"), 0)
        # The refusal for `LockedTargetID` sits inside the matched element, exactly where the source's
        # `Case` is, so an unmatched hero answers `0` there instead -- as GwAu3 does.
        self.assertEqual(data_party.Party_GetHeroFlagInfo(1, "LockedTargetID"), 0)

    def test_locked_target_id_refuses_and_names_both_offsets(self) -> None:
        self._serve(self._world([self._flag()]))
        with self.assertRaises(NotImplementedError) as raised:
            data_party.Party_GetHeroFlagInfo(1, "LockedTargetID")
        message = str(raised.exception)
        self.assertIn("GwAu3_Data_Party.au3:398", message)
        self.assertIn("0x20", message)
        self.assertIn("world_context.py:717-739", message)


if __name__ == "__main__":
    unittest.main()
