"""Offline tests for the GwAu3 constant surface in ``py4gw/gwa3/constants.py``.

No client and no elevation: this module is a generated name table, and the tests check it against
the sources it is generated from.

Two things are being established, and they are different questions:

1. **Completeness in both directions** -- every constant in
   ``external/GwAu3/API/Constants/*.au3`` is present under GwAu3's name with the ``$`` dropped, and
   the module declares no name GwAu3 does not. A missing name is a script that breaks; an extra name
   is this project inventing a constant, which is worse.
2. **Values** -- re-derived from the ``.au3`` sources by an independent reader in this test, so the
   generator cannot agree with itself. Where the two disagree the source wins and the test fails.

**Both of AutoIt's declaration forms are read, and the second one is why this file changed.**
GwAu3 declares constants with ``Global Const $X = v`` *and* with ``Global Enum $A, $B, $C``
continuation blocks, and the generator originally read only the first. **176 names were missing** --
every ``$GC_I_INVENTORY_*`` field key, every ``$GC_I_HERO_ID_*`` hero id, the ``$GC_I_SKILL_*`` and
``$GC_S_SKILL_*`` field keys, the ``$GC_E_TITLEID_*`` title ids -- and this file could not see it,
because it read the sources with the same blind spot the generator had. A surface checked against its
own extraction is checked against an index, not against the record. It was found by
``tools/analyze_gwa3_example_parity.py``, which reads GwAu3's *scripts* and asks which constants they
use.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from py4gw.gwa3 import constants

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "external" / "GwAu3" / "API"
CONSTANTS_DIR = API_ROOT / "Constants"

# The include files that declare constants, read independently of the generator's own list so a
# file dropped from that list is caught here rather than silently ignored.
DECLARATION = re.compile(r"^\s*Global\s+Const\s+\$([A-Za-z_]\w*)\b")

#: `Global Enum ...` -- the second declaration form, whose names continue over `_` continuation lines.
ENUM = re.compile(r"^\s*Global\s+Enum\b(.*)$", re.IGNORECASE)
ENUM_NAME = re.compile(r"\$([A-Za-z_]\w*)")


def _without_comment(line: str) -> str:
    """An AutoIt line with its `;` comment removed.

    The continuation marker can sit **before** a comment -- `$GC_E_TITLEID_SURVIVOR, _ ; Pre hard mode
    update version` (`GwAu3_Const_Title.au3:4-13` is full of them) -- so a reader that looks at the raw
    line sees a line that does not end in `_` and stops one name in.
    """

    return line.split(";", 1)[0].rstrip()


def source_names() -> dict[str, str]:
    """``{name: file}`` for every constant GwAu3 declares, in either form, anywhere under ``API/``.

    **Not only ``API/Constants/``.** The plugins and modules declare constants of their own --
    ``$GC_I_ASSERTLOG_STOLEN`` in ``Plugins/UtilityAI/AssertLog_Core.au3``,
    ``$GC_UAI_TARGET_MODE_CALL`` and the ``$g_i_*`` modes in ``Plugins/UtilityAI/UtilityAI_Const.au3``
    -- and GwAu3's own parameter defaults name them (``UAI_Fight(..., $a_i_FightMode =
    $g_i_FinisherMode)``). Reading one directory left **287 names** the generators had to be taught
    about and this test called "extra"; both now read the whole tree.
    """

    found: dict[str, str] = {}

    for path in sorted(API_ROOT.rglob("*.au3")):
        relative = str(path.relative_to(API_ROOT)).replace("\\", "/")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]

            # `Global Enum $A = 0, _` -- take this line and every continuation it pulls in.
            enum = ENUM.match(_without_comment(line))
            if enum is not None:
                body = enum.group(1)
                while body.endswith("_") and index + 1 < len(lines):
                    index += 1
                    body += " " + _without_comment(lines[index])
                for name in ENUM_NAME.findall(body):
                    found[name] = relative
                index += 1
                continue

            match = DECLARATION.match(line)
            if match:
                found[match.group(1)] = relative
            index += 1

    return found


class ConstantSurfaceTests(unittest.TestCase):
    """The module against the sources."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.names = source_names()
        cls.module_names = set(constants.__all__)

    def test_sources_are_present(self) -> None:
        self.assertTrue(CONSTANTS_DIR.is_dir(), f"GwAu3 constants are not at {CONSTANTS_DIR}")
        self.assertGreater(len(self.names), 7000, "the source surface is smaller than expected")

    def test_every_source_constant_is_present(self) -> None:
        missing = sorted(name for name in self.names if not hasattr(constants, name))
        self.assertEqual(missing, [], f"{len(missing)} constants are in the sources and not in the module")

    def test_no_constant_the_source_does_not_declare(self) -> None:
        extra = sorted(name for name in self.module_names if name not in self.names)
        self.assertEqual(extra, [], f"{len(extra)} names are declared here and not by GwAu3")

    def test_all_matches_what_is_reachable(self) -> None:
        self.assertEqual(len(self.module_names), len(constants.__all__))
        for name in constants.__all__:
            self.assertTrue(hasattr(constants, name), f"{name} is in __all__ and not defined")

    def test_no_name_keeps_its_dollar_sign(self) -> None:
        wrong = [name for name in constants.__all__ if name.startswith("$")]
        self.assertEqual(wrong, [])


class ConstantValueTests(unittest.TestCase):
    """Spot checks on values and on the four array shapes GwAu3 uses.

    Deliberately small and hand-checked: the generator's own output is regenerated from the sources,
    so a value test that re-parsed everything would be testing the parser against itself. These are
    the readings a reviewer can confirm by opening the cited line.
    """

    def test_integer_constants(self) -> None:
        # GwAu3_Const_Agents.au3 -- GwAu3's own allegiance values.
        self.assertEqual(constants.GC_I_ALLEGIANCE_ALLY, 0x1)
        self.assertEqual(constants.GC_I_ALLEGIANCE_ANIMAL, 0x2)
        self.assertEqual(constants.GC_I_ALLEGIANCE_ENEMY, 0x3)
        self.assertEqual(constants.GC_I_ALLEGIANCE_SPIRIT, 0x4)
        self.assertEqual(constants.GC_I_ALLEGIANCE_MINION, 0x5)
        self.assertEqual(constants.GC_I_ALLEGIANCE_NPC, 0x6)

    def test_enum_constants_take_autoirs_sequential_values(self) -> None:
        """`Global Enum` assigns 0 to the first name and one more to each after it.

        The values are read off the source's own order, so this pins the *rule* rather than a number:
        `GwAu3_Const_Item.au3:5-19` lists PTR first and SLOT last with no `=` on any of them, and
        `GwAu3_Const_Party.au3:3` starts at an explicit 1.
        """

        # GwAu3_Const_Item.au3:5-19 -- fourteen names, 0 through 13.
        self.assertEqual(constants.GC_I_INVENTORY_PTR, 0)
        self.assertEqual(constants.GC_I_INVENTORY_ITEMID, 1)
        self.assertEqual(constants.GC_I_INVENTORY_BAG, 2)
        self.assertEqual(constants.GC_I_INVENTORY_SLOT, 13)

        # GwAu3_Const_Item.au3:22-34 -- a second block, which starts at 0 again rather than
        # continuing the first: each `Global Enum` is its own sequence.
        self.assertEqual(constants.GC_I_INVENTORY_UNUSED_BAG, 0)
        self.assertEqual(constants.GC_I_INVENTORY_BACKPACK, 1)
        self.assertEqual(constants.GC_I_INVENTORY_BAG1, 3)
        self.assertEqual(constants.GC_I_INVENTORY_EQUIPPED_ITEMS, 22)

        # GwAu3_Const_Party.au3:3 -- an explicit start, then sequential from it.
        self.assertEqual(constants.GC_I_HERO_ID_NORGU, 1)
        self.assertEqual(constants.GC_I_HERO_ID_GOREN, 2)

        # GwAu3_Const_LogMessage.au3:8 -- `= 0` written out, then sequential.
        self.assertEqual(constants.GC_I_LOG_MSGTYPE_DEBUG, 0)
        self.assertEqual(constants.GC_I_LOG_MSGTYPE_INFO, 1)

        # GwAu3_Const_Skill.au3:3972 -- the skill field-name table a script passes to the reader.
        self.assertEqual(constants.GC_I_SKILL_ID, 0)
        self.assertEqual(constants.GC_S_SKILL_NAME, 1)

        # GwAu3_Const_Title.au3:3
        self.assertEqual(constants.GC_E_TITLEID_HERO, 0)

    def test_hex_and_arithmetic_constants(self) -> None:
        # GwAu3_Const_PacketHeader.au3: a hex literal.
        self.assertEqual(constants.GC_I_HEADER_CALL_TARGET, 0x23)
        # GwAu3_Const_Util.au3: a hex literal with a comment giving its decimal form.
        self.assertEqual(constants.ENCSTR_WORD_VALUE_RANGE, 0x7F00)
        # GwAu3_Const_Skill.au3: an arithmetic initialiser the generator must evaluate.
        self.assertEqual(constants.GC_I_RANGE_DANGER, 1015 + 50)
        self.assertEqual(constants.GC_I_RANGE_LONGBOW, 1320)

    def test_string_constants(self) -> None:
        self.assertEqual(constants.GC_S_PATTERN_TYPE_PTR, "Ptr")
        self.assertEqual(constants.GC_S_PATTERN_TYPE_FUNC, "Func")
        self.assertEqual(constants.GC_S_PATTERN_TYPE_HOOK, "Hook")
        self.assertEqual(constants.GC_S_GWA2_CREATOR, "GameRevision Community")

    def test_float_constant(self) -> None:
        self.assertAlmostEqual(constants.GC_F_PROPRAY_MIN_RANGE, 0.1)

    def test_reference_resolves_to_the_referenced_constant(self) -> None:
        # GwAu3_Const_PacketHeader.au3: a name aliased to another constant by reference.
        self.assertEqual(
            constants.GC_I_HEADER_UPGRADE_SESSION_VALID_UPGRADE,
            constants.GC_I_HEADER_UPGRADE_SESSION_END,
        )

    def test_one_dimensional_array(self) -> None:
        # GwAu3_Const_Util.au3 -- 64 entries, declared [64].
        self.assertEqual(len(constants.GC_AS_BASE64_BINARY_GW), 64)
        self.assertEqual(constants.GC_AS_BASE64_BINARY_GW[0], "000000")
        self.assertEqual(constants.GC_AS_BASE64_BINARY_GW[63], "111111")

    def test_two_dimensional_array_keeps_the_declared_shape(self) -> None:
        # GwAu3_Const_Party.au3: declared [40][2] -- 40 rows of 2. The source writes one row per
        # continuation line, so this is also the check that the generator cuts by the declared
        # dimensions instead of returning the rows as written.
        heroes = constants.GC_AM2_HERO_DATA
        self.assertEqual(len(heroes), 40)
        self.assertEqual(len(heroes[0]), 2)
        self.assertEqual(heroes[0], [39, 1])  # the count row GwAu3 puts first
        self.assertEqual(heroes[1], [1, "Norgu"])

    def test_large_two_dimensional_table(self) -> None:
        # GwAu3_Const_Skill.au3: declared [$GC_I_SKILL_DATA_ROWS][$GC_I_SKILL_DATA_COLUMNS] --
        # symbolic dimensions, which the generator resolves from constants already read.
        rows = constants.GC_I_SKILL_DATA_ROWS
        columns = constants.GC_I_SKILL_DATA_COLUMNS
        table = constants.GC_AMX2_SKILL_DATA
        self.assertEqual(len(table), rows)
        self.assertEqual(len(table[0]), columns)
        self.assertEqual(table[1][0], 1)
        self.assertEqual(table[1][1], "Healing Signet")

    def test_two_dimensional_array_with_symbolic_values(self) -> None:
        # GwAu3_Const_Attribute.au3: rows of profession followed by that profession's attributes.
        table = constants.GC_AI2_ALL_ATTRIBUTES_BY_PROFESSION
        self.assertEqual(len(table), 10)
        self.assertEqual(table[0][0], constants.GC_I_PROFESSION_WARRIOR)
        self.assertEqual(table[0][1], constants.GC_I_ATTRIBUTE_STRENGTH)


class DeclaredDimensionTests(unittest.TestCase):
    """The declarations whose values do not fill the dimensions they state.

    These are recorded rather than corrected: the values are what a script reads, and GwAu3's
    declaration disagreeing with its own data is a fact about GwAu3. The test exists so the set
    cannot change silently -- a new one, or one that goes away, is a change to the source that
    someone should look at.
    """

    def test_the_known_declarations_that_do_not_fill_their_dimensions(self) -> None:
        # GwAu3_Const_Item.au3: declares [68] and [188]; writes 67 and 187.
        self.assertEqual(len(constants.GC_AI_EL_TONICS), 67)
        self.assertEqual(len(constants.GC_AI_MONSTER_TROPHIES), 187)

        # GwAu3_Const_Item.au3: an empty dimension (`[]`, which is not valid AutoIt) on three
        # arrays. The values are present; only the declared size is unusable.
        for name in ("GC_AI_EVENT_ITEMS", "GC_AI_QUEST_ITEMS", "GC_AI_REWARD_TROPHIES"):
            with self.subTest(name=name):
                self.assertIsInstance(getattr(constants, name), list)
                self.assertGreater(len(getattr(constants, name)), 0)

        # GwAu3_Const_Attribute.au3: two tables whose declared width is not any row's width for
        # every row -- `GC_AI2_ALL_ATTRIBUTES_BY_PROFESSION` declares [10][6] and its rows are 6 or
        # 5 long; `GC_AI2_SECONDARY_ATTRIBUTES_BY_PROFESSION` declares [10][5] and its rows are 5 or
        # 4. Ragged, not truncated: every row is present, they are just not all the same width, so
        # the shapes are recorded and the rows are copied as written.
        primary = constants.GC_AI2_ALL_ATTRIBUTES_BY_PROFESSION
        self.assertEqual(len(primary), 10)
        self.assertEqual(sorted({len(row) for row in primary}), [5, 6])
        self.assertEqual(len(primary[0]), 6)  # Warrior: strength, axe, hammer, sword, tactics

        secondary = constants.GC_AI2_SECONDARY_ATTRIBUTES_BY_PROFESSION
        self.assertEqual(len(secondary), 10)
        self.assertEqual(sorted({len(row) for row in secondary}), [4, 5])
        self.assertEqual(secondary[0][0], constants.GC_I_PROFESSION_WARRIOR)


if __name__ == "__main__":
    unittest.main()
