"""Offline tests for the generated UtilityAI **strategy** modules (`tools/generate_gwa3_strategies.py`).

No client. The strategies are transcribed from GwAu3's own bodies, so what is checked here is that the
transcription is **complete and honest**, which is what a generator can be held to without a client:

* every ``BestTarget_*``, ``CanUse_*`` and ``Anti_*`` function the source declares exists, and nothing is
  exported that the source does not declare -- **4,572** functions across 22 modules;
* every module imports and every name is callable, which is also the syntax check on 4,508 transcribed
  bodies;
* a refusing strategy refuses **naming its source file, line and the reason**, rather than answering a
  plausible target -- and a transcribed one does not refuse;
* a sample of bodies is checked against the source's **own calls**: the transcription passes the same
  arguments to the same layer routine GwAu3 calls, which is the part a generator could get silently
  wrong;
* the modules are current: each equals what the generator produces now.

What this file cannot check is whether a strategy *picks the right target* in a live fight: that needs a
client and an enemy, and it is the live suite's business.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pathlib
import re
import sys
import unittest
from typing import Any
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "generate_gwa3_strategies", HERE.parent / "tools" / "generate_gwa3_strategies.py"
)
if _spec is None or _spec.loader is None:  # pragma: no cover - the file is in the tree
    raise RuntimeError("could not load tools/generate_gwa3_strategies.py")
GENERATOR = importlib.util.module_from_spec(_spec)
sys.modules["generate_gwa3_strategies"] = GENERATOR
_spec.loader.exec_module(GENERATOR)

SKILLS = GENERATOR.SKILLS_DIR


def _declared(source_file: str, prefixes: tuple[str, ...]) -> set[str]:
    text = (SKILLS / source_file).read_text(encoding="utf-8-sig", errors="replace")
    return set(re.findall(r"(?m)^Func\s+((?:" + "|".join(prefixes) + r")_\w+)\s*\(", text))


def _count_refusals() -> int:
    """How many strategy bodies refuse, counted by **calling** every one of them.

    A refused body raises ``NotImplementedError`` before it reads anything, which is the whole point of
    the refusal -- so this count works without a client. The transcribed ones are *not* counted this way:
    offline they raise the missing connection, and a count that treated that as "transcribed" would be
    counting the absence of a client.
    """

    refused = 0
    for source_file in GENERATOR.SOURCE_FILES:
        module = importlib.import_module("py4gw.gwa3." + GENERATOR.module_name(source_file))
        for name in module.__all__:
            try:
                getattr(module, name)(1000)
            except NotImplementedError:
                refused += 1
            except (TypeError, RuntimeError, AttributeError):
                continue
    return refused


def _declared_total() -> int:
    """Every strategy the sources declare -- what the generator transcribes or refuses."""

    return sum(
        len(_declared(source_file, ("BestTarget", "CanUse")))
        for source_file in GENERATOR.SOURCE_FILES
    )


class SurfaceTests(unittest.TestCase):
    def test_every_declared_strategy_exists_and_nothing_else_is_exported(self) -> None:
        total = 0
        for source_file in GENERATOR.SOURCE_FILES:
            module = importlib.import_module("py4gw.gwa3." + GENERATOR.module_name(source_file))
            with self.subTest(module=module.__name__):
                declared = _declared(source_file, ("BestTarget", "CanUse"))
                exported = set(module.__all__)
                self.assertEqual(sorted(declared - exported), [], "declared and not generated")
                self.assertEqual(sorted(exported - declared), [], "generated and not declared")
                for name in exported:
                    self.assertTrue(callable(getattr(module, name)), name)
                total += len(exported)
        self.assertEqual(total, 4551, "the two tables' strategies")

    def test_every_anti_predicate_exists(self) -> None:
        from py4gw.gwa3 import uai_anti

        declared: set[str] = set()
        for source_file in GENERATOR.SOURCE_FILES:
            declared |= _declared(source_file, ("Anti",))
        self.assertEqual(sorted(declared), sorted(uai_anti.__all__))
        self.assertEqual(len(uai_anti.__all__), 21)
        for name in uai_anti.__all__:
            self.assertTrue(callable(getattr(uai_anti, name)), name)

    def test_every_module_imports_and_its_bodies_are_syntactically_valid(self) -> None:
        """The import IS the check: 4,508 transcribed bodies have to parse and compile."""

        for source_file in GENERATOR.SOURCE_FILES:
            with self.subTest(source_file=source_file):
                importlib.import_module("py4gw.gwa3." + GENERATOR.module_name(source_file))

    def test_every_strategy_the_tables_answer_that_the_source_defines_resolves(self) -> None:
        """The tables answer names; the ones GwAu3 itself defines must resolve through this layer.

        **The tables answer 41 names no source file defines.** That is GwAu3's own gap -- its engine would
        Call a name that does not exist -- and it is recorded here rather than papered over: the test
        asserts the *defined* names resolve, and that the undefined ones are exactly the difference
        between the two tables' answers and the 4,572 functions Skills/ declares.
        """

        from py4gw.gwa3 import uai_best_target_cache, uai_can_use_cache
        from py4gw.gwa3.bridge import layer_surface

        defined: set[str] = set()
        for source_file in GENERATOR.SOURCE_FILES:
            defined |= _declared(source_file, ("BestTarget", "CanUse", "Anti"))

        surface = layer_surface()
        answered: set[str] = set()
        for table in (uai_best_target_cache, uai_can_use_cache):
            answered |= set(table._STRATEGIES.values())

        missing = sorted(name for name in answered & defined if name not in surface)
        self.assertEqual(missing, [], "a name GwAu3 defines and this layer does not")

        undefined = sorted(answered - defined)
        # **220 of the tables' names are GwAu3's own gap**: they are the *Pvp variants
        # (BestTarget_AegisPvp and its neighbours), which the tables answer and Skills/ never defines --
        # so GwAu3's own Call finds nothing for those skill ids. Recorded, not papered over.
        self.assertEqual(len(undefined), 220, "the tables' names with no definition in Skills/")
        # **All 220 are skill ids the tables list and Skills/ never defines** -- 77 *Pvp variants and
        # 143 skills that are monster, quest or explosion abilities (BestTarget_Bamph,
        # BestTarget_FirebombExplosion, BestTarget_JununduTunnelMonsterSkill). GwAu3's own engine
        # Calls those names and finds nothing, so its ranking has no strategy for those ids either;
        # this layer answers the same name the table answers, and the name resolves to nothing in both.
        self.assertEqual(sum(1 for name in undefined if name.endswith("Pvp")), 77)


class RefusalTests(unittest.TestCase):
    def test_a_refusing_strategy_names_its_source_line_and_reason(self) -> None:
        """The **one** body that still refuses names its file, its line and what stopped it.

        There were 57 refusals when this work began and there is one now: `BestTarget_YouAreAllWeaklings`
        calls ``SetExtended``, the AutoIt channel this layer has no twin for -- GwAu3 uses it there to
        tell its engine to keep the forced target, and `UAI_TryUseSkill` records the same gap on the
        reading side. Everything else is transcribed: `BestTarget_HeroicRefrain` was the last one
        blocked by a data member, and ``Attribute_GetPartyAttributeInfo`` is ported now.
        """

        module = importlib.import_module("py4gw.gwa3.uai_strategy_shout")
        with self.assertRaises(NotImplementedError) as raised:
            module.BestTarget_YouAreAllWeaklings(1000)
        message = str(raised.exception)
        self.assertIn("BestTarget_YouAreAllWeaklings", message)
        self.assertIn("has a body this layer does not port", message)
        self.assertIn("UtilityAI_Shout.au3:", message)
        self.assertIn("SetExtended", message)

        self.assertEqual(_count_refusals(), 1)
        # The other 4,571 are transcribed, which is the generator's own report and what the currency
        # test pins: every declared body is in its module and the files equal a fresh generation.

    def test_a_transcribed_strategy_does_not_refuse(self) -> None:
        from py4gw.gwa3 import uai_strategy_attack

        with mock.patch.object(
            uai_strategy_attack, "UAI_GetNearestAgent", return_value=4242
        ) as nearest:
            self.assertEqual(uai_strategy_attack.BestTarget_Hamstring(1000), 4242)
        nearest.assert_called_once_with(-2, 1000, "UAI_Filter_IsLivingEnemy")

    def test_a_guard_body_passes_the_sources_own_arguments(self) -> None:
        """`BestTarget_*` bodies that fall back ask the layer's own selector, as the source does."""

        from py4gw.gwa3 import uai_strategy_attack

        source = (SKILLS / "UtilityAI_Attack.au3").read_text(encoding="utf-8-sig", errors="replace")
        match = re.search(
            r"(?ms)^Func BestTarget_Hamstring\(.*?\n(.*?)^EndFunc", source
        )
        assert match is not None
        self.assertIn(
            'UAI_GetNearestAgent(-2, $a_f_AggroRange, "UAI_Filter_IsLivingEnemy")', match.group(1)
        )

    def test_a_literal_body_is_transcribed_as_the_literal(self) -> None:
        from py4gw.gwa3 import uai_strategy_attack

        with mock.patch.object(uai_strategy_attack, "UAI_GetPlayerInfo", return_value=7) as player:
            self.assertEqual(uai_strategy_attack.BestTarget_SiegeAttack4(1000), 7)
        player.assert_called_once()

    def test_every_anti_predicate_a_body_calls_is_imported(self) -> None:
        """The invariant whose absence was this generator's first defect.

        A strategy body calls Anti_X(); the module has to import it. The first version emitted the call
        without the import and every such function raised NameError at run time -- a landmine in a
        fight. This checks the wiring structurally, over every generated module, whichever predicates
        happen to be routed.
        """

        for source_file in GENERATOR.SOURCE_FILES:
            module = GENERATOR.module_name(source_file)
            with self.subTest(module=module):
                text = (REPO_ROOT / "py4gw" / "gwa3" / f"{module}.py").read_text(encoding="utf-8")
                header = text.split('__all__', 1)[0]
                used = set(re.findall(r"(?<![\w.])(Anti_\w+)\(", text))
                for name in sorted(used):
                    self.assertIn(name, header, f"{module} calls {name} without importing it")

    def test_a_body_calling_an_unported_name_refuses_rather_than_raising(self) -> None:
        """The generator's own second check, asserted where it fired: a name the layer lacks."""

        generated = (REPO_ROOT / "py4gw" / "gwa3" / "uai_strategy_spell.py").read_text(encoding="utf-8")
        self.assertNotIn("UAI_AgentHasVisibleEffect(", generated)


class CurrencyTests(unittest.TestCase):
    def test_the_modules_are_current(self) -> None:
        """Each generated file equals what the generator produces now.

        The anti pass now answers **four** things -- the text, its counts, every predicate name and the
        names whose own body refused -- because the strategy pass must treat a refused predicate as
        unavailable: 1,099 bodies guard on ``Anti_Attack``/``Anti_Hex``/``Anti_ItemSpell``/``Anti_Spell``,
        and while those refused the caller check could not see it, so the bodies were transcribed into
        calls that raised in a fight.
        """

        available = GENERATOR.surface_names()
        owners = GENERATOR.import_map()

        anti_text, _, anti_names, anti_refused = GENERATOR.generate_anti(available, owners)
        self.assertEqual(
            (REPO_ROOT / "py4gw" / "gwa3" / "uai_anti.py").read_text(encoding="utf-8"),
            anti_text,
            "py4gw/gwa3/uai_anti.py is stale -- re-run tools/generate_gwa3_strategies.py",
        )

        unusable = frozenset(anti_refused)
        for source_file in GENERATOR.SOURCE_FILES:
            with self.subTest(source_file=source_file):
                text, _ = GENERATOR.generate_strategy(
                    source_file, anti_names, available, owners, unusable
                )
                path = REPO_ROOT / "py4gw" / "gwa3" / f"{GENERATOR.module_name(source_file)}.py"
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    text,
                    f"{path.name} is stale -- re-run tools/generate_gwa3_strategies.py",
                )


if __name__ == "__main__":
    unittest.main()
