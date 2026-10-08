"""Offline tests for the self-test battery (`self_test.py`) and its tab in `main.py`.

The battery is what a person presses instead of testing 20,000 entries by hand, so the things that
matter about it are:

* **its offline checks pass** -- the map's completeness, the engine's safety rules, known answers
  from members that need no client, and the window's own wiring;
* **it never fails for want of a client** -- the client checks are *skipped* when nothing is
  connected, because a window with no client is a state and not a defect;
* **a failing check is a failure, and nothing else happens** -- a wrong answer and a check that
  raises are both reported as ``fail`` with what it saw, so the battery cannot take the window down;
* **the window runs it and writes its report**, and the report check leaves no files behind;
* **it cannot write to the client**: every member the surface classifies as a write is blocked while
  a live section runs, and that guard is driven here without a client.
"""

from __future__ import annotations

import importlib
import types
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

import main as main_module
import self_test
import test_surface
from py4gw import gui

#: The real map builder, held before any patch replaces the module attribute.
_BUILD_ENTRIES = test_surface.build_entries
_MAP: tuple[test_surface.Entry, ...] | None = None


def _cached_map() -> tuple[test_surface.Entry, ...]:
    """The library map, built once for every test in this file."""

    global _MAP
    if _MAP is None:
        _MAP = _BUILD_ENTRIES()
    return _MAP


class _Win32Stub:
    """The two answers the window wants from the Windows layer, and nothing else."""

    def __init__(self, clients: list[dict[str, Any]], *, elevated: bool) -> None:
        self.clients = clients
        self.elevated = elevated

    def find_guild_wars(self) -> list[dict[str, Any]]:
        return list(self.clients)

    def is_elevated(self) -> bool:
        return self.elevated


class BatteryTest(unittest.TestCase):
    """The battery's own behaviour: what it passes, what it skips, and how it fails."""

    @classmethod
    def setUpClass(cls) -> None:
        """Run the offline battery once: every test here reads its results."""

        cls.results = self_test.run_checks()

    def test_the_offline_battery_passes(self) -> None:
        """With no client, every check that can run passes: nothing fails."""

        failed = [result for result in self.results if result.status == "fail"]
        self.assertEqual(
            failed,
            [],
            "; ".join(f"{result.area}/{result.name}: {result.actual}" for result in failed),
        )
        passed = [result for result in self.results if result.status == "pass"]
        self.assertGreater(len(passed), 20)

    def test_the_client_checks_are_skipped_rather_than_failed(self) -> None:
        """A check that needs the client is skipped without one, and says so."""

        client_checks = [result for result in self.results if result.area == "client"]
        self.assertTrue(client_checks, "the battery should carry client checks")
        for result in client_checks:
            self.assertEqual(result.status, "skip", result.name)
            self.assertIn("no client connected", result.actual)

    def test_the_window_checks_are_skipped_without_a_window(self) -> None:
        """A check that needs the window is skipped when the battery runs headless."""

        window_checks = [result for result in self.results if result.area == "window"]
        self.assertTrue(window_checks)
        for result in window_checks:
            self.assertEqual(result.status, "skip", result.name)
            self.assertEqual(result.actual, "no window")

    def test_each_check_says_what_it_expected_and_what_it_saw(self) -> None:
        """Every result carries the expectation in words and the observation, pass or skip."""

        for result in self.results:
            self.assertTrue(result.expected, result.name)
            self.assertTrue(result.actual, result.name)
            self.assertIn(result.status, ("pass", "fail", "skip"))

    def test_a_wrong_answer_is_reported_as_a_failure(self) -> None:
        """A check that sees something else fails with what it saw, and the battery continues."""

        wrong = self_test.Check(
            area="test",
            name="wrong answer",
            expected="one thing",
            call=lambda _context: self_test.expect(False, "saw another"),
        )
        raising = self_test.Check(
            area="test",
            name="raises",
            expected="no exception",
            call=lambda _context: (_ for _ in ()).throw(ValueError("boom")),
        )
        good = self_test.Check(
            area="test",
            name="fine",
            expected="one thing",
            call=lambda _context: self_test.expect(True, "saw it"),
        )
        with mock.patch.object(self_test, "CHECKS", (wrong, raising, good)):
            results = self_test.run_checks()
        by_name = {result.name: result for result in results}
        self.assertEqual(by_name["wrong answer"].status, "fail")
        self.assertEqual(by_name["wrong answer"].actual, "saw another")
        self.assertEqual(by_name["raises"].status, "fail")
        self.assertIn("ValueError: boom", by_name["raises"].actual)
        self.assertEqual(by_name["fine"].status, "pass")
        self.assertIn("PASS 1, FAIL 2", self_test.summarise(results))

    def test_a_client_check_cannot_run_without_a_connection(self) -> None:
        """Asking for only the client checks without a client skips all of them."""

        results = self_test.run_checks(only_client=True)
        self.assertTrue(results)
        self.assertTrue(all(result.status == "skip" for result in results))

    def test_the_report_says_every_check_and_its_verdict(self) -> None:
        """The report text carries the summary and one block per check."""

        text = self_test.report(self.results)
        self.assertIn("py4gw self-test", text)
        self.assertIn("PASS ", text)
        for result in self.results:
            self.assertIn(result.name, text)
            self.assertIn(result.expected, text)


class WriteGuardTest(unittest.TestCase):
    """The battery is read-only by construction, proved without a client.

    Every member the surface classifies as a write is replaced by a recorder while a live section
    runs. These tests drive that guard directly: a write that is called is refused and recorded, and
    every member is put back exactly as it was, whatever happened.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Build the map once: it costs ~0.8 s and nothing here changes it."""

        cls.entries = test_surface.build_entries()

    def guard(self) -> self_test.Context:
        return self_test.Context(entries=self.entries)

    def a_write(self) -> tuple[Any, type, Any]:
        """One *callable* write member, with its class and its original attribute.

        Callable on purpose: 36 of the map's 246 "writes" are namespace classes and constants read as
        writes from their names, and the guard leaves those alone by design (replacing ``Party.Players``
        broke ``Party.GetPartyLeaderID`` live). This helper drives the guard the way the guard works.
        """

        for entry in self.entries:
            if entry.access != "write" or not entry.owner:
                continue
            owner = getattr(importlib.import_module(entry.group), entry.owner, None)
            if not isinstance(owner, type) or entry.name not in owner.__dict__:
                continue
            attribute = owner.__dict__[entry.name]
            if isinstance(attribute, (type, types.ModuleType)) or not callable(attribute):
                continue
            return entry, owner, attribute
        raise AssertionError("the map classifies no callable write member")

    def test_a_write_member_is_replaced_while_the_guard_is_held(self) -> None:
        """The guard blocks the write, records it, and its call fails loudly."""

        entry, owner, original = self.a_write()
        context = self.guard()
        with self_test.writes_blocked(context):
            self.assertIsNot(owner.__dict__[entry.name], original)
            with self.assertRaises(self_test.CheckFailed) as raised:
                getattr(owner, entry.name)()
            self.assertIn(entry.name, str(raised.exception))
        self.assertEqual(context.data["write_calls"], [entry.label])
        self.assertTrue(context.data["writes_blocked"])

    def test_every_member_the_guard_replaced_is_put_back(self) -> None:
        """After the guard, each replaced member is the same object it was before."""

        entry, owner, original = self.a_write()
        context = self.guard()
        with self_test.writes_blocked(context):
            replaced = owner.__dict__[entry.name]
        self.assertIs(owner.__dict__[entry.name], original)
        self.assertIsNot(replaced, original)

    def test_the_live_safety_check_fails_when_a_write_was_called(self) -> None:
        """The safety check reads what the guard recorded, either way."""

        entry, owner, _original = self.a_write()
        context = self.guard()
        with self_test.writes_blocked(context):
            with self.assertRaises(self_test.CheckFailed):
                getattr(owner, entry.name)()
        with self.assertRaises(self_test.CheckFailed):
            self_test._live_safety(context)  # noqa: SLF001
        clean = self.guard()
        with self_test.writes_blocked(clean):
            pass
        self.assertIn("none was called", self_test._live_safety(clean))  # noqa: SLF001


class LiveAreaTest(unittest.TestCase):
    """The live sections are part of the same battery, and skip without a client."""

    def test_every_live_area_is_registered_with_a_check_that_needs_a_client(self) -> None:
        """Each live area names at least one check, and every one of them needs the client."""

        live = self_test.live_areas()
        self.assertEqual(
            live,
            (
                "live contexts",
                "live char",
                "live map",
                "live player",
                "live agents",
                "live party",
                "live world",
                "live camera",
                "live text parser",
                "live instance",
                "live items",
                "live agreement",
                "live data dump",
                "live safety",
            ),
        )
        for area in live:
            checks = [check for check in self_test.CHECKS if check.area == area]
            self.assertTrue(checks, area)
            self.assertTrue(all(check.needs_client for check in checks), area)

    def test_the_live_checks_skip_rather_than_fail_without_a_client(self) -> None:
        """Without a connection every live section is skipped, with the reason stated."""

        results = self_test.run_checks(areas=self_test.live_areas())
        self.assertEqual(len(results), len(self_test.live_areas()))
        for result in results:
            self.assertEqual(result.status, "skip", result)
            self.assertEqual(result.actual, "no client connected")


class WindowBatteryTest(unittest.TestCase):
    """The battery as the window runs it, from the Self-test tab."""

    def setUp(self) -> None:
        """Build the window with a stand-in Windows layer, as the other window tests do."""

        gui.Opt("GUIOnEventMode", 1)
        patcher = mock.patch.object(test_surface, "build_entries", _cached_map)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.window = main_module.MainWindow()
        self.window._win32 = cast(  # noqa: SLF001 - the window is driven directly
            Any, _Win32Stub([{"pid": 1234, "name": "Gw.exe", "path": r"F:\GW\GW1\Gw.exe"}], elevated=False)
        )
        self.window._build_interface()  # noqa: SLF001
        gui.Sleep(50)

    def tearDown(self) -> None:
        """Close the window; the interpreter is left for the next test in this class."""

        self.window._on_close()  # noqa: SLF001

    @classmethod
    def tearDownClass(cls) -> None:
        """Destroy the interpreter once every test here has run, and forget it.

        The layer creates the shared root only when it has none, so it is cleared here: a later class
        in the same process builds a fresh interpreter rather than drawing on a destroyed one.
        """

        root = gui._default._root  # noqa: SLF001
        if root is not None:
            try:
                root.destroy()
            except Exception:  # noqa: BLE001 - a destroyed interpreter is the goal either way
                pass
            gui._default._root = None  # noqa: SLF001

    def test_the_self_test_tab_runs_the_battery_and_shows_every_check(self) -> None:
        """The tab's button runs the battery: window checks pass, client checks skip."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._self_test_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(80)
        self.window._run_self_test()  # noqa: SLF001
        results = self.window._self_test_results  # noqa: SLF001
        self.assertEqual(len(results), len(self_test.CHECKS))
        statuses: dict[str, int] = {}
        for result in results:
            statuses[result.status] = statuses.get(result.status, 0) + 1
        self.assertEqual(statuses.get("fail", 0), 0)
        self.assertGreater(statuses.get("pass", 0), 20)
        self.assertGreater(statuses.get("skip", 0), 0)
        # Every check is a row in the table, with its verdict and what it saw.
        table = self.window._self_test_table
        widget = gui._default._controls[table.listview].widget  # noqa: SLF001
        rows = [widget.item(item, "values") for item in widget.get_children("")]
        self.assertEqual(len(rows), len(self_test.CHECKS))
        self.assertTrue(all(row[0] in ("pass", "fail", "skip") for row in rows))
        window_rows = [row for row in rows if row[1] == "window"]
        self.assertTrue(window_rows)
        self.assertTrue(all(row[0] == "pass" for row in window_rows), window_rows)
        summary = gui.GUICtrlRead(self.window._self_test_status.label)  # noqa: SLF001
        self.assertIn("PASS", summary)
        self.assertIn("FAIL 0", summary)
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_the_battery_leaves_no_files_behind_and_writes_its_report(self) -> None:
        """The report check cleans up after itself, and Save test report writes the verdict."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._self_test_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(50)
        self.window._run_self_test()  # noqa: SLF001
        self.assertFalse(main_module.SELF_TEST_WORKING_FULL.exists())  # noqa: SLF001
        self.assertFalse(main_module.SELF_TEST_WORKING_SUMMARY.exists())  # noqa: SLF001

        target = Path(__file__).with_name(".self_test_report.txt")
        original = main_module.SELF_TEST_REPORT_PATH
        main_module.SELF_TEST_REPORT_PATH = target
        try:
            self.window._save_self_test_report()  # noqa: SLF001
            text = target.read_text(encoding="utf-8")
        finally:
            main_module.SELF_TEST_REPORT_PATH = original
            target.unlink(missing_ok=True)
        self.assertIn("py4gw self-test", text)
        self.assertIn("client", text)
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_the_client_checks_run_when_a_connection_is_claimed(self) -> None:
        """With a stand-in connection the client checks are attempted, not skipped.

        The stand-in answers nothing, so the checks fail -- which is the point: a check that needs a
        client is *run* when one is claimed, and its failure names what was missing rather than
        silently passing.
        """

        self.window._connection = cast(Any, object())  # noqa: SLF001 - a connection that answers nothing
        results = self_test.run_checks(
            self_test.Context(
                entries=self.window._surface_entries,  # noqa: SLF001
                client=self.window._connection,  # noqa: SLF001
                window=self.window,
                connected=True,
            ),
            areas=("client",),
        )
        self.assertTrue(results)
        self.assertFalse(any(result.status == "skip" for result in results))
        self.assertTrue(any(result.status == "fail" for result in results))
        self.window._connection = None  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
