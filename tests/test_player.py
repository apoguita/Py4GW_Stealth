"""Live Guild Wars tests for the ported ``Player`` class.

These are assertions, not a printout: every implemented member is checked
against the context it claims to read, or against an invariant that must hold in
a loaded map. Cross-checking two independent routes is the point — a wrapper
that returns a plausible number would still fail most of these.

The suite needs a character logged in to a loaded map. At the character-select
screen it skips, because most of the class has nothing to report there.

Run it from the project directory while Guild Wars is running::

    python -m unittest tests.test_player -v
"""

from __future__ import annotations

import unittest

import py4gw
from py4gw.client import ConnectedClient
from py4gw.context.agent_array import AgentStruct
from py4gw.context.char_context import CharContextStruct
from py4gw.context.friend_list_context import FriendListStruct
from py4gw.context.party_context import PlayerPartyMemberStruct
from py4gw.context.world_context import PlayerStruct, WorldContextStruct
from py4gw.player import Player, PlayerStatus, _pick_highest

#: A moving player drifts between the two reads compared in the position test.
#: At roughly 300 units per second and a sub-millisecond gap, the drift is far
#: below this bound; it is generous only to keep the test from being flaky.
POSITION_TOLERANCE = 50.0


class LivePlayerTests(unittest.TestCase):
    """Verify the ported Player members against a live client."""

    client: ConnectedClient
    char_context: CharContextStruct
    world: WorldContextStruct
    friend_list: FriendListStruct | None
    local_player: PlayerStruct

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to a client that has a character in a loaded map."""

        win32 = py4gw.Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.client = py4gw.connect(clients[0])

        from py4gw.map import Map

        if not Map.IsMapReady():
            py4gw.disconnect()
            raise unittest.SkipTest(
                "Log a character into a loaded map before running this test "
                f"(instance type {Map.GetInstanceTypeName()})."
            )

        char_context = cls.client.read_char_context()
        if char_context is None:
            py4gw.disconnect()
            raise unittest.SkipTest(
                "The character context is gated: the map is not ready."
            )
        cls.char_context = char_context
        world = cls.client.read_world_context()
        if world is None:
            py4gw.disconnect()
            raise unittest.SkipTest("The world context is not readable right now.")
        cls.world = world

        try:
            cls.friend_list = cls.client.read_friend_list()
        except (OSError, RuntimeError):
            cls.friend_list = None

        player_number = int(cls.char_context.player_number)
        local_player = world.GetPlayerById(player_number)
        if local_player is None:
            py4gw.disconnect()
            raise unittest.SkipTest(
                f"The world context has no player record for {player_number}."
            )
        cls.local_player = local_player

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    # ── identity ──────────────────────────────────────────────────────────

    def test_player_number_matches_char_context(self) -> None:
        """Read the player number from the character context."""

        self.assertIsNotNone(Player.GetPlayerNumber())
        self.assertEqual(Player.GetPlayerNumber(), int(self.char_context.player_number))

    def test_player_is_loaded(self) -> None:
        """Report a loaded player in a ready map."""

        self.assertTrue(Player.IsPlayerLoaded())

    def test_player_and_party_is_player_loaded_agree(self) -> None:
        """Keep the one load-bearing check implemented in exactly one place.

        ``Player.IsPlayerLoaded`` delegates to ``Party.IsPlayerLoaded``. They
        previously held two copies that had already diverged — one used the
        stricter ``ready`` gate, the other the native-parity ``is_map_ready`` —
        so they could disagree whenever the account agent context was
        unreadable. This pins them together.
        """

        from py4gw.party import Party

        self.assertEqual(Player.IsPlayerLoaded(), Party.IsPlayerLoaded())

    def test_party_is_player_loaded_is_a_bool(self) -> None:
        """Return a real bool, not Reforged's ``pass`` (which yields ``None``)."""

        from py4gw.party import Party

        self.assertIsInstance(Party.IsPlayerLoaded(), bool)

    def test_agent_id_matches_world_context(self) -> None:
        """Read the agent id from the controlled-character pointer."""

        controlled = self.world.player_controlled_character
        self.assertIsNotNone(controlled)
        assert controlled is not None
        self.assertGreater(Player.GetAgentID(), 0)
        self.assertEqual(Player.GetAgentID(), int(controlled.agent_id))

    def test_agent_record_matches_the_agent_id(self) -> None:
        """Return the record the agent id names, not some other agent."""

        agent = Player.GetAgent()
        self.assertIsNotNone(agent)
        assert agent is not None
        self.assertIsInstance(agent, AgentStruct)
        self.assertEqual(int(agent.agent_id), Player.GetAgentID())

    def test_observing_id_matches_the_game_global(self) -> None:
        """Read the same global native ``GetObservingId`` reads."""

        snapshot = self.client.read_player_agent_id()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertGreater(Player.GetObservingID(), 0)
        self.assertEqual(Player.GetObservingID(), int(snapshot.agent_id))

    def test_observing_id_matches_controlled_when_not_spectating(self) -> None:
        """Agree with the controlled character while not observing a match."""

        if self.char_context.current_map_id != self.char_context.observe_map_id:
            self.skipTest("This client is spectating, so the ids may differ.")
        self.assertEqual(Player.GetObservingID(), Player.GetAgentID())

    def test_name_matches_the_character_context(self) -> None:
        """Read the player name from the character context."""

        name = Player.GetName()
        self.assertTrue(name.strip(), "the player name must not be empty")
        self.assertEqual(name, self.char_context.player_name_str)
        self.assertEqual(name, self.client.character_name())

    def test_account_name_matches_the_world_context(self) -> None:
        """Read the account name from ``world->accountInfo``."""

        account_info = self.world.account_info
        self.assertIsNotNone(account_info)
        assert account_info is not None
        self.assertTrue(Player.GetAccountName())
        self.assertEqual(Player.GetAccountName(), account_info.account_name_str)

    def test_account_email_is_sanitized_ascii(self) -> None:
        """Return an address the sanitizer accepts, or the fallback."""

        email = Player.GetAccountEmail()
        self.assertTrue(email)
        email.encode("ascii")
        self.assertLessEqual(len(email), Player._ACCOUNT_EMAIL_MAX_LEN)

    def test_uuid_matches_the_character_context(self) -> None:
        """Read the four UUID words from the character context."""

        uuid = Player.GetPlayerUUID()
        self.assertEqual(len(uuid), 4)
        self.assertEqual(uuid, self.char_context.player_uuid)
        self.assertTrue(
            any(word != 0 for word in uuid), "a logged-in character has a UUID"
        )

    def test_position_matches_the_agent_record(self) -> None:
        """Return a real position, not the (0.0, 0.0) failure sentinel."""

        agent = Player.GetAgent()
        self.assertIsNotNone(agent)
        assert agent is not None

        xy = Player.GetXY()
        self.assertNotEqual(xy, (0.0, 0.0))

        fresh = agent.xy
        self.assertAlmostEqual(xy[0], fresh[0], delta=POSITION_TOLERANCE)
        self.assertAlmostEqual(xy[1], fresh[1], delta=POSITION_TOLERANCE)

    def test_party_number_indexes_the_matching_member(self) -> None:
        """Index the party list at the login number this player reports."""

        party_context = self.client.read_party_context()
        self.assertIsNotNone(party_context)
        assert party_context is not None
        party = party_context.player_party
        self.assertIsNotNone(party)
        assert party is not None
        members: list[PlayerPartyMemberStruct] = list(party.players or [])
        if not members:
            self.skipTest("The client is not in a party.")

        index = Player.GetPartyNumber()
        login_number = Player.GetLoginNumber()
        self.assertGreaterEqual(index, -1)
        if index >= 0:
            self.assertLess(index, len(members))
            self.assertEqual(int(members[index].login_number), login_number)

    def test_login_number_is_a_party_member(self) -> None:
        """Report a login number that belongs to the current party."""

        party_context = self.client.read_party_context()
        assert party_context is not None and party_context.player_party is not None
        members = list(party_context.player_party.players or [])
        if not members:
            self.skipTest("The client is not in a party.")
        login_numbers = {int(member.login_number) for member in members}
        self.assertIn(Player.GetLoginNumber(), login_numbers)

    # ── progression ───────────────────────────────────────────────────────

    def test_level_matches_the_world_context(self) -> None:
        """Take the maximum of the duplicated level fields."""

        expected = max(int(self.world.level), int(self.world.level_dupe))
        self.assertEqual(Player.GetLevel(), expected)
        self.assertGreaterEqual(Player.GetLevel(), 1)
        self.assertLessEqual(Player.GetLevel(), 20)

    def test_experience_matches_the_world_context(self) -> None:
        """Take the maximum of the duplicated experience fields."""

        expected = max(
            int(self.world.experience), int(self.world.experience_dupe)
        )
        self.assertEqual(Player.GetExperience(), expected)
        self.assertGreaterEqual(Player.GetExperience(), 0)

    def test_morale_matches_the_world_context(self) -> None:
        """Take the maximum of the duplicated morale fields."""

        expected = max(int(self.world.morale), int(self.world.morale_dupe))
        self.assertEqual(Player.GetMorale(), expected)

    def test_skill_points_match_the_world_context(self) -> None:
        """Read both skill-point fields."""

        self.assertEqual(
            Player.GetSkillPointData(),
            (
                int(self.world.current_skill_points),
                int(self.world.total_earned_skill_points),
            ),
        )


    def test_rank_data_shape(self) -> None:
        """Return five non-negative values."""

        rank = Player.GetRankData()
        self.assertEqual(len(rank), 5)
        for value in rank:
            self.assertGreaterEqual(value, 0)

    def test_tournament_reward_points_match_the_world_context(self) -> None:
        """Read the tournament points from ``world->accountInfo``."""

        account_info = self.world.account_info
        assert account_info is not None
        self.assertEqual(
            Player.GetTournamentRewardPoints(),
            int(account_info.tournament_reward_points),
        )

    def test_account_flags_match_the_player_record(self) -> None:
        """Read the flags from this player's own world-context record."""

        self.assertEqual(
            Player.GetAccountFlags(), int(self.local_player.reforged_or_dhuums_flags)
        )

    def test_account_flag_helpers_agree_with_the_bitfield(self) -> None:
        """Derive each helper from the same raw flags value."""

        flags = Player.GetAccountFlags()
        self.assertEqual(Player.IsDhuumsCovenant(), (flags & 0x1) != 0)
        self.assertEqual(Player.IsMelandrusAccord(), (flags & 0x2) != 0)
        self.assertEqual(Player.IsReforged(), (flags & 0x4) != 0)

    # ── collections ───────────────────────────────────────────────────────

    def test_missions_match_the_world_context(self) -> None:
        """Read all four mission-flag arrays."""

        self.assertEqual(
            Player.GetMissionsCompleted(), list(self.world.missions_completed or [])
        )
        self.assertEqual(
            Player.GetMissionsBonusCompleted(),
            list(self.world.missions_bonus or []),
        )
        self.assertEqual(
            Player.GetMissionsCompletedHM(),
            list(self.world.missions_completed_hm or []),
        )
        self.assertEqual(
            Player.GetMissionsBonusCompletedHM(),
            list(self.world.missions_bonus_hm or []),
        )

    def test_mission_arrays_are_bitmap_words(self) -> None:
        """Verify the four mission arrays are 32-bit bitmap words.

        `MISSION_BITMAP_ENTRIES` is 25 and each entry is a bitmap of mission
        flags, so a completed-mission array of 25 words describes up to 800
        bits. Treating the elements as per-mission states yields nonsense.
        """

        for name, values in (
            ("missions_completed", Player.GetMissionsCompleted()),
            ("missions_bonus", Player.GetMissionsBonusCompleted()),
            ("missions_completed_hm", Player.GetMissionsCompletedHM()),
            ("missions_bonus_hm", Player.GetMissionsBonusCompletedHM()),
        ):
            with self.subTest(array=name):
                self.assertTrue(values, f"{name} must not be empty")
                for value in values:
                    self.assertGreaterEqual(int(value), 0)
                    self.assertLessEqual(int(value), 0xFFFFFFFF)
                # These are bitmap words, not 0/1 flags: the words carry values
                # well above a flag. The caller does its own bit math.
                self.assertTrue(any(int(value) != 0 for value in values))

    def test_minions_match_the_world_context(self) -> None:
        """Read the controlled-minion pairs."""

        expected = [
            (int(minion.agent_id), int(minion.minion_count))
            for minion in (self.world.controlled_minions or [])
        ]
        self.assertEqual(Player.GetControlledMinions(), expected)

    def test_skills_match_the_world_context(self) -> None:
        """Read both skill arrays.

        `learnable_character_skills` is an ordinary skill-id array that is empty
        unless a trainer or signet is active; `unlocked_character_skills` is a
        bitmap and is covered separately.
        """

        self.assertEqual(
            Player.GetLearnableCharacterSkills(),
            list(self.world.learnable_character_skills or []),
        )
        self.assertEqual(
            Player.GetUnlockedCharacterSkills(),
            list(self.world.unlocked_character_skills or []),
        )

    def test_faction_triples_match_the_world_context(self) -> None:
        """Read all four faction triples."""

        for result, names in (
            (
                Player.GetKurzickData(),
                ("current_kurzick", "total_earned_kurzick", "max_kurzick"),
            ),
            (
                Player.GetLuxonData(),
                ("current_luxon", "total_earned_luxon", "max_luxon"),
            ),
            (
                Player.GetImperialData(),
                ("current_imperial", "total_earned_imperial", "max_imperial"),
            ),
            (
                Player.GetBalthazarData(),
                ("current_balth", "total_earned_balth", "max_balth"),
            ),
        ):
            with self.subTest(faction=names[2]):
                current, total, maximum = names
                self.assertEqual(
                    result,
                    (
                        max(
                            int(getattr(self.world, current)),
                            int(getattr(self.world, current + "_dupe")),
                        ),
                        max(
                            int(getattr(self.world, total)),
                            int(getattr(self.world, total + "_dupe")),
                        ),
                        int(getattr(self.world, maximum)),
                    ),
                )

    def test_faction_values_are_non_negative(self) -> None:
        """Keep every faction component a non-negative count."""

        for result in (
            Player.GetKurzickData(),
            Player.GetLuxonData(),
            Player.GetImperialData(),
            Player.GetBalthazarData(),
        ):
            with self.subTest(result=result):
                for value in result:
                    self.assertGreaterEqual(value, 0)

    # ── titles ────────────────────────────────────────────────────────────

    def test_title_array_matches_the_world_context(self) -> None:
        """Read the title records and their index list."""

        titles = Player.GetTitleArrayRaw()
        self.assertEqual(len(titles), len(self.world.titles or []))
        self.assertEqual(Player.GetTitleArray(), list(range(len(titles))))

    def test_get_title_bounds(self) -> None:
        """Return a record only for an index that exists.

        Each call re-reads the world context, so ``GetTitle`` returns a freshly
        decoded record rather than the identical object. Compare values, not
        identity.
        """

        titles = Player.GetTitleArrayRaw()
        self.assertTrue(titles, "a loaded character has title records")

        first = Player.GetTitle(0)
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.to_dict(), titles[0].to_dict())

        self.assertIsNone(Player.GetTitle(-1))
        self.assertIsNone(Player.GetTitle(len(titles)))

    def test_active_title_id_is_in_range(self) -> None:
        """Report an index into the title array."""

        count = len(Player.GetTitleArrayRaw())
        self.assertGreaterEqual(Player.GetActiveTitleID(), 0)
        self.assertLess(Player.GetActiveTitleID(), count)

    def test_active_title_matches_the_player_tier(self) -> None:
        """Find the title whose tier index the player record names."""

        active_tier = int(self.local_player.active_title_tier)
        active_id = Player.GetActiveTitleID()
        title = Player.GetTitle(active_id)
        self.assertIsNotNone(title)
        assert title is not None
        self.assertEqual(int(title.current_title_tier_index), active_tier)

    # ── status and chat state ─────────────────────────────────────────────



    def test_agent_id_validity(self) -> None:
        """Accept the player's own agent and reject id zero."""

        self.assertTrue(Player.IsAgentIDValid(Player.GetAgentID()))
        self.assertFalse(Player.IsAgentIDValid(0))

    def test_mouse_over_id_is_the_documented_zero(self) -> None:
        """Report zero, because the native runtime never assigns the field."""

        self.assertEqual(Player.GetMouseOverID(), 0)

    def test_duplicated_fields_resolve_like_the_native_runtime(self) -> None:
        """Cross-check each duplicated pair against ``PickHighest`` semantics.

        A plain ``max`` would return ``0xFFFFFFFF`` when a duplicate reads the
        sentinel; the native discards it.
        """

        for label, actual, first, second in (
            (
                "morale",
                Player.GetMorale(),
                int(self.world.morale),
                int(self.world.morale_dupe),
            ),
            (
                "experience",
                Player.GetExperience(),
                int(self.world.experience),
                int(self.world.experience_dupe),
            ),
            (
                "level",
                Player.GetLevel(),
                int(self.world.level),
                int(self.world.level_dupe),
            ),
        ):
            with self.subTest(field=label):
                self.assertEqual(actual, _pick_highest(first, second))
                self.assertNotEqual(actual, 0xFFFFFFFF)

        current, total = Player.GetSkillPointData()
        self.assertEqual(
            current,
            _pick_highest(
                int(self.world.current_skill_points),
                int(self.world.current_skill_points_dupe),
            ),
        )
        self.assertEqual(
            total,
            _pick_highest(
                int(self.world.total_earned_skill_points),
                int(self.world.total_earned_skill_points_dupe),
            ),
        )

    def test_player_status_matches_the_friend_list(self) -> None:
        """Read the status from ``friend_list->player_status``."""

        if self.friend_list is None:
            self.skipTest("This client has no readable friend list.")
        self.assertEqual(
            Player.GetPlayerStatus(), int(self.friend_list.player_status)
        )
        self.assertIn(Player.GetPlayerStatus(), range(5))

    def test_player_status_name_is_known(self) -> None:
        """Name the status, or report ``unknown`` for an undeclared value."""

        name = Player.GetPlayerStatusName()
        expected = PlayerStatus.from_value(Player.GetPlayerStatus())
        self.assertEqual(
            name, expected.display_name if expected is not None else "unknown"
        )

    def test_is_typing_matches_the_chat_reader(self) -> None:
        """Read the same typing frame id the client connection reports."""

        self.assertIsInstance(Player.IsTyping(), bool)
        self.assertEqual(Player.IsTyping(), self.client.is_typing())

    # ── disabled members ──────────────────────────────────────────────────

    def test_disabled_members_refuse_while_connected(self) -> None:
        """Refuse in a live session too, not only without a client."""

        for name, call in (
            ("Move", lambda: Player.Move(0.0, 0.0)),
            ("ChangeTarget", lambda: Player.ChangeTarget(1)),
            ("GetTargetID", Player.GetTargetID),
            ("GetInstanceUptime", Player.GetInstanceUptime),
            ("GetChatHistory", Player.GetChatHistory),
            ("SendChat", lambda: Player.SendChat(0, "hi")),
        ):
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn(f"Player.{name}", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
