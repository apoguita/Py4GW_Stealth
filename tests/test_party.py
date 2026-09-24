"""Live Guild Wars tests for the ported ``Party`` class.

Each assertion is checked against the party context it claims to read, or against
an invariant that must hold in a loaded map. The four members that were ported
from the wrong source first time round -- ``GetPartySize``, ``GetHeroCount``,
``IsPartyLeader`` and ``IsPartyLoaded`` -- are each pinned here.

Run it from the project directory while Guild Wars is running::

    python -m unittest tests.test_party -v
"""

from __future__ import annotations

import math
import unittest

import py4gw
from py4gw.client import ConnectedClient
from py4gw.context.party_context import PartyInfoStruct
from py4gw.party import Party

ACTIVE = 0xFFFFFFFF
"""The native "this player" index, passed through from ``get_is_player_ticked``."""


class LivePartyTests(unittest.TestCase):
    """Verify the ported Party members against a live client."""

    client: ConnectedClient
    party: PartyInfoStruct

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to a client whose party context is readable."""

        from py4gw.map import Map

        clients = py4gw.Win32().find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.client = py4gw.connect(clients[0])

        if not Map.IsMapReady():
            py4gw.disconnect()
            raise unittest.SkipTest(
                "Log a character into a loaded map before running this test "
                f"(instance type {Map.GetInstanceTypeName()})."
            )

        party = Party._party()
        if party is None:
            py4gw.disconnect()
            raise unittest.SkipTest("The party context is not readable right now.")
        cls.party = party

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    # ── membership ────────────────────────────────────────────────────────

    def test_lists_match_the_party_context(self) -> None:
        """Read each member list from the party info arrays."""

        self.assertEqual(
            [int(m.login_number) for m in Party.GetPlayers()],
            [int(m.login_number) for m in (self.party.players or [])],
        )
        self.assertEqual(len(Party.GetHeroes()), len(self.party.heroes or []))
        self.assertEqual(len(Party.GetHenchmen()), len(self.party.henchmen or []))

    def test_party_size_counts_every_member_kind(self) -> None:
        """``GetPartySize`` is players plus heroes plus henchmen, not players."""

        expected = (
            len(self.party.players or [])
            + len(self.party.heroes or [])
            + len(self.party.henchmen or [])
        )
        self.assertEqual(Party.GetPartySize(), expected)
        self.assertGreaterEqual(Party.GetPartySize(), Party.GetPlayerCount())

    def test_player_count_matches_the_players_array(self) -> None:
        """``GetPlayerCount`` counts players only."""

        self.assertEqual(Party.GetPlayerCount(), len(self.party.players or []))

    def test_hero_count_matches_the_heroes_array(self) -> None:
        """``GetHeroCount`` is ``heroes.size()``, not the context's hero_count."""

        self.assertEqual(Party.GetHeroCount(), len(self.party.heroes or []))

    def test_henchman_count_matches_the_henchmen_array(self) -> None:
        """``GetHenchmanCount`` is ``henchmen.size()``."""

        self.assertEqual(Party.GetHenchmanCount(), len(self.party.henchmen or []))

    def test_party_id_matches_the_context(self) -> None:
        """Read the id from the party info record."""

        self.assertEqual(Party.GetPartyID(), int(self.party.party_id))

    # ── state ─────────────────────────────────────────────────────────────

    def test_leader_is_the_first_connected_player(self) -> None:
        """``IsPartyLeader`` uses the first connected member, not the flag bit.

        Native ``get_is_leader`` walks the player array for the first connected
        member and compares its login number. ``PartyContext::IsPartyLeader()``
        reads a flag bit instead, and the two can disagree, so this checks the
        computation the binding uses.
        """

        from py4gw.player import Player

        players = Party.GetPlayers()
        if not players:
            self.skipTest("The party has no players.")
        player_number = Player.GetPlayerNumber()
        expected = False
        for member in players:
            if bool(member.is_connected):
                expected = int(member.login_number) == player_number
                break
        self.assertEqual(Party.IsPartyLeader(), expected)

    def test_party_connected_requires_every_member(self) -> None:
        """``IsPartyConnected`` is every player reporting connected."""

        players = Party.GetPlayers()
        if not players:
            self.assertFalse(Party._is_party_connected())
            return
        self.assertEqual(
            Party._is_party_connected(),
            all(bool(member.is_connected) for member in players),
        )

    def test_party_loaded_combines_gate_player_and_connection(self) -> None:
        """``IsPartyLoaded`` is the gate, the player check, and every member."""

        from py4gw.map import Map
        from py4gw.player import Player

        expected = (
            Map.IsMapReady() and Player.IsPlayerLoaded() and Party._is_party_connected()
        )
        self.assertEqual(Party.IsPartyLoaded(), expected)

    def test_ticking_agrees_across_members(self) -> None:
        """The three ticked accessors must not contradict each other."""

        from py4gw.player import Player

        players = Party.GetPlayers()
        if not players:
            self.assertFalse(Party.IsAllTicked())
            return

        self.assertEqual(
            Party.IsAllTicked(), all(bool(member.is_ticked) for member in players)
        )
        self.assertEqual(
            Party.IsPlayerTicked(ACTIVE),
            Party.IsPlayerTicked(Party.GetOwnPartyNumber())
            if Party.GetOwnPartyNumber() >= 0
            else Party.IsPlayerTicked(ACTIVE),
        )
        # The player is a member, so "all ticked" implies "this player ticked".
        if Party.IsAllTicked():
            self.assertTrue(Party.IsPlayerTicked(ACTIVE))
        self.assertIsInstance(Player.GetPlayerNumber(), int)

    def test_player_ticked_at_an_index_reads_that_member(self) -> None:
        """An explicit index reads the member at that position."""

        players = Party.GetPlayers()
        if not players:
            self.skipTest("The party has no players.")
        for index, member in enumerate(players):
            with self.subTest(index=index):
                self.assertEqual(
                    Party.IsPlayerTicked(index), bool(member.is_ticked)
                )
        self.assertFalse(Party.IsPlayerTicked(len(players)))

    def test_defeated_matches_the_context_flag(self) -> None:
        """``IsPartyDefeated`` is ``PartyContext::IsDefeated()``."""

        context = Party._context()
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(Party.IsPartyDefeated(), bool(context.is_defeated))

    def test_hard_mode_matches_the_context_flag(self) -> None:
        """``IsHardMode`` is ``PartyContext::InHardMode()``."""

        context = Party._context()
        assert context is not None
        self.assertEqual(Party.IsHardMode(), bool(context.in_hard_mode))
        self.assertEqual(Party.IsNormalMode(), not Party.IsHardMode())

    def test_hard_mode_unlocked_matches_the_world_context(self) -> None:
        """``IsHardModeUnlocked`` reads the world context, not the party one."""

        world = Party._world()
        self.assertIsNotNone(world)
        assert world is not None
        self.assertEqual(
            Party.IsHardModeUnlocked(), int(world.is_hard_mode_unlocked) != 0
        )

    # ── the recorded finding ──────────────────────────────────────────────

    def test_others_matches_the_party_context_array(self) -> None:
        """``GetOthers`` reads ``PartyInfo::others``, the array with data.

        The binding's own ``others`` vector is a separate, never-populated copy;
        Reforged reads the game array in ``PartyContext.py:78``, and so does
        this. Solo in an outpost the array is usually empty, which is why this
        compares against the context rather than asserting a length.
        """

        self.assertEqual(
            Party.GetOthers(), [int(value) for value in (self.party.others or [])]
        )

    def test_hero_index_finds_each_hero(self) -> None:
        """``GetHeroIndex`` returns each hero's one-based position.

        Native matches on the hero id *and* the owning player, and returns
        ``index + 1`` so that ``0`` stays free to mean "not found".
        """

        heroes = Party.GetHeroes()
        if not heroes:
            self.assertEqual(Party.GetHeroIndex(1), 0)
            return
        for index, hero in enumerate(heroes):
            with self.subTest(hero_id=int(hero.hero_id)):
                self.assertEqual(Party.GetHeroIndex(int(hero.hero_id)), index + 1)
        self.assertEqual(Party.GetHeroIndex(999), 0)

    def test_hero_agent_ids_by_party_position(self) -> None:
        """Position 0 is the controlled character, then the hero array."""

        from py4gw.player import Player

        heroes = Party.GetHeroes()
        self.assertEqual(
            Party.Heroes.GetHeroAgentIDByPartyPosition(0), Player.GetAgentID()
        )
        for index, hero in enumerate(heroes):
            with self.subTest(position=index + 1):
                self.assertEqual(
                    Party.Heroes.GetHeroAgentIDByPartyPosition(index + 1),
                    int(hero.agent_id),
                )
        self.assertEqual(
            Party.Heroes.GetHeroAgentIDByPartyPosition(len(heroes) + 1), 0
        )

    def test_hero_id_lookups_resolve_with_heroes_present(self) -> None:
        """Both hero-id lookups return hits, not the miss value."""

        heroes = Party.GetHeroes()
        if not heroes:
            self.skipTest("The party has no heroes.")
        for index, hero in enumerate(heroes):
            with self.subTest(agent_id=int(hero.agent_id)):
                self.assertEqual(
                    Party.Heroes.GetHeroIDByAgentID(int(hero.agent_id)),
                    int(hero.hero_id),
                )
                self.assertEqual(
                    Party.Heroes.GetHeroIDByPartyPosition(index),
                    int(hero.hero_id),
                )
        self.assertIsNone(Party.Heroes.GetHeroIDByAgentID(0xFFFFFF))
        self.assertIsNone(Party.Heroes.GetHeroIDByPartyPosition(len(heroes) + 5))

    def test_hero_position_by_agent_id(self) -> None:
        """``GetHeroPartyPositionByAgentID`` is zero-based, ``-1`` on a miss."""

        heroes = Party.GetHeroes()
        if not heroes:
            self.skipTest("The party has no heroes.")
        for index, hero in enumerate(heroes):
            with self.subTest(agent_id=int(hero.agent_id)):
                self.assertEqual(
                    Party.Heroes.GetHeroPartyPositionByAgentID(int(hero.agent_id)),
                    index,
                )
        self.assertEqual(Party.Heroes.GetHeroPartyPositionByAgentID(0xFFFFFF), -1)

    def test_target_id_by_agent_id_walks_hero_flags(self) -> None:
        """Exercise the ``world->hero_flags`` walk, not just its early exit."""

        heroes = Party.GetHeroes()
        world = Party._world()
        self.assertIsNotNone(world)
        assert world is not None

        for hero in heroes:
            agent_id = int(hero.agent_id)
            expected = 0
            for flag in world.hero_flags or []:
                if int(flag.agent_id) == agent_id:
                    expected = int(flag.locked_target_id)
            with self.subTest(agent_id=agent_id):
                self.assertEqual(
                    Party.Heroes.GetTargetIDByAgentID(agent_id), expected
                )
        self.assertEqual(Party.Heroes.GetTargetIDByAgentID(0xFFFFFF), 0)

    def test_all_flag_matches_the_world_context(self) -> None:
        """``GetAllFlag`` reads ``world->all_flag`` raw, as native does.

        The game stores an *unset* flag as ``(+inf, +inf, 0.0)``, so this does
        not assume a flag is up: it compares against the raw floats either way.
        """

        world = Party._world()
        assert world is not None

        x = float(world.all_flag_array[0])
        y = float(world.all_flag_array[1])
        self.assertEqual(Party.Heroes.GetAllFlag(), (x, y))
        self.assertEqual(Party.Heroes.IsAllFlagged(), x != 0.0 or y != 0.0)
        self.assertEqual(Party.Heroes.IsHeroFlagged(0), Party.Heroes.IsAllFlagged())
        self.assertFalse(Party.Heroes.IsHeroFlagged(1))

        if math.isfinite(x) and math.isfinite(y):
            # A set flag is a real map position; an unset one is non-finite.
            self.assertNotEqual((x, y), (0.0, 0.0))

    def test_hero_flag_positions_are_readable_but_flagged_stays_false(self) -> None:
        """Pin the source limitation in ``IsHeroFlagged``.

        Native answers only for position ``0`` and returns ``False`` for every
        other position, commented "hero_flags access via context not directly
        available". The array *is* readable - ``world->hero_flags[i].flag`` holds
        that hero's own flag position - so the comment is stale. This port keeps
        the source's behaviour, and this test records the evidence so the
        limitation is not mistaken for a read failure.
        """

        heroes = Party.GetHeroes()
        if not heroes:
            self.skipTest("The party has no heroes.")

        world = Party._world()
        assert world is not None

        # The array is real and aligned with the party's hero order.
        self.assertEqual(
            [int(flag.agent_id) for flag in (world.hero_flags or [])],
            [int(hero.agent_id) for hero in heroes],
        )

        for position in range(1, len(heroes) + 1):
            with self.subTest(position=position):
                self.assertFalse(Party.Heroes.IsHeroFlagged(position))

    def test_pet_info_matches_the_world_context(self) -> None:
        """``GetPetInfo`` finds the owner's pet, and owner 0 means this player."""

        from py4gw.player import Player

        world = Party._world()
        assert world is not None
        owner = Player.GetAgentID()
        expected = next(
            (p for p in (world.pets or []) if int(p.owner_agent_id) == owner), None
        )
        if expected is None:
            self.skipTest("This player has no pet.")

        by_owner = Party.Pets.GetPetInfo(owner)
        self.assertEqual(by_owner.agent_id, expected.agent_id)
        self.assertEqual(by_owner.owner_agent_id, expected.owner_agent_id)
        self.assertEqual(by_owner.behavior, expected.behavior)

        # Owner 0 is the controlled character, per native get_pet_info.
        self.assertEqual(Party.Pets.GetPetInfo(0).agent_id, expected.agent_id)
        self.assertEqual(Party.Pets.GetPetID(0), int(expected.agent_id))
        self.assertEqual(Party.Pets.GetPetBehavior(0), int(expected.behavior))

    def test_pet_info_for_an_owner_without_a_pet_is_zeroed(self) -> None:
        """An owner with no pet gets the source's zeroed record."""

        world = Party._world()
        assert world is not None
        owners = {int(p.owner_agent_id) for p in (world.pets or [])}
        absent = next(a for a in range(0xFFFF0000, 0xFFFF0010) if a not in owners)

        info = Party.Pets.GetPetInfo(absent)
        self.assertEqual(int(info.agent_id), 0)
        self.assertEqual(int(info.owner_agent_id), 0)
        self.assertEqual(Party.Pets.GetPetID(absent), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
