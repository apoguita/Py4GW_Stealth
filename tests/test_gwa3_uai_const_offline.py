"""Offline tests for `py4gw/gwa3/uai_const.py` -- GwAu3's **mutable** UtilityAI settings.

No client. The module holds the ``UtilityAI_Const.au3`` ``Global`` variables -- the ones that are
*state*, not values -- and the test reads the source's own assignments to check each one, because a
global's initial value is a decision GwAu3 made and a port that guessed it would change what a fresh
bot does. The two that matter most are recorded in the module's docstring and asserted here:

* ``$g_i_FightMode`` starts at **1**, which is *Pressure*: a fresh UtilityAI prefers the highest-HP
  target, the opposite of what the name suggests;
* ``$g_i_TargetMode`` starts at ``$GC_UAI_TARGET_MODE_CALL`` (0).

The caches the file also declares (``$g_as_BestTargetCache``, ``$g_as_CanUseCache``) are **not** here,
and the test says why: this layer answers the names those tables hold live, so there is nothing for a
caller to fill.

The weapon-set state (``:30-72``) and the fourteen mod tables (``:74-388``) arrived with
``Equipment/UtilityAI_WeaponSets.au3``, and the mod tables are checked **row for row against the
source's own text** -- they are transcription, and transcription is where a silent mistake lives.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from py4gw.gwa3 import constants, uai_const

SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "external"
    / "GwAu3"
    / "API" / "Plugins" / "UtilityAI" / "UtilityAI_Const.au3"
)


def _assignments() -> dict[str, str]:
    """``{global name: the expression it is assigned}`` from the source's own ``Global`` lines."""

    text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
    found = {}
    for match in re.finditer(r"(?m)^\s*Global\s+\$(\w+)\s*=\s*(?P<value>.+?)\s*$", text):
        found[match.group(1)] = match.group("value").strip()
    return found


#: ``Global $g_as2_<name>[n][3] = [`` -- the header of one mod table, and the size it declares.
_TABLE_HEAD = re.compile(r"(?m)^Global\s+\$g_(as2_\w+)\s*\[(\d+)\]\[3\]\s*=\s*\[")
_ROW = re.compile(r'\[\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*\]')


def _mod_tables() -> dict[str, tuple[int, list[list[str]]]]:
    """``{module name: (declared size, rows)}``, parsed out of the source's own mod region.

    A row is a three-string array entry. The block ends at the ``]]`` that closes the outer array --
    which is also the end of the last row's line -- so the parse needs no comment stripping: the row
    regex stops at the row's own closing bracket, and the two rows the source annotates with a
    trailing ``;`` comment are read exactly like the rest.
    """

    text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
    tables: dict[str, tuple[int, list[list[str]]]] = {}
    for head in _TABLE_HEAD.finditer(text):
        # The block runs to the end of the **line** that closes the outer array, because the `]]`
        # itself is on the last row's own line: stopping at the bracket would drop that row.
        close = text.index("]]", head.end())
        block = text[head.end() : text.index("\n", close)]
        rows = [[row.group(1), row.group(2), row.group(3)] for row in _ROW.finditer(block)]
        tables["g_" + head.group(1)] = (int(head.group(2)), rows)
    return tables


class GlobalTests(unittest.TestCase):
    def test_the_source_still_declares_them(self) -> None:
        """Each global this module carries is one the source assigns -- and the reverse is not claimed."""

        assignments = _assignments()
        for name in (
            "g_i_FightMode",
            "g_i_BestTarget",
            "g_i_ForceTarget",
            "g_i_AttackTarget",
            "g_i_LastCalledTarget",
            "g_v_AvoidPlayerNumbers",
            "g_i_TargetMode",
        ):
            with self.subTest(name=name):
                self.assertIn(name, assignments)
                self.assertTrue(hasattr(uai_const, name))

    def test_the_values_are_the_sources_own(self) -> None:
        assignments = _assignments()
        self.assertEqual(uai_const.g_i_FightMode, int(assignments["g_i_FightMode"]))
        self.assertEqual(uai_const.g_i_BestTarget, int(assignments["g_i_BestTarget"]))
        self.assertEqual(uai_const.g_i_ForceTarget, int(assignments["g_i_ForceTarget"]))
        self.assertEqual(uai_const.g_i_AttackTarget, int(assignments["g_i_AttackTarget"]))
        self.assertEqual(uai_const.g_i_LastCalledTarget, int(assignments["g_i_LastCalledTarget"]))
        self.assertEqual(
            uai_const.g_v_AvoidPlayerNumbers, int(assignments["g_v_AvoidPlayerNumbers"])
        )

    def test_the_target_mode_names_the_constant_its_source_names(self) -> None:
        self.assertEqual(_assignments()["g_i_TargetMode"], "$GC_UAI_TARGET_MODE_CALL")
        self.assertEqual(uai_const.g_i_TargetMode, constants.GC_UAI_TARGET_MODE_CALL)

    def test_the_fight_mode_starts_in_pressure_and_that_is_the_sources_choice(self) -> None:
        """``Global $g_i_FightMode = 1`` with ``Enum $g_i_FinisherMode, $g_i_PressureMode`` below it."""

        self.assertEqual(_assignments()["g_i_FightMode"], "1")
        self.assertEqual(uai_const.g_i_FightMode, constants.g_i_PressureMode)
        self.assertNotEqual(uai_const.g_i_FightMode, constants.g_i_FinisherMode)

    def test_the_two_string_caches_are_deliberately_absent(self) -> None:
        """They are caches, and this layer answers their contents live -- so a caller has nothing to fill.

        The source declares them as **arrays** (``Global $g_as_BestTargetCache[9]``), which the
        ``Global $name = value`` scan above does not match, so they are checked against the file's text.
        """

        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        self.assertIn("$g_as_BestTargetCache[9]", text)
        self.assertIn("$g_as_CanUseCache[9]", text)
        self.assertFalse(hasattr(uai_const, "g_as_BestTargetCache"))
        self.assertFalse(hasattr(uai_const, "g_as_CanUseCache"))

    def test_the_globals_are_mutable_state_and_are_written_the_way_the_source_writes_them(self) -> None:
        """A script assigns them; the module must not turn them into constants."""

        original = uai_const.g_i_FightMode
        try:
            uai_const.g_i_FightMode = constants.g_i_FinisherMode
            self.assertEqual(uai_const.g_i_FightMode, constants.g_i_FinisherMode)
        finally:
            uai_const.g_i_FightMode = original


class ModTableTests(unittest.TestCase):
    """The fourteen mod tables (``:74-388``), **row for row against the source**.

    These are transcribed data, and a transcription is exactly where a silent mistake lives: one
    dropped row or one mistyped hex pair would change which mods a bot finds. So the test parses the
    source's own region and compares every row and every table's declared size.
    """

    def test_every_mod_table_the_source_declares_is_carried(self) -> None:
        tables = _mod_tables()
        self.assertEqual(len(tables), 14)
        for name in tables:
            with self.subTest(table=name):
                self.assertTrue(hasattr(uai_const, name), name)

    def test_every_row_is_the_sources_row(self) -> None:
        for name, (_declared, rows) in _mod_tables().items():
            with self.subTest(table=name):
                carried = [list(row) for row in getattr(uai_const, name)]
                self.assertEqual(carried, rows)

    def test_every_table_has_the_size_the_source_declares(self) -> None:
        for name, (declared, rows) in _mod_tables().items():
            with self.subTest(table=name):
                self.assertEqual(len(rows), declared)
                self.assertEqual(len(getattr(uai_const, name)), declared)

    def test_each_row_is_a_name_an_effect_and_a_byte_sequence(self) -> None:
        for name in _mod_tables():
            for row in getattr(uai_const, name):
                with self.subTest(table=name, row=row[0]):
                    self.assertEqual(len(row), 3)
                    self.assertTrue(row[0])
                    self.assertTrue(row[1])

    def test_the_sources_own_unknown_byte_sequences_are_kept_as_written(self) -> None:
        """Two rows carry ``"????????"`` -- an upgrade whose bytes GwAu3 never filled in."""

        carriers = [
            (name, row[0])
            for name in _mod_tables()
            for row in getattr(uai_const, name)
            if row[2] == "????????"
        ]
        self.assertEqual(
            sorted(carriers),
            [
                ("g_as2_FocusUpgrade", "Focus Core of Adptitude"),
                ("g_as2_MartialWeaponsInscription", "Let the Memory Live Again"),
            ],
        )


class WeaponSetStateTests(unittest.TestCase):
    """The weapon-set state the file declares (``:30-72``), with the sizes it declares."""

    def test_the_set_table_is_four_rows_of_fourteen_zeroed_indices(self) -> None:
        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        self.assertIn("$g_a2D_WeaponSets[4][14]", text)
        self.assertEqual(len(uai_const.g_a2D_WeaponSets), 4)
        for row in uai_const.g_a2D_WeaponSets:
            self.assertEqual(len(row), 14)
            self.assertEqual(row, [0] * 14)

    def test_the_ten_trackers_start_at_zero_and_zero(self) -> None:
        for name in (
            "g_ai_High_Hp_Set",
            "g_ai_High_Energy_Set",
            "g_ai_Best_Offensive_Set",
            "g_ai_Best_Defensive_Set",
            "g_ai_Best_Casting_Set",
            "g_ai_Best_Enchant_Set",
            "g_ai_Best_Ranged_Set",
            "g_ai_Best_Vampiric_Set",
            "g_ai_Best_Zealous_Set",
        ):
            with self.subTest(name=name):
                self.assertEqual(getattr(uai_const, name), [0, 0])

    def test_the_mod_name_table_is_four_sets_by_two_weapons_by_eight_slots(self) -> None:
        text = SOURCE.read_text(encoding="utf-8-sig", errors="replace")
        self.assertIn("$g_as3_Weapon_Mods[4][2][8]", text)
        self.assertEqual(len(uai_const.g_as3_Weapon_Mods), 4)
        for plane in uai_const.g_as3_Weapon_Mods:
            self.assertEqual(len(plane), 2)
            for row in plane:
                self.assertEqual(row, [""] * 8)

    def test_the_two_hysteresis_flags_start_false(self) -> None:
        assignments = _assignments()
        for name in ("g_b_InDefensiveMode", "g_b_InLowEnergyMode"):
            with self.subTest(name=name):
                self.assertEqual(assignments[name], "False")
                self.assertFalse(getattr(uai_const, name))

    def test_the_debug_switch_starts_false_as_the_source_declares_it(self) -> None:
        self.assertEqual(_assignments()["g_b_UAI_Debug"], "False")
        self.assertFalse(uai_const.g_b_UAI_Debug)


if __name__ == "__main__":
    unittest.main()
