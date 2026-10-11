"""Offline tests for the GwAu3 route map and the generator that produces it.

The route map's value is entirely in its citations: a row that names a Stealth member which does not
exist is worse than a row that admits it has no route, because it reads as work already done. This
suite exists because exactly that happened while the map was being written -- five rows cited
``Agent.GetDistance``, ``GetDistanceToXY``, ``GetDistanceSq``, ``GetNpcInfoByAgentID`` and
``GetBestTarget``, and **none of those five members exists anywhere in ``py4gw/``**. Grepping for them
is what found it.

So the tests here check the map's two mechanical properties: every citation resolves, and the map
covers the surface it claims to.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

# The generator is a script, not an installed module; load it by path so a test can read ROUTES.
_spec = importlib.util.spec_from_file_location(
    "generate_gwa3_route_map", HERE.parent / "tools" / "generate_gwa3_route_map.py"
)
if _spec is None or _spec.loader is None:  # pragma: no cover - the file is in the tree
    raise RuntimeError("could not load tools/generate_gwa3_route_map.py for its ROUTES table")
GENERATOR = importlib.util.module_from_spec(_spec)
sys.modules["generate_gwa3_route_map"] = GENERATOR
_spec.loader.exec_module(GENERATOR)

# `py4gw/<path>.py:<line>` or `py4gw/<path>.py:<line>-<line>`, with an optional trailing comment in
# parentheses. A citation that names no line (`py4gw/agent.py (GetDistance)`) is deliberately NOT
# matched, so it fails the "every citation carries a line" test below.
FILE_LINE = re.compile(r"(?P<path>py4gw/[\w/]+\.py):(?P<line>\d+)")


class RouteCitationTests(unittest.TestCase):
    """Every route that names a Stealth member cites a real file and line."""

    def test_every_route_citation_carries_a_line_number(self) -> None:
        missing = [
            f"{name}: {route.citation!r}"
            for name, route in GENERATOR.ROUTES.items()
            if route.citation and not FILE_LINE.search(route.citation)
        ]
        self.assertEqual(missing, [], "these citations name a file but no line number")

    def test_every_cited_file_exists(self) -> None:
        bad: list[str] = []
        for name, route in GENERATOR.ROUTES.items():
            for match in FILE_LINE.finditer(route.citation):
                if not (REPO_ROOT / match.group("path")).is_file():
                    bad.append(f"{name}: {match.group('path')}")
        self.assertEqual(bad, [], "these citations name a file that does not exist")

    def test_every_cited_line_is_inside_its_file(self) -> None:
        bad: list[str] = []
        for name, route in GENERATOR.ROUTES.items():
            for match in FILE_LINE.finditer(route.citation):
                path = REPO_ROOT / match.group("path")
                if not path.is_file():
                    continue
                line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
                if int(match.group("line")) > line_count:
                    bad.append(f"{name}: {match.group('path')}:{match.group('line')} > {line_count} lines")
        self.assertEqual(bad, [], "these citations point past the end of their file")

    def test_a_route_names_a_member_or_explains_why_not(self) -> None:
        """A row with no member must carry a note -- that note is the work item."""

        bare = [
            name
            for name, route in GENERATOR.ROUTES.items()
            if not route.member and not route.note
        ]
        self.assertEqual(bare, [], "these entries have neither a member nor an explanation")


class RouteCoverageTests(unittest.TestCase):
    """The map against the surface it is generated from."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.declared = GENERATOR.parse_declarations()
        cls.by_name = {function.name: function for function in cls.declared}

    def test_the_declared_surface_is_parsed(self) -> None:
        # 645 was the count from the session's one-line-per-declaration index, which three
        # inventories found to be missing functions. The parser here reads the sources directly, so
        # it must find at least those 645 plus the known misses.
        self.assertGreaterEqual(len(self.declared), 648, "the parser is missing declarations")

    def test_the_known_misses_are_present(self) -> None:
        # Each of these was missed by the regex extraction and found by an inventory reading the
        # source line by line. They are the regression check for the parser.
        for name, file, line in (
            ("Party_LockHeroTarget", "GwAu3_Cmd_Party.au3", 55),
            ("Party_SetHeroAggression", "GwAu3_Cmd_Party.au3", 60),
            ("PreGame_CharName", "GwAu3_Data_PreGame.au3", 19),
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.by_name, f"{name} was not parsed")
                self.assertEqual(self.by_name[name].file, file)
                self.assertEqual(self.by_name[name].line, line)

    def test_every_route_key_is_a_function_gwau3_declares(self) -> None:
        """A route for a name GwAu3 does not declare would be this project inventing a function."""

        declared = set(self.by_name)
        unknown = sorted(name for name in GENERATOR.ROUTES if name not in declared)
        self.assertEqual(
            unknown,
            [],
            "these ROUTES keys are not GwAu3 function names -- an invented name, or a typo",
        )

    def test_every_route_has_a_tier(self) -> None:
        for name in GENERATOR.ROUTES:
            with self.subTest(name=name):
                tier, reason = GENERATOR.tier_for(name, "")
                self.assertIn(
                    tier,
                    ("ROUTED", "REFUSED", "NOT APPLICABLE", "NO ROUTE YET"),
                    f"{name} produced tier {tier!r}",
                )
                self.assertTrue(reason, f"{name} has no reason")

    def test_a_recorded_member_gives_the_routed_tier(self) -> None:
        for name, route in GENERATOR.ROUTES.items():
            if route.member:
                with self.subTest(name=name):
                    tier, _ = GENERATOR.tier_for(name, "")
                    self.assertEqual(tier, "ROUTED", f"{name} names a member and is not ROUTED")


class MapFileTests(unittest.TestCase):
    """The written map, so it cannot drift from the generator without being regenerated."""

    def test_the_map_is_regenerated_and_current(self) -> None:
        path = GENERATOR.OUTPUT_PATH
        self.assertTrue(path.is_file(), "docs/GWA3_ROUTE_MAP.md has not been generated")
        text = path.read_text(encoding="utf-8")
        declared = GENERATOR.parse_declarations()
        expected = GENERATOR.render(declared, GENERATOR.load_mechanisms(), GENERATOR.load_call_census())
        self.assertEqual(
            text,
            expected,
            "docs/GWA3_ROUTE_MAP.md is stale -- re-run python tools/generate_gwa3_route_map.py",
        )

    def test_the_map_states_what_it_does_not_establish(self) -> None:
        text = GENERATOR.OUTPUT_PATH.read_text(encoding="utf-8")
        self.assertIn("What this map does not establish", text)
        self.assertIn("not a live result", text)


if __name__ == "__main__":
    unittest.main()
