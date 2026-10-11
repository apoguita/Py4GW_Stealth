"""Offline tests for `py4gw/gwa3/uai_utils.py` -- the UtilityAI arithmetic layer.

No client and no elevation. **These tests pin the constants**, because they are the whole function: a
changed armour bonus or hit-point slope changes what a bot decides to attack, and none of the numbers
is derivable from the others. Each assertion cites the GwAu3 line its number comes from.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import constants, uai_get_agent, uai_utils

#: The two columns the party-range tests key their coordinate table on.
_X = constants.GC_UAI_AGENT_X


class _Agent:
    """The ported agent reads, as the module uses them."""

    def __init__(self, level: int = 20, primary: int = 1, health: float = 1.0) -> None:
        self.level = level
        self.primary = primary
        self.health = health

    def install(self) -> list[mock._patch]:
        patches = [
            mock.patch.object(uai_utils.Agent, "GetProfessions", lambda _id: (self.primary, 0)),
            mock.patch.object(uai_utils.Agent, "GetLevel", lambda _id: self.level),
            mock.patch.object(uai_utils.Agent, "GetHealth", lambda _id: self.health),
        ]
        for patch in patches:
            patch.start()
        return patches


class ArmorBonusTests(unittest.TestCase):
    """``UtilityAI_Utils.au3:315-324``: Warrior/Paragon 20, Ranger/Assassin/Dervish 10, else 0."""

    def test_the_three_cases(self) -> None:
        for profession in (1, 9):
            with self.subTest(profession=profession):
                self.assertEqual(uai_utils.UAI_GetArmorBonus(profession), 20)
        for profession in (2, 7, 10):
            with self.subTest(profession=profession):
                self.assertEqual(uai_utils.UAI_GetArmorBonus(profession), 10)
        for profession in (0, 3, 4, 5, 6, 8, 99):
            with self.subTest(profession=profession):
                self.assertEqual(uai_utils.UAI_GetArmorBonus(profession), 0)


class HitPointTests(unittest.TestCase):
    """``:327-342``: level x 20 + 80, plus 20 per level above 20 in hard mode only."""

    def test_the_normal_mode_formula(self) -> None:
        agent = _Agent(level=20)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        with mock.patch.object(uai_utils.Party, "IsHardMode", return_value=False):
            # 20 x 20 + 80 = 480, which is a level-20 character's real maximum.
            self.assertEqual(uai_utils.UAI_GetEstimatedMaxHP(1), 480)

    def test_the_hard_mode_bonus_applies_above_twenty_only(self) -> None:
        agent = _Agent(level=28)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        with mock.patch.object(uai_utils.Party, "IsHardMode", return_value=True):
            # 28 x 20 + 80 + (28 - 20) x 20 = 560 + 80 + 160 = 800.
            self.assertEqual(uai_utils.UAI_GetEstimatedMaxHP(1), 800)
        with mock.patch.object(uai_utils.Party, "IsHardMode", return_value=False):
            self.assertEqual(uai_utils.UAI_GetEstimatedMaxHP(1), 640)

    def test_an_unknown_level_answers_twenty(self) -> None:
        """``:332`` -- "Default to level 20 if unknown"."""

        agent = _Agent(level=0)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        with mock.patch.object(uai_utils.Party, "IsHardMode", return_value=False):
            self.assertEqual(uai_utils.UAI_GetEstimatedMaxHP(1), 480)

    def test_the_current_estimate_is_the_fraction_times_the_maximum(self) -> None:
        agent = _Agent(level=20, health=0.5)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        with mock.patch.object(uai_utils.Party, "IsHardMode", return_value=False):
            self.assertEqual(uai_utils.UAI_GetEstimatedCurrentHP(1), 240)
            agent.health = 0.0
            self.assertEqual(uai_utils.UAI_GetEstimatedCurrentHP(1), 0)


class ArmorRatingTests(unittest.TestCase):
    """``:353-386``: level x 3 + the profession bonus, with two conditional extras."""

    def test_base_armor(self) -> None:
        agent = _Agent(level=20, primary=1)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        # Warrior: 20 x 3 + 20 = 80.
        self.assertEqual(uai_utils.UAI_GetBaseArmor(1), 80)
        agent.primary = 3  # Monk: no bonus.
        self.assertEqual(uai_utils.UAI_GetBaseArmor(1), 60)

    def test_the_two_conditional_extras(self) -> None:
        agent = _Agent(level=20, primary=1)
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])
        self.assertEqual(uai_utils.UAI_GetPhysicalArmor(1), 100)  # Warrior +20 physical
        self.assertEqual(uai_utils.UAI_GetElementalArmor(1), 80)

        agent.primary = 2  # Ranger
        self.assertEqual(uai_utils.UAI_GetPhysicalArmor(1), 70)
        self.assertEqual(uai_utils.UAI_GetElementalArmor(1), 100)  # Ranger +30 elemental


class DamageCurveTests(unittest.TestCase):
    """``:392-405``: 2 ^ ((60 - armour) / 40), and penetration capped at 100%."""

    def test_the_reference_point_is_one(self) -> None:
        # "60 AL = 1.0x damage" (``:390``).
        self.assertAlmostEqual(uai_utils.UAI_GetDamageMultiplier(60), 1.0)
        # 100 AL halves it: 2 ^ (-1).
        self.assertAlmostEqual(uai_utils.UAI_GetDamageMultiplier(100), 0.5)
        # And a negative rating clamps to zero: 2 ^ 1.5.
        self.assertAlmostEqual(uai_utils.UAI_GetDamageMultiplier(-50), 2 ** 1.5)
        self.assertAlmostEqual(uai_utils.UAI_GetDamageMultiplier(0), 2 ** 1.5)

    def test_penetration_short_circuits_and_caps(self) -> None:
        # No penetration returns the armour unchanged, not rounded through the arithmetic.
        self.assertEqual(uai_utils.UAI_GetEffectiveArmor(81, 0), 81)
        self.assertEqual(uai_utils.UAI_GetEffectiveArmor(81, -1), 81)
        # 20% penetration on 100 AL is 80 AL, which is the source's own example (``:400``).
        self.assertEqual(uai_utils.UAI_GetEffectiveArmor(100, 0.2), 80)
        # Above 100% is capped rather than allowed to invert the armour.
        self.assertEqual(uai_utils.UAI_GetEffectiveArmor(100, 2), 0)


class EstimateDamageTests(unittest.TestCase):
    """``:412-433``: the armour is chosen by type, and armour-ignoring returns first."""

    def test_armor_ignoring_never_reads_the_agent(self) -> None:
        """Its short-circuit is first, so it works for an agent that cannot be resolved."""

        with mock.patch.object(uai_utils.Agent, "GetProfessions") as professions:
            self.assertEqual(uai_utils.UAI_EstimateDamage(50, 999, "armor-ignoring"), 50)
            professions.assert_not_called()

    def test_the_three_armour_arms(self) -> None:
        agent = _Agent(level=20, primary=1)  # Warrior: physical 100, elemental 80, base 80.
        patches = agent.install()
        self.addCleanup(lambda: [patch.stop() for patch in patches])

        # physical -> 100 AL -> 2 ^ ((60-100)/40) = 0.5 -> 100 damage becomes 50.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "physical"), 50)
        # elemental -> 80 AL -> 2 ^ (-0.5) -> about 70.7 -> 71.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "elemental"), 71)
        # fire is one of the five elemental spellings.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "fire"), 71)
        # anything else is the base rating, which for a Warrior is 80.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "chaos"), 71)
        # and penetration moves it: 60% of 100 AL is 40 AL, which is *below* the 60 AL reference, so
        # the multiplier goes above 1 -- 2 ^ 0.5 -- and the damage rises rather than falling.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "physical", 0.6), 141)
        # 40% of 100 AL is the 60 AL reference, which is exactly 1.0x.
        self.assertEqual(uai_utils.UAI_EstimateDamage(100, 1, "physical", 0.4), 100)


class ProfessionClassTests(unittest.TestCase):
    """``:436-469``: the three switches, which partition the ten professions."""

    def test_each_predicate_covers_its_own_professions(self) -> None:
        casters = (3, 4, 5, 6, 8)
        melee = (1, 7, 10)
        ranged = (2, 9)

        for profession in range(0, 11):
            with self.subTest(profession=profession):
                agent = _Agent(primary=profession)
                patches = agent.install()
                try:
                    self.assertEqual(uai_utils.UAI_IsCaster(1), profession in casters)
                    self.assertEqual(uai_utils.UAI_IsMelee(1), profession in melee)
                    self.assertEqual(uai_utils.UAI_IsRanged(1), profession in ranged)
                    # Every profession is in at most one group, and none is in two.
                    groups = (
                        profession in casters,
                        profession in melee,
                        profession in ranged,
                    )
                    self.assertLessEqual(sum(groups), 1)
                finally:
                    for patch in patches:
                        patch.stop()

    def test_the_declared_surface(self) -> None:
        """The module's own declarations, and the source's lines they come from.

        The thirteen estimation helpers were the whole module until 2026-10-10; the party layer of the
        engine joined them then (``UtilityAI_Utils.au3:143-285``), which is what the two counts record:
        eight more names, and each one present in the source's own ``Func`` list.
        """

        import pathlib
        import re

        source = (
            pathlib.Path(__file__).resolve().parent.parent
            / "external"
            / "GwAu3"
            / "API"
            / "Plugins"
            / "UtilityAI"
            / "Core"
            / "UtilityAI_Utils.au3"
        ).read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", source))

        self.assertEqual(len(uai_utils.__all__), 27)
        for name in uai_utils.__all__:
            with self.subTest(name=name):
                self.assertIn(name, declared, "not declared in UtilityAI_Utils.au3")
                self.assertTrue(callable(getattr(uai_utils, name)))


class PartyQueryTests(unittest.TestCase):
    """The engine's party layer (``UtilityAI_Utils.au3:143-285``).

    The three aggro questions and the called target, over stubbed party and agent reads. **The stubs are
    the members the source calls**, so what is checked is the source's own control flow: the flagged-hero
    skip, the two different distances in the range search, and the "first other player who called
    something" rule.
    """

    def _party(self, heroes: list[tuple[int, float, float]], players: list[tuple[int, int]] | None = None):
        """``{hero number: (agent id, flag x, flag y)}`` and ``{player number: (login, called)}``."""

        hero_rows = {index + 1: row for index, row in enumerate(heroes)}
        player_rows = {index + 1: row for index, row in enumerate(players or [])}

        def my_party_info(info: str) -> int:
            return {
                "ArrayHeroPartyMemberSize": len(hero_rows),
                "ArrayPlayerPartyMemberSize": len(player_rows),
            }.get(info, 0)

        def flag_info(number: int, info: str) -> float:
            row = hero_rows.get(int(number))
            if row is None:
                return 0
            return row[1] if info == "FlagX" else row[2]

        def hero_info(number: int, info: str) -> int:
            row = hero_rows.get(int(number))
            if row is None:
                return 0
            return row[0] if info == "AgentID" else 0

        def player_info(number: int, info: str) -> int:
            row = player_rows.get(int(number))
            if row is None:
                return 0
            return row[0] if info == "LoginNumber" else row[1]

        return my_party_info, flag_info, hero_info, player_info

    def _patched(self, party, **extra):
        patches = [
            mock.patch.object(uai_utils, "Party_GetMyPartyInfo", party[0]),
            mock.patch.object(uai_utils, "Party_GetHeroFlagInfo", party[1]),
            mock.patch.object(uai_utils, "Party_GetMyPartyHeroInfo", party[2]),
            mock.patch.object(uai_utils, "Party_GetMyPartyPlayerMemberInfo", party[3]),
        ]
        for target, value in extra.items():
            patches.append(mock.patch.object(uai_utils, target, value))
        return patches

    def _run(self, patches, call):
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return call()

    def test_the_two_context_wrappers_delegate(self) -> None:
        seen: list[str] = []

        def context(info: str) -> int:
            seen.append(info)
            return 3

        with mock.patch("py4gw.gwa3.data_party.Party_GetPartyContextInfo", context):
            self.assertEqual(uai_utils.Party_GetSize(), 3)
            self.assertEqual(uai_utils.Party_GetHeroCount(), 3)
        self.assertEqual(seen, ["TotalPartySize", "HeroCount"])

    def test_hero_slot_zero_is_the_player(self) -> None:
        with mock.patch.object(uai_utils, "UAI_GetPlayerInfo", lambda column: 4242), mock.patch.object(
            uai_utils, "Party_GetMyPartyHeroInfo", lambda number, info: 7
        ):
            self.assertEqual(uai_utils.Party_GetHeroAgentID(0), 4242)
            self.assertEqual(uai_utils.Party_GetHeroID(0), 4242)
            self.assertEqual(uai_utils.Party_GetHeroAgentID(1), 7)
            self.assertEqual(uai_utils.Party_GetHeroID(1), 7)

    def test_the_count_query_answers_the_players_enemy_first(self) -> None:
        party = self._party([(100, 0.0, 0.0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_GetNearestAgent", lambda *args: 55))
        self.assertEqual(self._run(patches, lambda: uai_utils.UAI_CountEnemyInPartyAggroRange(1320)), 55)

    def test_the_count_query_skips_a_flagged_hero_and_answers_a_count_from_an_unflagged_one(self) -> None:
        # Hero 1 stands where it was flagged (skipped); hero 2 is unflagged, and the source answers
        # `UAI_CountAgents`' *count* from it -- not an agent id, which is the source's own mix-up.
        party = self._party([(100, 10.0, 0.0), (200, 0.0, 0.0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_GetNearestAgent", lambda *args: 0))
        calls: list[tuple] = []

        def count_agents(agent_id, aggro_range, filters):
            calls.append((agent_id, aggro_range, filters))
            return 4

        patches.append(mock.patch.object(uai_get_agent, "UAI_CountAgents", count_agents))
        self.assertEqual(self._run(patches, lambda: uai_utils.UAI_CountEnemyInPartyAggroRange(1320)), 4)
        self.assertEqual(calls, [(200, 1320, "UAI_Filter_IsLivingEnemy")])

    def test_the_count_query_answers_zero_with_no_hero_and_no_player_enemy(self) -> None:
        party = self._party([])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_GetNearestAgent", lambda *args: 0))
        self.assertEqual(self._run(patches, lambda: uai_utils.UAI_CountEnemyInPartyAggroRange()), 0)

    def test_the_boolean_query_uses_the_player_then_an_unflagged_hero(self) -> None:
        party = self._party([(100, 0.0, 0.0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_IsAgentInRange", lambda *args: False))
        self.assertFalse(self._run(patches, lambda: uai_utils.UAI_IsEnemyInPartyAggroRange(1320)))

        party = self._party([(100, 0.0, 0.0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_IsAgentInRange", lambda *args: True))
        self.assertTrue(self._run(patches, lambda: uai_utils.UAI_IsEnemyInPartyAggroRange(1320)))

    def test_the_range_search_picks_the_enemy_nearest_the_player_among_those_near_the_hero(self) -> None:
        """Two distances: qualification is from the **hero**, the winner is nearest the **player**."""

        party = self._party([(200, 0.0, 0.0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_get_agent, "UAI_GetNearestAgent", lambda *args: 0))
        patches.append(mock.patch.object(uai_get_agent, "_cached_ids", lambda: [51, 52, 53]))
        patches.append(
            mock.patch.object(uai_get_agent, "_cached_distance", lambda agent_id: {51: 900.0, 52: 100.0, 53: 5.0}[agent_id])
        )
        # The hero is at the origin, so 51 and 52 are inside its 300-unit range and 53 is not.
        coordinates = {200: (0.0, 0.0), 51: (150.0, 0.0), 52: (250.0, 0.0), 53: (400.0, 0.0)}
        patches.append(
            mock.patch.object(
                uai_utils, "UAI_GetAgentInfoByID", lambda agent_id, column: coordinates[int(agent_id)][0 if column == _X else 1]
            )
        )
        patches.append(
            mock.patch.object(
                uai_utils, "UAI_GetAgentInfo", lambda agent_id, column: coordinates[int(agent_id)][0 if column == _X else 1]
            )
        )
        with mock.patch("py4gw.gwa3.uai_filter.UAI_Filter_IsLivingEnemy", lambda agent_id: True):
            self.assertEqual(
                self._run(patches, lambda: uai_utils.UAI_GetNearestEnemyInPartyRange(300)), 52
            )

    def test_the_called_target_skips_self_and_takes_the_first_non_zero(self) -> None:
        party = self._party([], players=[(1, 0), (2, 777), (3, 888)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_utils, "Agent_GetAgentInfo", lambda agent_id, key: 1))
        # Player 1 is self (same login), so 777 is the answer even though 888 is also called.
        self.assertEqual(self._run(patches, uai_utils.UAI_GetPartyCalledTarget), 777)

    def test_the_called_target_answers_zero_when_nobody_called(self) -> None:
        party = self._party([], players=[(1, 0)])
        patches = self._patched(party)
        patches.append(mock.patch.object(uai_utils, "Agent_GetAgentInfo", lambda agent_id, key: 1))
        self.assertEqual(self._run(patches, uai_utils.UAI_GetPartyCalledTarget), 0)


if __name__ == "__main__":
    unittest.main()
