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
    QuestStruct,
    TitleStruct,
    TitleTierStruct,
    PlayerStruct,
    PlayerControlledCharacterStruct,
    ProfessionStateStruct,
    SkillbarCastStruct,
    WorldContextStruct,
)


class WorldContextOfflineTests(unittest.TestCase):
    """Keep the external root fixed-width and bounded without a live client."""

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
