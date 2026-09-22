"""Offline source-parity checks for the external ``GuildContext`` reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    CapeDesign,
    CapeDesignStruct,
    GHKey,
    GHKeyStruct,
    GetGuildArray,
    Guild,
    GuildContext,
    GuildContextStruct,
    GuildHistoryEvent,
    GuildHistoryEventStruct,
    GuildPlayer,
    GuildPlayerStruct,
    GuildStruct,
    TownAlliance,
    TownAllianceStruct,
)


class _EmptyReader:
    """Reader that exposes null array headers and zero-filled records."""

    def read(self, address: int, size: int) -> bytes:
        del address
        return bytes(size)


class GuildContextParityTests(unittest.TestCase):
    """Keep every declared GuildContext record and facade member aligned."""

    def test_source_record_aliases_share_the_same_layout(self) -> None:
        """The source names refer to the implementation layouts directly."""

        self.assertIs(GHKey, GHKeyStruct)
        self.assertIs(CapeDesign, CapeDesignStruct)
        self.assertIs(TownAlliance, TownAllianceStruct)
        self.assertIs(GuildHistoryEvent, GuildHistoryEventStruct)
        self.assertIs(Guild, GuildStruct)
        self.assertIs(GuildPlayer, GuildPlayerStruct)

    def test_layouts_and_offsets_match_native(self) -> None:
        """Fixed-width records retain every native field coordinate."""

        sizes = {
            GHKeyStruct: 0x10,
            CapeDesignStruct: 0x1C,
            TownAllianceStruct: 0x78,
            GuildHistoryEventStruct: 0x208,
            GuildStruct: 0xAC,
            GuildPlayerStruct: 0x174,
            GuildContextStruct: 0x368,
        }
        fields = {
            TownAllianceStruct: {
                "name_enc": 0x0C,
                "tag_enc": 0x4C,
                "cape": 0x58,
                "map_id": 0x74,
            },
            GuildStruct: {
                "key": 0x00,
                "h0010": 0x10,
                "index": 0x24,
                "name_enc": 0x30,
                "tag_enc": 0x80,
                "cape": 0x90,
            },
            GuildPlayerStruct: {
                "vtable": 0x00,
                "name_ptr": 0x04,
                "invited_name_enc": 0x08,
                "current_name_enc": 0x30,
                "inviter_name_enc": 0x58,
                "invite_time": 0x80,
                "promoter_name_enc": 0x84,
                "offline": 0xDC,
                "member_type": 0xE0,
                "status": 0xE4,
            },
            GuildContextStruct: {
                "h0020_array": 0x20,
                "player_name_enc": 0x34,
                "player_guild_index": 0x60,
                "player_gh_key": 0x64,
                "announcement_enc": 0x78,
                "factions_outpost_guilds_array": 0x2A8,
                "player_guild_history_array": 0x2CC,
                "guild_array_array": 0x2F8,
                "h0318_array": 0x318,
                "h032C_array": 0x32C,
                "player_roster_array": 0x358,
            },
        }
        for structure, size in sizes.items():
            self.assertEqual(ctypes.sizeof(structure), size)
        for structure, expected in fields.items():
            for name, offset in expected.items():
                self.assertEqual(getattr(structure, name).offset, offset, name)

    def test_source_helpers_and_encoded_properties(self) -> None:
        """Key parsing, validity, and encoded/display properties are retained."""

        key = GHKeyStruct.from_hex("01020304")
        self.assertTrue(key.is_valid)
        self.assertEqual(bytes(key)[:4], bytes.fromhex("01020304"))
        self.assertEqual(key.as_string, "01020304")
        with self.assertRaises(ValueError):
            GHKeyStruct.from_hex("1234")

        alliance = TownAllianceStruct()
        alliance.name_enc = (ctypes.c_uint16 * 32).from_buffer_copy(
            "Kurzick\x00".encode("utf-16-le")
            + b"\x00" * (64 - len("Kurzick\x00".encode("utf-16-le")))
        )
        alliance.tag_enc = (ctypes.c_uint16 * 5).from_buffer_copy(
            "K\x00".encode("utf-16-le")
            + b"\x00" * (10 - len("K\x00".encode("utf-16-le")))
        )
        self.assertEqual(alliance.name_encoded_str, "Kurzick")
        self.assertEqual(alliance.name_str, "Kurzick")
        self.assertEqual(alliance.tag_encoded_str, "K")
        self.assertEqual(alliance.tag_str, "K")
        self.assertEqual(bytes(alliance.name), bytes(alliance.name_enc))
        self.assertEqual(bytes(alliance.tag), bytes(alliance.tag_enc))

        player = GuildPlayerStruct()
        self.assertIsNone(player.name_encoded_str)
        self.assertIsNone(player.name_str)
        self.assertEqual(bytes(player.invited_name), bytes(player.invited_name_enc))

    def test_empty_remote_arrays_preserve_source_none_results(self) -> None:
        """Empty source array properties return ``None`` rather than a fake list."""

        snapshot = GuildContextStruct().bind_reader(_EmptyReader(), 0x100000)
        self.assertIsNone(snapshot.h0020_ptrs)
        self.assertIsNone(snapshot.factions_outpost_guilds)
        self.assertIsNone(snapshot.player_guild_history)
        self.assertIsNone(snapshot.guild_array)
        self.assertIsNone(snapshot.h0318_ptrs)
        self.assertIsNone(snapshot.h032C_ptrs)
        self.assertIsNone(snapshot.player_roster)
        self.assertEqual(snapshot.h0020.m_size, snapshot.h0020_array.m_size)
        self.assertEqual(snapshot.h0318.m_size, snapshot.h0318_array.m_size)
        self.assertEqual(snapshot.h032C.m_size, snapshot.h032C_array.m_size)
        self.assertIsNone(snapshot.guilds)

    def test_facade_declares_external_cache_and_callback_boundary(self) -> None:
        """Static source members exist and callback execution is explicit."""

        GuildContext.disable()
        self.assertEqual(GuildContext.get_ptr(), 0)
        self.assertIsNone(GuildContext.get_context())
        with self.assertRaises(NotImplementedError):
            GuildContext.enable()

    def test_native_array_helper_is_exported(self) -> None:
        """The native ``GetGuildArray`` spelling remains a public alias."""

        from py4gw.context.guild_context import get_guild_array

        self.assertIs(GetGuildArray, get_guild_array)


if __name__ == "__main__":
    unittest.main(verbosity=2)
