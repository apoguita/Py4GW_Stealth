"""Offline tests for `py4gw/gwa3/uai_filter.py` -- the sixty-four UtilityAI agent predicates.

No client and no elevation. What is being established:

* **the surface is GwAu3's own, all sixty-four of it** -- the module is checked against the source's
  `Func` lines in both directions by name, because a filter set is exactly the kind of thing a missing
  entry hides in;
* the compound predicates keep GwAu3's guard **order** and its exact comparisons -- the loyalty pair
  differs from its sibling in one character (`<= 0` against `> 0`), and the three ``IsLastStrike``
  predicates are one read against three constants;
* the refusals refuse, and each names its own reason rather than a shared one.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from unittest import mock

from py4gw.gwa3 import constants, uai_filter

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Plugins"
    / "UtilityAI"
    / "Targeting"
    / "UtilityAI_AgentFilter.au3"
)


def _columns(**values: object) -> object:
    """A stand-in for `UAI_GetAgentInfo` that answers from a column-name table."""

    def accessor(agent_id: object, column: int) -> object:
        for name, value in values.items():
            if column == getattr(constants, f"GC_UAI_AGENT_{name}"):
                return value
        return 0

    return accessor


class SurfaceTests(unittest.TestCase):
    """The module against GwAu3's own declarations, in both directions."""

    def test_the_surface_is_the_sources_own(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (UAI_Filter_\w+)\(", text))
        implemented = set(uai_filter.__all__)
        self.assertEqual(sorted(declared - implemented), [], "declared and not implemented")
        self.assertEqual(sorted(implemented - declared), [], "implemented and not declared")
        self.assertEqual(len(declared), 64)
        for name in implemented:
            self.assertTrue(callable(getattr(uai_filter, name)), name)


class AllegianceTests(unittest.TestCase):
    """The six living/dead predicates: one shape, three allegiances, two directions."""

    def test_living_enemy_reads_allegiance_health_and_death(self) -> None:
        with mock.patch.object(
            uai_filter,
            "UAI_GetAgentInfo",
            _columns(Allegiance=3, HP=1.0, IsDead=False),
        ):
            self.assertTrue(uai_filter.UAI_Filter_IsLivingEnemy(1))
        with mock.patch.object(
            uai_filter,
            "UAI_GetAgentInfo",
            _columns(Allegiance=1, HP=1.0, IsDead=False),
        ):
            self.assertFalse(uai_filter.UAI_Filter_IsLivingEnemy(1), "an ally is not an enemy")

    def test_the_dead_form_inverts_the_health_test(self) -> None:
        """`<= 0` in the living pair, `> 0` in the dead pair -- one character apart."""

        with mock.patch.object(
            uai_filter,
            "UAI_GetAgentInfo",
            _columns(Allegiance=3, HP=0.0, IsDead=True),
        ):
            self.assertTrue(uai_filter.UAI_Filter_IsDeadEnemy(1))
            self.assertFalse(uai_filter.UAI_Filter_IsLivingEnemy(1))

    def test_each_allegiance_has_its_own_pair(self) -> None:
        cases = {
            "UAI_Filter_IsLivingAlly": 1,
            "UAI_Filter_IsLivingEnemy": 3,
            "UAI_Filter_IsLivingNPC": 6,
        }
        for name, allegiance in cases.items():
            with self.subTest(name=name):
                with mock.patch.object(
                    uai_filter,
                    "UAI_GetAgentInfo",
                    _columns(Allegiance=allegiance, HP=1.0, IsDead=False),
                ):
                    self.assertTrue(getattr(uai_filter, name)(1))
                with mock.patch.object(
                    uai_filter,
                    "UAI_GetAgentInfo",
                    _columns(Allegiance=99, HP=1.0, IsDead=False),
                ):
                    self.assertFalse(getattr(uai_filter, name)(1))


class LastStrikeTests(unittest.TestCase):
    """``:10-29``: one column, three constants, and a two-value form."""

    def test_the_three_constants(self) -> None:
        cases = {
            "UAI_Filter_IsLastStrikeIsLead": 1,
            "UAI_Filter_IsLastStrikeIsOffHand": 2,
            "UAI_Filter_IsLastStrikeIsDual": 3,
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(LastStrike=value)
                ):
                    self.assertTrue(getattr(uai_filter, name)(1))
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(LastStrike=99)
                ):
                    self.assertFalse(getattr(uai_filter, name)(1))

    def test_the_two_value_form(self) -> None:
        for value, expected in ((1, True), (2, True), (3, False), (0, False)):
            with self.subTest(value=value):
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(LastStrike=value)
                ):
                    self.assertIs(uai_filter.UAI_Filter_IsLastStrikeLeadOrOffHand(1), expected)


class HealthFractionTests(unittest.TestCase):
    """``:510-520``: strictly below, strictly above, and half satisfies neither."""

    def test_the_two_bands_do_not_overlap(self) -> None:
        with mock.patch.object(uai_filter, "UAI_GetAgentInfo", _columns(HP=0.5)):
            self.assertFalse(uai_filter.UAI_Filter_IsBelow50HP(1))
            self.assertFalse(uai_filter.UAI_Filter_IsAbove50HP(1))

    def test_the_bands(self) -> None:
        for value, below, above, quarter in (
            (0.1, True, False, True),
            (0.3, True, False, False),
            (0.9, False, True, False),
        ):
            with self.subTest(value=value):
                with mock.patch.object(uai_filter, "UAI_GetAgentInfo", _columns(HP=value)):
                    self.assertIs(uai_filter.UAI_Filter_IsBelow50HP(1), below)
                    self.assertIs(uai_filter.UAI_Filter_IsAbove50HP(1), above)
                    self.assertIs(uai_filter.UAI_Filter_IsBelow25HP(1), quarter)


class NPCProfessionTests(unittest.TestCase):
    """``:184-422``: a player answers False, and the profession comes from the agent."""

    def test_a_player_is_never_one_of_them(self) -> None:
        """The guard is `LoginNumber <> 0` -- a hero is excluded even if its profession matches."""

        with mock.patch.object(
            uai_filter, "UAI_GetAgentInfo", _columns(LoginNumber=42)
        ), mock.patch.object(uai_filter, "UAI_GetAgentProfession", return_value=1):
            self.assertFalse(uai_filter.UAI_Filter_IsWarrior(1))

    def test_an_npc_matches_its_profession(self) -> None:
        cases = {
            "UAI_Filter_IsWarrior": 1,
            "UAI_Filter_IsRanger": 2,
            "UAI_Filter_IsMonk": 3,
            "UAI_Filter_IsNecromancer": 4,
            "UAI_Filter_IsMesmer": 5,
            "UAI_Filter_IsElementalist": 6,
            "UAI_Filter_IsAssassin": 7,
            "UAI_Filter_IsRitualist": 8,
            "UAI_Filter_IsParagon": 9,
            "UAI_Filter_IsDervish": 10,
        }
        for name, profession in cases.items():
            with self.subTest(name=name):
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(LoginNumber=0)
                ), mock.patch.object(
                    uai_filter, "UAI_GetAgentProfession", return_value=profession
                ):
                    self.assertTrue(getattr(uai_filter, name)(1))
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(LoginNumber=0)
                ), mock.patch.object(uai_filter, "UAI_GetAgentProfession", return_value=99):
                    self.assertFalse(getattr(uai_filter, name)(1))


class RefusalTests(unittest.TestCase):
    """Every refusal, and each names its own reason."""

    def test_the_model_state_predicates_read_their_column(self) -> None:
        """They used to refuse through it; the three columns answer the Data module's sets now.

        `UAI_Filter_IsMoving`/`IsAttacking`/`IsIdle` are one `UAI_GetPlayerInfo` read each, and the
        column they read is the one GwAu3's two files disagree about -- answered from the definition
        Reforged Native agrees with (`py4gw/gwa3/uai_agent.py` carries the comparison and the live
        measurement that settled it).
        """

        for name in ("UAI_Filter_IsMoving", "UAI_Filter_IsAttacking", "UAI_Filter_IsIdle"):
            with self.subTest(name=name):
                with mock.patch.object(uai_filter, "_info", lambda agent_id, column: True):
                    self.assertTrue(getattr(uai_filter, name)(1))
                with mock.patch.object(uai_filter, "_info", lambda agent_id, column: False):
                    self.assertFalse(getattr(uai_filter, name)(1))

    def test_the_visible_effect_predicates_ask_the_member_for_their_own_effect_id(self) -> None:
        """Each is one call with ``$GC_I_EFFECT_TYPE_STATUS`` and its own id constant (``:93-117``).

        They used to refuse here, because `UAI_AgentHasVisibleEffect` was not ported; the member now
        walks the agent's own visible-effect list, so what is asserted is the **call** -- the type and
        the id constant, named literally per predicate -- and the boolean it returns.
        """

        for name, effect_id in (
            ("UAI_Filter_IsDiseased", constants.GC_I_EFFECT_ID_DISEASED),
            ("UAI_Filter_IsDazed", constants.GC_I_EFFECT_ID_DAZED),
            ("UAI_Filter_IsWeakness", constants.GC_I_EFFECT_ID_WEAKNESS),
            ("UAI_Filter_IsPoisoned", constants.GC_I_EFFECT_ID_POISONED),
            ("UAI_Filter_IsBlind", constants.GC_I_EFFECT_ID_BLINDED),
            ("UAI_Filter_IsBurning", constants.GC_I_EFFECT_ID_BURNING),
            ("UAI_Filter_IsBleeding", constants.GC_I_EFFECT_ID_BLEEDING),
        ):
            with self.subTest(name=name):
                with mock.patch.object(
                    uai_filter, "UAI_AgentHasVisibleEffect", return_value=True
                ) as visible:
                    self.assertIs(getattr(uai_filter, name)(235), True)
                visible.assert_called_once_with(
                    235, constants.GC_I_EFFECT_TYPE_STATUS, effect_id
                )

                with mock.patch.object(
                    uai_filter, "UAI_AgentHasVisibleEffect", return_value=False
                ):
                    self.assertIs(getattr(uai_filter, name)(235), False)

    def test_the_npc_flag_predicates_name_the_array(self) -> None:
        for name in (
            "UAI_Filter_IsSpirit",
            "UAI_Filter_IsControlledSpirit",
            "UAI_Filter_IsMinion",
            "UAI_Filter_IsControlledMinion",
        ):
            with self.subTest(name=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(uai_filter, name)(1)
                message = str(raised.exception)
                self.assertIn("UtilityAI_AgentFilter.au3", message)
                self.assertIn("py4gw", message)

    def test_the_two_global_readers_name_their_global(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            uai_filter.UAI_Filter_AgentHasMoreHpThanMe(1)
        self.assertIn("$g_i_BestTarget", str(raised.exception))

        with self.assertRaises(NotImplementedError) as raised:
            uai_filter.UAI_Filter_IsNotAvoided(1)
        self.assertIn("$g_v_AvoidPlayerNumbers", str(raised.exception))

    def test_is_not_poisoned_reads_the_effect_word_while_is_poisoned_reads_the_list(self) -> None:
        """Two spellings of one question, two mechanisms in GwAu3, both routed here."""

        with mock.patch.object(uai_filter, "UAI_GetAgentInfo", _columns(IsPoisoned=False)):
            self.assertTrue(uai_filter.UAI_Filter_IsNotPoisoned(1))
        with mock.patch.object(
            uai_filter, "UAI_AgentHasVisibleEffect", return_value=True
        ) as visible:
            self.assertTrue(uai_filter.UAI_Filter_IsPoisoned(1))
        visible.assert_called_once_with(
            1, constants.GC_I_EFFECT_TYPE_STATUS, constants.GC_I_EFFECT_ID_POISONED
        )


class CompoundTests(unittest.TestCase):
    """The one-line predicates and the two-read forms."""

    def test_the_effect_word_predicates_are_one_read(self) -> None:
        # `(column value, expected answer)` -- the two differ for the `Not*` forms, which is exactly
        # what those forms are for.
        cases = {
            "UAI_Filter_IsEnchanted": (True, True),
            "UAI_Filter_IsConditioned": (True, True),
            "UAI_Filter_IsCrippled": (True, True),
            "UAI_Filter_IsDeepWounded": (True, True),
            "UAI_Filter_NotIsDeepWounded": (True, False),
            "UAI_Filter_IsNotDeepWounded": (True, False),
            "UAI_Filter_IsDegenHexed": (True, True),
            "UAI_Filter_IsHexed": (True, True),
            "UAI_Filter_IsWeaponSpelled": (True, True),
            "UAI_Filter_IsKnocked": (True, True),
            "UAI_Filter_IsCasting": (True, True),
        }
        columns = {
            "UAI_Filter_IsEnchanted": "IsEnchanted",
            "UAI_Filter_IsConditioned": "IsConditioned",
            "UAI_Filter_IsCrippled": "IsCrippled",
            "UAI_Filter_IsDeepWounded": "IsDeepWounded",
            "UAI_Filter_NotIsDeepWounded": "IsDeepWounded",
            "UAI_Filter_IsNotDeepWounded": "IsDeepWounded",
            "UAI_Filter_IsDegenHexed": "IsDegenHexed",
            "UAI_Filter_IsHexed": "IsHexed",
            "UAI_Filter_IsWeaponSpelled": "IsWeaponSpelled",
            "UAI_Filter_IsKnocked": "IsKnockedDown",
            "UAI_Filter_IsCasting": "IsCasting",
        }
        for name, (column_value, expected) in cases.items():
            with self.subTest(name=name):
                with mock.patch.object(
                    uai_filter, "UAI_GetAgentInfo", _columns(**{columns[name]: column_value})
                ):
                    self.assertIs(getattr(uai_filter, name)(1), expected)

    def test_the_or_forms_read_both_columns(self) -> None:
        values = {
            constants.GC_UAI_AGENT_IsHexed: False,
            constants.GC_UAI_AGENT_IsEnchanted: False,
            constants.GC_UAI_AGENT_IsConditioned: True,
        }
        with mock.patch.object(
            uai_filter, "UAI_GetAgentInfo", lambda _id, column: values[column]
        ):
            # GwAu3's own spelling of this one has a typo in its name, kept here.
            self.assertTrue(uai_filter.UAI_Filter_IdConditionedOrEnchanted(1))
            self.assertTrue(uai_filter.UAI_Filter_IsHexedOrConditioned(1))
            self.assertFalse(uai_filter.UAI_Filter_IsHexedOrEnchanted(1))

    def test_the_gadget_forms_differ_by_one_test(self) -> None:
        with mock.patch.object(
            uai_filter,
            "UAI_GetAgentInfo",
            _columns(IsItemType=False, IsLivingType=True),
        ):
            # A living agent is not a gadget but does pass the gadget-or-living test.
            self.assertFalse(uai_filter.UAI_Filter_IsGadget(1))
            self.assertTrue(uai_filter.UAI_Filter_IsGadgetOrLiving(1))

    def test_the_boss_and_harbinger_forms(self) -> None:
        with mock.patch.object(
            uai_filter, "UAI_GetAgentInfo", _columns(HasBossGlow=True)
        ):
            self.assertTrue(uai_filter.UAI_Filter_IsBoss(1))
        with mock.patch.object(
            uai_filter, "UAI_GetAgentInfo", _columns(PlayerNumber=5459)
        ):
            self.assertTrue(uai_filter.UAI_Filter_IsHarbingers(1))
        with mock.patch.object(
            uai_filter, "UAI_GetAgentInfo", _columns(PlayerNumber=1234)
        ):
            self.assertFalse(uai_filter.UAI_Filter_IsHarbingers(1))

    def test_exclude_me_compares_against_the_player(self) -> None:
        with mock.patch.object(uai_filter, "UAI_GetPlayerInfo", return_value=235):
            self.assertFalse(uai_filter.UAI_Filter_ExcludeMe(235))
            self.assertTrue(uai_filter.UAI_Filter_ExcludeMe(999))

    def test_the_profession_class_forms_delegate(self) -> None:
        with mock.patch.object(uai_filter, "UAI_IsMelee", return_value=True):
            self.assertTrue(uai_filter.UAI_Filter_IsMelee(1))
        with mock.patch.object(uai_filter, "UAI_IsCaster", return_value=False):
            self.assertFalse(uai_filter.UAI_Filter_IsCaster(1))
            self.assertTrue(uai_filter.UAI_Filter_IsNotCaster(1))
        with mock.patch.object(uai_filter, "UAI_IsRanged", return_value=True):
            self.assertTrue(uai_filter.UAI_Filter_IsRanged(1))


if __name__ == "__main__":
    unittest.main()
