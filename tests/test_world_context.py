"""Live read-only checks for the external WorldContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
    WorldContext,
    WorldContextStruct,
)


class LiveWorldContextTests(unittest.TestCase):
    """Verify the root pointer path and scalar snapshot against Guild Wars."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first running client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader, int(module["base_address"]), int(module["size"])
        )
        cls.scanner.initialize()
        cls.game_context = GameContext(
            cls.reader, cls.scanner, PatternCatalog.from_directory("offsets")
        )
        cls.game_context.initialize()
        cls.context = WorldContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_root(self) -> None:
        """The external root remains exactly the maintained 0x854 bytes."""

        self.assertEqual(ctypes.sizeof(WorldContextStruct), 0x854)
        self.assertEqual(WorldContextStruct.player_number.offset, 0x67C)
        self.assertEqual(WorldContextStruct.experience.offset, 0x740)
        self.assertEqual(WorldContextStruct.foes_to_kill.offset, 0x850)

    def test_resolves_world_context_from_game_context(self) -> None:
        """Follow GameContext.world_context rather than inventing a new scan."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The client has no active WorldContext.")
        self.assertGreater(address, 0)
        print(f"Live WorldContext: 0x{address:08X}")

    def test_reads_world_root_and_array_headers(self) -> None:
        """Read root scalars and bounded array metadata without child traversal."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        self.assertEqual(len(bytes(snapshot)), 0x854)
        self.assertGreaterEqual(int(snapshot.level), 0)
        self.assertGreaterEqual(int(snapshot.experience), 0)
        for size in snapshot.array_sizes.values():
            self.assertGreaterEqual(size, 0)
        print(
            "Live world: "
            f"player={snapshot.player_number}, level={snapshot.level}, "
            f"experience={snapshot.experience}, players="
            f"{snapshot.array_sizes['players_array']}"
        )

    def test_reads_party_attributes_and_effect_blocks(self) -> None:
        """Read complete party attribute/effect arrays from the live root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        attributes = snapshot.party_attributes or []
        effects = snapshot.party_effects or []
        self.assertLessEqual(len(attributes), 128)
        self.assertLessEqual(len(effects), 128)
        if attributes:
            self.assertEqual(len(attributes[0].attributes), 54)
        if effects:
            self.assertLessEqual(len(effects[0].buffs), 64)
            self.assertLessEqual(len(effects[0].effects), 128)
        print(
            "Live world child blocks: "
            f"party_attributes={len(attributes)}, party_effects={len(effects)}"
        )

    def test_reads_complete_player_and_npc_records(self) -> None:
        """Read the complete player/NPC arrays through their root headers."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        players = snapshot.players or []
        npcs = snapshot.npc_models or []
        self.assertEqual(len(players), snapshot.array_sizes["players_array"])
        self.assertEqual(len(npcs), snapshot.array_sizes["npc_models_array"])
        if players:
            self.assertGreaterEqual(int(players[0].player_number), 0)
        if npcs:
            self.assertGreaterEqual(int(npcs[0].files_count), 0)
        print(
            "Live world records: "
            f"players={len(players)}, npc_models={len(npcs)}"
        )

    def test_live_array_properties_match_source_sizes(self) -> None:
        """Every source array property returns its full advertised count."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        source_arrays = (
            ("message_buff_array", "message_buff"),
            ("dialog_buff_array", "dialog_buff"),
            ("merch_items_array", "merch_items"),
            ("merch_items2_array", "merch_items2"),
            ("map_agents_array", "map_agents"),
            ("party_allies_array", "party_allies"),
            ("party_attributes_array", "party_attributes"),
            ("h04B8_array", "h04B8_ptrs"),
            ("h04C8_array", "h04C8_ptrs"),
            ("h04DC_array", "h04DC_ptrs"),
            ("party_effects_array", "party_effects"),
            ("h0518_array", "h0518_ptrs"),
            ("quest_log_array", "quest_log"),
            ("mission_objectives_array", "mission_objectives"),
            ("henchmen_agent_ids_array", "henchmen_agent_ids"),
            ("hero_flags_array", "hero_flags"),
            ("hero_info_array", "hero_info"),
            ("cartographed_areas_array", "cartographed_areas"),
            ("controlled_minion_count_array", "controlled_minions"),
            ("missions_completed_array", "missions_completed"),
            ("missions_bonus_array", "missions_bonus"),
            ("missions_completed_hm_array", "missions_completed_hm"),
            ("missions_bonus_hm_array", "missions_bonus_hm"),
            ("unlocked_map_array", "unlocked_maps"),
            ("party_morale_array", "party_morale"),
            ("pets_array", "pets"),
            ("party_profession_states_array", "party_profession_states"),
            ("h06CC_array", "h06CC_ptrs"),
            ("h06E0_array", "h06E0_ptrs"),
            ("party_skillbar_array", "party_skillbars"),
            ("learnable_character_skills_array", "learnable_character_skills"),
            ("unlocked_character_skills_array", "unlocked_character_skills"),
            ("duplicated_character_skills_array", "duplicated_character_skills"),
            ("h0730_array", "h0730_ptrs"),
            ("agent_name_info_array", "agent_name_info"),
            ("h07DC_array", "h07DC_ptrs"),
            ("mission_map_icons_array", "mission_map_icons"),
            ("npc_models_array", "npc_models"),
            ("players_array", "players"),
            ("titles_array", "titles"),
            ("title_tiers_array", "title_tiers"),
        )
        for array_name, property_name in source_arrays:
            with self.subTest(array=array_name):
                values = getattr(snapshot, property_name) or []
                self.assertEqual(
                    len(values),
                    snapshot.array_sizes[array_name],
                    f"{property_name} was truncated before the source size",
                )

        # Reforged's source property is currently an unconditional ``None``;
        # the native array field exists, but the Python accessor does not read it.
        self.assertIsNone(snapshot.vanquished_areas)

    def test_reads_complete_hero_and_pet_records(self) -> None:
        """Read all hero flag/info and pet records through their root arrays."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        hero_flags = snapshot.hero_flags or []
        hero_info = snapshot.hero_info or []
        pets = snapshot.pets or []
        self.assertEqual(len(hero_flags), snapshot.array_sizes["hero_flags_array"])
        self.assertEqual(len(hero_info), snapshot.array_sizes["hero_info_array"])
        self.assertEqual(len(pets), snapshot.array_sizes["pets_array"])
        if hero_info:
            self.assertGreaterEqual(int(hero_info[0].level), 0)
        if pets:
            self.assertGreaterEqual(int(pets[0].agent_id), 0)
        print(
            "Live world hero records: "
            f"flags={len(hero_flags)}, info={len(hero_info)}, pets={len(pets)}"
        )

    def test_reads_complete_skill_records(self) -> None:
        """Read skillbars and skill-ID arrays through the live world root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        skillbars = snapshot.skillbars or []
        learnable = snapshot.learnable_character_skills or []
        unlocked = snapshot.unlocked_character_skills or []
        duplicated = snapshot.duplicated_character_skills or []
        self.assertEqual(len(skillbars), snapshot.array_sizes["party_skillbar_array"])
        self.assertEqual(len(learnable), snapshot.array_sizes["learnable_character_skills_array"])
        self.assertEqual(len(unlocked), snapshot.array_sizes["unlocked_character_skills_array"])
        self.assertEqual(len(duplicated), snapshot.array_sizes["duplicated_character_skills_array"])
        if skillbars:
            self.assertEqual(len(skillbars[0].skills), 8)
        print(
            "Live world skills: "
            f"skillbars={len(skillbars)}, learnable={len(learnable)}, "
            f"unlocked={len(unlocked)}, duplicated={len(duplicated)}"
        )

    def test_reads_complete_quest_and_title_records(self) -> None:
        """Read quest/objective and title/tier arrays from the live root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        quests = snapshot.quests or []
        objectives = snapshot.mission_objectives or []
        titles = snapshot.titles or []
        tiers = snapshot.title_tiers or []
        self.assertEqual(len(quests), snapshot.array_sizes["quest_log_array"])
        self.assertEqual(len(objectives), snapshot.array_sizes["mission_objectives_array"])
        self.assertEqual(len(titles), snapshot.array_sizes["titles_array"])
        self.assertEqual(len(tiers), snapshot.array_sizes["title_tiers_array"])
        if quests:
            self.assertGreaterEqual(int(quests[0].quest_id), 0)
        if titles:
            self.assertGreaterEqual(int(titles[0].current_points), 0)
        print(
            "Live world quest/title records: "
            f"quests={len(quests)}, objectives={len(objectives)}, "
            f"titles={len(titles)}, tiers={len(tiers)}"
        )

    def test_reads_complete_source_child_records_and_helpers(self) -> None:
        """Read the remaining source-backed WorldContext child surfaces."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        map_agents = snapshot.map_agents or []
        allies = snapshot.party_allies or []
        minions = snapshot.controlled_minions or []
        professions = snapshot.party_profession_states or []
        morale = snapshot.party_morale or []
        names = snapshot.agent_name_info or []
        icons = snapshot.mission_map_icons or []
        self.assertEqual(len(map_agents), snapshot.array_sizes["map_agents_array"])
        self.assertEqual(len(allies), snapshot.array_sizes["party_allies_array"])
        self.assertEqual(len(minions), snapshot.array_sizes["controlled_minion_count_array"])
        self.assertEqual(len(professions), snapshot.array_sizes["party_profession_states_array"])
        self.assertEqual(len(morale), snapshot.array_sizes["party_morale_array"])
        self.assertEqual(len(names), snapshot.array_sizes["agent_name_info_array"])
        self.assertEqual(len(icons), snapshot.array_sizes["mission_map_icons_array"])
        self.assertIsInstance(snapshot.get_party_attributes(), dict)
        if map_agents:
            self.assertIsInstance(map_agents[0].is_dead, bool)
        print(
            "Live world source children: "
            f"map_agents={len(map_agents)}, allies={len(allies)}, "
            f"minions={len(minions)}, professions={len(professions)}, "
            f"morale={len(morale)}, names={len(names)}, icons={len(icons)}"
        )

    def test_accesses_live_source_property_surface(self) -> None:
        """Exercise each declared root and sampled child property live."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")

        root_properties = [
            name
            for name, member in vars(WorldContextStruct).items()
            if isinstance(member, property)
        ]
        child_records = 0
        child_properties = 0
        for name in root_properties:
            value = getattr(snapshot, name)
            if not isinstance(value, list):
                continue
            for record in value[:2]:
                child_records += 1
                for member_name, member in vars(type(record)).items():
                    if isinstance(member, property):
                        getattr(record, member_name)
                        child_properties += 1

        self.assertGreater(len(root_properties), 0)
        print(
            "Live WorldContext property access: "
            f"root_properties={len(root_properties)}, "
            f"sampled_child_records={child_records}, "
            f"child_properties={child_properties}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
