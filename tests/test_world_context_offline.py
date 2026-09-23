"""Offline safety and layout checks for the WorldContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    AccountInfoStruct,
    AgentEffectsStruct,
    AgentNameInfoStruct,
    AttributeStruct,
    BuffStruct,
    ControlledMinionsStruct,
    EffectStruct,
    HeroFlagStruct,
    HeroInfoStruct,
    GWArray,
    PartyAttributeStruct,
    NPCStruct,
    MapAgentStruct,
    MissionMapIconStruct,
    PartyAllyStruct,
    PartyMemberMoraleInfoStruct,
    PartyMoraleLinkStruct,
    PetInfoStruct,
    SkillbarSkillStruct,
    SkillbarStruct,
    DupeSkillStruct,
    GamePosStruct,
    MissionObjectiveStruct,
    NPC_ModelStruct,
    QuestStruct,
    TitleStruct,
    TitleTierStruct,
    PlayerStruct,
    PlayerControlledCharacterStruct,
    ProfessionStateStruct,
    SkillbarCastStruct,
    WorldContextStruct,
    WorldGamePos,
    WorldVec2f,
    WorldVec3f,
    WorldContext,
)


class EmptyReader:
    """Return empty bytes for properties that must not read empty arrays."""

    def read(self, address: int, size: int) -> bytes:
        return bytes(size)


class FixedBufferReader:
    """Expose one fixed byte region to a bounded array reader."""

    def __init__(self, base_address: int, content: bytes) -> None:
        self.base_address = base_address
        self.content = content

    def read(self, address: int, size: int) -> bytes:
        offset = address - self.base_address
        return self.content[offset : offset + size]


class MappedBufferReader:
    """Expose several fixed byte regions to remote string properties."""

    def __init__(self, regions: dict[int, bytes]) -> None:
        self.regions = regions

    def read(self, address: int, size: int) -> bytes:
        for base_address, content in self.regions.items():
            offset = address - base_address
            if 0 <= offset < len(content):
                chunk = content[offset : offset + size]
                return chunk + bytes(size - len(chunk))
        return bytes(size)


class WorldContextOfflineTests(unittest.TestCase):
    """Keep the external root fixed-width and bounded without a live client."""

    def test_source_coordinate_value_types_and_helpers(self) -> None:
        """World child properties expose the same value types as Reforged."""

        self.assertEqual(WorldVec2f().to_tuple(), (0.0, 0.0))
        self.assertEqual(WorldVec3f().to_tuple(), (0.0, 0.0, 0.0))
        self.assertEqual(WorldGamePos().to_tuple(), (0.0, 0.0, 0))

        icon = MissionMapIconStruct(X=12.5, Y=-4.0)
        position = icon.position
        self.assertIsInstance(position, WorldVec2f)
        assert position is not None
        self.assertEqual(position.to_tuple(), (12.5, -4.0))
        self.assertEqual(position.to_list(), [12.5, -4.0])
        self.assertEqual((position + WorldVec2f(1.0, 2.0)).to_tuple(), (13.5, -2.0))
        self.assertEqual((position - WorldVec2f(2.5, 1.0)).to_tuple(), (10.0, -5.0))
        self.assertEqual((position * 2.0).to_tuple(), (25.0, -8.0))
        self.assertEqual((position / 2.0).to_tuple(), (6.25, -2.0))
        with self.assertRaises(ValueError):
            _ = icon.position / 0.0

        hero_flag = HeroFlagStruct(flag_ptr=WorldVec2f(3.0, 4.0))
        flag = hero_flag.flag
        self.assertIsInstance(flag, WorldVec2f)
        assert flag is not None
        self.assertEqual(flag.to_tuple(), (3.0, 4.0))

        world = WorldContextStruct()
        world.all_flag_array[:] = (5.0, 6.0, 7.0)
        all_flag = world.all_flag
        self.assertIsInstance(all_flag, WorldVec3f)
        assert all_flag is not None
        self.assertEqual(all_flag.to_tuple(), (5.0, 6.0, 7.0))
        self.assertEqual(all_flag.to_list(), [5.0, 6.0, 7.0])

        quest = QuestStruct(marker_ptr=WorldGamePos(8.0, 9.0, 2))
        marker = quest.marker
        self.assertIsInstance(marker, WorldGamePos)
        assert marker is not None
        self.assertEqual(marker.to_tuple(), (8.0, 9.0, 2))

    def test_native_layout_offsets(self) -> None:
        """The root size and key fields match the maintained native header."""

        self.assertEqual(ctypes.sizeof(WorldContextStruct), 0x854)
        self.assertEqual(WorldContextStruct.message_buff_array.offset, 0x04)
        self.assertEqual(WorldContextStruct.party_effects_array.offset, 0x508)
        self.assertEqual(WorldContextStruct.players_array.offset, 0x80C)
        self.assertEqual(WorldContextStruct.foes_killed.offset, 0x84C)
        self.assertEqual(ctypes.sizeof(AttributeStruct), 0x14)
        self.assertEqual(ctypes.sizeof(AccountInfoStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(MapAgentStruct), 0x34)
        self.assertEqual(ctypes.sizeof(PartyAllyStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(ControlledMinionsStruct), 0x08)
        self.assertEqual(ctypes.sizeof(PartyMemberMoraleInfoStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(PartyMoraleLinkStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(PlayerControlledCharacterStruct), 0x134)
        self.assertEqual(ctypes.sizeof(ProfessionStateStruct), 0x14)
        self.assertEqual(ctypes.sizeof(SkillbarCastStruct), 0x08)
        self.assertEqual(ctypes.sizeof(AgentNameInfoStruct), 0x38)
        self.assertEqual(ctypes.sizeof(MissionMapIconStruct), 0x28)
        self.assertEqual(ctypes.sizeof(PartyAttributeStruct), 0x43C)
        self.assertEqual(ctypes.sizeof(EffectStruct), 0x18)
        self.assertEqual(ctypes.sizeof(BuffStruct), 0x10)
        self.assertEqual(ctypes.sizeof(AgentEffectsStruct), 0x24)
        self.assertEqual(ctypes.sizeof(NPCStruct), 0x30)
        self.assertEqual(ctypes.sizeof(PlayerStruct), 0x50)
        self.assertEqual(ctypes.sizeof(HeroFlagStruct), 0x24)
        self.assertEqual(ctypes.sizeof(HeroInfoStruct), 0x78)
        self.assertEqual(ctypes.sizeof(PetInfoStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(SkillbarSkillStruct), 0x14)
        self.assertEqual(ctypes.sizeof(SkillbarStruct), 0xBC)
        self.assertEqual(ctypes.sizeof(DupeSkillStruct), 0x08)
        self.assertEqual(ctypes.sizeof(GamePosStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(QuestStruct), 0x34)
        self.assertEqual(ctypes.sizeof(MissionObjectiveStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(TitleStruct), 0x2C)
        self.assertEqual(ctypes.sizeof(TitleTierStruct), 0x0C)

    def test_source_struct_field_names_and_order(self) -> None:
        """Source structure names and field order survive x86 adaptation."""

        self.assertIs(NPCStruct, NPC_ModelStruct)
        self.assertEqual(
            [field[0] for field in NPC_ModelStruct._fields_],
            [
                "model_file_id",
                "h0004",
                "scale",
                "sex",
                "npc_flags",
                "primary",
                "h0018",
                "default_level",
                "padding1",
                "padding2",
                "name_enc_ptr",
                "model_files_ptr",
                "files_count",
                "files_capacity",
            ],
        )
        self.assertEqual(
            [field[0] for field in HeroInfoStruct._fields_][-1],
            "name_encoded_str",
        )
        self.assertEqual(
            [field[0] for field in MissionMapIconStruct._fields_][1:3],
            ["X", "Y"],
        )
        self.assertEqual(
            [field[0] for field in TitleTierStruct._fields_][-1],
            "tier_name_enc_ptr",
        )
        root_fields = [field[0] for field in WorldContextStruct._fields_]
        self.assertEqual(root_fields[0], "account_info_ptr")
        self.assertIn("quest_log_array", root_fields)
        self.assertEqual(root_fields[-2:], ["foes_killed", "foes_to_kill"])

    def test_array_sizes_read_headers_only(self) -> None:
        """Array metadata is available without materializing child records."""

        context = WorldContextStruct()
        context.players_array = GWArray(0x100000, 12, 3, 0)
        context.titles_array = GWArray(0x110000, 7, 2, 0)

        sizes = context.array_sizes

        self.assertEqual(sizes["players_array"], 3)
        self.assertEqual(sizes["titles_array"], 2)

    def test_flag_rejects_non_finite_values(self) -> None:
        """Invalid remote floats are not exposed as meaningful coordinates."""

        context = WorldContextStruct()
        context.all_flag_array[0] = float("nan")
        self.assertIsNone(context.all_flag_value)

    def test_attribute_properties_are_local_and_bounded(self) -> None:
        """Inline attributes do not trigger remote reads."""

        context = PartyAttributeStruct()
        context.agent_id = 7
        context.attribute_array[3].attribute_id = 12
        context.attribute_array[3].level = 9
        self.assertEqual(len(context.attributes), 54)
        self.assertEqual(len(context.valid_attributes), 1)
        self.assertEqual(context.attribute_array[3].name, "Energy Storage")
        self.assertEqual(context.attribute_array[3].GetName(), "Energy Storage")

    def test_world_arrays_are_not_materialized_until_requested(self) -> None:
        """The root only stores array headers until a property is requested."""

        context = WorldContextStruct()
        context.party_attributes_array = GWArray(0x100000, 128, 1, 0)
        context.party_effects_array = GWArray(0x110000, 128, 1, 0)
        self.assertEqual(context.array_sizes["party_attributes_array"], 1)
        self.assertEqual(context.array_sizes["party_effects_array"], 1)

    def test_quest_log_uses_the_reforged_property_name(self) -> None:
        """Both names expose the same quest-log array."""

        context = WorldContextStruct().bind_reader(EmptyReader())

        self.assertEqual(context.quest_log, context.quests)

    def test_vanquished_areas_preserves_source_stub_behavior(self) -> None:
        """The source accessor returns None despite declaring an array field."""

        context = WorldContextStruct().bind_reader(EmptyReader())
        context.vanquished_areas_array = GWArray(0x100000, 4, 2, 0)

        self.assertEqual(context.array_sizes["vanquished_areas_array"], 2)
        self.assertIsNone(context.vanquished_areas)

    def test_profession_bit_helper_preserves_source_shift_behavior(self) -> None:
        """A negative profession index raises as it does in the source helper."""

        state = ProfessionStateStruct()
        state.unlocked_professions = 1

        with self.assertRaises(ValueError):
            state.IsProfessionUnlocked(-1)

        self.assertFalse(state.IsProfessionUnlocked(32))

    def test_empty_arrays_and_text_buffers_match_source_returns(self) -> None:
        """Empty source arrays are None; message buffers are character lists."""

        context = WorldContextStruct().bind_reader(EmptyReader())
        source_optional_arrays = (
            "message_buff",
            "dialog_buff",
            "merch_items",
            "merch_items2",
            "map_agents",
            "party_allies",
            "party_attributes",
            "h04B8_ptrs",
            "h04C8_ptrs",
            "h04DC_ptrs",
            "party_effects",
            "h0518_ptrs",
            "quest_log",
            "mission_objectives",
            "henchmen_agent_ids",
            "hero_flags",
            "hero_info",
            "cartographed_areas",
            "controlled_minions",
            "missions_completed",
            "missions_bonus",
            "missions_completed_hm",
            "missions_bonus_hm",
            "unlocked_maps",
            "player_morale",
            "party_morale",
            "player_controlled_character",
            "pets",
            "party_profession_states",
            "h06CC_ptrs",
            "h06E0_ptrs",
            "party_skillbars",
            "learnable_character_skills",
            "unlocked_character_skills",
            "duplicated_character_skills",
            "h0730_ptrs",
            "agent_name_info",
            "h07DC_ptrs",
            "mission_map_icons",
            "npc_models",
            "players",
            "titles",
            "title_tiers",
            "vanquished_areas",
        )
        for property_name in source_optional_arrays:
            with self.subTest(property_name=property_name):
                self.assertIsNone(getattr(context, property_name))

        reader = FixedBufferReader(0x20000, b"A\x00B\x00\x00\x00")
        context.bind_reader(reader)
        context.message_buff_array = GWArray(0x20000, 2, 2, 0)
        self.assertEqual(context.message_buff, ["A", "B"])
        self.assertEqual(context.message_buffer, "AB")

    def test_player_lookup_uses_source_player_number_field(self) -> None:
        """GetPlayerById compares the source player number, not agent ID."""

        player = PlayerStruct()
        player.player_number = 17
        player.agent_id = 9001
        reader = FixedBufferReader(0x30000, bytes(player))
        context = WorldContextStruct().bind_reader(reader)
        context.players_array = GWArray(0x30000, ctypes.sizeof(PlayerStruct), 1, 0)

        found = context.GetPlayerById(17)
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.player_number, 17)
        self.assertIsNone(context.GetPlayerById(9001))

    def test_player_name_enc_str_uses_source_name_pointer(self) -> None:
        """The source name_enc_str property reads name_ptr, not name_enc_ptr."""

        player = PlayerStruct()
        player.name_ptr = 0x40000
        player.name_enc_ptr = 0x41000
        reader = MappedBufferReader(
            {
                0x40000: "actual name\x00".encode("utf-16-le"),
                0x41000: "other name\x00".encode("utf-16-le"),
            }
        )
        player.bind_reader(reader)

        self.assertEqual(player.name_encoded_str, "actual name")
        self.assertEqual(player.name_enc_encoded_str, "other name")
        self.assertEqual(player.name_enc_str, player.name_str)

    def test_indirect_strings_are_not_silently_truncated_at_256(self) -> None:
        """Longer source strings are returned whole within the safety limit."""

        expected = "N" * 300
        player = PlayerStruct()
        player.name_ptr = 0x42000
        player.bind_reader(
            MappedBufferReader(
                {0x42000: (expected + "\x00").encode("utf-16-le")}
            )
        )

        self.assertEqual(player.name_encoded_str, expected)

        unterminated = PlayerStruct()
        unterminated.name_ptr = 0x43000
        unterminated.bind_reader(
            MappedBufferReader(
                {0x43000: ("X" * 32_768).encode("utf-16-le")}
            )
        )
        with self.assertRaisesRegex(ValueError, "not terminated"):
            _ = unterminated.name_encoded_str

    def test_string_properties_preserve_null_vs_empty_source_values(self) -> None:
        """A null source pointer differs from a pointer to an empty string."""

        player = PlayerStruct()
        player.bind_reader(MappedBufferReader({0x44000: b"\x00\x00"}))

        player.name_ptr = 0
        self.assertIsNone(player.name_encoded_str)

        player.name_ptr = 0x44000
        self.assertEqual(player.name_encoded_str, "")
        self.assertEqual(player.name_str, "")

    def test_context_arrays_read_past_the_old_arbitrary_caps(self) -> None:
        """A valid source array is fully materialized rather than truncated."""

        count = 520
        player = PlayerStruct()
        player.player_number = 42
        payload = bytes(player) * count
        reader = FixedBufferReader(0x50000, payload)
        context = WorldContextStruct().bind_reader(reader)
        context.players_array = GWArray(
            0x50000, ctypes.sizeof(PlayerStruct) * count, count, 0
        )

        players = context.players
        self.assertIsNotNone(players)
        assert players is not None
        self.assertEqual(len(players), count)
        found = context.GetPlayerById(42)
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.player_number, players[0].player_number)

    def test_context_array_rejects_excessive_read_size_without_truncating(self) -> None:
        """Oversized arrays fail clearly instead of silently returning a prefix."""

        context = WorldContextStruct().bind_reader(EmptyReader())
        count = (16 * 1024 * 1024 // ctypes.sizeof(ctypes.c_uint32)) + 1
        context.unlocked_character_skills_array = GWArray(
            0x60000, count, count, 0
        )

        with self.assertRaisesRegex(ValueError, "per-array read limit"):
            _ = context.unlocked_character_skills

    def test_source_facade_names_are_present_and_external_safe(self) -> None:
        """The source callback API is declared without registering callbacks."""

        WorldContext._ptr = 0x1234
        WorldContext._cached_ctx = WorldContextStruct()

        self.assertEqual(WorldContext.get_ptr(), 0x1234)
        self.assertIsNotNone(WorldContext.get_context())
        with self.assertRaisesRegex(NotImplementedError, "callback runtime"):
            WorldContext.enable()

        WorldContext.disable()

        self.assertEqual(WorldContext.get_ptr(), 0)
        self.assertIsNone(WorldContext.get_context())

    def test_player_and_npc_flags_are_decoded_locally(self) -> None:
        """Player and NPC classification properties use only fixed fields."""

        player = PlayerStruct()
        player.flags = 0x800
        player.reforged_or_dhuums_flags = 0x7
        self.assertTrue(player.is_pvp)
        self.assertTrue(player.is_reforged)
        npc = NPCStruct()
        npc.npc_flags = 0x30
        self.assertTrue(npc.is_henchman)
        self.assertTrue(npc.is_hero)

    def test_hero_name_and_flag_properties_are_local(self) -> None:
        """Hero names and flag coordinates use fixed inline fields."""

        hero = HeroInfoStruct()
        hero.name_enc[0] = ord("A")
        hero.name_enc[1] = ord("b")
        self.assertEqual(hero.name, "Ab")
        flag = HeroFlagStruct()
        flag.flag_ptr.x = 10.5
        flag.flag_ptr.y = -4.0
        self.assertIsNotNone(flag.flag)
        assert flag.flag is not None
        self.assertEqual((flag.flag.x, flag.flag.y), (10.5, -4.0))

    def test_skillbar_properties_are_local(self) -> None:
        """Skillbar validity and slot IDs use the fixed native record."""

        skillbar = SkillbarStruct()
        skillbar.agent_id = 31
        skillbar.skills[0].skill_id = 123
        self.assertTrue(skillbar.is_valid)
        self.assertEqual(skillbar.skill_ids[0], 123)

    def test_quest_and_title_flags_are_decoded_locally(self) -> None:
        """Quest/title status properties use only fixed fields."""

        quest = QuestStruct()
        quest.log_state = 0x72
        self.assertTrue(quest.is_completed)
        self.assertTrue(quest.is_current_mission_quest)
        self.assertTrue(quest.is_primary)
        title = TitleStruct()
        title.props = 0x3
        self.assertTrue(title.is_percentage_based)
        self.assertFalse(title.has_tiers)
        tier = TitleTierStruct()
        tier.tier_number = 2
        self.assertTrue(tier.is_valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
