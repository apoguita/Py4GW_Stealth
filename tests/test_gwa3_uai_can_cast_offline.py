"""Offline tests for `py4gw/gwa3/uai_can_cast.py` -- GwAu3's cast gate.

No client. Every read the bodies make is one of this layer's own members, so a test stubs them and checks
GwAu3's **decisions**, which is where its build knowledge lives:

* `UAI_CanAutoAttack`'s four punishing hexes and its damage pricing against the player's hit points;
* `UAI_IsCastSensible`: a non-self skill is always sensible, an enchantment is tested by the effect's
  remaining time, and a stance/glyph/preparation only by whether the *current* one is the same skill;
* `UAI_CanUse`'s order and its arithmetic: the adrenaline branch answering before any energy is priced,
  the cooldown, the sacrifice and Masochism health costs, the overcast ceiling at half maximum energy, the
  type- and attribute-gated energy modifiers, and the clamp -- **minimum one, zero only under Way of the
  Empty Palm**;
* `UAI_CanDrop`'s fifteen item-spell algorithms, one ``Case`` at a time;
* and the private `_UAI_EffectEndingSoon`, kept under the source's own spelling.
"""

from __future__ import annotations

import pathlib
import re
import unittest
from typing import Any
from unittest import mock

from py4gw.gwa3 import constants, uai_can_cast, uai_effects

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Core" / "UtilityAI_CanCast.au3"
)


class _World:
    """A stand-in for everything the module reads, with per-test overrides."""

    def __init__(self, **values: Any) -> None:
        self.static: dict[str, Any] = {
            "SkillID": 1062,
            "SkillType": constants.GC_I_SKILL_TYPE_SPELL,
            "Target": constants.GC_I_SKILL_TARGET_ENEMY,
            "Adrenaline": 0,
            "EnergyCost": 5,
            "Attribute": 0,
            "WeaponReq": 0,
            "Combo": 0,
            "Activation": 1,
        }
        self.dynamic: dict[str, Any] = {"Adrenaline": 0, "IsRecharged": True}
        self.player: dict[str, Any] = {
            "IsHexed": False,
            "IsConditioned": False,
            "CurrentHP": 500,
            "MaxHP": 500,
            "CurrentEnergy": 50,
            "MaxEnergy": 50,
            "Overcast": 0,
        }
        self.effects: set[int] = set()
        self.scales: dict[int, float] = {}
        self.skill_info: dict[str, Any] = {"HealthCost": 0, "Overcast": 0}
        self.static.update(values.pop("static", {}))
        self.dynamic.update(values.pop("dynamic", {}))
        self.player.update(values.pop("player", {}))
        self.skill_info.update(values.pop("skill_info", {}))
        self.__dict__.update(values)

    def serve(self, test: unittest.TestCase) -> None:
        patches = [
            mock.patch.object(
                uai_can_cast, "_static", lambda slot, column: self.static.get(column, 0)
            ),
            mock.patch.object(
                uai_can_cast, "_dynamic", lambda slot, column: self.dynamic.get(column, 0)
            ),
            mock.patch.object(
                uai_can_cast,
                "UAI_GetPlayerInfo",
                lambda column: self.player[
                    {
                        constants.GC_UAI_AGENT_IsHexed: "IsHexed",
                        constants.GC_UAI_AGENT_IsConditioned: "IsConditioned",
                        constants.GC_UAI_AGENT_CurrentHP: "CurrentHP",
                        constants.GC_UAI_AGENT_MaxHP: "MaxHP",
                        constants.GC_UAI_AGENT_CurrentEnergy: "CurrentEnergy",
                        constants.GC_UAI_AGENT_MaxEnergy: "MaxEnergy",
                        constants.GC_UAI_AGENT_Overcast: "Overcast",
                    }[column]
                ],
            ),
            mock.patch.object(
                uai_can_cast, "UAI_PlayerHasEffect", lambda skill_id: skill_id in self.effects
            ),
            mock.patch.object(
                uai_can_cast, "UAI_GetPlayerEffectInfo", lambda skill_id, column: self.scales.get(int(skill_id), 0)
            ),
            mock.patch.object(
                uai_can_cast,
                "Skill_GetSkillInfo",
                lambda skill_id, key="": self.skill_info.get(key, 0),
            ),
            mock.patch.object(
                uai_effects,
                "_player_effect_of_type",
                lambda skill_type: self.type_skill_id.get(skill_type, 0),
            ),
        ]
        for patch in patches:
            patch.start()
            test.addCleanup(patch.stop)

    type_skill_id: dict[int, int] = {}


class SurfaceTests(unittest.TestCase):
    def test_the_surface_is_the_sources_own(self) -> None:
        """Four public functions and one private helper, **all under the source's own names**.

        ``_UAI_EffectEndingSoon`` is a ``Func`` of that file like the other four, and this layer keeps
        an underscore-prefixed GwAu3 name as written -- `_GetArmorScore`, `_UAI_BestCoveragePosition`
        and `_UAI_CountAlliesInRange` in `uai_get_agent.py` are the same rule. (It was spelled
        ``_effect_ending_soon`` until this was checked, which made the layer's private names
        inconsistent in one direction only.)
        """

        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        declared = set(re.findall(r"(?m)^Func (\w+)\(", text))
        self.assertEqual(sorted(declared - {"_UAI_EffectEndingSoon"}), sorted(uai_can_cast.__all__))
        self.assertTrue(callable(uai_can_cast._UAI_EffectEndingSoon))

    def test_every_constant_it_names_is_declared_in_the_constants_module(self) -> None:
        """The transcription uses the **declared** spelling, not the plugin's mixed-case reference.

        GwAu3's plugin files name constants case-insensitively; Python does not, so a mixed-case name that
        only matches in AutoIt would be an `AttributeError` here. This is the check that found thirty of
        them the first time this module was written.
        """

        text = (
            pathlib.Path(__file__).resolve().parent.parent / "py4gw" / "gwa3" / "uai_can_cast.py"
        ).read_text(encoding="utf-8")
        used = sorted(set(re.findall(r"_constants\.(\w+)", text)))
        missing = [name for name in used if not hasattr(constants, name)]
        self.assertEqual(missing, [], "mixed-case constant names that do not resolve")


class CanAutoAttackTests(unittest.TestCase):
    def test_a_hex_free_player_can_attack(self) -> None:
        _World(player={"IsHexed": False}).serve(self)
        self.assertTrue(uai_can_cast.UAI_CanAutoAttack())

    def test_each_punishing_hex_answers_false(self) -> None:
        for skill_id in (
            constants.GC_I_SKILL_ID_SPIRIT_SHACKLES,
            constants.GC_I_SKILL_ID_INEPTITUDE,
            constants.GC_I_SKILL_ID_CLUMSINESS,
            constants.GC_I_SKILL_ID_WANDERING_EYE,
        ):
            with self.subTest(skill_id=skill_id):
                _World(player={"IsHexed": True}, effects={skill_id}).serve(self)
                self.assertFalse(uai_can_cast.UAI_CanAutoAttack())

    def test_reflected_damage_is_priced_against_current_hp_plus_fifteen_percent(self) -> None:
        empathy = constants.GC_I_SKILL_ID_EMPATHY
        world = _World(player={"IsHexed": True, "CurrentHP": 100, "MaxHP": 500})
        world.effects = {empathy}
        world.scales = {empathy: 200.0}
        world.serve(self)
        # 200 > 100 + 75 -> the reflected damage outweighs the hit points -> attacking is not safe.
        self.assertFalse(uai_can_cast.UAI_CanAutoAttack())

        world = _World(player={"IsHexed": True, "CurrentHP": 100, "MaxHP": 500})
        world.effects = {empathy}
        world.scales = {empathy: 175.0}
        world.serve(self)
        # 175 is *not* greater than 175 -- the source's comparison is strict, so this is safe.
        self.assertTrue(uai_can_cast.UAI_CanAutoAttack())

    def test_all_three_reflect_hexes_add_up(self) -> None:
        world = _World(player={"IsHexed": True, "CurrentHP": 100, "MaxHP": 500})
        world.effects = {
            constants.GC_I_SKILL_ID_EMPATHY,
            constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT,
            constants.GC_I_SKILL_ID_SPOIL_VICTOR,
        }
        world.scales = {skill_id: 70.0 for skill_id in world.effects}
        world.serve(self)
        # 210 > 175 -> unsafe.
        self.assertFalse(uai_can_cast.UAI_CanAutoAttack())


class IsCastSensibleTests(unittest.TestCase):
    def test_a_skill_that_is_not_self_targeted_is_always_sensible(self) -> None:
        _World(static={"Target": constants.GC_I_SKILL_TARGET_ENEMY}).serve(self)
        self.assertTrue(uai_can_cast.UAI_IsCastSensible(1))

    def test_an_enchantment_is_tested_by_the_effects_remaining_time(self) -> None:
        world = _World(
            static={
                "Target": constants.GC_I_SKILL_TARGET_SELF,
                "SkillType": constants.GC_I_SKILL_TYPE_ENCHANTMENT,
                "Activation": 1,
            }
        )
        world.scales = {1062: 1500.0}
        world.serve(self)
        # 1500 <= 1 * 1000 + 1000 -> ending soon -> sensible to re-cast.
        self.assertTrue(uai_can_cast.UAI_IsCastSensible(1))

        world = _World(
            static={
                "Target": constants.GC_I_SKILL_TARGET_SELF,
                "SkillType": constants.GC_I_SKILL_TYPE_ENCHANTMENT,
                "Activation": 1,
            }
        )
        world.scales = {1062: 9000.0}
        world.serve(self)
        self.assertFalse(uai_can_cast.UAI_IsCastSensible(1))

    def test_a_stance_is_a_waste_unless_the_current_one_is_the_same_skill(self) -> None:
        stance = constants.GC_I_SKILL_TYPE_STANCE
        world = _World(
            static={
                "Target": constants.GC_I_SKILL_TARGET_SELF,
                "SkillType": stance,
                "SkillID": 1062,
            }
        )
        world.type_skill_id = {stance: 0}
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_IsCastSensible(1))

        world = _World(
            static={
                "Target": constants.GC_I_SKILL_TARGET_SELF,
                "SkillType": stance,
                "SkillID": 1062,
            }
        )
        world.type_skill_id = {stance: 999}
        world.serve(self)
        self.assertFalse(uai_can_cast.UAI_IsCastSensible(1))

        world = _World(
            static={
                "Target": constants.GC_I_SKILL_TARGET_SELF,
                "SkillType": stance,
                "SkillID": 1062,
                "Activation": 1,
            }
        )
        world.type_skill_id = {stance: 1062}
        world.scales = {1062: 500.0}
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_IsCastSensible(1))


class CanUseTests(unittest.TestCase):
    def test_a_skill_whose_adrenaline_is_not_ready_answers_false(self) -> None:
        _World(static={"Adrenaline": 5}, dynamic={"Adrenaline": 2}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

    def test_a_skill_whose_adrenaline_is_ready_answers_true_without_pricing_energy(self) -> None:
        world = _World(static={"Adrenaline": 5}, dynamic={"Adrenaline": 5}, player={"CurrentEnergy": 0})
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

    def test_a_recharging_slot_answers_false(self) -> None:
        _World(dynamic={"IsRecharged": False}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

    def test_a_sacrifice_cost_is_paid_in_hit_points_and_refuses_when_it_would_kill(self) -> None:
        world = _World(
            player={"CurrentHP": 40, "MaxHP": 500},
            skill_info={"HealthCost": 10},
        )
        world.serve(self)
        # 10% of 500 = 50 > 40 -> refuse.
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

        world = _World(
            player={"CurrentHP": 100, "MaxHP": 500},
            skill_info={"HealthCost": 10},
        )
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

    def test_masochism_adds_five_percent_of_maximum_health_to_any_spell(self) -> None:
        world = _World(player={"CurrentHP": 50, "MaxHP": 500})
        world.effects = {constants.GC_I_SKILL_ID_MASOCHISM}
        world.serve(self)
        # 5% of 500 = 25, and 50 > 25 -- so this still casts.
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

        world = _World(player={"CurrentHP": 20, "MaxHP": 500})
        world.effects = {constants.GC_I_SKILL_ID_MASOCHISM}
        world.serve(self)
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

    def test_overcast_refuses_at_half_of_maximum_energy(self) -> None:
        world = _World(player={"Overcast": 40, "MaxEnergy": 50}, skill_info={"Overcast": 10})
        world.serve(self)
        # 40 + 10 >= 25 -> refuse.
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

        world = _World(player={"Overcast": 0, "MaxEnergy": 50}, skill_info={"Overcast": 10})
        world.effects = {constants.GC_I_SKILL_ID_GLYPH_OF_ENERGY}
        world.serve(self)
        # Glyph of Energy zeroes the cost -> 0 >= 25 is false -> allowed.
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

    def test_the_energy_cost_is_clamped_to_one_and_only_the_empty_palm_zeroes_it(self) -> None:
        # A 5-energy spell with every reduction in play still costs one.
        world = _World(
            static={"EnergyCost": 5, "SkillType": constants.GC_I_SKILL_TYPE_SPELL},
            player={"CurrentEnergy": 1},
        )
        world.effects = {constants.GC_I_SKILL_ID_ENERGIZING_WIND}
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

        world = _World(
            static={"EnergyCost": 5, "SkillType": constants.GC_I_SKILL_TYPE_SPELL},
            player={"CurrentEnergy": 0},
        )
        world.effects = {constants.GC_I_SKILL_ID_ENERGIZING_WIND}
        world.serve(self)
        # The clamp floors the cost at one, so no energy is not enough.
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

        world = _World(
            static={
                "EnergyCost": 5,
                "SkillType": constants.GC_I_SKILL_TYPE_SPELL,
                "Combo": constants.GC_I_SKILL_COMBO_DUAL_ATTACK,
            },
            player={"CurrentEnergy": 0},
        )
        world.effects = {constants.GC_I_SKILL_ID_WAY_OF_THE_EMPTY_PALM}
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

    def test_a_type_gated_modifier_only_applies_to_its_own_type(self) -> None:
        # Natures Renewal doubles a hex's cost; for a spell it must do nothing.
        world = _World(
            static={"EnergyCost": 5, "SkillType": constants.GC_I_SKILL_TYPE_HEX},
            player={"CurrentEnergy": 9},
        )
        world.effects = {constants.GC_I_SKILL_ID_NATURES_RENEWAL}
        world.serve(self)
        self.assertFalse(uai_can_cast.UAI_CanUse(1))

        world = _World(
            static={"EnergyCost": 5, "SkillType": constants.GC_I_SKILL_TYPE_SPELL},
            player={"CurrentEnergy": 9},
        )
        world.effects = {constants.GC_I_SKILL_ID_NATURES_RENEWAL}
        world.serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

    def test_no_effect_and_enough_energy_casts(self) -> None:
        _World(static={"EnergyCost": 10}, player={"CurrentEnergy": 10}).serve(self)
        self.assertTrue(uai_can_cast.UAI_CanUse(1))

        _World(static={"EnergyCost": 10}, player={"CurrentEnergy": 9}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanUse(1))


class CanDropTests(unittest.TestCase):
    """The fifteen item-spell algorithms (``UtilityAI_CanCast.au3:158-376``).

    Each case is checked against the evidence it uses, and the two that need no client at all -- the
    energy and health thresholds, and the five spells the source never drops -- are checked directly.
    """

    def test_an_unknown_skill_answers_false(self) -> None:
        _World(static={"SkillID": 1}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanDrop(1))

    def test_the_five_item_spells_the_source_never_drops(self) -> None:
        for skill_id in (
            constants.GC_I_SKILL_ID_VOCAL_WAS_SOGOLON,
            constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI,
            constants.GC_I_SKILL_ID_VENGEFUL_WAS_KHANHEI,
            constants.GC_I_SKILL_ID_TRANQUIL_WAS_TANASEN,
            constants.GC_I_SKILL_ID_MIGHTY_WAS_VORIZUN,
        ):
            with self.subTest(skill_id=skill_id):
                _World(static={"SkillID": skill_id}).serve(self)
                self.assertFalse(uai_can_cast.UAI_CanDrop(1))

    def test_the_energy_item_spell_drops_below_a_quarter_or_below_fifteen(self) -> None:
        skill = constants.GC_I_SKILL_ID_ENERGETIC_WAS_LEE_SA
        for current, maximum, expected in ((10, 50, True), (20, 50, False), (14, 100, True), (30, 100, False)):
            with self.subTest(current=current, maximum=maximum):
                _World(
                    static={"SkillID": skill},
                    player={"CurrentEnergy": current, "MaxEnergy": maximum},
                ).serve(self)
                self.assertEqual(uai_can_cast.UAI_CanDrop(1), expected)

    def test_the_healing_item_spell_drops_below_half_health(self) -> None:
        skill = constants.GC_I_SKILL_ID_GENEROUS_WAS_TSUNGRAI
        _World(static={"SkillID": skill}, player={"CurrentHP": 200, "MaxHP": 500}).serve(self)
        self.assertTrue(uai_can_cast.UAI_CanDrop(1))

        _World(static={"SkillID": skill}, player={"CurrentHP": 300, "MaxHP": 500}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanDrop(1))

    def test_the_condition_item_spell_is_the_players_own_condition(self) -> None:
        skill = constants.GC_I_SKILL_ID_RESILIENT_WAS_XIKO
        _World(static={"SkillID": skill}, player={"IsConditioned": True}).serve(self)
        self.assertTrue(uai_can_cast.UAI_CanDrop(1))

        _World(static={"SkillID": skill}, player={"IsConditioned": False}).serve(self)
        self.assertFalse(uai_can_cast.UAI_CanDrop(1))

    def test_a_ritualist_hex_still_recharging_answers_false(self) -> None:
        """`Anguished Was Lingwah` drops only when every Ritualist hex on the bar is spent.

        The stub answers for **every** slot from one table -- the slot being asked for is the item spell
        itself (its ``SkillID``), and slot 2 is a Ritualist hex whose recharge state is what the case
        tests.
        """

        lingwah = constants.GC_I_SKILL_ID_ANGUISHED_WAS_LINGWAH
        ritualist_hex = {
            "SkillType": constants.GC_I_SKILL_TYPE_HEX,
            "Profession": constants.GC_I_PROFESSION_RITUALIST,
        }
        slots = {1: {"SkillID": lingwah}, 2: ritualist_hex}

        def static(slot: Any, column: str) -> Any:
            return slots.get(int(slot), {}).get(column, 0)

        _World().serve(self)
        with mock.patch.object(uai_can_cast, "_static", static), mock.patch.object(
            uai_can_cast, "_dynamic", lambda slot, column: True
        ):
            # The hex is recharged, so the item spell is held back.
            self.assertFalse(uai_can_cast.UAI_CanDrop(1))

        with mock.patch.object(uai_can_cast, "_static", static), mock.patch.object(
            uai_can_cast, "_dynamic", lambda slot, column: False
        ):
            # Nothing is recharged, so there is a Ritualist hex to wait for -- and the answer is
            # "there is one", which is what the source returns (`:172`).
            self.assertTrue(uai_can_cast.UAI_CanDrop(1))

    def test_a_bar_with_no_ritualist_hex_answers_false(self) -> None:
        lingwah = constants.GC_I_SKILL_ID_ANGUISHED_WAS_LINGWAH
        slots = {
            1: {"SkillID": lingwah},
            2: {"SkillType": constants.GC_I_SKILL_TYPE_SPELL, "Profession": 0},
        }

        def static(slot: Any, column: str) -> Any:
            return slots.get(int(slot), {}).get(column, 0)

        _World().serve(self)
        with mock.patch.object(uai_can_cast, "_static", static), mock.patch.object(
            uai_can_cast, "_dynamic", lambda slot, column: True
        ):
            self.assertFalse(uai_can_cast.UAI_CanDrop(1))


if __name__ == "__main__":
    unittest.main()
