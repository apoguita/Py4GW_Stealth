"""Offline tests for `py4gw/gwa3/uai_weaponsets.py` -- GwAu3's four weapon sets.

No client and no elevation. What is established here is the file's own arithmetic and its own tables:

* the surface is all **eighteen** functions ``Equipment/UtilityAI_WeaponSets.au3`` declares, which the
  test reads out of the source;
* the analysis -- `UAI_SaveWeaponSetFromMemory` through `UAI_SearchModsInArray` -- scores a set out of
  its mod bytes, with the source's own weights, and fills the ten best-set trackers from it;
* the string searches are **case-insensitive**, because AutoIt's ``StringInStr`` and ``StringReplace``
  are, and a mod that has been found is struck out of the working string so a later row cannot match
  the same bytes again;
* the decision members answer the source's own values: the weapon-requirement switch, the nine
  situation names, the hysteresis thresholds and the "first set that has the property" rule for the
  three boolean trackers;
* `UAI_ChangeWeaponSet` reaches the **refused** enqueue and says so, while its
  already-on-this-set quick check means a caller that asks for the set it is on pays nothing;
* and `_D` -- the plugin's debug helper, which this file calls 41 times -- is a no-op with the
  switch in the state the source declares.
"""

from __future__ import annotations

import copy
import pathlib
import re
import unittest
from unittest import mock

from py4gw.gwa3 import constants, uai_const, uai_utils, uai_weaponsets

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API" / "Plugins" / "UtilityAI" / "Equipment" / "UtilityAI_WeaponSets.au3"
)

_TRACKERS = (
    "g_ai_High_Hp_Set",
    "g_ai_High_Energy_Set",
    "g_ai_Best_Offensive_Set",
    "g_ai_Best_Defensive_Set",
    "g_ai_Best_Casting_Set",
    "g_ai_Best_Enchant_Set",
    "g_ai_Best_Ranged_Set",
    "g_ai_Best_Vampiric_Set",
    "g_ai_Best_Zealous_Set",
)


class _Item:
    """A stand-in for an item record: only the fields the weapon-set file reads."""

    def __init__(self, item_id: int, item_type: int, mod_struct: str = "0x") -> None:
        self.item_id = item_id
        self.item_type = item_type
        self.mod_struct = mod_struct


class WeaponSetTestCase(unittest.TestCase):
    """Restores the plugin's mutable state, because the analysis writes into `uai_const`."""

    def setUp(self) -> None:
        sets = copy.deepcopy(uai_const.g_a2D_WeaponSets)
        mods = copy.deepcopy(uai_const.g_as3_Weapon_Mods)
        trackers = {name: list(getattr(uai_const, name)) for name in _TRACKERS}
        flags = (
            uai_const.g_b_InDefensiveMode,
            uai_const.g_b_InLowEnergyMode,
            uai_const.g_b_UAI_Debug,
        )
        self.addCleanup(self._restore, sets, mods, trackers, flags)

    @staticmethod
    def _restore(sets: list, mods: list, trackers: dict, flags: tuple) -> None:
        for row, saved in zip(uai_const.g_a2D_WeaponSets, sets):
            row[:] = saved
        for plane, saved_plane in zip(uai_const.g_as3_Weapon_Mods, mods):
            for row, saved_row in zip(plane, saved_plane):
                row[:] = saved_row
        for name, saved in trackers.items():
            getattr(uai_const, name)[:] = saved
        (
            uai_const.g_b_InDefensiveMode,
            uai_const.g_b_InLowEnergyMode,
            uai_const.g_b_UAI_Debug,
        ) = flags

    # -- the fixtures the analysis is driven with ------------------------------------------

    def _patch_data(self, weapon: _Item | None, offhand: _Item | None, set_index: int = 0) -> None:
        """The two inventory pointers and the field reads the analysis makes through them.

        ``Item_GetModStruct`` is keyed by **item id**, because that is what the source hands it
        (``:186`` passes ``$a_i_ItemId``, not the record).
        """

        info = {
            f"WeaponSet{set_index}WeaponPtr": weapon,
            f"WeaponSet{set_index}OffhandPtr": offhand,
        }
        mods = {
            item.item_id: item.mod_struct
            for item in (weapon, offhand)
            if isinstance(item, _Item)
        }
        self._patchers = [
            mock.patch.object(
                uai_weaponsets, "Item_GetInventoryInfo", lambda key: info.get(key)
            ),
            mock.patch.object(
                uai_weaponsets,
                "Item_GetItemInfoByPtr",
                lambda record, field: {
                    "ItemID": record.item_id,
                    "ItemType": record.item_type,
                }[field],
            ),
            mock.patch.object(
                uai_weaponsets, "Item_GetModStruct", lambda item_id: mods.get(int(item_id), "")
            ),
        ]
        for patcher in self._patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _row(self, index: int = 0) -> list:
        return uai_const.g_a2D_WeaponSets[index]


class SourceSurfaceTests(unittest.TestCase):
    def test_the_module_exports_every_function_the_source_declares(self) -> None:
        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        declared = sorted(set(re.findall(r"(?m)^Func (\w+)\(", text)))
        self.assertEqual(declared, sorted(uai_weaponsets.__all__))
        self.assertEqual(len(uai_weaponsets.__all__), 18)

    def test_the_debug_helper_is_the_one_this_file_calls(self) -> None:
        """``_D`` is declared in ``UtilityAI_Utils.au3``, so it is ported in `uai_utils`."""

        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        # 37 at the start of a line and 4 more behind an `If ... Then`, which is how the source
        # writes the four extra summary lines at the end of `UAI_DetermineWeaponSets`.
        self.assertEqual(len(re.findall(r"(?m)^\s*_D\(", text)), 37)
        self.assertEqual(len(re.findall(r"_D\(", text)), 41)
        self.assertTrue(callable(uai_utils._D))
        self.assertFalse(uai_const.g_b_UAI_Debug)

    def test_the_debug_helper_does_nothing_while_the_switch_is_off(self) -> None:
        """``If $g_b_UAI_Debug Then _D(" " & $msg)`` -- with the switch off, nothing at all."""

        self.assertIsNone(uai_utils._D("anything"))

    def test_the_debug_helper_recurses_when_the_switch_is_on(self) -> None:
        """The source's own body calls ``_D`` again, so the message never reaches a printer.

        Ported as written: the flag is the check the source makes, and the recursive call is its
        next line. Python ends the same recursion with ``RecursionError`` where AutoIt ends it with
        its own stack.
        """

        uai_const.g_b_UAI_Debug = True
        try:
            with self.assertRaises(RecursionError):
                uai_utils._D("x")
        finally:
            uai_const.g_b_UAI_Debug = False


class TableLookupTests(unittest.TestCase):
    """The five pure table functions: no client, no state."""

    def test_two_handed_weapons_are_the_sources_five(self) -> None:
        for item_type in (
            constants.GC_I_TYPE_DAGGERS,
            constants.GC_I_TYPE_HAMMER,
            constants.GC_I_TYPE_SCYTHE,
            constants.GC_I_TYPE_BOW,
            constants.GC_I_TYPE_STAFF,
        ):
            with self.subTest(item_type=item_type):
                self.assertTrue(uai_weaponsets.UAI_IsTwoHandedWeapon(item_type))
        for item_type in (constants.GC_I_TYPE_SWORD, constants.GC_I_TYPE_WAND, 0):
            with self.subTest(item_type=item_type):
                self.assertFalse(uai_weaponsets.UAI_IsTwoHandedWeapon(item_type))

    def test_ranged_weapons_are_the_sources_four_and_not_the_two_handed_list(self) -> None:
        for item_type in (
            constants.GC_I_TYPE_BOW,
            constants.GC_I_TYPE_SPEAR,
            constants.GC_I_TYPE_WAND,
            constants.GC_I_TYPE_STAFF,
        ):
            with self.subTest(item_type=item_type):
                self.assertTrue(uai_weaponsets.UAI_IsRangedWeapon(item_type))
        # A spear is ranged and single-handed; a hammer is two-handed and melee.
        self.assertTrue(uai_weaponsets.UAI_IsRangedWeapon(constants.GC_I_TYPE_SPEAR))
        self.assertFalse(uai_weaponsets.UAI_IsTwoHandedWeapon(constants.GC_I_TYPE_SPEAR))
        self.assertTrue(uai_weaponsets.UAI_IsTwoHandedWeapon(constants.GC_I_TYPE_HAMMER))
        self.assertFalse(uai_weaponsets.UAI_IsRangedWeapon(constants.GC_I_TYPE_HAMMER))

    def test_the_weapon_type_names_are_the_sources_own(self) -> None:
        self.assertEqual(uai_weaponsets.UAI_GetWeaponTypeName(constants.GC_I_TYPE_AXE), "Axe")
        self.assertEqual(uai_weaponsets.UAI_GetWeaponTypeName(constants.GC_I_TYPE_DAGGERS), "Daggers")
        self.assertEqual(uai_weaponsets.UAI_GetWeaponTypeName(constants.GC_I_TYPE_SCYTHE), "Scythe")
        self.assertEqual(uai_weaponsets.UAI_GetWeaponTypeName(99), "Unknown (99)")

    def test_the_offhand_type_names_are_the_sources_own(self) -> None:
        self.assertEqual(uai_weaponsets.UAI_GetOffhandTypeName(constants.GC_I_TYPE_OFFHAND), "Focus")
        self.assertEqual(uai_weaponsets.UAI_GetOffhandTypeName(constants.GC_I_TYPE_SHIELD), "Shield")
        self.assertEqual(uai_weaponsets.UAI_GetOffhandTypeName(0), "Empty")
        self.assertEqual(uai_weaponsets.UAI_GetOffhandTypeName(7), "Unknown (7)")

    def test_a_weapon_requirement_bit_maps_to_the_item_type_the_source_maps_it_to(self) -> None:
        expected = {
            1: constants.GC_I_TYPE_AXE,
            2: constants.GC_I_TYPE_BOW,
            8: constants.GC_I_TYPE_DAGGERS,
            16: constants.GC_I_TYPE_HAMMER,
            32: constants.GC_I_TYPE_SCYTHE,
            64: constants.GC_I_TYPE_SPEAR,
            128: constants.GC_I_TYPE_SWORD,
        }
        for requirement, item_type in expected.items():
            with self.subTest(requirement=requirement):
                self.assertEqual(
                    uai_weaponsets.UAI_WeaponReqToItemType(requirement), item_type
                )
        for requirement in (0, 3, 256):
            with self.subTest(requirement=requirement):
                self.assertEqual(uai_weaponsets.UAI_WeaponReqToItemType(requirement), 0)


class ExtractBonusTests(unittest.TestCase):
    """The two regex readers, against the effects the mod tables actually carry."""

    def test_a_health_pattern_is_read_from_either_spelling(self) -> None:
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("Health +30"), 30)
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("+30 HP"), 30)
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("+45 HP while Enchanted"), 45)
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("+60 HP while Hexed"), 60)

    def test_a_health_pattern_that_is_not_there_answers_zero(self) -> None:
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("Armor +5"), 0)
        self.assertEqual(uai_weaponsets.UAI_ExtractHPBonus("Bleeding +33%"), 0)

    def test_an_energy_pattern_is_read_and_its_absence_answers_zero(self) -> None:
        self.assertEqual(uai_weaponsets.UAI_ExtractEnergyBonus("Energy +5"), 5)
        self.assertEqual(uai_weaponsets.UAI_ExtractEnergyBonus("Energy +15 (-1 energy regen)"), 15)
        self.assertEqual(uai_weaponsets.UAI_ExtractEnergyBonus("Health +30"), 0)

    def test_every_row_of_every_mod_table_is_read_without_an_error(self) -> None:
        """The two readers are handed all 298 effect strings the source carries."""

        total = 0
        for name in dir(uai_const):
            if not name.startswith("g_as2_"):
                continue
            for row in getattr(uai_const, name):
                total += 1
                self.assertIsInstance(uai_weaponsets.UAI_ExtractHPBonus(row[1]), int)
                self.assertIsInstance(uai_weaponsets.UAI_ExtractEnergyBonus(row[1]), int)
        self.assertEqual(total, 298)


class SearchModsInArrayTests(WeaponSetTestCase):
    """`UAI_SearchModsInArray`: the search, the strike-out and the weights."""

    def _search(self, table: str, mod_struct: str, finding: int = 0, new: str = "") -> tuple:
        return uai_weaponsets.UAI_SearchModsInArray(
            getattr(uai_const, table), mod_struct, new, finding, 1, 1
        )

    def test_a_condition_mod_scores_five_on_the_offensive_score(self) -> None:
        new, finding = self._search("g_as2_AxeUpgrade", "0xDE016824")
        self.assertEqual(finding, 1)
        self.assertEqual(new, "0x")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Barbed")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore], 5)

    def test_the_search_finds_an_upper_case_pattern_in_a_lower_case_string(self) -> None:
        """AutoIt's ``StringInStr`` is case-insensitive; the port's search is too."""

        _new, finding = self._search("g_as2_AxeUpgrade", "0xde016824")
        self.assertEqual(finding, 1)
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Barbed")

    def test_a_mod_already_found_is_not_found_again(self) -> None:
        """The strike-out is what stops the same bytes matching a second row.

        The second search is handed the **original** string again -- as
        ``UAI_FindAndSaveModFromMemory`` does for every table it searches -- with the remaining string
        the first call produced, and the mod is behind it: nothing is found and the remaining string is
        unchanged.
        """

        new, finding = self._search("g_as2_AxeUpgrade", "0xDE016824")
        self.assertEqual(new, "0x")
        again, finding = uai_weaponsets.UAI_SearchModsInArray(
            uai_const.g_as2_AxeUpgrade, "0xDE016824", new, finding, 1, 1
        )
        self.assertEqual(finding, 1)
        self.assertEqual(again, "0x")

    def test_the_sundering_mod_takes_the_heaviest_offensive_weight(self) -> None:
        _new, finding = self._search("g_as2_AxeUpgrade", "0x1414F823")
        self.assertEqual(finding, 1)
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Sundering")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore], 20)

    def test_vampiric_and_zealous_set_their_flags_and_add_to_the_offensive_score(self) -> None:
        _new, finding = self._search("g_as2_AxeUpgrade", "0x00032825")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Vampiric (+3)")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_HasVampiric], 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore], 15)

        self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore] = 0
        _new, finding = self._search("g_as2_AxeUpgrade", "0x01001825")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Zealous")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_HasZealous], 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore], 10)

    def test_a_fortitude_mod_adds_health_to_both_the_hp_and_the_defensive_score(self) -> None:
        _new, finding = self._search("g_as2_AxeUpgrade", "0x001E4823")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Axe Grip of Fortitude")
        self.assertEqual(finding, 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_MaxHP], 30)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_DefensiveScore], 30)

    def test_a_focus_fortitude_mod_adds_energy(self) -> None:
        """``Staff Head Insightful`` is ``Energy +5``; the focus fortitude is ``Health +30``."""

        _new, finding = self._search("g_as2_StaffWandUpgrade", "0x0500D822")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Staff Head Insightful")
        self.assertEqual(finding, 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_MaxEnergy], 5)

        _new, finding = self._search("g_as2_FocusUpgrade", "0x001E4823")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Focus Core of Fortitude")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_MaxHP], 30)

    def test_the_casting_weights_are_the_sources_own(self) -> None:
        for pattern, weight in (
            ("0x02500140828", 20),  # Staff Head Adept, HCT20
            ("0x000A0822", 10),  # Staff Head Swift, HCT10
            ("0x00142828", 20),  # Wand Wrapping of Quickening, HSR20
            ("0x000AA823", 10),  # Wand Wrapping of Memory, HSR10
        ):
            with self.subTest(pattern=pattern):
                self._row()[constants.GC_UAI_WEAPONSET_CastingScore] = 0
                self._search("g_as2_StaffWandUpgrade", pattern)
                self.assertEqual(
                    self._row()[constants.GC_UAI_WEAPONSET_CastingScore], weight
                )

    def test_an_enchanting_mod_scores_twenty_on_the_enchant_score(self) -> None:
        _new, finding = self._search("g_as2_AxeUpgrade", "0x1400B822")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Axe Grip of Enchanting")
        self.assertEqual(finding, 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_EnchantScore], 20)

    def test_a_damage_inscription_scores_fifteen(self) -> None:
        _new, finding = self._search("g_as2_MartialWeaponsInscription", "0x0F327822")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Strength and Honor")
        self.assertEqual(finding, 1)
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_OffensiveScore], 15)

    def test_an_armor_inscription_scores_ten_and_a_shelter_grip_seven(self) -> None:
        _new, _finding = self._search("g_as2_FocusShieldWeaponsInscription", "0x05009821")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Faith is My Shield")
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_DefensiveScore], 10)

        # A second, fresh search: `finding` is zero again, so the mod lands at slot zero.
        self._search("g_as2_AxeUpgrade", "0x07005821")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Axe Grip of Shelter")
        # 10 (Armor +5 from the first mod) + 7 (armor vs) for the second
        self.assertEqual(self._row()[constants.GC_UAI_WEAPONSET_DefensiveScore], 17)

    def test_the_finding_counter_indexes_the_mods_that_were_saved(self) -> None:
        """Three patterns in one string are found in the **table's** order, not the string's."""

        _new, finding = self._search("g_as2_AxeUpgrade", "0xDE0168241414F823E2016824")
        self.assertEqual(finding, 3)
        self.assertEqual(
            list(uai_const.g_as3_Weapon_Mods[0][0][:3]),
            ["Barbed", "Cruel", "Sundering"],
        )

    def test_an_empty_mod_string_finds_nothing(self) -> None:
        """The empty string GwAu3's ``Item_GetModStruct`` answers for an item with no mod array."""

        new, finding = self._search("g_as2_AxeUpgrade", "")
        self.assertEqual(finding, 0)
        self.assertEqual(new, "")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "")


class FindAndSaveModTests(WeaponSetTestCase):
    """`UAI_FindAndSaveModFromMemory`: which two tables a weapon type searches."""

    def _find(self, item_type: int, weapon: int, mod_struct: str = "0x") -> list[str]:
        with mock.patch.object(
            uai_weaponsets, "Item_GetModStruct", lambda item_id: mod_struct
        ), mock.patch.object(
            uai_weaponsets, "UAI_SearchModsInArray", wraps=uai_weaponsets.UAI_SearchModsInArray
        ) as search:
            uai_weaponsets.UAI_FindAndSaveModFromMemory(1, item_type, 1, weapon)
        return [call.args[0] for call in search.call_args_list]

    def test_a_bow_searches_its_own_upgrades_and_the_martial_inscriptions(self) -> None:
        tables = self._find(constants.GC_I_TYPE_BOW, 1)
        self.assertEqual(
            tables, [uai_const.g_as2_BowUpgrade, uai_const.g_as2_MartialWeaponsInscription]
        )

    def test_a_wand_searches_the_shared_staff_table_and_the_spell_casting_inscriptions(self) -> None:
        for item_type in (constants.GC_I_TYPE_WAND, constants.GC_I_TYPE_STAFF):
            with self.subTest(item_type=item_type):
                tables = self._find(item_type, 1)
                self.assertEqual(
                    tables,
                    [
                        uai_const.g_as2_StaffWandUpgrade,
                        uai_const.g_as2_SpellCastingWeaponsInscription,
                    ],
                )

    def test_a_shield_searches_the_shield_table_and_the_focus_shield_inscriptions(self) -> None:
        tables = self._find(constants.GC_I_TYPE_SHIELD, 2)
        self.assertEqual(
            tables,
            [
                uai_const.g_as2_ShieldUpgrade,
                uai_const.g_as2_FocusShieldWeaponsInscription,
            ],
        )

    def test_a_focus_searches_the_focus_table_and_the_focus_shield_inscriptions(self) -> None:
        tables = self._find(constants.GC_I_TYPE_OFFHAND, 2)
        self.assertEqual(
            tables,
            [
                uai_const.g_as2_FocusUpgrade,
                uai_const.g_as2_FocusShieldWeaponsInscription,
            ],
        )

    def test_an_empty_offhand_slot_searches_nothing(self) -> None:
        self.assertEqual(self._find(0, 2), [])

    def test_a_weapon_type_with_no_table_searches_nothing(self) -> None:
        """A type the source's ``Switch`` has no case for falls through, which is its own silence."""

        self.assertEqual(self._find(constants.GC_I_TYPE_SHIELD, 1), [])


class SaveWeaponSetTests(WeaponSetTestCase):
    """`UAI_SaveWeaponSetFromMemory`: the row it fills and the trackers it updates."""

    def test_a_set_outside_one_to_four_is_not_read(self) -> None:
        with mock.patch.object(
            uai_weaponsets, "Item_GetInventoryInfo"
        ) as accessor:
            uai_weaponsets.UAI_SaveWeaponSetFromMemory(0)
            uai_weaponsets.UAI_SaveWeaponSetFromMemory(5)
        accessor.assert_not_called()

    def test_a_sword_and_shield_set_is_scored_out_of_its_mods(self) -> None:
        """The whole analysis, end to end, on the bytes of two real upgrades.

        The sword carries ``DE016824`` (Barbed, ``+33%`` condition) and ``001E4823`` (Fortitude,
        ``Health +30``); the shield carries ``001E4823`` (Shield Handle of Fortitude). The strike-out
        is what keeps the sword's Fortitude row from matching the shield's bytes as well.
        """

        self._patch_data(
            _Item(11, constants.GC_I_TYPE_SWORD, "0xDE016824001E4823"),
            _Item(12, constants.GC_I_TYPE_SHIELD, "0x001E4823"),
        )
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(1)

        row = self._row()
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponType], constants.GC_I_TYPE_SWORD)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponId], 11)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffhandType], constants.GC_I_TYPE_SHIELD)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffhandId], 12)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_MaxHP], 60)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_DefensiveScore], 60)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffensiveScore], 5)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_IsRanged], 0)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_HasShield], 1)
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][0], "Barbed")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][0][1], "Sword Pommel of Fortitude")
        self.assertEqual(uai_const.g_as3_Weapon_Mods[0][1][0], "Shield Handle of Fortitude")

        # The trackers take this set: HP 60, defensive 60 + 60 + the shield's flat 20, offensive 5.
        self.assertEqual(uai_const.g_ai_High_Hp_Set, [60, 1])
        self.assertEqual(uai_const.g_ai_Best_Defensive_Set, [140, 1])
        self.assertEqual(uai_const.g_ai_Best_Offensive_Set, [5, 1])
        self.assertEqual(uai_const.g_ai_Best_Casting_Set, [0, 0])
        self.assertEqual(uai_const.g_ai_Best_Enchant_Set, [0, 0])

    def test_a_two_handed_weapon_skips_its_offhand(self) -> None:
        self._patch_data(
            _Item(11, constants.GC_I_TYPE_HAMMER, "0xDE016824"),
            _Item(12, constants.GC_I_TYPE_SHIELD, "0x001E4823"),
            set_index=1,
        )
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(2)

        row = self._row(1)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffhandId], 12)
        # The offhand's id and type are recorded, but its mods are never searched.
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_MaxHP], 0)
        self.assertEqual(uai_const.g_as3_Weapon_Mods[1][1], ["", "", "", "", "", "", "", ""])

    def test_a_ranged_weapon_takes_the_ranged_tracker_once(self) -> None:
        self._patch_data(_Item(11, constants.GC_I_TYPE_BOW, "0xDE016824"), None)
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(1)
        self.assertEqual(uai_const.g_ai_Best_Ranged_Set, [1, 1])

        # A second bow does not move it: `And $g_ai_Best_Ranged_Set[0] = 0` in the source.
        self._patch_data(_Item(21, constants.GC_I_TYPE_BOW, "0xDE016824"), None, set_index=1)
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(2)
        self.assertEqual(uai_const.g_ai_Best_Ranged_Set, [1, 1])

    def test_a_set_with_no_weapon_keeps_its_zero_row(self) -> None:
        self._patch_data(None, None)
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(3)

        row = self._row(2)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponId], 0)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_MaxHP], 0)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_IsRanged], 0)
        self.assertEqual(uai_const.g_ai_High_Hp_Set, [0, 0])

    def test_a_zero_energy_row_is_never_a_best_energy_set(self) -> None:
        """``> $g_ai_High_Energy_Set[0]`` with both at zero leaves the set number at zero."""

        self._patch_data(_Item(11, constants.GC_I_TYPE_BOW, "0x"), None)
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(1)
        self.assertEqual(uai_const.g_ai_High_Energy_Set, [0, 0])


class DetermineWeaponSetsTests(WeaponSetTestCase):
    def test_all_four_sets_are_walked_and_the_trackers_are_reset_first(self) -> None:
        for name in _TRACKERS:
            getattr(uai_const, name)[:] = [7, 3]

        with mock.patch.object(
            uai_weaponsets, "UAI_SaveWeaponSetFromMemory"
        ) as save:
            uai_weaponsets.UAI_DetermineWeaponSets()

        self.assertEqual([call.args[0] for call in save.call_args_list], [1, 2, 3, 4])
        for name in _TRACKERS:
            with self.subTest(name=name):
                self.assertEqual(getattr(uai_const, name), [0, 0])


class DecisionTests(WeaponSetTestCase):
    """The members that choose a set, with the switches observed rather than performed."""

    def _switch(self) -> mock.MagicMock:
        patcher = mock.patch.object(uai_weaponsets, "UAI_ChangeWeaponSet")
        switch = patcher.start()
        self.addCleanup(patcher.stop)
        return switch

    def test_find_weapon_set_by_type_answers_five_when_it_is_already_equipped(self) -> None:
        with mock.patch.object(
            uai_weaponsets,
            "UAI_GetPlayerInfo",
            lambda info: constants.GC_I_TYPE_SWORD,
        ):
            self.assertEqual(
                uai_weaponsets.UAI_FindWeaponSetByType(constants.GC_I_TYPE_SWORD), 5
            )

    def test_find_weapon_set_by_type_answers_the_set_that_holds_the_type(self) -> None:
        self._row(2)[constants.GC_UAI_WEAPONSET_WeaponType] = constants.GC_I_TYPE_AXE
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0):
            self.assertEqual(
                uai_weaponsets.UAI_FindWeaponSetByType(constants.GC_I_TYPE_AXE), 3
            )
            self.assertEqual(uai_weaponsets.UAI_FindWeaponSetByType(999), 0)

    def test_the_situation_names_are_the_sources_nine_and_they_are_case_insensitive(self) -> None:
        uai_const.g_ai_High_Hp_Set[:] = [60, 2]
        uai_const.g_ai_Best_Zealous_Set[:] = [1, 4]
        self.assertEqual(uai_weaponsets.UAI_GetWeaponSetForSituation("hp"), 2)
        self.assertEqual(uai_weaponsets.UAI_GetWeaponSetForSituation("HP"), 2)
        self.assertEqual(uai_weaponsets.UAI_GetWeaponSetForSituation("Zealous"), 4)
        self.assertEqual(uai_weaponsets.UAI_GetWeaponSetForSituation("energy"), 0)
        self.assertEqual(uai_weaponsets.UAI_GetWeaponSetForSituation("nonsense"), 0)

    def test_the_combat_choice_falls_back_to_set_one(self) -> None:
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0.9):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 1)

    def _health(self, hp: float, energy: float = 30) -> mock._patch:
        """`UAI_GetPlayerInfo` answering the two columns this member reads."""

        return mock.patch.object(
            uai_weaponsets,
            "UAI_GetPlayerInfo",
            lambda info: hp if info == constants.GC_UAI_AGENT_HP else energy,
        )

    def test_the_defensive_hysteresis_enters_at_thirty_percent_and_leaves_at_fifty(self) -> None:
        uai_const.g_ai_Best_Defensive_Set[:] = [140, 3]
        uai_const.g_ai_High_Hp_Set[:] = [60, 2]

        with self._health(0.9):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 2)
            self.assertFalse(uai_const.g_b_InDefensiveMode)

        with self._health(0.30):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 3)
            self.assertTrue(uai_const.g_b_InDefensiveMode)

        # 0.45 is above the entry threshold and below the exit one: still defensive.
        with self._health(0.45):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 3)
            self.assertTrue(uai_const.g_b_InDefensiveMode)

        with self._health(0.50):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 2)
            self.assertFalse(uai_const.g_b_InDefensiveMode)

    def test_the_low_energy_hysteresis_enters_at_five_and_leaves_at_twenty_five(self) -> None:
        uai_const.g_ai_High_Energy_Set[:] = [15, 4]
        uai_const.g_ai_Best_Zealous_Set[:] = [1, 3]

        with self._health(0.9, 30):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 1)
            self.assertFalse(uai_const.g_b_InLowEnergyMode)

        with self._health(0.9, 5):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 4)
            self.assertTrue(uai_const.g_b_InLowEnergyMode)

        with self._health(0.9, 20):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 4)
            self.assertTrue(uai_const.g_b_InLowEnergyMode)

        with self._health(0.9, 25):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 1)
            self.assertFalse(uai_const.g_b_InLowEnergyMode)

    def test_the_zealous_set_is_the_energy_fallback(self) -> None:
        uai_const.g_ai_Best_Zealous_Set[:] = [1, 3]
        with self._health(0.9, 1):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 3)

    def test_an_offensive_set_wins_when_nothing_else_is_triggered(self) -> None:
        uai_const.g_ai_Best_Offensive_Set[:] = [25, 2]
        with self._health(0.9, 30):
            self.assertEqual(uai_weaponsets.UAI_GetBestWeaponSetForCombat(), 2)

    def test_should_switch_answers_false_when_the_player_is_already_on_the_best_set(self) -> None:
        uai_const.g_ai_Best_Offensive_Set[:] = [25, 2]
        with self._health(0.9, 30), mock.patch.object(
            uai_weaponsets, "UAI_IsOnWeaponSet", lambda set_number: True
        ):
            self.assertFalse(uai_weaponsets.UAI_ShouldSwitchWeaponSet())

    def test_should_switch_performs_the_switch_when_a_change_is_needed(self) -> None:
        uai_const.g_ai_Best_Offensive_Set[:] = [25, 2]
        with self._health(0.9, 30), mock.patch.object(
            uai_weaponsets, "UAI_IsOnWeaponSet", lambda set_number: False
        ), mock.patch.object(uai_weaponsets, "UAI_ChangeWeaponSet") as change:
            self.assertTrue(uai_weaponsets.UAI_ShouldSwitchWeaponSet())
        change.assert_called_once_with(uai_const.g_ai_Best_Offensive_Set[1])

    def test_the_skill_slot_choice_prefers_the_defensive_set_when_health_is_low(self) -> None:
        uai_const.g_ai_Best_Defensive_Set[:] = [140, 3]
        switch = self._switch()
        with mock.patch.object(
            uai_weaponsets,
            "UAI_GetPlayerInfo",
            lambda info: 0.1 if info == constants.GC_UAI_AGENT_HP else 0,
        ), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_SPELL
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_called_once_with(3)

    def test_the_skill_slot_choice_leaves_attack_skills_alone_when_health_is_low(self) -> None:
        """The source's own exception: an attack or an enchantment skips both survival priorities."""

        uai_const.g_ai_Best_Defensive_Set[:] = [140, 3]
        uai_const.g_ai_Best_Casting_Set[:] = [30, 4]
        switch = self._switch()
        with mock.patch.object(
            uai_weaponsets,
            "UAI_GetPlayerInfo",
            lambda info: 0.1 if info == constants.GC_UAI_AGENT_HP else 0,
        ), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_ATTACK
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_not_called()

    def test_a_shout_keeps_the_current_set_and_switches_nothing(self) -> None:
        uai_const.g_ai_Best_Casting_Set[:] = [30, 4]
        switch = self._switch()
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0.9), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_SHOUT
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_not_called()

    def test_a_spell_prefers_the_casting_set(self) -> None:
        uai_const.g_ai_Best_Casting_Set[:] = [30, 4]
        switch = self._switch()
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0.9), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_SPELL
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_called_once_with(4)

    def test_an_enchantment_prefers_the_enchant_set_and_falls_back_to_casting(self) -> None:
        uai_const.g_ai_Best_Enchant_Set[:] = [20, 2]
        uai_const.g_ai_Best_Casting_Set[:] = [30, 4]
        switch = self._switch()
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0.9), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_ENCHANTMENT
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_called_once_with(2)

        switch.reset_mock()
        uai_const.g_ai_Best_Enchant_Set[:] = [0, 0]
        with mock.patch.object(uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0.9), mock.patch.object(
            uai_weaponsets,
            "UAI_GetStaticSkillInfo",
            lambda slot, column: constants.GC_I_SKILL_TYPE_ENCHANTMENT
            if column == constants.GC_UAI_STATIC_SKILL_SkillType
            else 0,
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_called_once_with(4)

    def test_an_attack_skill_looks_for_the_set_with_its_weapon_type(self) -> None:
        self._row(1)[constants.GC_UAI_WEAPONSET_WeaponType] = constants.GC_I_TYPE_AXE
        switch = self._switch()
        with mock.patch.object(
            uai_weaponsets, "UAI_GetPlayerInfo", lambda info: constants.GC_I_TYPE_SWORD
        ), mock.patch.object(
            uai_weaponsets, "UAI_GetStaticSkillInfo", lambda slot, column: 0
        ), mock.patch.object(
            uai_weaponsets, "UAI_WeaponReqToItemType", lambda req: constants.GC_I_TYPE_AXE
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_not_called()

    def test_a_ready_attack_weapon_ends_the_attempt_without_a_switch(self) -> None:
        """``UAI_FindWeaponSetByType`` answers ``5`` for "already equipped", and the source returns."""

        switch = self._switch()
        with mock.patch.object(
            uai_weaponsets, "UAI_GetPlayerInfo", lambda info: constants.GC_I_TYPE_SWORD
        ), mock.patch.object(
            uai_weaponsets, "UAI_GetStaticSkillInfo", lambda slot, column: 0
        ), mock.patch.object(
            uai_weaponsets, "UAI_FindWeaponSetByType", lambda item_type: 5
        ), mock.patch.object(
            uai_weaponsets, "UAI_WeaponReqToItemType", lambda req: constants.GC_I_TYPE_SWORD
        ), mock.patch.object(
            uai_weaponsets, "UAI_GetPlayerInfo", lambda info: 0
        ):
            uai_weaponsets.UAI_GetBestWeaponSetBySkillSlot(1)
        switch.assert_not_called()


class ChangeWeaponSetTests(WeaponSetTestCase):
    def test_asking_for_the_set_the_player_is_on_does_nothing(self) -> None:
        """``If UAI_IsOnWeaponSet($a_i_Set) Then Return`` -- the quick check is the whole call."""

        with mock.patch.object(
            uai_weaponsets, "UAI_IsOnWeaponSet", lambda set_number: True
        ), mock.patch.object(uai_weaponsets, "Core_PerformAction") as action:
            self.assertIsNone(uai_weaponsets.UAI_ChangeWeaponSet(2))
        action.assert_not_called()

    def test_a_real_switch_is_two_cancels_then_the_sets_own_press(self) -> None:
        """The source's three sends, as the source writes them: cancel, cancel, then the set.

        ``UAI_ChangeWeaponSet`` asks `UAI_IsOnWeaponSet` once as its quick check (``:492``) and then once
        per turn of its loop (``:520``). Here the quick check says no and the loop's first check says yes,
        so exactly one set press is made after the two cancels, and the three calls are asserted in the
        source's own order with its own control codes -- ``0xAF`` for the cancel and ``0x81``-``0x84`` for
        the set (``UAI_ChangeWeaponSet``'s ``Switch`` over GwAu3's four constants).
        """

        answers = iter((False, True))

        def on_weapon_set(set_number: int) -> bool:
            return next(answers, True)

        with mock.patch.object(
            uai_weaponsets, "UAI_IsOnWeaponSet", on_weapon_set
        ), mock.patch.object(uai_weaponsets, "Core_PerformAction") as action:
            self.assertIsNone(uai_weaponsets.UAI_ChangeWeaponSet(2))

        activate = constants.GC_I_CONTROL_TYPE_ACTIVATE
        cancel = constants.GC_I_CONTROL_ACTION_CANCEL_ACTION
        self.assertEqual(
            action.call_args_list,
            [
                mock.call(cancel, activate),
                mock.call(cancel, activate),
                mock.call(constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_2, activate),
            ],
        )

    def test_the_four_sets_are_the_four_control_actions_the_enum_carries(self) -> None:
        """GwAu3's four set constants and this port's own enum name the same four codes."""

        from py4gw.enums_src.ui_enums import ControlAction

        self.assertEqual(
            [
                constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1,
                constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_2,
                constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_3,
                constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_4,
            ],
            [
                ControlAction.ControlAction_ActivateWeaponSet1.value,
                ControlAction.ControlAction_ActivateWeaponSet2.value,
                ControlAction.ControlAction_ActivateWeaponSet3.value,
                ControlAction.ControlAction_ActivateWeaponSet4.value,
            ],
        )


class LiveModBytesTests(WeaponSetTestCase):
    """The analysis over the client's **own** mod bytes, read from a real character.

    Every hex string below is one row of `tests/live_reports/gwa3_inventory.log` (pid 19696,
    2026-10-10), produced read-only by `tests/probe_gwa3_inventory_live.py`: the four weapon sets'
    records, found through the inventory struct's own pointers. What the port finds in them is
    asserted here, so the weights and the search are checked against bytes the game wrote rather than
    against bytes this test wrote.

    The character's setup is in the numbers: sets 1 and 2 hold the same axe and set 1 has no offhand,
    sets 2 and 4 share one shield, set 3 is a bow with no offhand, and set 4 is a zealous axe with a
    Fortitude grip.
    """

    #: ``(set number, slot, item id, item type, the record's mod bytes in GwAu3's text form)``.
    LIVE = (
        (1, "weapon", 6096, 2, "0x091298270002482684000824080130250005B824260208244D0430250506A8286801"
                               "0824D00232250F00A822061CA8A7007898A4000000C0"),
        (2, "weapon", 6096, 2, "0x091298270002482684000824080130250005B824260208244D0430250506A8286801"
                               "0824D00232250F00A822061CA8A7007898A4000000C0"),
        (2, "offhand", 3813, 24, "0x091198270200A820002D88230810B8A7000000C0"),
        (3, "weapon", 122, 5, "0x00011826091998270001B8240F0038220A0018204801082490023025E1016824CE00"
                              "08249D013025070058210F1CA8A7000000C0"),
        (4, "weapon", 94, 2, "0x091298270002B8240F327822A30008244601302501001825460130250100C820D900"
                             "0824B3013025001E4823061CA8A7007898A4000000C0"),
        (4, "offhand", 3813, 24, "0x091198270200A820002D88230810B8A7000000C0"),
    )

    def _analyse(self, set_number: int, slot: str) -> None:
        """Run the port's `UAI_SaveWeaponSetFromMemory` over the live rows for one set and slot."""

        pointers = {}
        mods = {}
        types = {}
        for index, which, item_id, item_type, mod_struct in self.LIVE:
            key = f"WeaponSet{index - 1}{'Weapon' if which == 'weapon' else 'Offhand'}Ptr"
            if index == set_number and which == slot:
                pointers[key] = item_id
            mods[item_id] = mod_struct
            types[item_id] = item_type
        self._patch_data_raw(pointers, mods, types)
        uai_weaponsets.UAI_SaveWeaponSetFromMemory(set_number)

    def _patch_data_raw(self, pointers: dict, mods: dict, types: dict) -> None:
        """The inventory pointer, the field reads through it, and the mod bytes, all by item id.

        A pointer here is the **item id** rather than a record, which is enough for both reads the
        analysis makes through it: ``Item_GetItemInfoByPtr`` is asked for ``ItemID`` -- answered with
        the id itself -- and for ``ItemType``, which the id maps to.
        """

        patchers = [
            mock.patch.object(
                uai_weaponsets, "Item_GetInventoryInfo", lambda key: pointers.get(key)
            ),
            mock.patch.object(
                uai_weaponsets,
                "Item_GetItemInfoByPtr",
                lambda record, field: record if field == "ItemID" else types[int(record)],
            ),
            mock.patch.object(
                uai_weaponsets, "Item_GetModStruct", lambda item_id: mods.get(int(item_id), "")
            ),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_fiery_axe_with_a_damage_inscription(self) -> None:
        """Set 1: ``Fiery`` scored nothing, ``Dance with Death`` is a ``Damage +15%`` inscription."""

        self._analyse(1, "weapon")
        row = self._row(0)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponType], constants.GC_I_TYPE_AXE)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponId], 6096)
        self.assertEqual(
            [name for name in uai_const.g_as3_Weapon_Mods[0][0] if name],
            ["Fiery", "Dance with Death"],
        )
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffensiveScore], 15)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_DefensiveScore], 0)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_IsRanged], 0)

    def test_an_endurance_shield_with_a_stance_inscription(self) -> None:
        """Set 2's shield: ``+45 HP while in a Stance`` and ``Damage -2 (while in a Stance)``.

        The health mod is the one that adds twice -- to ``MaxHP`` and to the defensive score -- and
        the ``Damage -`` inscription adds five more, so 45 and 50.
        """

        self._analyse(2, "offhand")
        row = self._row(1)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffhandType], constants.GC_I_TYPE_SHIELD)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffhandId], 3813)
        self.assertEqual(
            [name for name in uai_const.g_as3_Weapon_Mods[1][1] if name],
            ["Shield Handle of Endurance", "Run For Your Life!"],
        )
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_MaxHP], 45)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_DefensiveScore], 50)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_HasShield], 1)

    def test_a_crippling_bow_with_a_shelter_grip_and_a_damage_inscription(self) -> None:
        """Set 3: the bow's own table finds ``Crippling`` and the grip, the martial one the inscription."""

        self._analyse(3, "weapon")
        row = self._row(2)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_WeaponType], constants.GC_I_TYPE_BOW)
        self.assertEqual(
            [name for name in uai_const.g_as3_Weapon_Mods[2][0] if name],
            ["Crippling", "Bow Grip of Shelter", "To the Pain!"],
        )
        # Crippling is a `+33%` condition (5), To the Pain! a `Damage +15%` (15); the grip is `armor vs`.
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffensiveScore], 20)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_DefensiveScore], 7)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_IsRanged], 1)
        self.assertEqual(uai_const.g_ai_Best_Ranged_Set, [1, 3])

    def test_a_zealous_axe_with_a_fortitude_grip(self) -> None:
        """Set 4: ``Zealous`` (10 and its flag), ``Fortitude`` (30 health) and a ``Damage +15%``."""

        self._analyse(4, "weapon")
        row = self._row(3)
        self.assertEqual(
            [name for name in uai_const.g_as3_Weapon_Mods[3][0] if name],
            ["Zealous", "Axe Grip of Fortitude", "Strength and Honor"],
        )
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_OffensiveScore], 25)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_MaxHP], 30)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_DefensiveScore], 30)
        self.assertEqual(row[constants.GC_UAI_WEAPONSET_HasZealous], 1)
        self.assertEqual(uai_const.g_ai_High_Hp_Set, [30, 4])
        self.assertEqual(uai_const.g_ai_Best_Zealous_Set, [1, 4])
        self.assertEqual(uai_const.g_ai_Best_Offensive_Set, [25, 4])

    def test_the_same_axe_in_two_sets_scores_the_same_way(self) -> None:
        """Sets 1 and 2 hold one axe; the analysis is the source's, so it answers the same row."""

        self._analyse(1, "weapon")
        first = list(self._row(0))
        uai_const.g_a2D_WeaponSets[1][:] = [0] * 14
        self._analyse(2, "weapon")
        self.assertEqual(list(self._row(1)), first)

    def test_the_best_energy_set_stays_unset_when_no_set_has_an_energy_mod(self) -> None:
        """None of the character's six items carries an energy mod -- so the tracker keeps its zero."""

        for set_number, slot, *_rest in self.LIVE:
            self._analyse(set_number, slot)
        self.assertEqual(uai_const.g_ai_High_Energy_Set, [0, 0])


if __name__ == "__main__":
    unittest.main()
