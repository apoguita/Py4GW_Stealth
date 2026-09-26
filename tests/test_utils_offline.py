"""Offline tests for the ported ``Utils`` and ``Color`` classes.

Three things are pinned here, and none of them needs a client.

**The surface is the source's.** The 40 member names are read out of Reforged's own
``Py4GWCoreLib/py4gwcorelib_src/Utils.py`` at test time — not copied into this file — and compared
with what the port declares, in the source's order, so a member that is dropped, renamed or added
fails here. ``Color``'s surface is pinned the same way against ``py4gwcorelib_src/Color.py``.

**The values are the source's.** The source files are loaded *themselves* — with the two modules
they import that this project does not have stubbed (``PyImGui``, and the ``..enums`` re-export hub,
which is fed the constants the ported ``enums_src/GameData_enums.py`` declares) — and every
implemented member is called beside its ported counterpart over a table of inputs. That is a real
cross-check of the arithmetic rather than a second copy of it in the test: the 68-case base64 table,
the template encoder and parser, the markup regexes and the colour packing are all compared against
the code Reforged ships.

**The members that raise name what they still need.** ``TokenizeMarkupText`` (the client's ImGui text
measure) and ``GenerateSkillbarTemplate`` (the ``Skillbar`` class), and the default path of
``BalthazarSkillIdToDialogId`` (``Skill.ExtraData.GetIDPvP``), each raise ``NotImplementedError``
naming the work item. ``GwinchToPixels`` and ``PixelsToGwinch`` are the source's bodies and raise
from ``Map.MissionMap.GetScale``, which is Map's Stage 5 read — the source's own call graph.

The two modules are loaded under a private package name so the controller's own ``sys.modules`` keeps
only what it had; ``PyImGui`` is added for the duration of the load and removed again.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import agent as agent_module
from py4gw import player as player_module
from py4gw import skill as skill_module
from py4gw import skillbar as skillbar_module
from py4gw.map import Map
from py4gw.py4gwcorelib_src import color as color_module
from py4gw.py4gwcorelib_src import utils as utils_module
from py4gw.py4gwcorelib_src.color import Color, ColorPalette
from py4gw.py4gwcorelib_src.utils import Utils

#: Reforged's own files. They are the specification, so they are read and loaded rather than quoted.
SOURCE_ROOT = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib")
SOURCE_DIR = SOURCE_ROOT / "py4gwcorelib_src"
SOURCE_UTILS = SOURCE_DIR / "Utils.py"
SOURCE_COLOR = SOURCE_DIR / "Color.py"

#: The private package the source files are loaded under.
_PACKAGE = "_reforged_source_under_test"


def _load_source_modules() -> tuple[Any, Any, Any]:
    """Load the source's ``Color`` and ``Utils`` next to the port, with their gaps stubbed.

    ``Utils.py`` imports two things this project does not have: ``PyImGui`` (an in-client binding
    module) and ``..enums`` (``Py4GWCoreLib/enums.py``, a re-export hub for ``enums_src``). Both are
    supplied here so the *source's own bodies* can be executed and compared against the port; the
    ``..enums`` stub carries the same three constants the ported
    ``py4gw/enums_src/game_data_enums.py`` declares, which ``tests/test_enums_offline.py`` already
    pins against that file.

    Returns ``(source_color_module, source_utils_module, added_sys_modules)``.
    """

    added: list[str] = []

    def _register(name: str, module: types.ModuleType) -> types.ModuleType:
        if name not in sys.modules:
            added.append(name)
        sys.modules[name] = module
        return module

    parent = _register(_PACKAGE, types.ModuleType(_PACKAGE))
    parent.__path__ = [str(SOURCE_ROOT)]  # type: ignore[attr-defined]
    sub = _register(f"{_PACKAGE}.py4gwcorelib_src", types.ModuleType(f"{_PACKAGE}.py4gwcorelib_src"))
    sub.__path__ = [str(SOURCE_DIR)]  # type: ignore[attr-defined]

    _register("PyImGui", types.ModuleType("PyImGui"))

    enums = _register(f"{_PACKAGE}.enums", types.ModuleType(f"{_PACKAGE}.enums"))
    enums.__dict__.update(
        {
            "CAP_EXPERIENCE": utils_module.CAP_EXPERIENCE,
            "CAP_STEP": utils_module.CAP_STEP,
            "EXPERIENCE_PROGRESSION": utils_module.EXPERIENCE_PROGRESSION,
        }
    )

    color_spec = importlib.util.spec_from_file_location(
        f"{_PACKAGE}.py4gwcorelib_src.Color", SOURCE_COLOR
    )
    assert color_spec is not None and color_spec.loader is not None
    source_color = importlib.util.module_from_spec(color_spec)
    _register(f"{_PACKAGE}.py4gwcorelib_src.Color", source_color)
    color_spec.loader.exec_module(source_color)

    utils_spec = importlib.util.spec_from_file_location(
        f"{_PACKAGE}.py4gwcorelib_src.Utils", SOURCE_UTILS
    )
    assert utils_spec is not None and utils_spec.loader is not None
    source_utils = importlib.util.module_from_spec(utils_spec)
    _register(f"{_PACKAGE}.py4gwcorelib_src.Utils", source_utils)
    utils_spec.loader.exec_module(source_utils)

    return source_color, source_utils, added


if SOURCE_UTILS.is_file() and SOURCE_COLOR.is_file():
    SOURCE_COLOR_MODULE, SOURCE_UTILS_MODULE, _ADDED_MODULES = _load_source_modules()
    # ``PyImGui`` is the controller's again; the loaded source modules stay reachable through the
    # references above, which is all the comparisons below need.
    if "PyImGui" in _ADDED_MODULES:
        del sys.modules["PyImGui"]
else:  # pragma: no cover - the checkout is present in this project
    SOURCE_COLOR_MODULE = None
    SOURCE_UTILS_MODULE = None
    _ADDED_MODULES = []


requires_source = unittest.skipUnless(
    SOURCE_UTILS_MODULE is not None and SOURCE_COLOR_MODULE is not None,
    f"Reforged's Utils.py/Color.py are not at {SOURCE_DIR}",
)


def _source_color_class() -> Any:
    """Return the loaded source ``Color`` class, for the tests that need it."""

    assert SOURCE_COLOR_MODULE is not None, "the source Color.py was not loaded"
    return SOURCE_COLOR_MODULE.Color


class UtilsSurfaceTests(unittest.TestCase):
    """The port declares the source's surface, in the source's order, and nothing else."""

    def _source_text(self) -> str:
        if not SOURCE_UTILS.is_file():
            self.skipTest(f"Reforged's Utils.py is not at {SOURCE_UTILS}")
        return SOURCE_UTILS.read_text(encoding="utf-8")

    def _source_members(self) -> list[str]:
        return re.findall(r"^    def\s+(\w+)\s*\(", self._source_text(), re.M)

    def test_the_port_declares_every_source_member_in_order(self) -> None:
        """40 members, the source's names, the source's order — none missing, none added."""

        source_members = self._source_members()
        self.assertEqual(len(source_members), 40)

        ported = [
            name
            for name, value in vars(Utils).items()
            if isinstance(value, staticmethod)
        ]
        self.assertEqual(ported, source_members)

    def test_every_member_is_a_staticmethod(self) -> None:
        """The source declares every member as ``@staticmethod``; none takes ``self``."""

        for name in self._source_members():
            self.assertIsInstance(vars(Utils).get(name), staticmethod, msg=name)

    def test_the_class_body_holds_the_sources_import_and_nothing_else(self) -> None:
        """``Utils.py:13`` puts ``from typing import Tuple`` in the class body; so does the port.

        Nothing else belongs there: a class-body name that is not that import and not a member is a
        member the sources do not declare.
        """

        extras = {
            name
            for name in vars(Utils)
            if not name.startswith("__") and not isinstance(vars(Utils)[name], staticmethod)
        }
        self.assertEqual(extras, {"Tuple"})


class UtilsValueTests(unittest.TestCase):
    """Every implemented member returns the source's own value, over a table of inputs."""

    #: ``(member, argument tuples)``. Each call is made on the port and on the loaded source module
    #: and the two answers are compared, so the table carries inputs rather than expected values.
    CALLS: tuple[tuple[str, tuple[tuple[Any, ...], ...]], ...] = (
        ("HasFlag", ((0x0F, 0x01), (0x10, 0x01), (0, 0), (0xFFFF, 0xFFFF))),
        ("Distance", (((1.0, 1.0), (4.0, 5.0)), ((0.0, 0.0), (0.0, 0.0)), (None, (1.0, 1.0)), ((1.0, 1.0), None))),
        ("point_in_circle", ((0.0, 0.0, 0.0, 0.0, 5.0), (3.0, 4.0, 0.0, 0.0, 5.0), (6.0, 0.0, 0.0, 0.0, 5.0))),
        ("point_in_polygon", ((0.5, 0.5, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
                              (2.0, 2.0, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]))),
        ("IsPointInRect", ((5.0, 5.0, 0.0, 0.0, 10.0, 10.0), (11.0, 5.0, 0.0, 0.0, 10.0, 10.0))),
        ("format_bytes", ((0,), (512,), (1024,), (1536,), (1024 * 1024,), (3 * 1024 ** 3,), (5 * 1024 ** 4,))),
        ("RGBToNormal", ((255, 128, 0, 64), (0, 0, 0, 0))),
        ("RGBToDXColor", ((1, 2, 3, 4), (255, 255, 255, 255))),
        ("RGBToColor", ((1, 2, 3, 4), (255, 0, 128, 255))),
        ("ColorToTuple", ((0x04030201,), (0xFFFFFFFF,), (0,))),
        ("TupleToColor", (((1.0, 0.5, 0.0, 1.0),), ((0.0, 0.0, 0.0, 0.0),))),
        ("DegToRad", ((180.0,), (0.0,), (-90.0,))),
        ("RadToDeg", ((3.141592653589793,), (0.0,))),
        ("TrueFalseColor", ((True,), (False,), (0,), (1,))),
        ("GetFirstFromArray", (([7, 8],), ([],), (None,), (("a",),))),
        ("PixelsToUV", ((10, 20, 30, 40, 100, 200), (0, 0, 0, 0, 1, 1))),
        ("SafeInt", (("12",), (12.7,), (float("nan"),), (float("inf"),), (None,), ([],), (5, 3))),
        ("SafeFloat", (("12.5",), (12,), (float("nan"),), (None,), (1.5, 2.0))),
        ("split_uppercase", (("SomeVariableName",), ("lower",), ("",))),
        ("humanize_string", (("Some_VariableName",), ("plain",))),
        ("GetExperienceProgression", ((0,), (1000,), (50000,), (182599,), (182600,), (200000,), (500000,))),
        ("StripMarkup", (("<c=@gold>Hello</c>",), ("{s}bullet",), ("a<br>b",), ("<p>x</p>",), ("",), ("plain text",))),
        ("base64_to_bin64", (("A",), ("B",), ("z",), ("+",), ("/",), ("!",))),
        ("dec_to_bin64", ((0, 4), (14, 4), (5, 8), (1023, 10))),
        ("bin64_to_dec", (("000000",), ("100000",), ("111111",), ("",))),
        ("bin64_to_base64", (("000000",), ("100000010000",), ("1",))),
        ("encode_skill_template", ((1, 2, {}, []), (5, 6, {0: 12, 1: 9}, [1, 2, 3, 4, 5, 6, 7, 8]),
                                   (200, 300, {70: 12}, [1000] * 8))),
        ("ParseSkillbarTemplate", (("OQAAAA",), ("OQJTAYAsBQCOwUA",))),
        ("calculate_energy_pips", ((30.0, 0.75), (100.0, 1.0), (0.0, 0.0))),
        ("calculate_health_pips", ((480.0, 3.5), (600.0, -2.0), (0.0, 0.0))),
        ("SkillIdToDialogId", ((42,), (0,), (2000,))),
        ("BalthazarSkillIdToDialogId", ((42, False), (0, False), (70000, False))),
    )

    def _both(self, member: str, args: tuple[Any, ...]) -> tuple[Any, Any]:
        if SOURCE_UTILS_MODULE is None:
            self.skipTest("Reforged's Utils.py is not available")
        return getattr(Utils, member)(*args), getattr(SOURCE_UTILS_MODULE.Utils, member)(*args)

    def test_every_member_matches_the_source_over_the_table(self) -> None:
        """The arithmetic is the source's, compared call for call against the source's own code."""

        for member, argument_sets in self.CALLS:
            for args in argument_sets:
                with self.subTest(member=member, args=args):
                    ported, source = self._both(member, args)
                    self.assertEqual(ported, source)

    def test_the_normalized_colour_matches_the_sources_colour(self) -> None:
        """``NormalToColor`` returns the source's ``Color`` with the source's channel values."""

        if SOURCE_UTILS_MODULE is None:
            self.skipTest("Reforged's Utils.py is not available")
        for channels in ((1.0, 0.5, 0.0, 1.0), (0.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0, 1.0)):
            with self.subTest(channels=channels):
                ported = Utils.NormalToColor(channels)
                source = SOURCE_UTILS_MODULE.Utils.NormalToColor(channels)
                self.assertIsInstance(ported, Color)
                self.assertEqual(ported.to_tuple(), source.to_tuple())

    def test_the_template_encoder_and_parser_round_trip(self) -> None:
        """A template the member builds is read back by the member's own parser."""

        skills = [1, 2, 3, 4, 5, 6, 7, 8]
        attributes = {0: 12, 1: 9, 2: 3}
        template = Utils.encode_skill_template(5, 6, attributes, skills)
        self.assertIsInstance(template, str)
        self.assertNotEqual(template, "")

        prof_primary, prof_secondary, parsed_attributes, parsed_skills = Utils.ParseSkillbarTemplate(template)
        self.assertEqual((prof_primary, prof_secondary), (5, 6))
        self.assertEqual(parsed_attributes, attributes)
        self.assertEqual(parsed_skills, skills)

    def test_the_base_timestamp_is_milliseconds_into_the_utc_day(self) -> None:
        """``GetBaseTimestamp`` reads the host clock, so it is bounded rather than compared."""

        value = Utils.GetBaseTimestamp()
        self.assertIsInstance(value, int)
        self.assertGreaterEqual(value, 0)
        self.assertLess(value, 24 * 60 * 60 * 1000)


class UtilsRaisingTests(unittest.TestCase):
    """The members that are not built yet name themselves and their work item."""

    def test_tokenize_markup_text_names_the_client_im_gui_measure(self) -> None:
        """The wrapping needs ``PyImGui.calc_text_size``, which only the client can answer."""

        with self.assertRaises(NotImplementedError) as caught:
            Utils.TokenizeMarkupText("<c=@gold>hi</c>", 100.0)
        message = str(caught.exception)
        self.assertIn("TokenizeMarkupText", message)
        self.assertIn("PyImGui.calc_text_size", message)
        self.assertIn("The source's member works", message)

    def test_generate_skillbar_template_composes_the_sources_inputs(self) -> None:
        """``Utils.py:622-665``: eight slots, two professions, the positive attributes, encoded.

        The member is a composition, so the test drives it with the four reads it makes and checks
        the template it hands to ``encode_skill_template`` — including the two details the source's
        body decides: an attribute at level ``0`` is left out, and a ``None`` profession becomes
        ``0``.
        """

        skill_ids = {1: 5, 2: 0, 3: 42, 4: 0, 5: 0, 6: 0, 7: 0, 8: 7}
        attributes = [
            mock.Mock(attribute_id=0, level_base=12),
            mock.Mock(attribute_id=1, level_base=0),
            mock.Mock(attribute_id=2, level_base=9),
        ]
        expected_attributes = {0: 12, 2: 9}
        expected_skills = [5, 0, 42, 0, 0, 0, 0, 7]

        with mock.patch.object(
            skillbar_module.SkillBar,
            "GetSkillIDBySlot",
            staticmethod(lambda slot: skill_ids[slot]),
        ), mock.patch.object(
            agent_module.Agent, "GetProfessionIDs", staticmethod(lambda agent_id: (5, 6))
        ), mock.patch.object(
            agent_module.Agent, "GetAttributes", staticmethod(lambda agent_id: attributes)
        ), mock.patch.object(
            player_module.Player, "GetAgentID", staticmethod(lambda: 1234)
        ):
            template = Utils.GenerateSkillbarTemplate()

        self.assertEqual(
            template,
            Utils.encode_skill_template(5, 6, expected_attributes, expected_skills),
        )
        self.assertNotEqual(template, "")

    def test_generate_skillbar_template_turns_missing_professions_into_zero(self) -> None:
        """``Utils.py:642-645``: a ``None`` profession becomes ``0`` before encoding."""

        with mock.patch.object(
            skillbar_module.SkillBar, "GetSkillIDBySlot", staticmethod(lambda slot: 0)
        ), mock.patch.object(
            agent_module.Agent, "GetProfessionIDs", staticmethod(lambda agent_id: (None, None))
        ), mock.patch.object(
            agent_module.Agent, "GetAttributes", staticmethod(lambda agent_id: [])
        ), mock.patch.object(
            player_module.Player, "GetAgentID", staticmethod(lambda: 0)
        ):
            template = Utils.GenerateSkillbarTemplate()

        self.assertEqual(template, Utils.encode_skill_template(0, 0, {}, [0] * 8))

    def test_generate_skillbar_template_answers_empty_where_the_source_does(self) -> None:
        """``Utils.py:662-665``: any failure in the body answers ``""`` — the source's own handler.

        With nothing connected the first read inside the ``try`` fails, and the member's answer is
        the source's, not a raise: the body catches its own exception and returns the empty string.
        """

        with mock.patch("py4gw.client._current_client", None):
            self.assertEqual(Utils.GenerateSkillbarTemplate(), "")

    def test_the_default_balthazar_path_is_the_sources_remap(self) -> None:
        """``Utils.py:801-812``: the PvP id is remapped, then masked into the dialog id.

        The remap reads the skill constant record through the ported ``Skill`` class, so the record
        answer is supplied here and the member's own arithmetic is what is checked. The values are
        the branches the source's condition distinguishes: a real PvP id (remapped), the id
        unchanged, the ``0x0D6C`` sentinel (kept), and ``0`` (kept).
        """

        cases: tuple[tuple[int, int, int], ...] = (
            (42, 142, 0x10000000 | 142),
            (42, 42, 0x10000000 | 42),
            (42, 0x0D6C, 0x10000000 | 42),
            (42, 0, 0x10000000 | 42),
            (70000, 70001, 0x10000000 | (70001 & 0xFFFF)),
        )
        for skill_id, pvp_id, expected in cases:
            with self.subTest(skill_id=skill_id, pvp_id=pvp_id):
                with mock.patch.object(
                    skill_module.Skill.ExtraData,
                    "GetIDPvP",
                    staticmethod(lambda _skill_id, _pvp=pvp_id: _pvp),
                ):
                    self.assertEqual(Utils.BalthazarSkillIdToDialogId(skill_id), expected)

    def test_the_balthazar_remap_matches_the_source_for_the_same_pvp_id(self) -> None:
        """The port and the loaded source agree, given the same skill record."""

        if SOURCE_UTILS_MODULE is None:
            self.skipTest("Reforged's Utils.py is not available")

        stub = types.ModuleType(f"{_PACKAGE}.Skill")

        class _StubSkill:
            class ExtraData:
                @staticmethod
                def GetIDPvP(skill_id: int) -> int:
                    return 142

        stub.Skill = _StubSkill  # type: ignore[attr-defined]
        sys.modules[f"{_PACKAGE}.Skill"] = stub
        try:
            with mock.patch.object(
                skill_module.Skill.ExtraData,
                "GetIDPvP",
                staticmethod(lambda _skill_id: 142),
            ):
                for skill_id in (1, 42, 2000, 0, -1):
                    with self.subTest(skill_id=skill_id):
                        self.assertEqual(
                            Utils.BalthazarSkillIdToDialogId(skill_id),
                            SOURCE_UTILS_MODULE.Utils.BalthazarSkillIdToDialogId(skill_id),
                        )
        finally:
            sys.modules.pop(f"{_PACKAGE}.Skill", None)

    def test_the_balthazar_zero_guard_comes_before_the_remap(self) -> None:
        """``Utils.py:797-799``: a non-positive id answers ``0`` without reaching the remap.

        The source's guard is ``int(skill_id or 0) <= 0``, so ``None`` — a value a Python caller
        can pass where the binding would refuse the type — takes the same branch. That is the
        source's own truthiness test, not a guard this port added.
        """

        self.assertEqual(Utils.BalthazarSkillIdToDialogId(0), 0)
        self.assertEqual(Utils.BalthazarSkillIdToDialogId(-1), 0)
        self.assertEqual(Utils.BalthazarSkillIdToDialogId(None), 0)  # type: ignore[arg-type]


class UtilsDelegationTests(unittest.TestCase):
    """``GwinchToPixels``/``PixelsToGwinch`` are the source's bodies over ``Map``'s two reads."""

    def test_the_conversion_is_the_sources_arithmetic(self) -> None:
        """With ``Map``'s zoom and scale read, both members answer the source's value."""

        with mock.patch.object(Map.MissionMap, "GetZoom", staticmethod(lambda: 2.0)), \
                mock.patch.object(Map.MissionMap, "GetScale", staticmethod(lambda: (1.5, 1.0))):
            pixels = Utils.GwinchToPixels(96.0)
            self.assertEqual(pixels, 96.0 * (1.5 * 2.0) / 96.0)
            self.assertEqual(Utils.PixelsToGwinch(pixels), 96.0)
            self.assertEqual(Utils.GwinchToPixels(96.0, 0.5), 96.0 * (1.5 * 2.5) / 96.0)

    def test_the_scale_read_is_where_the_raise_comes_from(self) -> None:
        """``GetZoom`` is ported; ``GetScale`` is Map's Stage 5 read, so the raise names it."""

        with mock.patch.object(Map.MissionMap, "GetZoom", staticmethod(lambda: 2.0)):
            with self.assertRaises(NotImplementedError) as caught:
                Utils.GwinchToPixels(96.0)
        self.assertIn("MissionMap.GetScale", str(caught.exception))


class UtilsAdaptationTests(unittest.TestCase):
    """The two departures from the source's text, and the reason each exists."""

    def test_the_module_does_not_import_py_im_gui(self) -> None:
        """``Utils.py:6`` imports ``PyImGui``; this port loads no in-client binding module."""

        if not SOURCE_UTILS.is_file():
            self.skipTest(f"Reforged's Utils.py is not at {SOURCE_UTILS}")
        self.assertIn("import PyImGui", SOURCE_UTILS.read_text(encoding="utf-8"))
        self.assertFalse(hasattr(utils_module, "PyImGui"))

    def test_the_constants_come_from_the_port_of_the_module_that_declares_them(self) -> None:
        """``Utils.py:11`` reaches them through ``..enums``; here they are the ported declarations."""

        from py4gw.enums_src import game_data_enums

        self.assertIs(utils_module.CAP_EXPERIENCE, game_data_enums.CAP_EXPERIENCE)
        self.assertIs(utils_module.CAP_STEP, game_data_enums.CAP_STEP)
        self.assertIs(utils_module.EXPERIENCE_PROGRESSION, game_data_enums.EXPERIENCE_PROGRESSION)

    def test_clear_sub_modules_unloads_matching_modules_and_skips_persistent_ones(self) -> None:
        """``Utils.py:814-841``: every match goes, a ``PERSISTENT`` one stays.

        The source logs each decision to Reforged's console inside the client, which has no external
        equivalent; the decisions themselves are what the port carries, and this drives both.
        """

        prefix = "_utils_port_test_module"
        plain = types.ModuleType(f"{prefix}_plain")
        persistent = types.ModuleType(f"{prefix}_persistent")
        persistent.PERSISTENT = True  # type: ignore[attr-defined]
        sys.modules[plain.__name__] = plain
        sys.modules[persistent.__name__] = persistent
        try:
            Utils.ClearSubModules(prefix)
            self.assertNotIn(plain.__name__, sys.modules)
            self.assertIn(persistent.__name__, sys.modules)
        finally:
            sys.modules.pop(plain.__name__, None)
            sys.modules.pop(persistent.__name__, None)

    def test_the_console_lines_the_source_emits_are_not_ported(self) -> None:
        """The source's ``ConsoleLog`` calls are diagnostics, and there is no external console.

        The divergence is the same one already recorded for ``Agent``'s ``PySystem.Console``: the
        decisions are carried, the log lines are not. This asserts the code rather than the
        docstring — the docstring names the missing console on purpose.
        """

        if not SOURCE_UTILS.is_file():
            self.skipTest(f"Reforged's Utils.py is not at {SOURCE_UTILS}")
        self.assertIn("ConsoleLog(", SOURCE_UTILS.read_text(encoding="utf-8"))
        self.assertNotIn("ConsoleLog(", inspect.getsource(Utils.ClearSubModules))

    def test_get_experience_progression_returns_the_percentage_the_source_returns(self) -> None:
        """The source's docstring says a tuple; its body returns the percentage (``Utils.py:221-246``).

        Ported as written, and pinned here so a later pass does not "fix" it into the docstring.
        """

        self.assertIsInstance(Utils.GetExperienceProgression(1000), float)
        self.assertIsInstance(Utils.GetExperienceProgression(500000), float)


class ColorSurfaceTests(unittest.TestCase):
    """``Color`` and ``ColorPalette`` declare the source's surface."""

    def _source_text(self) -> str:
        if not SOURCE_COLOR.is_file():
            self.skipTest(f"Reforged's Color.py is not at {SOURCE_COLOR}")
        return SOURCE_COLOR.read_text(encoding="utf-8")

    def _source_class_members(self, name: str) -> list[str]:
        tree = ast.parse(self._source_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                return [
                    child.name
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
        return []

    def test_the_color_class_declares_every_source_member(self) -> None:
        """Every ``def`` the source's ``Color`` has exists on the port's, in the same order."""

        source_members = self._source_class_members("Color")
        self.assertTrue(source_members)
        ported = [
            name
            for name, value in vars(Color).items()
            if callable(value) or isinstance(value, (staticmethod, classmethod, property))
        ]
        self.assertEqual(ported, source_members)

    def test_the_palette_declares_every_source_member(self) -> None:
        """The palette's names and their values are the source's, member for member."""

        source_members = [
            name
            for name, _ in ColorPalette.__members__.items()
        ]
        if SOURCE_COLOR_MODULE is None:
            self.skipTest("Reforged's Color.py is not available")
        source_palette = list(SOURCE_COLOR_MODULE.ColorPalette.__members__.items())
        self.assertEqual(source_members, [name for name, _ in source_palette])

        for name, member in source_palette:
            with self.subTest(member=name):
                self.assertEqual(ColorPalette[name].color.to_tuple(), member.color.to_tuple())

    def test_the_palette_helpers_answer_the_sources_values(self) -> None:
        """``GetColor``/``ListColors``/``HasColor`` (``Color.py:401-412``)."""

        if SOURCE_COLOR_MODULE is None:
            self.skipTest("Reforged's Color.py is not available")
        for name in ("GwGold", "gw gold", "  GW_GOLD ", "not a colour", ""):
            with self.subTest(name=name):
                ported = ColorPalette.GetColor(name)
                source = SOURCE_COLOR_MODULE.ColorPalette.GetColor(name)
                self.assertEqual(ported.to_tuple(), source.to_tuple())
                self.assertEqual(ColorPalette.HasColor(name), SOURCE_COLOR_MODULE.ColorPalette.HasColor(name))
        self.assertEqual(ColorPalette.ListColors(), SOURCE_COLOR_MODULE.ColorPalette.ListColors())


@requires_source
class ColorValueTests(unittest.TestCase):
    """``Color``'s arithmetic is the source's, compared against the loaded source class."""

    def test_the_packers_and_unpackers_match(self) -> None:
        """ABGR and ARGB packing, in both directions, over the same channel values."""

        source_color = _source_color_class()
        for channels in ((255, 0, 128, 255), (1, 2, 3, 4), (0, 0, 0, 0), (255, 255, 255, 255)):
            r, g, b, a = channels
            with self.subTest(channels=channels):
                self.assertEqual(Color(r, g, b, a).to_color(), source_color(r, g, b, a).to_color())
                self.assertEqual(Color(r, g, b, a).to_dx_color(), source_color(r, g, b, a).to_dx_color())
                self.assertEqual(Color(r, g, b, a).to_argb(), source_color(r, g, b, a).to_argb())
                self.assertEqual(Color(r, g, b, a).to_abgr(), source_color(r, g, b, a).to_abgr())

                packed = source_color(r, g, b, a).to_color()
                ported = Color()
                ported.from_color(packed)
                source_restored = source_color()
                source_restored.from_color(packed)
                self.assertEqual(ported.to_tuple(), source_restored.to_tuple())

    def test_the_transforms_match(self) -> None:
        """Desaturate, saturate, shift, opacity and negate, over the same colours."""

        source_color = _source_color_class()
        for channels in ((200, 100, 50, 255), (10, 10, 10, 128), (0, 255, 0, 255)):
            for amount in (0.0, 0.25, 1.0):
                with self.subTest(channels=channels, amount=amount):
                    ported = Color(*channels)
                    source = source_color(*channels)
                    self.assertEqual(ported.desaturate(amount).to_tuple(), source.desaturate(amount).to_tuple())
                    self.assertEqual(ported.saturate(amount).to_tuple(), source.saturate(amount).to_tuple())
                    self.assertEqual(ported.opacity(amount).to_tuple(), source.opacity(amount).to_tuple())
                    self.assertEqual(ported.Negate().to_tuple(), source.Negate().to_tuple())
            with self.subTest(channels=channels, shift=True):
                ported_target = Color(1, 2, 3, 4)
                source_target = source_color(1, 2, 3, 4)
                self.assertEqual(
                    Color(*channels).shift(ported_target, 0.5).to_tuple(),
                    source_color(*channels).shift(source_target, 0.5).to_tuple(),
                )

    def test_the_string_and_json_forms_match(self) -> None:
        """``to_hex``/``from_hex``, ``to_rgba_string``/``from_rgba_string`` and the JSON pair."""

        source_color = _source_color_class()
        for channels in ((255, 0, 128, 255), (1, 2, 3, 4)):
            with self.subTest(channels=channels):
                ported = Color(*channels)
                source = source_color(*channels)
                self.assertEqual(ported.to_hex(), source.to_hex())
                self.assertEqual(ported.to_hex(include_alpha=False), source.to_hex(include_alpha=False))
                self.assertEqual(ported.to_rgba_string(), source.to_rgba_string())
                self.assertEqual(ported.to_json(), source.to_json())
                self.assertEqual(Color.from_hex(source.to_hex()).to_tuple(), source.to_tuple())
                self.assertEqual(Color.from_hex(source.to_hex(False)).to_tuple(), source.from_hex(source.to_hex(False)).to_tuple())
                self.assertEqual(Color.from_rgba_string(source.to_rgba_string()).to_tuple(), source.to_tuple())

    def test_the_normalized_and_float_tuple_forms_match(self) -> None:
        """``from_tuple``, ``from_tuple_normalized``, ``from_float_tuple`` and their inverses."""

        source_color = _source_color_class()
        normalized = (1.0, 0.5, 0.0, 1.0)
        self.assertEqual(
            Color.from_tuple(normalized).to_tuple(),
            source_color.from_tuple(normalized).to_tuple(),
        )
        self.assertEqual(
            Color.from_tuple_normalized(normalized).to_tuple(),
            source_color.from_tuple_normalized(normalized).to_tuple(),
        )
        self.assertEqual(
            Color.from_float_tuple((255.0, 128.0, 0.0, 255.0)).to_tuple(),
            source_color.from_float_tuple((255.0, 128.0, 0.0, 255.0)).to_tuple(),
        )
        self.assertEqual(
            Color(255, 128, 0, 64).to_tuple_normalized(),
            source_color(255, 128, 0, 64).to_tuple_normalized(),
        )
        self.assertEqual(Color(255, 128, 0, 64).rgb_tuple, source_color(255, 128, 0, 64).rgb_tuple)
        self.assertEqual(Color(255, 128, 0, 64).color_tuple, source_color(255, 128, 0, 64).color_tuple)
        self.assertEqual(Color(255, 128, 0, 64).color_int, source_color(255, 128, 0, 64).color_int)

    def test_the_clamping_and_equality_match(self) -> None:
        """``set_rgba`` clamps, and equality is by channel tuple (``Color.py:12-14, 159-166``)."""

        source_color = _source_color_class()
        ported = Color()
        source = source_color()
        ported.set_rgba(-5, 300, 128, 0)
        source.set_rgba(-5, 300, 128, 0)
        self.assertEqual(ported.to_tuple(), source.to_tuple())
        self.assertEqual(ported, Color(0, 255, 128, 0))
        self.assertNotEqual(ported, Color(0, 255, 128, 1))
        self.assertEqual(hash(ported), hash(Color(0, 255, 128, 0)))
