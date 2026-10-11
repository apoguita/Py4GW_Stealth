"""Offline tests for `py4gw/gwa3/uai_get_agent.py` -- GwAu3's targeting and positioning queries.

No client and no elevation. Nothing in this module touches the client directly: every question it asks
goes through a handful of accessors, so a test replaces those with a table and checks the *arithmetic
and the comparisons* -- which is where this file's behaviour lives. What is being established:

* **the surface is GwAu3's own, all twenty-six of it** -- every ``Func`` in ``UtilityAI_GetAgent.au3``
  exists here under its own name, and nothing is exported that the source does not declare;
* the three translations the module header states are the ones made: a cache row is an agent id, the
  ``Distance`` column is computed as the cache computes it, and the fight mode is read at call time;
* the two-pass area-target search answers what GwAu3's answers -- group size first, then the mode's
  average-HP tie-break, with an ineligible agent still counting toward its neighbours' groups;
* the ward search's candidate set (points **and** pairwise midpoints) and its anchor tie-break;
* the source's own quirks are kept, because a test is where they stop looking like accidents: the
  unused reference id in `UAI_GetAgentLowest`, and `UAI_MoveTowardCorpse` answering ``True`` on timeout;
* the one refusal refuses, and names the member it needs.

The stubs are the same shape as the real accessors: ``UAI_GetAgentInfo(agent_id, column)`` positionally,
keyed by the ``GC_UAI_AGENT_*`` values out of the generated constants module.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from typing import Any
from unittest import mock

from py4gw.gwa3 import constants, uai_const, uai_get_agent

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Plugins"
    / "UtilityAI"
    / "Targeting"
    / "UtilityAI_GetAgent.au3"
)

PLAYER_ID = 900


def _column(name: str) -> int:
    return int(getattr(constants, f"GC_UAI_AGENT_{name}"))


def _agent_info(rows: dict[int, dict[str, Any]]) -> Any:
    """A stand-in for `UAI_GetAgentInfo` that answers from ``{agent id: {column name: value}}``."""

    def accessor(agent_id: Any, column: Any) -> Any:
        for name, value in rows.get(agent_id, {}).items():
            if column == _column(name):
                return value
        return 0

    return accessor


def _player_info(x: float = 0.0, y: float = 0.0, agent_id: int = PLAYER_ID) -> Any:
    def accessor(column: Any) -> Any:
        if column == _column("ID"):
            return agent_id
        if column == _column("X"):
            return x
        if column == _column("Y"):
            return y
        return 0

    return accessor


def _distances(values: dict[int, float]) -> Any:
    return lambda agent_id: values[agent_id]


class SurfaceTests(unittest.TestCase):
    """The module against GwAu3's own declarations, in both directions."""

    def test_every_declared_function_exists_and_nothing_else_is_exported(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(len(declared), 26)

        missing = sorted(name for name in declared if not hasattr(uai_get_agent, name))
        self.assertEqual(missing, [], "declared by GwAu3 and not implemented here")

        unexpected = sorted(set(uai_get_agent.__all__) - declared)
        self.assertEqual(unexpected, [], "exported and not declared by GwAu3")

        for name in uai_get_agent.__all__:
            self.assertTrue(callable(getattr(uai_get_agent, name)), name)

    def test_the_private_helpers_are_kept_out_of_the_surface(self) -> None:
        private = {name for name in uai_get_agent.__all__ if name.startswith("_")}
        self.assertEqual(sorted(private), [], "a private helper is exported")

        for name in ("_GetArmorScore", "_UAI_CountAlliesInRange", "_UAI_BestCoveragePosition",
                     "_UAI_GetBestCorpse"):
            self.assertTrue(callable(getattr(uai_get_agent, name)), name)


class ConvertAgentIDTests(unittest.TestCase):
    def test_it_is_agent_convert_id_under_the_plugins_name(self) -> None:
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", return_value=42) as convert:
            self.assertEqual(uai_get_agent.UAI_ConvertAgentID(-2), 42)
        convert.assert_called_once_with(-2)


class CachedDistanceTests(unittest.TestCase):
    """``$GC_UAI_AGENT_Distance`` is computed the way the cache computes it."""

    def test_it_is_the_player_relative_distance_without_z(self) -> None:
        rows = {7: {"X": 30.0, "Y": 40.0}}
        with mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)
        ):
            self.assertEqual(uai_get_agent._cached_distance(7), 50.0)

    def test_a_negative_offset_is_squared_away(self) -> None:
        rows = {7: {"X": 70.0, "Y": 60.0}}
        with mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetPlayerInfo", _player_info(100.0, 100.0)
        ):
            self.assertEqual(uai_get_agent._cached_distance(7), 50.0)


class FindAgentByPlayerNumberTests(unittest.TestCase):
    def _call(self, player_number: Any) -> int:
        rows = {
            10: {"PlayerNumber": 3, "X": 10.0, "Y": 0.0},
            11: {"PlayerNumber": 4, "X": 5000.0, "Y": 0.0},
            12: {"PlayerNumber": 5, "X": 60.0, "Y": 0.0},
        }
        distances = {10: 10.0, 11: 5000.0, 12: 60.0}
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(distances)
        ):
            return uai_get_agent.UAI_FindAgentByPlayerNumber(player_number, -2, 100)

    def test_a_single_player_number(self) -> None:
        self.assertEqual(self._call(3), 10)

    def test_a_list_of_player_numbers_stops_at_the_first_match(self) -> None:
        self.assertEqual(self._call([5, 3]), 10)

    def test_a_player_number_out_of_range_answers_zero(self) -> None:
        self.assertEqual(self._call(4), 0)

    def test_nothing_matching_answers_zero(self) -> None:
        self.assertEqual(self._call(99), 0)

    def test_the_reference_agent_is_skipped(self) -> None:
        rows = {12: {"PlayerNumber": 5, "X": 60.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: 12), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [12]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances({12: 60.0})
        ):
            self.assertEqual(uai_get_agent.UAI_FindAgentByPlayerNumber(5, 12, 100), 0)


class CountAndRangeTests(unittest.TestCase):
    """The reference point is the *reference agent*, not the player -- the source says so at ``:47``."""

    def _rows(self) -> dict[int, dict[str, Any]]:
        return {
            10: {"X": 100.0, "Y": 0.0},
            11: {"X": 200.0, "Y": 0.0},
            12: {"X": 900.0, "Y": 0.0},
        }

    def _patched(self) -> Any:
        return (
            mock.patch.object(
                uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID if value == -2 else int(value)
            ),
            mock.patch.object(uai_get_agent, "_cached_ids", lambda: [10, 11, 12]),
            mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(self._rows())),
            mock.patch.object(uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0, PLAYER_ID)),
            mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info({10: self._rows()[10]})),
        )

    def test_count_measures_from_the_player_when_the_reference_is_the_player(self) -> None:
        patches = self._patched()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertEqual(uai_get_agent.UAI_CountAgents(-2, 250), 2)

    def test_count_measures_from_the_reference_agent_when_it_is_someone_else(self) -> None:
        patches = self._patched()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        # From agent 10, agent 11 is 100 away and agent 12 is 800 -- so 250 covers only 11.
        self.assertEqual(uai_get_agent.UAI_CountAgents(10, 250), 1)

    def test_in_range_answers_a_boolean(self) -> None:
        patches = self._patched()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertTrue(uai_get_agent.UAI_IsAgentInRange(-2, 250))
        self.assertFalse(uai_get_agent.UAI_IsAgentInRange(-2, 50))


class NearestAndFarthestTests(unittest.TestCase):
    def _call(self, function: Any) -> int:
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12]
        ), mock.patch.object(uai_get_agent, "_cached_distance", _distances({10: 90.0, 11: 20.0, 12: 70.0})):
            return function(-2, 100)

    def test_nearest_is_the_smallest_distance(self) -> None:
        self.assertEqual(self._call(uai_get_agent.UAI_GetNearestAgent), 11)

    def test_farthest_is_the_largest_distance(self) -> None:
        self.assertEqual(self._call(uai_get_agent.UAI_GetFarthestAgent), 10)

    def test_out_of_range_agents_are_not_candidates(self) -> None:
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11]
        ), mock.patch.object(uai_get_agent, "_cached_distance", _distances({10: 90.0, 11: 200.0})):
            self.assertEqual(uai_get_agent.UAI_GetNearestAgent(-2, 100), 10)
            self.assertEqual(uai_get_agent.UAI_GetFarthestAgent(-2, 100), 10)

    def test_the_reference_agent_is_excluded(self) -> None:
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: 11), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11]
        ), mock.patch.object(uai_get_agent, "_cached_distance", _distances({10: 90.0, 11: 20.0})):
            self.assertEqual(uai_get_agent.UAI_GetNearestAgent(11, 100), 10)


class LowestAndHighestTests(unittest.TestCase):
    """``UAI_GetAgentLowest``/``Highest`` do **not** exclude the reference agent -- the source computes
    ``$l_i_RefID`` at ``:177``/``:204`` and never consults it."""

    def _patched(self) -> list[Any]:
        rows = {
            10: {"HP": 300.0},
            11: {"HP": 100.0},
            12: {"HP": 200.0},
        }
        return [
            mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: 11),
            mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 3),
            mock.patch.object(uai_get_agent, "_cached_ids", lambda: [10, 11, 12]),
            mock.patch.object(uai_get_agent, "_cached_distance", _distances({10: 10.0, 11: 20.0, 12: 30.0})),
            mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)),
        ]

    def test_lowest_answers_the_smallest_column_and_may_be_the_reference_agent(self) -> None:
        patches = self._patched()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertEqual(uai_get_agent.UAI_GetAgentLowest(11, 100, _column("HP")), 11)

    def test_highest_answers_the_largest_column(self) -> None:
        patches = self._patched()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertEqual(uai_get_agent.UAI_GetAgentHighest(11, 100, _column("HP")), 10)

    def test_an_empty_cache_answers_zero_before_anything_is_read(self) -> None:
        with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID), mock.patch.object(
            uai_get_agent, "UAI_GetAgentCount", lambda: 0
        ):
            self.assertEqual(uai_get_agent.UAI_GetAgentLowest(-2), 0)
            self.assertEqual(uai_get_agent.UAI_GetAgentHighest(-2), 0)


class BestSingleTargetTests(unittest.TestCase):
    def _call(self, mode: int) -> int:
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = mode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentLowest", return_value=1) as lowest, mock.patch.object(
            uai_get_agent, "UAI_GetAgentHighest", return_value=2
        ) as highest:
            answer = uai_get_agent.UAI_GetBestSingleTarget()
            self.assertEqual(lowest.call_count, 1 if mode == constants.g_i_FinisherMode else 0)
            self.assertEqual(highest.call_count, 1 if mode == constants.g_i_PressureMode else 0)
        return answer

    def test_finisher_mode_takes_the_lowest(self) -> None:
        self.assertEqual(self._call(constants.g_i_FinisherMode), 1)

    def test_pressure_mode_takes_the_highest(self) -> None:
        self.assertEqual(self._call(constants.g_i_PressureMode), 2)

    def test_a_mode_that_is_neither_answers_zero(self) -> None:
        self.assertEqual(self._call(7), 0)

    def test_the_default_is_gwaus_own_one(self) -> None:
        self.assertEqual(uai_const.g_i_FightMode, 1)
        self.assertEqual(uai_const.g_i_FightMode, constants.g_i_PressureMode)


class ArmorScoreTests(unittest.TestCase):
    def _call(self, damage_type: str) -> float:
        with mock.patch.object(uai_get_agent, "UAI_GetElementalArmor", lambda agent: 60), mock.patch.object(
            uai_get_agent, "UAI_GetPhysicalArmor", lambda agent: 80
        ), mock.patch.object(uai_get_agent, "UAI_GetBaseArmor", lambda agent: 100), mock.patch.object(
            uai_get_agent, "UAI_GetDamageMultiplier", lambda armor: armor / 100.0
        ):
            return uai_get_agent._GetArmorScore(1, 200.0, damage_type)

    def test_elemental_family_uses_elemental_armor(self) -> None:
        for damage_type in ("Elemental", "Fire", "Cold", "Lightning", "Earth"):
            self.assertEqual(self._call(damage_type), 200.0 / 0.6, damage_type)

    def test_physical_family_uses_physical_armor(self) -> None:
        for damage_type in ("Physical", "Blunt", "Piercing", "Slashing"):
            self.assertEqual(self._call(damage_type), 200.0 / 0.8, damage_type)

    def test_anything_else_uses_base_armor(self) -> None:
        self.assertEqual(self._call("Chaos"), 200.0 / 1.0)

    def test_the_comparison_is_case_insensitive_as_autoits_is(self) -> None:
        self.assertEqual(self._call("elemental"), self._call("Elemental"))
        self.assertEqual(self._call("PHYSICAL"), self._call("Physical"))


class BestAOETargetTests(unittest.TestCase):
    """Two groups of two, sized the same and priced differently: the mode decides which one wins."""

    ROWS = {
        10: {"X": 0.0, "Y": 0.0, "HP": 100.0},
        11: {"X": 100.0, "Y": 0.0, "HP": 100.0},
        12: {"X": 2000.0, "Y": 0.0, "HP": 500.0},
        13: {"X": 2100.0, "Y": 0.0, "HP": 900.0},
    }
    DISTANCES = {10: 50.0, 11: 60.0, 12: 70.0, 13: 80.0}

    def _call(self, mode: int, **kwargs: Any) -> int:
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = mode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12, 13]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(self.ROWS)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(self.DISTANCES)
        ):
            return uai_get_agent.UAI_GetBestAOETarget(**kwargs)

    def test_finisher_takes_the_group_with_the_lowest_average_hp(self) -> None:
        self.assertIn(self._call(constants.g_i_FinisherMode), (10, 11))

    def test_pressure_takes_the_group_with_the_highest_average_hp(self) -> None:
        self.assertIn(self._call(constants.g_i_PressureMode), (12, 13))

    def test_a_smaller_group_never_beats_a_bigger_one(self) -> None:
        # The pair is 2,100 apart, so each of agents 10/11/12/13 groups only with what is adjacent.
        rows = dict(self.ROWS)
        rows[11] = {"X": 5000.0, "Y": 0.0, "HP": 100.0}
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12, 13]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(self.DISTANCES)
        ):
            # 10 is alone now, and 12/13 are still a pair -- so a pair wins over the singleton,
            # even though the singleton is the lowest HP in the set.
            self.assertIn(uai_get_agent.UAI_GetBestAOETarget(), (12, 13))

    def test_an_ineligible_agent_still_counts_toward_its_neighbours_group(self) -> None:
        # Agent 11 is out of range but adjacent to 10, so 10's group is 2 -- the source's arithmetic
        # (`:258` marks eligibility, `:273-283` counts every in-AOE pair regardless).
        distances = {10: 50.0, 11: 5000.0, 12: 6000.0, 13: 7000.0}
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12, 13]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(self.ROWS)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(distances)
        ):
            self.assertEqual(uai_get_agent.UAI_GetBestAOETarget(range=100), 10)

    def test_an_ineligible_group_cannot_win(self) -> None:
        rows = {
            10: {"X": 0.0, "Y": 0.0, "HP": 100.0},
            11: {"X": 9000.0, "Y": 0.0, "HP": 100.0},
            12: {"X": 2000.0, "Y": 0.0, "HP": 500.0},
            13: {"X": 2100.0, "Y": 0.0, "HP": 900.0},
        }
        distances = {10: 50.0, 11: 5000.0, 12: 5000.0, 13: 5000.0}
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12, 13]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(distances)
        ):
            self.assertEqual(uai_get_agent.UAI_GetBestAOETarget(range=100), 10)

    def test_a_filter_that_matches_nothing_answers_zero(self) -> None:
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11]
        ), mock.patch.object(uai_get_agent, "_ApplyFilters", lambda agent, filters: False):
            self.assertEqual(uai_get_agent.UAI_GetBestAOETarget(custom_filter="UAI_Filter_IsLivingEnemy"), 0)

    def test_an_empty_cache_answers_zero(self) -> None:
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 0):
            self.assertEqual(uai_get_agent.UAI_GetBestAOETarget(), 0)

    def test_the_damage_type_variant_prices_each_agent_once(self) -> None:
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 4), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10, 11, 12, 13]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(self.ROWS)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances(self.DISTANCES)
        ), mock.patch.object(
            uai_get_agent, "_GetArmorScore", side_effect=lambda agent_id, hp, damage_type: float(agent_id)
        ) as score:
            answer = uai_get_agent.UAI_GetBestAOETargetByDamageType()
        self.assertEqual(score.call_count, 4, "the armor score is computed once per agent")
        self.assertIn(answer, (10, 11))

    def test_a_single_target_is_its_own_group(self) -> None:
        rows = {10: {"X": 0.0, "Y": 0.0, "HP": 100.0}}
        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        with mock.patch.object(uai_get_agent, "UAI_GetAgentCount", lambda: 1), mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [10]
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances({10: 50.0})
        ):
            self.assertEqual(uai_get_agent.UAI_GetBestAOETarget(), 10)


class BestTargetByDamageTypeTests(unittest.TestCase):
    def test_finisher_keeps_the_lowest_score_and_pressure_the_highest(self) -> None:
        rows = {10: {"HP": 100.0}, 11: {"HP": 400.0}}
        scores = {10: 100.0 / 0.6, 11: 400.0 / 1.4}
        for mode, expected in ((constants.g_i_FinisherMode, 10), (constants.g_i_PressureMode, 11)):
            original = uai_const.g_i_FightMode
            self.addCleanup(setattr, uai_const, "g_i_FightMode", original)
            uai_const.g_i_FightMode = mode
            with mock.patch.object(uai_get_agent, "Agent_ConvertID", lambda value: PLAYER_ID), mock.patch.object(
                uai_get_agent, "UAI_GetAgentCount", lambda: 2
            ), mock.patch.object(uai_get_agent, "_cached_ids", lambda: [10, 11]), mock.patch.object(
                uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
            ), mock.patch.object(
                uai_get_agent, "_cached_distance", _distances({10: 10.0, 11: 20.0})
            ), mock.patch.object(
                uai_get_agent, "_GetArmorScore", lambda agent_id, hp, damage_type: scores[agent_id]
            ):
                self.assertEqual(uai_get_agent.UAI_GetBestTargetByDamageType(), expected, mode)


class WardPositionTests(unittest.TestCase):
    """The candidates are the points **and** their pairwise midpoints (``:467-478``)."""

    def test_the_midpoint_wins_when_it_covers_both_allies(self) -> None:
        rows = {1: {"X": 0.0, "Y": 0.0}, 2: {"X": 100.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [1, 2]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsLivingAlly", lambda agent: True
        ), mock.patch.object(uai_get_agent, "UAI_Filter_ExcludeMe", lambda agent: True), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ), mock.patch.object(uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)):
            self.assertEqual(uai_get_agent.UAI_GetBestWardPosition(60), [50.0, 0.0, 2])

    def test_no_allies_answers_the_zero_triple(self) -> None:
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [1, 2]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsLivingAlly", lambda agent: False
        ), mock.patch.object(uai_get_agent, "UAI_Filter_ExcludeMe", lambda agent: True), mock.patch.object(
            uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)
        ):
            self.assertEqual(uai_get_agent.UAI_GetBestWardPosition(), [0, 0, 0])

    def test_the_player_is_excluded_from_the_allies_to_cover(self) -> None:
        rows = {1: {"X": 0.0, "Y": 0.0}, 2: {"X": 100.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [1, 2]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsLivingAlly", lambda agent: True
        ), mock.patch.object(
            uai_get_agent, "UAI_Filter_ExcludeMe", lambda agent: agent != 1
        ), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ), mock.patch.object(uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)):
            self.assertEqual(uai_get_agent.UAI_GetBestWardPosition(60), [100.0, 0.0, 1])

    def test_the_offensive_ward_covers_living_enemies_and_does_not_exclude_the_player(self) -> None:
        rows = {1: {"X": 0.0, "Y": 0.0}, 2: {"X": 100.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [1, 2]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsLivingEnemy", lambda agent: True
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)
        ):
            self.assertEqual(uai_get_agent.UAI_GetBestOffensiveWardPosition(60), [50.0, 0.0, 2])

    def test_the_martial_ward_skips_casters(self) -> None:
        rows = {1: {"X": 0.0, "Y": 0.0}, 2: {"X": 100.0, "Y": 0.0}, 3: {"X": 200.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [1, 2, 3]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsLivingEnemy", lambda agent: True
        ), mock.patch.object(
            uai_get_agent, "UAI_IsCaster", lambda agent: agent == 3
        ), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ), mock.patch.object(uai_get_agent, "UAI_GetPlayerInfo", _player_info(0.0, 0.0)):
            self.assertEqual(uai_get_agent.UAI_GetBestMartialEnemyPosition(60), [50.0, 0.0, 2])

    def test_a_tie_resolves_toward_the_anchor(self) -> None:
        # Two candidates cover the same single point; the one nearer the player wins.
        positions = uai_get_agent._UAI_BestCoveragePosition([100.0], [0.0], 1, 60.0, 0.0, 0.0)
        self.assertEqual(positions, [100.0, 0.0, 1])

    def test_a_count_of_zero_answers_before_any_work(self) -> None:
        self.assertEqual(
            uai_get_agent._UAI_BestCoveragePosition([1.0], [1.0], 0, 60.0, 0.0, 0.0), [0, 0, 0]
        )

    def test_count_allies_in_range_counts_the_first_n_points(self) -> None:
        count = uai_get_agent._UAI_CountAlliesInRange([0.0, 30.0, 90.0], [0.0, 0.0, 0.0], 3, 0.0, 0.0, 1600)
        self.assertEqual(count, 2)
        count = uai_get_agent._UAI_CountAlliesInRange([0.0, 30.0, 90.0], [0.0, 0.0, 0.0], 1, 0.0, 0.0, 1600)
        self.assertEqual(count, 1)


class MoveToWardPositionTests(unittest.TestCase):
    def _patched(self, best: list[float], player: tuple[float, float]) -> list[Any]:
        return [
            mock.patch.object(uai_get_agent, "UAI_GetBestWardPosition", return_value=best),
            mock.patch.object(uai_get_agent, "UAI_GetBestOffensiveWardPosition", return_value=best),
            mock.patch.object(
                uai_get_agent,
                "Agent_GetAgentInfo",
                side_effect=lambda agent_id, info: player[0] if info == "X" else player[1],
            ),
            mock.patch.object(uai_get_agent, "Map_Move", return_value=True),
            mock.patch.object(uai_get_agent.time, "sleep", return_value=None),
        ]

    def test_a_position_with_no_coverage_answers_false_without_moving(self) -> None:
        patches = self._patched([0, 0, 0], (0.0, 0.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertFalse(uai_get_agent.UAI_MoveToWardPosition())
        uai_get_agent.Map_Move.assert_not_called()  # type: ignore[attr-defined]

    def test_arrival_answers_true(self) -> None:
        patches = self._patched([500.0, 600.0, 3], (500.0, 600.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertTrue(uai_get_agent.UAI_MoveToWardPosition())
        uai_get_agent.Map_Move.assert_called_once_with(500.0, 600.0, 0)  # type: ignore[attr-defined]

    def test_an_offensive_ward_type_uses_the_offensive_position(self) -> None:
        patches = self._patched([500.0, 600.0, 3], (500.0, 600.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertTrue(
            uai_get_agent.UAI_MoveToWardPosition(
                constants.GC_I_RANGE_AREA, constants.GC_I_UAI_WARDTYPE_OFFENSIVE
            )
        )
        uai_get_agent.UAI_GetBestOffensiveWardPosition.assert_called_once()  # type: ignore[attr-defined]

    def test_a_ward_type_that_is_neither_answers_false(self) -> None:
        patches = self._patched([500.0, 600.0, 3], (500.0, 600.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertFalse(uai_get_agent.UAI_MoveToWardPosition(constants.GC_I_RANGE_AREA, 7))

    def test_the_five_second_bound_is_kept(self) -> None:
        patches = self._patched([500.0, 600.0, 3], (0.0, 0.0))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        with mock.patch.object(uai_get_agent.time, "monotonic", side_effect=[0.0, 10.0]):
            self.assertFalse(uai_get_agent.UAI_MoveToWardPosition())


class CorpseTests(unittest.TestCase):
    def test_the_ally_support_corpse_uses_the_sources_own_filter_string(self) -> None:
        with mock.patch.object(uai_get_agent, "_UAI_GetBestCorpse", side_effect=lambda r, f: (r, f)) as helper:
            self.assertEqual(
                uai_get_agent.UAI_GetBestCorpseForAllySupport(1320), (1320, "UAI_Filter_IsLivingAlly")
            )
        helper.assert_called_once_with(1320, "UAI_Filter_IsLivingAlly")

    def test_the_enemy_pressure_corpse_uses_the_sources_own_filter_string(self) -> None:
        with mock.patch.object(uai_get_agent, "_UAI_GetBestCorpse", side_effect=lambda r, f: (r, f)) as helper:
            self.assertEqual(
                uai_get_agent.UAI_GetBestCorpseForEnemyPressure(1320), (1320, "UAI_Filter_IsLivingEnemy")
            )
        helper.assert_called_once_with(1320, "UAI_Filter_IsLivingEnemy")

    def test_is_corpse_nearest_is_strict_about_a_tie(self) -> None:
        rows = {
            20: {"X": 100.0, "Y": 0.0},
            21: {"X": 100.0, "Y": 0.0},
        }
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [20, 21]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsDeadEnemy", lambda agent: True
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ):
            self.assertTrue(uai_get_agent.UAI_IsCorpseNearest(20, 0.0, 0.0))

    def test_a_closer_corpse_displaces_the_target(self) -> None:
        rows = {
            20: {"X": 100.0, "Y": 0.0},
            21: {"X": 10.0, "Y": 0.0},
        }
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [20, 21]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsDeadEnemy", lambda agent: True
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ):
            self.assertFalse(uai_get_agent.UAI_IsCorpseNearest(20, 0.0, 0.0))

    def test_a_living_agent_is_not_a_corpse(self) -> None:
        rows = {20: {"X": 100.0, "Y": 0.0}, 21: {"X": 10.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [20, 21]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsDeadEnemy", lambda agent: agent == 20
        ), mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ):
            self.assertTrue(uai_get_agent.UAI_IsCorpseNearest(20, 0.0, 0.0))

    def test_the_best_corpse_is_the_one_its_members_surround(self) -> None:
        rows = {
            30: {"X": 0.0, "Y": 0.0},  # corpse with one member near it
            31: {"X": 2000.0, "Y": 0.0},  # corpse with none
            40: {"X": 50.0, "Y": 0.0},  # member
        }
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: [30, 31, 40]), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsDeadEnemy", lambda agent: agent in (30, 31)
        ), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", _agent_info(rows)
        ), mock.patch.object(
            uai_get_agent, "_cached_distance", _distances({30: 100.0, 31: 100.0, 40: 120.0})
        ), mock.patch.object(
            uai_get_agent, "_ApplyFilters", lambda agent, filters: True
        ), mock.patch.object(
            uai_get_agent, "UAI_GetPlayerInfo", lambda column: 4242
        ), mock.patch.object(
            uai_get_agent, "UAI_MoveTowardCorpse", lambda corpse_id: False
        ):
            # Corpse 30 is the nearest one, so the player's own id comes straight back.
            self.assertEqual(uai_get_agent._UAI_GetBestCorpse(1320, "UAI_Filter_IsLivingAlly"), 4242)

    def test_no_corpse_answers_zero(self) -> None:
        with mock.patch.object(uai_get_agent, "_cached_ids", lambda: []), mock.patch.object(
            uai_get_agent, "UAI_Filter_IsDeadEnemy", lambda agent: False
        ):
            self.assertEqual(uai_get_agent._UAI_GetBestCorpse(1320, "UAI_Filter_IsLivingAlly"), 0)

    def test_move_toward_corpse_answers_true_when_the_corpse_is_nearest(self) -> None:
        rows = {20: {"X": 100.0, "Y": 0.0}}
        with mock.patch.object(uai_get_agent, "UAI_GetAgentInfoByID", _agent_info(rows)), mock.patch.object(
            uai_get_agent, "Agent_GetAgentInfo", lambda agent_id, info: 0.0
        ), mock.patch.object(uai_get_agent, "Map_Move", lambda x, y, randomize: True), mock.patch.object(
            uai_get_agent.time, "sleep", lambda seconds: None
        ), mock.patch.object(uai_get_agent, "UAI_IsCorpseNearest", lambda corpse, x, y: False):
            # Never nearest and never close enough: the source's own trailing `Return True` (`:778`).
            self.assertTrue(uai_get_agent.UAI_MoveTowardCorpse(20))


class PlayerHasOtherMesmerHexTests(unittest.TestCase):
    def _call(self, effects: list[int], exclude: int = 99) -> bool:
        with mock.patch.object(uai_get_agent.Player, "GetAgentID", lambda: PLAYER_ID), mock.patch.object(
            uai_get_agent._effect, "get_effects", lambda agent_id: [
                mock.Mock(skill_id=skill_id) for skill_id in effects
            ]
        ), mock.patch.object(
            uai_get_agent,
            "Skill_GetSkillInfo",
            lambda skill_id, info: (
                constants.GC_I_PROFESSION_MESMER if skill_id in (5, 6) else 1
            )
            if info == "Profession"
            else (constants.GC_I_SKILL_TYPE_HEX if skill_id == 5 else 2),
        ):
            return uai_get_agent.UAI_PlayerHasOtherMesmerHex(exclude)

    def test_a_mesmer_hex_is_found(self) -> None:
        self.assertTrue(self._call([5]))

    def test_a_mesmer_non_hex_is_not(self) -> None:
        self.assertFalse(self._call([6]))

    def test_a_non_mesmer_skill_is_not(self) -> None:
        self.assertFalse(self._call([7]))

    def test_the_excluded_skill_is_skipped(self) -> None:
        self.assertFalse(self._call([5], exclude=5))

    def test_no_effects_answers_false(self) -> None:
        self.assertFalse(self._call([]))


class RefusalTests(unittest.TestCase):
    def test_the_condition_count_answers_the_agents_that_carry_conditions(self) -> None:
        """``:619-672``: the walk, the seven-effect count and the two fight-mode scores.

        It refused until `UAI_AgentHasVisibleEffect` was ported; what is asserted here is the source's
        *arithmetic* -- an agent with no count is skipped, Finisher prefers the lowest ``HP / count``
        and Pressure the highest ``HP * count``, and the answer is an agent id (``0`` when none
        qualifies).
        """

        effects = {
            # Agent 11 carries one condition, agent 22 carries three -- `(agent, effect id)` pairs,
            # with the ids the source's own list names (`:623-627`).
            (11, constants.GC_I_EFFECT_ID_DISEASED): True,
            (22, constants.GC_I_EFFECT_ID_BLEEDING): True,
            (22, constants.GC_I_EFFECT_ID_BLINDED): True,
            (22, constants.GC_I_EFFECT_ID_DISEASED): True,
        }
        agents = {11: (0.5, True), 22: (0.5, True)}
        patches = [
            mock.patch.object(uai_get_agent, "_cached_ids", lambda: [11, 22]),
            mock.patch.object(uai_get_agent, "_cached_distance", lambda agent_id: 100.0),
            mock.patch.object(
                uai_get_agent,
                "UAI_GetAgentInfo",
                lambda agent_id, column: (
                    agents[agent_id][1]
                    if column == constants.GC_UAI_AGENT_IsConditioned
                    else agents[agent_id][0]
                ),
            ),
            mock.patch.object(
                uai_get_agent,
                "UAI_AgentHasVisibleEffect",
                lambda agent_id, effect_type, effect_id: effects.get(
                    (agent_id, effect_id), False
                ),
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

        original = uai_const.g_i_FightMode
        self.addCleanup(setattr, uai_const, "g_i_FightMode", original)

        # Finisher: `HP / count` -- 0.5/3 beats 0.5/1, so the *lowest* score wins and 22 takes it.
        uai_const.g_i_FightMode = constants.g_i_FinisherMode
        self.assertEqual(uai_get_agent.UAI_GetBestTargetByConditionCount(), 22)

        # Pressure: `HP * count` -- 1.5 beats 0.5, the highest wins, and 22 takes it again.
        uai_const.g_i_FightMode = constants.g_i_PressureMode
        self.assertEqual(uai_get_agent.UAI_GetBestTargetByConditionCount(), 22)

    def test_an_agent_out_of_range_is_skipped(self) -> None:
        patches = [
            mock.patch.object(uai_get_agent, "_cached_ids", lambda: [11]),
            mock.patch.object(uai_get_agent, "_cached_distance", lambda agent_id: 9000.0),
            mock.patch.object(
                uai_get_agent,
                "UAI_GetAgentInfo",
                lambda agent_id, column: True,
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.assertEqual(uai_get_agent.UAI_GetBestTargetByConditionCount(), 0)

    def test_an_unconditioned_agent_is_skipped_before_any_effect_is_read(self) -> None:
        with mock.patch.object(
            uai_get_agent, "_cached_ids", lambda: [11]
        ), mock.patch.object(
            uai_get_agent, "_cached_distance", lambda agent_id: 100.0
        ), mock.patch.object(
            uai_get_agent, "UAI_GetAgentInfo", lambda agent_id, column: False
        ), mock.patch.object(uai_get_agent, "UAI_AgentHasVisibleEffect") as visible:
            self.assertEqual(uai_get_agent.UAI_GetBestTargetByConditionCount(), 0)
        visible.assert_not_called()


if __name__ == "__main__":
    unittest.main()
