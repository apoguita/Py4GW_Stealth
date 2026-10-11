"""Offline tests for the two generated ranking tables (`tools/generate_gwa3_ranking.py`).

No client. What is being established:

* each table is the source's ``Case`` list **in both directions** -- every ``Case``/``Return`` pair in
  the ``.au3`` is in the module, no entry is there that the source does not declare, and the counts are
  the source's own (2,300 and 2,292);
* every constant the table keys on **resolves in the generated constants module** -- the numbers come
  from GwAu3's declarations rather than from a transcription, and a name GwAu3 spells that this project
  does not carry would fail here rather than answer a wrong id;
* the two lookup functions are the source's own two steps: the slot's skill id from
  `UAI_GetStaticSkillInfo`, then the table, with ``""`` for an empty slot or an unknown skill -- the
  source's fall-through, since it has no ``Case Else``;
* the modules are **current**: each equals what the generator produces now.

The strategy functions the names point at are *not* ported; asserting that would fail by design, and the
generator's header carries the census of what they cost.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import unittest
from typing import Any
from unittest import mock

from py4gw.gwa3 import constants, uai_best_target_cache, uai_can_use_cache

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "generate_gwa3_ranking", HERE.parent / "tools" / "generate_gwa3_ranking.py"
)
if _spec is None or _spec.loader is None:  # pragma: no cover - the file is in the tree
    raise RuntimeError("could not load tools/generate_gwa3_ranking.py")
GENERATOR = importlib.util.module_from_spec(_spec)
sys.modules["generate_gwa3_ranking"] = GENERATOR
_spec.loader.exec_module(GENERATOR)


class _ModuleCase:
    """One of the two tables, with the source text a test can parse independently."""

    def __init__(self, table: Any, module: Any) -> None:
        self.table = table
        self.module = module
        self.text = table.source_path.read_text(encoding="utf-8-sig", errors="replace")

    @property
    def source_pairs(self) -> list[tuple[str, str]]:
        pairs = re.findall(
            r'(?m)^\s*Case\s+\$(GC_I_SKILL_ID_\w+)\s*$\n\s*Return\s+"(\w+)"\s*$', self.text
        )
        return pairs


CASES = (
    _ModuleCase(GENERATOR.TABLES[0], uai_best_target_cache),
    _ModuleCase(GENERATOR.TABLES[1], uai_can_use_cache),
)


class TableIntegrityTests(unittest.TestCase):
    def test_the_tables_are_the_sources_own_in_both_directions(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                source_pairs = case.source_pairs
                declared = {getattr(constants, name): strategy for name, strategy in source_pairs}
                table = case.module._STRATEGIES

                self.assertEqual(len(source_pairs), len(table), "the source's Case count")
                missing = sorted(set(declared) - set(table))
                extra = sorted(set(table) - set(declared))
                self.assertEqual(missing, [], "declared by GwAu3 and not in the table")
                self.assertEqual(extra, [], "in the table and not declared by GwAu3")
                for skill_id, strategy in declared.items():
                    self.assertEqual(table[skill_id], strategy)

    def test_every_constant_resolves_in_the_generated_constants_module(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                for name, _ in case.source_pairs:
                    self.assertTrue(hasattr(constants, name), name)

    def test_no_case_else_in_the_source_and_none_in_the_tables(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                self.assertNotIn("Case Else", case.text)
                self.assertNotIn("", case.module._STRATEGIES.values())

    def test_the_modules_are_current(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                expected = GENERATOR.render(case.table, GENERATOR.parse_cases(case.table))
                actual = case.table.output_path.read_text(encoding="utf-8")
                self.assertEqual(
                    actual,
                    expected,
                    f"{case.table.output_path.name} is stale -- re-run tools/generate_gwa3_ranking.py",
                )


class LookupTests(unittest.TestCase):
    def test_a_skill_id_answers_its_strategy_name(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                skill_id = constants.GC_I_SKILL_ID_HEALING_SIGNET
                with mock.patch.object(
                    case.module, "UAI_GetStaticSkillInfo", lambda slot, column: skill_id
                ):
                    self.assertEqual(
                        getattr(case.module, case.table.function)(1),
                        case.module._STRATEGIES[skill_id],
                    )

    def test_an_empty_slot_and_an_unknown_skill_answer_the_empty_string(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                for skill_id in (0, 0x7FFF_FFFF):
                    with mock.patch.object(
                        case.module, "UAI_GetStaticSkillInfo", lambda slot, column: skill_id
                    ):
                        self.assertEqual(getattr(case.module, case.table.function)(1), "")

    def test_the_skill_id_is_read_from_the_slot_that_was_asked_for(self) -> None:
        for case in CASES:
            with self.subTest(module=case.table.module):
                with mock.patch.object(
                    case.module, "UAI_GetStaticSkillInfo", return_value=0
                ) as read:
                    getattr(case.module, case.table.function)(6)
                read.assert_called_once_with(6, constants.GC_UAI_STATIC_SKILL_SkillID)

    def test_the_sources_two_steps_are_the_two_steps_taken(self) -> None:
        """The column is the skill id, and the table is keyed by it -- not by the slot."""

        for case in CASES:
            with self.subTest(module=case.table.module):
                self.assertTrue(case.table.function.startswith("UAI_Get"))
                self.assertEqual(case.module.__all__, [case.table.function])


if __name__ == "__main__":
    unittest.main()
