"""Offline source-parity checks for the external ``PartyContext`` reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    HenchmanPartyMember,
    HenchmanPartyMemberStruct,
    HeroPartyMember,
    HeroPartyMemberStruct,
    PartyContext,
    PartyContextStruct,
    PartyInfoStruct,
    PartySearchStruct,
    PartySearchType,
    PlayerPartyMember,
    PlayerPartyMemberStruct,
)


class _EmptyReader:
    """Minimal reader for a party snapshot with empty intrusive lists."""

    def read(self, address: int, size: int) -> bytes:
        del address
        return bytes(size)


class PartyContextParityTests(unittest.TestCase):
    """Keep every declared PartyContext layout and facade member aligned."""

    def test_source_record_aliases_share_the_same_layout(self) -> None:
        """The concise Reforged record names are aliases, not new layouts."""

        self.assertIs(PlayerPartyMember, PlayerPartyMemberStruct)
        self.assertIs(HeroPartyMember, HeroPartyMemberStruct)
        self.assertIs(HenchmanPartyMember, HenchmanPartyMemberStruct)

    def test_nested_layouts_and_offsets_match_sources(self) -> None:
        """Fixed-width records retain every native field coordinate."""

        expected = {
            PlayerPartyMemberStruct: {
                "login_number": 0x00,
                "called_target_id": 0x04,
                "state": 0x08,
            },
            HeroPartyMemberStruct: {
                "agent_id": 0x00,
                "owner_player_id": 0x04,
                "hero_id": 0x08,
                "h000C": 0x0C,
                "h0010": 0x10,
                "level": 0x14,
            },
            HenchmanPartyMemberStruct: {
                "agent_id": 0x00,
                "h0004": 0x04,
                "profession": 0x2C,
                "level": 0x30,
            },
            PartyInfoStruct: {
                "party_id": 0x00,
                "players_array": 0x04,
                "henchmen_array": 0x14,
                "heroes_array": 0x24,
                "others_array": 0x34,
                "h0044": 0x44,
                "invite_link": 0x7C,
            },
            PartySearchStruct: {
                "party_search_id": 0x00,
                "party_search_type": 0x04,
                "hardmode": 0x08,
                "district": 0x0C,
                "language": 0x10,
                "party_size": 0x14,
                "hero_count": 0x18,
                "message": 0x1C,
                "party_leader": 0x5C,
                "primary": 0x84,
                "secondary": 0x88,
                "level": 0x8C,
                "timestamp": 0x90,
            },
            PartyContextStruct: {
                "h0000": 0x00,
                "h0004_array": 0x04,
                "flag": 0x14,
                "h0018": 0x18,
                "request_list": 0x1C,
                "requests_count": 0x28,
                "sending_list": 0x2C,
                "sending_count": 0x38,
                "h003C": 0x3C,
                "parties_array": 0x40,
                "h0050": 0x50,
                "player_party_ptr": 0x54,
                "h0058": 0x58,
                "party_search_array": 0xC0,
            },
        }
        sizes = {
            PlayerPartyMemberStruct: 0x0C,
            HeroPartyMemberStruct: 0x18,
            HenchmanPartyMemberStruct: 0x34,
            PartyInfoStruct: 0x84,
            PartySearchStruct: 0x94,
            PartyContextStruct: 0xD0,
        }
        for structure, fields in expected.items():
            self.assertEqual(ctypes.sizeof(structure), sizes[structure])
            for name, offset in fields.items():
                self.assertEqual(getattr(structure, name).offset, offset, name)

    def test_source_properties_keep_flag_and_text_semantics(self) -> None:
        """Bit flags and encoded UTF-16 properties match Reforged behavior."""

        member = PlayerPartyMemberStruct(0, 0, 0x03)
        self.assertTrue(member.is_connected)
        self.assertTrue(member.is_ticked)
        self.assertTrue(member.connected())
        self.assertTrue(member.ticked())
        self.assertEqual(member.calledTargetId, 0)

        search = PartySearchStruct()
        search.message = (ctypes.c_uint16 * 32).from_buffer_copy(
            "Looking for heroes\x00".encode("utf-16-le")
            + b"\x00" * (64 - len("Looking for heroes\x00".encode("utf-16-le")))
        )
        search.party_leader = (ctypes.c_uint16 * 20).from_buffer_copy(
            "Leader\x00".encode("utf-16-le")
            + b"\x00" * (40 - len("Leader\x00".encode("utf-16-le")))
        )
        self.assertEqual(search.message_encoded_str, "Looking for heroes")
        self.assertEqual(search.message_str, "Looking for heroes")
        self.assertEqual(search.party_leader_encoded_str, "Leader")
        self.assertEqual(search.party_leader_str, "Leader")
        self.assertEqual(int(PartySearchType.HUNTING), 0)
        self.assertEqual(int(PartySearchType.PartySearchType_Hunting), 0)
        self.assertEqual(int(PartySearchType.GUILD), 4)

        context = PartyContextStruct()
        context.flag = 0xB0
        self.assertTrue(context.in_hard_mode)
        self.assertTrue(context.is_defeated)
        self.assertTrue(context.is_party_leader)
        self.assertTrue(context.InHardMode())
        self.assertTrue(context.IsDefeated())
        self.assertTrue(context.IsPartyLeader())

    def test_request_alias_matches_requests(self) -> None:
        """Reforged's ``request`` property must preserve the existing list view."""

        context = PartyContextStruct().bind_reader(_EmptyReader(), 0x100000)

        self.assertEqual(context.request, context.requests)
        self.assertEqual(context.sending, [])
        self.assertEqual(context.party_search, context.party_searches)
        self.assertEqual(context.h0004.m_size, context.h0004_array.m_size)
        party = PartyInfoStruct().bind_reader(_EmptyReader(), 0x100100)
        self.assertEqual(party.GetPartySize(), 0)

    def test_facade_declares_external_cache_and_callback_boundary(self) -> None:
        """Static source members exist and clearly reject in-process callbacks."""

        PartyContext.disable()
        self.assertEqual(PartyContext.get_ptr(), 0)
        self.assertIsNone(PartyContext.get_context())
        self.assertEqual(PartyContext._cached_ptr, 0)
        with self.assertRaises(NotImplementedError):
            PartyContext.enable()

    def test_layout_remains_native_sized(self) -> None:
        """The alias addition must not affect the fixed-width root layout."""

        self.assertEqual(ctypes.sizeof(PartyContextStruct), 0xD0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
