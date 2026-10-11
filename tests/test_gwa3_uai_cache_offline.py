"""Offline tests for `py4gw/gwa3/uai_cache.py` -- GwAu3's engine refresh calls.

No client. What is established:

* the surface is `Cache/UtilityAI_Cache.au3`'s own six functions;
* `Cache_SkillBar`'s guard answers ``False`` outside an explorable area **before anything else runs**, and
  answers ``True`` otherwise -- with the one armed branch (`$g_b_CacheWeaponSet`) calling
  `UAI_DetermineWeaponSets` and the disarmed default calling nothing;
* the two form-change members answer the source's own lists: the three blessings refresh and answer
  ``True``, the thirteen form-strike skills answer ``False``, and anything else refreshes and answers
  ``True`` -- its inversion of the blessing member;
* `UAI_UpdateAgentCache`/`UAI_UpdatePlayerCache` are NOT APPLICABLE: they answer ``None`` and read
  nothing, which is the documented substitution for the tables this layer does not keep;
* `UAI_ResetRuntime` returns the seven globals to the values their own files declare -- the six in
  `UtilityAI_Const.au3` and the feeder-enchantment timestamp `UtilityAI_EffectsCache.au3:51` declares;
* and `Map_GetInstanceInfo` -- the snippet `data_map` now carries, which `Cache_SkillBar` gates on --
  answers the source's one word and its three comparisons.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from unittest import mock

from py4gw.gwa3 import constants, data_map, uai_cache, uai_const, uai_effects

CACHE_SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Cache" / "UtilityAI_Cache.au3"
)
MAP_SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external" / "GwAu3" / "API" / "Modules" / "Data" / "GwAu3_Data_Map.au3"
)


class SurfaceTests(unittest.TestCase):
    def test_the_surface_is_the_sources_own(self) -> None:
        text = CACHE_SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(sorted(declared), sorted(uai_cache.__all__))
        self.assertEqual(len(uai_cache.__all__), 6)

    def test_the_map_instance_snippet_is_the_sources_own(self) -> None:
        text = MAP_SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        self.assertIn("Map_GetInstanceInfo", set(re.findall(r"(?m)^Func (\w+)\(", text)))
        self.assertIn("Map_GetInstanceInfo", data_map.__all__)


class CacheSkillBarTests(unittest.TestCase):
    def test_outside_an_explorable_area_it_answers_false_without_refreshing(self) -> None:
        with mock.patch.object(data_map, "Map_GetInstanceInfo", return_value=False), mock.patch.object(
            uai_cache, "UAI_CacheSkillBar"
        ) as refresh, mock.patch.object(uai_cache, "Map_GetInstanceInfo", return_value=False):
            self.assertFalse(uai_cache.Cache_SkillBar())
        refresh.assert_not_called()

    def test_in_an_explorable_area_it_refreshes_and_answers_true(self) -> None:
        original = uai_const.g_b_CacheWeaponSet
        self.addCleanup(setattr, uai_const, "g_b_CacheWeaponSet", original)
        uai_const.g_b_CacheWeaponSet = False
        with mock.patch.object(uai_cache, "Map_GetInstanceInfo", return_value=True), mock.patch.object(
            uai_cache, "UAI_CacheSkillBar"
        ) as refresh:
            self.assertTrue(uai_cache.Cache_SkillBar())
        refresh.assert_called_once()

    def test_an_armed_weapon_set_switch_analyses_the_sets(self) -> None:
        """The default path is untouched; the armed path analyses the sets (`:15`).

        ``If $g_b_CacheWeaponSet Then UAI_DetermineWeaponSets()`` is a **read** -- four sets out of the
        client's inventory struct -- so the branch runs here, and what refuses is the switch that
        analysis may later ask for, inside `UAI_ChangeWeaponSet`.
        """

        original = uai_const.g_b_CacheWeaponSet
        self.addCleanup(setattr, uai_const, "g_b_CacheWeaponSet", original)
        uai_const.g_b_CacheWeaponSet = True
        with mock.patch.object(uai_cache, "Map_GetInstanceInfo", return_value=True), mock.patch.object(
            uai_cache, "UAI_CacheSkillBar"
        ), mock.patch.object(uai_cache, "UAI_DetermineWeaponSets") as analyse:
            self.assertTrue(uai_cache.Cache_SkillBar())
        analyse.assert_called_once_with()

    def test_a_disarmed_weapon_set_switch_analyses_nothing(self) -> None:
        """GwAu3's default: the global is false, so the analysis is not reached at all."""

        original = uai_const.g_b_CacheWeaponSet
        self.addCleanup(setattr, uai_const, "g_b_CacheWeaponSet", original)
        uai_const.g_b_CacheWeaponSet = False
        with mock.patch.object(uai_cache, "Map_GetInstanceInfo", return_value=True), mock.patch.object(
            uai_cache, "UAI_CacheSkillBar"
        ), mock.patch.object(uai_cache, "UAI_DetermineWeaponSets") as analyse:
            self.assertTrue(uai_cache.Cache_SkillBar())
        analyse.assert_not_called()


class FormChangeTests(unittest.TestCase):
    def _slot(self, skill_id: int) -> None:
        patches = [
            mock.patch.object(uai_cache, "UAI_GetStaticSkillInfo", lambda slot, column: skill_id),
            mock.patch.object(uai_cache, "UAI_CacheSkillBar"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_blessing_refreshes_and_answers_true(self) -> None:
        for skill_id in (
            constants.GC_I_SKILL_ID_URSAN_BLESSING,
            constants.GC_I_SKILL_ID_VOLFEN_BLESSING,
            constants.GC_I_SKILL_ID_RAVEN_BLESSING,
        ):
            with self.subTest(skill_id=skill_id):
                self._slot(skill_id)
                self.assertTrue(uai_cache.Cache_FormChangeBuild(1))

    def test_a_skill_that_is_not_a_blessing_answers_false(self) -> None:
        self._slot(constants.GC_I_SKILL_ID_HEALING_SIGNET)
        self.assertFalse(uai_cache.Cache_FormChangeBuild(1))

    def test_a_form_strike_answers_false_without_refreshing(self) -> None:
        self._slot(constants.GC_I_SKILL_ID_VOLFEN_CLAW)
        with mock.patch.object(uai_cache, "UAI_CacheSkillBar") as refresh:
            self.assertFalse(uai_cache.Cache_EndFormChangeBuild(1))
        refresh.assert_not_called()

    def test_anything_else_refreshes_and_answers_true(self) -> None:
        self._slot(constants.GC_I_SKILL_ID_HEALING_SIGNET)
        with mock.patch.object(uai_cache, "UAI_CacheSkillBar") as refresh:
            self.assertTrue(uai_cache.Cache_EndFormChangeBuild(1))
        refresh.assert_called_once()

    def test_the_strike_list_is_the_sources_own_thirteen(self) -> None:
        """The list is transcribed, so its size is asserted against the source's own `Case` lines."""

        text = CACHE_SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        block = text[text.index("Func Cache_EndFormChangeBuild") : text.index("Func UAI_UpdateAgentCache")]
        cases = re.findall(r"\$GC_I_SKILL_ID_(\w+)", block)
        self.assertEqual(len(cases), 13)
        self.assertEqual(len(uai_cache._FORM_STRIKE_SKILLS), 13)


class NotApplicableTests(unittest.TestCase):
    def test_the_two_update_members_answer_none_and_read_nothing(self) -> None:
        with mock.patch.object(uai_cache, "UAI_CacheSkillBar", side_effect=AssertionError("read")), mock.patch.object(
            uai_cache, "UAI_GetStaticSkillInfo", side_effect=AssertionError("read")
        ):
            self.assertIsNone(uai_cache.UAI_UpdateAgentCache(1320))
            self.assertIsNone(uai_cache.UAI_UpdatePlayerCache())

    def test_the_runtime_reset_returns_the_seven_globals(self) -> None:
        for name in (
            "g_i_BestTarget",
            "g_i_ForceTarget",
            "g_i_AttackTarget",
            "g_i_LastCalledTarget",
        ):
            setattr(uai_const, name, 4242)
        uai_const.g_b_SkillChanged = True
        uai_const.g_b_CanUseSkill = False
        self.addCleanup(setattr, uai_const, "g_b_SkillChanged", False)
        self.addCleanup(setattr, uai_const, "g_b_CanUseSkill", True)

        uai_cache.UAI_ResetRuntime()

        self.assertEqual(
            (
                uai_const.g_i_BestTarget,
                uai_const.g_i_ForceTarget,
                uai_const.g_i_AttackTarget,
                uai_const.g_i_LastCalledTarget,
            ),
            (0, 0, 0, 0),
        )
        self.assertFalse(uai_const.g_b_SkillChanged)
        self.assertTrue(uai_const.g_b_CanUseSkill)

    def test_the_runtime_reset_also_zeroes_the_feeder_enchantment_timestamp(self) -> None:
        """``$g_i_LastFeederEnchTimestamp = 0`` (``UtilityAI_Cache.au3:72``).

        The global is declared in ``UtilityAI_EffectsCache.au3:51`` rather than beside the others, so it
        lives in `py4gw/gwa3/uai_effects.py` -- and this line is what makes `UAI_GetFeederEnchOnTop`
        report the same enchantment again after a reset.
        """

        original = uai_effects.g_i_LastFeederEnchTimestamp
        self.addCleanup(setattr, uai_effects, "g_i_LastFeederEnchTimestamp", original)
        uai_effects.g_i_LastFeederEnchTimestamp = 4242

        uai_cache.UAI_ResetRuntime()

        self.assertEqual(uai_effects.g_i_LastFeederEnchTimestamp, 0)


class MapInstanceInfoTests(unittest.TestCase):
    def _serve(self, instance_type: int) -> None:
        patch = mock.patch("py4gw.map.Map.GetInstanceType", lambda: instance_type)
        patch.start()
        self.addCleanup(patch.stop)

    def test_type_is_the_word_and_the_three_flags_are_its_comparisons(self) -> None:
        for instance_type, expected in ((0, "IsOutpost"), (1, "IsExplorable"), (2, "IsLoading")):
            with self.subTest(instance_type=instance_type):
                self._serve(instance_type)
                self.assertEqual(data_map.Map_GetInstanceInfo("Type"), instance_type)
                for key in ("IsOutpost", "IsExplorable", "IsLoading"):
                    with self.subTest(key=key):
                        self.assertEqual(
                            data_map.Map_GetInstanceInfo(key), key == expected
                        )

    def test_the_guards_answer_zero(self) -> None:
        self._serve(1)
        self.assertEqual(data_map.Map_GetInstanceInfo(""), 0)
        self.assertEqual(data_map.Map_GetInstanceInfo("NoSuchKey"), 0)


if __name__ == "__main__":
    unittest.main()
