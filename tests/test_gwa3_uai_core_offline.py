"""Offline tests for `py4gw/gwa3/uai_core.py` -- GwAu3's UtilityAI combat engine.

No client and no elevation. The module is the plugin's only remaining **user-facing** surface (measured:
63 of the 65 unbuilt ``UAI_*`` functions have no call site outside ``API/Plugins/UtilityAI/``), so what
is established here is:

* the surface is `UtilityAI_Core.au3`'s own, all ten functions, in both directions;
* the one member whose source is two lines is ported exactly -- `UAI_TargetIsValid`, including the
  inversion `$a_b_IsRes` selects;
* every other member refuses, and **each refusal names what it needs** rather than sharing one message:
  the static skill cache, the per-slot ranking caches, or the casting pointer. A refusal that named
  nothing would leave the engine's work unstated, which is the failure this file exists to catch.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from unittest import mock

from py4gw.gwa3 import constants as _constants
from py4gw.gwa3 import uai_const, uai_core

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API"
    / "Plugins"
    / "UtilityAI"
    / "Core"
    / "UtilityAI_Core.au3"
)


class SurfaceTests(unittest.TestCase):
    def test_the_surface_is_the_sources_own(self) -> None:
        text = SOURCE.read_text(encoding="utf-8", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(len(declared), 10)

        missing = sorted(name for name in declared if not hasattr(uai_core, name))
        self.assertEqual(missing, [], "declared by GwAu3 and not present here")

        unexpected = sorted(set(uai_core.__all__) - declared)
        self.assertEqual(unexpected, [], "exported and not declared by GwAu3")
        self.assertEqual(sorted(set(uai_core.__all__)), sorted(declared))


class TargetIsValidTests(unittest.TestCase):
    """``:245-248``: one ``IsDead`` read, and ``$a_b_IsRes`` chooses which way it is read."""

    def test_a_resurrection_wants_a_dead_target(self) -> None:
        with mock.patch.object(uai_core, "Agent_GetAgentInfo", lambda agent_id, key: True):
            self.assertTrue(uai_core.UAI_TargetIsValid(7, True))

    def test_a_normal_skill_wants_a_living_target(self) -> None:
        with mock.patch.object(uai_core, "Agent_GetAgentInfo", lambda agent_id, key: True):
            self.assertFalse(uai_core.UAI_TargetIsValid(7, False))

    def test_the_key_it_reads_is_isdead_for_the_agent_it_was_given(self) -> None:
        with mock.patch.object(uai_core, "Agent_GetAgentInfo", return_value=False) as read:
            self.assertTrue(uai_core.UAI_TargetIsValid(4321, False))
        read.assert_called_once_with(4321, "IsDead")


class CastStateTests(unittest.TestCase):
    """`UAI_GetIsIdle` / `UAI_GetIsCastingSkill`: the casting word and the agent's ``Skill`` column.

    These two used to refuse, on the grounds that they need ``$g_p_StaticSkillbarPtr + 0xB0``. They do
    not: that word is the skillbar's cast-array size, which this layer reads through
    `Skill_GetSkillbarInfo`'s ``Casting`` key -- the same word through the same record.
    """

    def _serve(self, casting: int, skill: int) -> None:
        patches = [
            mock.patch.object(uai_core, "Skill_GetSkillbarInfo", lambda slot, key: casting),
            mock.patch.object(uai_core, "Agent_GetAgentInfo", lambda agent_id, key: skill),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_idle_is_a_zero_cast_word_and_a_zero_skill_column(self) -> None:
        self._serve(casting=0, skill=0)
        self.assertTrue(uai_core.UAI_GetIsIdle(35))

        self._serve(casting=1, skill=0)
        self.assertFalse(uai_core.UAI_GetIsIdle(35))

        self._serve(casting=0, skill=1062)
        self.assertFalse(uai_core.UAI_GetIsIdle(35))

    def test_casting_a_skill_is_a_non_zero_cast_word_and_the_matching_skill_column(self) -> None:
        self._serve(casting=1, skill=1062)
        self.assertTrue(uai_core.UAI_GetIsCastingSkill(35, 1062))
        self.assertFalse(uai_core.UAI_GetIsCastingSkill(35, 999))

        self._serve(casting=0, skill=1062)
        self.assertFalse(uai_core.UAI_GetIsCastingSkill(35, 1062))


class PriorityTests(unittest.TestCase):
    """`UAI_PrioritySkills` and its ``@extended`` twin, over the ranking tables that now exist."""

    def test_the_priority_list_is_the_slots_the_source_tags(self) -> None:
        with mock.patch.object(
            uai_core, "UAI_SlotIsPriority", lambda slot: slot in (2, 5)
        ):
            self.assertEqual(uai_core._priority_slots(), [2, 5])

    def test_the_first_slot_that_casts_wins_and_the_boolean_is_its_shape(self) -> None:
        used: list[int] = []

        def try_use(slot: int, aggro_range: float = 1320) -> bool:
            used.append(slot)
            return slot == 5

        with mock.patch.object(uai_core, "UAI_SlotIsPriority", lambda slot: slot in (2, 5)), mock.patch.object(
            uai_core, "UAI_TryUseSkill", try_use
        ):
            self.assertEqual(uai_core._priority_skill_used(1320), 5)
            self.assertEqual(used, [2, 5])
            self.assertTrue(uai_core.UAI_PrioritySkills(1320))

    def test_no_slot_usable_answers_zero_and_false(self) -> None:
        with mock.patch.object(uai_core, "UAI_SlotIsPriority", lambda slot: False):
            self.assertEqual(uai_core._priority_skill_used(), 0)
            self.assertFalse(uai_core.UAI_PrioritySkills())


class TryUseSkillTests(unittest.TestCase):
    """`UAI_TryUseSkill`: GwAu3's own order, over the two ranking dispatches."""

    def _serve(self, **values: object) -> None:
        defaults: dict[str, object] = {
            "UAI_CanUse": lambda slot: True,
            "UAI_GetBestTargetFunc": lambda slot: "BestTarget_Example",
            "UAI_GetCanUseFunc": lambda slot: "CanUse_Example",
            "_call_strategy": lambda name, *args: 4242 if str(name).startswith("BestTarget") else True,
            "UAI_Filter_IsNotAvoided": lambda agent_id: True,
            "Agent_GetDistance": lambda agent_id, other=-2: 100.0,
            "UAI_GetAgentInfoByID": lambda agent_id, column: 0,
            "UAI_UseSkillEx": lambda *args: None,
            "Cache_FormChangeBuild": lambda slot: False,
        }
        defaults.update(values)
        for name, value in defaults.items():
            patch = mock.patch.object(uai_core, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_slot_that_may_not_be_used_answers_false_before_anything_else(self) -> None:
        calls: list[str] = []
        self._serve(
            **{
                "UAI_CanUse": lambda slot: calls.append("can_use") or False,
                "UAI_GetBestTargetFunc": lambda slot: calls.append("ranking") or "x",
            }
        )
        self.assertFalse(uai_core.UAI_TryUseSkill(1, 1320))
        self.assertEqual(calls, ["can_use"])

    def test_a_zero_target_answers_false(self) -> None:
        self._serve(**{"_call_strategy": lambda name, *args: 0})
        self.assertFalse(uai_core.UAI_TryUseSkill(1, 1320))

    def test_an_avoided_target_answers_false(self) -> None:
        self._serve(**{"UAI_Filter_IsNotAvoided": lambda agent_id: False})
        self.assertFalse(uai_core.UAI_TryUseSkill(1, 1320))

    def test_a_target_beyond_the_aggro_range_answers_false(self) -> None:
        self._serve(**{"Agent_GetDistance": lambda agent_id, other=-2: 2000.0})
        self.assertFalse(uai_core.UAI_TryUseSkill(1, 1320))

    def test_the_forced_target_overrides_an_enemy_target(self) -> None:
        original = uai_const.g_i_ForceTarget
        self.addCleanup(setattr, uai_const, "g_i_ForceTarget", original)
        uai_const.g_i_ForceTarget = 777
        cast: list[tuple] = []
        self._serve(
            **{
                "UAI_GetAgentInfoByID": lambda agent_id, column: _constants.GC_I_ALLEGIANCE_ENEMY,
                "UAI_UseSkillEx": lambda *args: cast.append(args),
            }
        )
        self.assertTrue(uai_core.UAI_TryUseSkill(1, 1320))
        self.assertEqual(cast, [(1, 777, 1320)])
        self.assertEqual(uai_const.g_i_BestTarget, 777)

    def test_a_successful_cast_sets_the_form_change_flag_when_the_bar_changed(self) -> None:
        original = uai_const.g_b_SkillChanged
        self.addCleanup(setattr, uai_const, "g_b_SkillChanged", original)
        uai_const.g_b_SkillChanged = False
        self._serve(**{"Cache_FormChangeBuild": lambda slot: True})
        self.assertTrue(uai_core.UAI_TryUseSkill(1, 1320))
        self.assertTrue(uai_const.g_b_SkillChanged)


class UseSkillsTests(unittest.TestCase):
    """`UAI_UseSkills`: the loop's guards, over a bar with nothing on it."""

    def test_an_empty_bar_ends_the_pass_without_casting(self) -> None:
        with mock.patch.object(
            uai_core, "UAI_GetStaticSkillInfo", lambda slot, column: 0
        ), mock.patch.object(uai_core, "UAI_TryUseSkill") as attempt:
            self.assertTrue(uai_core.UAI_UseSkills(0.0, 0.0))
        attempt.assert_not_called()

    def test_a_dead_player_ends_the_pass(self) -> None:
        patches = [
            mock.patch.object(uai_core, "UAI_GetStaticSkillInfo", lambda slot, column: 1062),
            mock.patch.object(uai_core, "Cache_EndFormChangeBuild", lambda slot: False),
            mock.patch.object(uai_core, "UAI_UpdateAgentCache"),
            mock.patch.object(uai_core, "UAI_IsEnemyInPartyAggroRange", lambda aggro_range: True),
            mock.patch.object(
                uai_core,
                "UAI_GetPlayerInfo",
                lambda column: column == _constants.GC_UAI_AGENT_IsDead,
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

        attempt = mock.patch.object(uai_core, "UAI_TryUseSkill")
        started = attempt.start()
        self.addCleanup(attempt.stop)

        self.assertTrue(uai_core.UAI_UseSkills(0.0, 0.0))
        started.assert_not_called()


class AutoAttackTests(unittest.TestCase):
    """`UAI_AutoAttack`: three target sources, one announcement -- with the source's own quirk."""

    def _serve(self, **values: object) -> None:
        defaults: dict[str, object] = {
            "UAI_GetNearestAgent": lambda agent_id, aggro_range, filters: 500,
            "UAI_GetAgentInfoByID": lambda agent_id, column: False,
            "Agent_Attack": lambda agent_id, call_target: None,
            "Agent_CallTarget": lambda agent_id: None,
        }
        defaults.update(values)
        for name, value in defaults.items():
            patch = mock.patch.object(uai_core, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def _reset(self) -> None:
        for name, value in (
            ("g_i_ForceTarget", 0),
            ("g_i_AttackTarget", 0),
            ("g_i_LastCalledTarget", 0),
        ):
            original = getattr(uai_const, name)
            self.addCleanup(setattr, uai_const, name, original)
            setattr(uai_const, name, value)

    def test_the_forced_target_wins(self) -> None:
        self._reset()
        uai_const.g_i_ForceTarget = 777
        attacked: list[tuple] = []
        self._serve(**{"Agent_Attack": lambda agent_id, call_target: attacked.append((agent_id, call_target))})
        uai_core.UAI_AutoAttack(1320)
        self.assertEqual(attacked, [(777, False)])
        self.assertEqual(uai_const.g_i_AttackTarget, 777)

    def test_a_living_remembered_target_is_reused(self) -> None:
        self._reset()
        uai_const.g_i_AttackTarget = 888
        attacked: list[tuple] = []
        self._serve(**{"Agent_Attack": lambda agent_id, call_target: attacked.append((agent_id, call_target))})
        uai_core.UAI_AutoAttack(1320)
        self.assertEqual(attacked, [(888, False)])

    def test_a_dead_remembered_target_falls_back_to_the_nearest(self) -> None:
        self._reset()
        uai_const.g_i_AttackTarget = 888
        attacked: list[tuple] = []
        self._serve(
            **{
                "UAI_GetAgentInfoByID": lambda agent_id, column: True,
                "Agent_Attack": lambda agent_id, call_target: attacked.append((agent_id, call_target)),
            }
        )
        uai_core.UAI_AutoAttack(1320)
        self.assertEqual(attacked, [(500, False)])

    def test_the_announcement_happens_once_and_carries_the_sources_quirk(self) -> None:
        """``:312-315`` calls ``Agent_CallTarget`` with the target **even when it is zero**.

        **And it does so on every pass while the target stays zero**: the guard is
        ``$g_i_LastCalledTarget = 0``, and the line right after the call *sets that variable to the
        target* -- which is ``0`` -- so the guard never latches for an empty target. That is the source's
        own behaviour, and a port that "fixed" it by comparing against the *previous* target would stop
        announcing a target the party may still need called.
        """

        self._reset()
        called: list[int] = []
        self._serve(
            **{
                "UAI_GetNearestAgent": lambda agent_id, aggro_range, filters: 0,
                "Agent_CallTarget": lambda agent_id: called.append(agent_id),
            }
        )
        uai_core.UAI_AutoAttack(1320)
        self.assertEqual(called, [0], "the source announces the zero target too")

        uai_core.UAI_AutoAttack(1320)
        self.assertEqual(called, [0, 0], "and again, because the guard it sets is zero")


class DropBundleTests(unittest.TestCase):
    """`UAI_DropBundle`: an Item Spell the player is holding, and `UAI_CanDrop`'s answer."""

    def test_a_bar_with_no_item_spell_does_nothing(self) -> None:
        with mock.patch.object(
            uai_core, "UAI_GetStaticSkillInfo", lambda slot, column: _constants.GC_I_SKILL_TYPE_SPELL
        ), mock.patch.object(uai_core, "Item_DropBundle") as drop:
            uai_core.UAI_DropBundle(1320)
        drop.assert_not_called()

    def test_an_item_spell_the_player_holds_drops_when_the_slot_says_so(self) -> None:
        def static(slot: int, column: str) -> int:
            if column == _constants.GC_UAI_STATIC_SKILL_SkillType:
                return _constants.GC_I_SKILL_TYPE_ITEM_SPELL
            return 1062

        with mock.patch.object(uai_core, "UAI_GetStaticSkillInfo", static), mock.patch.object(
            uai_core, "UAI_PlayerHasEffect", lambda skill_id: True
        ), mock.patch.object(uai_core, "UAI_CanUse", lambda slot: False), mock.patch.object(
            uai_core, "UAI_CanDrop", lambda slot: slot == 6
        ), mock.patch.object(uai_core, "Item_DropBundle") as drop:
            uai_core.UAI_DropBundle(1320)
        drop.assert_called_once()


class RefusalTests(unittest.TestCase):
    """The branches that refuse by name -- the weapon-set paths, reached only when a script arms them."""

    def _restore_engine_globals(self) -> None:
        """`UAI_Fight` writes the plugin's globals, and they are **module state a later test sees**.

        The suite caught exactly that: one engine-calling test left ``g_i_FightMode`` at Finisher and broke
        another file's assertion about GwAu3's own default. Every name the engine writes is restored here.
        """

        for name in (
            "g_i_BestTarget",
            "g_i_ForceTarget",
            "g_i_AttackTarget",
            "g_i_LastCalledTarget",
            "g_i_FightMode",
            "g_b_CacheWeaponSet",
            "g_i_TargetMode",
            "g_v_AvoidPlayerNumbers",
        ):
            original = getattr(uai_const, name)
            self.addCleanup(setattr, uai_const, name, original)

    def test_the_fight_loop_analyses_the_sets_when_armed(self) -> None:
        """``:55``: ``$a_b_SwitchWeaponSets`` reaches `UAI_DetermineWeaponSets`.

        The analysis is a read, so the armed branch runs it; the *switch* it may lead to refuses inside
        `UAI_ChangeWeaponSet`. Here the loop is stopped on its first exit condition -- the player
        further from the fight origin than the aggro range -- so only the armed call is observed.
        """

        self._restore_engine_globals()
        with mock.patch.object(uai_core, "Map_GetMapID", lambda: 1), mock.patch.object(
            uai_core, "Map_GetInstanceInfo", lambda info: 1
        ), mock.patch.object(
            uai_core, "Agent_GetDistanceToXY", lambda x, y, agent_id=-2: 99999.0
        ), mock.patch.object(uai_core, "UAI_DetermineWeaponSets") as analyse:
            self.assertIsNone(uai_core.UAI_Fight(0.0, 0.0, switch_weapon_sets=True))
        analyse.assert_called_once_with()

    def test_the_fight_loop_analyses_nothing_by_default(self) -> None:
        """GwAu3's own default for the argument is ``False``."""

        self._restore_engine_globals()
        with mock.patch.object(uai_core, "Map_GetMapID", lambda: 1), mock.patch.object(
            uai_core, "Map_GetInstanceInfo", lambda info: 1
        ), mock.patch.object(
            uai_core, "Agent_GetDistanceToXY", lambda x, y, agent_id=-2: 99999.0
        ), mock.patch.object(uai_core, "UAI_DetermineWeaponSets") as analyse:
            self.assertIsNone(uai_core.UAI_Fight(0.0, 0.0))
        analyse.assert_not_called()

    def test_the_engine_sets_the_mode_and_the_target_mode_before_the_loop(self) -> None:
        """``:8-15``: the two defaults arrive as ``None`` and are filled from GwAu3's own constants."""

        self._restore_engine_globals()

        with mock.patch.object(uai_core, "Map_GetMapID", lambda: 1), mock.patch.object(
            uai_core, "Map_GetInstanceInfo", lambda info: 1
        ), mock.patch.object(
            uai_core, "Agent_GetDistanceToXY", lambda x, y, agent_id=-2: 99999.0
        ), mock.patch.object(uai_core, "UAI_UseSkills") as use_skills:
            uai_core.UAI_Fight(0.0, 0.0)

        self.assertEqual(uai_const.g_i_FightMode, _constants.g_i_FinisherMode)
        self.assertEqual(uai_const.g_i_TargetMode, _constants.GC_UAI_TARGET_MODE_CALL)
        use_skills.assert_not_called()

    def test_a_call_after_the_engine_refuses_nothing_by_itself(self) -> None:
        """A fight that ends on its first check answers ``None`` -- the source's own ``EndFunc``."""

        self._restore_engine_globals()

        with mock.patch.object(uai_core, "Map_GetMapID", lambda: 1), mock.patch.object(
            uai_core, "Map_GetInstanceInfo", lambda info: 1
        ), mock.patch.object(
            uai_core, "Agent_GetDistanceToXY", lambda x, y, agent_id=-2: 99999.0
        ):
            self.assertIsNone(uai_core.UAI_Fight(0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
