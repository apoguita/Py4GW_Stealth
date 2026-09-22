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
        """Read bounded party attribute/effect records from the live root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        attributes = snapshot.party_attributes
        effects = snapshot.party_effects
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

    def test_reads_bounded_player_and_npc_records(self) -> None:
        """Read the populated player/NPC arrays through their root headers."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        players = snapshot.players
        npcs = snapshot.npc_models
        self.assertLessEqual(len(players), 512)
        self.assertLessEqual(len(npcs), 512)
        if players:
            self.assertGreaterEqual(int(players[0].player_number), 0)
        if npcs:
            self.assertGreaterEqual(int(npcs[0].files_count), 0)
        print(
            "Live world records: "
            f"players={len(players)}, npc_models={len(npcs)}"
        )

    def test_reads_bounded_hero_and_pet_records(self) -> None:
        """Read hero flags/info and pet records through their root arrays."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        hero_flags = snapshot.hero_flags
        hero_info = snapshot.hero_info
        pets = snapshot.pets
        self.assertLessEqual(len(hero_flags), 64)
        self.assertLessEqual(len(hero_info), 64)
        self.assertLessEqual(len(pets), 64)
        if hero_info:
            self.assertGreaterEqual(int(hero_info[0].level), 0)
        if pets:
            self.assertGreaterEqual(int(pets[0].agent_id), 0)
        print(
            "Live world hero records: "
            f"flags={len(hero_flags)}, info={len(hero_info)}, pets={len(pets)}"
        )

    def test_reads_bounded_skill_records(self) -> None:
        """Read skillbars and skill-ID arrays through the live world root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        skillbars = snapshot.skillbars
        learnable = snapshot.learnable_character_skills
        unlocked = snapshot.unlocked_character_skills
        duplicated = snapshot.duplicated_character_skills
        self.assertLessEqual(len(skillbars), 64)
        self.assertLessEqual(len(learnable), 512)
        self.assertLessEqual(len(unlocked), 512)
        self.assertLessEqual(len(duplicated), 512)
        if skillbars:
            self.assertEqual(len(skillbars[0].skills), 8)
        print(
            "Live world skills: "
            f"skillbars={len(skillbars)}, learnable={len(learnable)}, "
            f"unlocked={len(unlocked)}, duplicated={len(duplicated)}"
        )

    def test_reads_bounded_quest_and_title_records(self) -> None:
        """Read quest/objective and title/tier arrays from the live root."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        quests = snapshot.quests
        objectives = snapshot.mission_objectives
        titles = snapshot.titles
        tiers = snapshot.title_tiers
        self.assertLessEqual(len(quests), 256)
        self.assertLessEqual(len(objectives), 256)
        self.assertLessEqual(len(titles), 256)
        self.assertLessEqual(len(tiers), 256)
        if quests:
            self.assertGreaterEqual(int(quests[0].quest_id), 0)
        if titles:
            self.assertGreaterEqual(int(titles[0].current_points), 0)
        print(
            "Live world quest/title records: "
            f"quests={len(quests)}, objectives={len(objectives)}, "
            f"titles={len(titles)}, tiers={len(tiers)}"
        )

    def test_reads_source_child_records_and_helpers(self) -> None:
        """Read the remaining source-backed WorldContext child surfaces."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active WorldContext.")
        map_agents = snapshot.map_agents
        allies = snapshot.party_allies
        minions = snapshot.controlled_minions
        professions = snapshot.party_profession_states
        morale = snapshot.party_morale
        names = snapshot.agent_name_info
        icons = snapshot.mission_map_icons
        self.assertLessEqual(len(map_agents), 512)
        self.assertLessEqual(len(allies), 128)
        self.assertLessEqual(len(minions), 128)
        self.assertLessEqual(len(professions), 128)
        self.assertLessEqual(len(morale), 128)
        self.assertLessEqual(len(names), 512)
        self.assertLessEqual(len(icons), 512)
        self.assertIsInstance(snapshot.get_party_attributes(), dict)
        if map_agents:
            self.assertIsInstance(map_agents[0].is_dead, bool)
        print(
            "Live world source children: "
            f"map_agents={len(map_agents)}, allies={len(allies)}, "
            f"minions={len(minions)}, professions={len(professions)}, "
            f"morale={len(morale)}, names={len(names)}, icons={len(icons)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
