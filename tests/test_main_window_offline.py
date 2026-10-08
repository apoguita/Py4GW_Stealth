"""Offline tests for the root window (`main.py`) drawn with the AutoIt-compatible GUI layer.

No client and no elevation are involved: the window's Windows layer is replaced by a stand-in that
answers the two questions the window asks it -- which Guild Wars clients exist, and whether this
shell may connect -- so every case here runs the same way on any machine.

What these tests pin is what the window's user sees, and what it is *allowed* to do:

* a refresh **replaces** the client list: it does not add a second copy of every row, which is what
  happened while ``GUICtrlDelete`` on a ListView item left the row in the control;
* **without an elevated shell nothing connects at all** -- no ``ConnectedClient`` is constructed,
  not for the client list and not for the Connect button -- which is the library's own precondition
  (``ConnectedClient.__init__`` asserts elevation before it resolves or writes anything);
* choosing a context **shows it and reads it**, so a click on the list fills the table beside it;
* a read that *failed* is reported as the failure it is, and never as "in selection menus", which
  is a statement about the client rather than about the read.
"""

from __future__ import annotations

import unittest
import ctypes
import json
import struct
from pathlib import Path
from typing import Any, cast
from unittest import mock

import main as main_module
import test_surface
from py4gw import TextParserStruct, gui


#: The real builder, held before any patch replaces the module attribute: a cached wrapper that
#: called ``test_surface.build_entries`` by name would call itself.
_BUILD_ENTRIES = test_surface.build_entries


def _cached_map() -> tuple[test_surface.Entry, ...]:
    """The library map, built once for every test in this file."""

    global _MAP
    if _MAP is None:
        _MAP = _BUILD_ENTRIES()
    return _MAP


_MAP: tuple[test_surface.Entry, ...] | None = None


class _Win32Stub:
    """The two answers the window wants from the Windows layer, and nothing else."""
    def __init__(self, clients: list[dict[str, Any]], *, elevated: bool) -> None:
        self.clients = clients
        self.elevated = elevated

    def find_guild_wars(self) -> list[dict[str, Any]]:
        return list(self.clients)

    def is_elevated(self) -> bool:
        return self.elevated


class _ConnectionRecorder:
    """Stand in for ``ConnectedClient`` and record every construction attempt."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.error = error

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        raise AssertionError("this test does not expect a connection to be built")


class MainWindowTestCase(unittest.TestCase):
    """Base class: build the window, drive it, and destroy it afterwards."""

    window: main_module.MainWindow

    def setUp(self) -> None:
        """Build the window's interface, hidden, with two clients and an unelevated shell.

        The build refreshes the client list, and the stand-in starts unelevated on purpose: that
        keeps the build from reaching a real connection, and a test that wants the elevated path
        says so by flipping :attr:`_Win32Stub.elevated`.

        The library map is built once per process and shared by every test here: it costs ~0.8 s and
        nothing in these tests changes it.
        """

        gui.Opt("GUIOnEventMode", 1)
        patcher = mock.patch.object(test_surface, "build_entries", _cached_map)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.window = main_module.MainWindow()
        self.clients = [
            {"pid": 1111, "name": "Gw.exe", "path": r"F:\GW\GW1\Gw.exe"},
            {"pid": 2222, "name": "Gw.exe", "path": r"F:\GW\GW1\Gw.exe"},
        ]
        self.win32 = _Win32Stub(self.clients, elevated=False)
        self.window._win32 = cast(Any, self.win32)  # noqa: SLF001 - the window is driven directly
        self.window._build_interface()  # noqa: SLF001 - the window is driven directly, not run
        gui.Sleep(50)

    def tearDown(self) -> None:
        """Close the window; the Tk interpreter is left for the next test in this class."""

        self.window._on_close()  # noqa: SLF001

    @classmethod
    def tearDownClass(cls) -> None:
        """Destroy the interpreter the window was drawn on, once every test has run.

        The layer creates the shared root only when it has none, so the destroyed interpreter is
        forgotten here: a later class in the same process -- the battery's own window tests, for
        instance -- then builds a fresh one instead of drawing on a destroyed one.
        """

        root = gui._default._root  # noqa: SLF001
        if root is not None:
            try:
                root.destroy()
            except Exception:  # noqa: BLE001 - a destroyed interpreter is the goal either way
                pass
            gui._default._root = None  # noqa: SLF001

    def rows(self) -> list[tuple[str, ...]]:
        """Return the client list's rows as the tuples the ListView holds."""

        widget = self.gui_control(self.window._client_table.listview)  # noqa: SLF001
        return [
            tuple(str(part) for part in widget.item(item, "values"))
            for item in widget.get_children("")
        ]

    def gui_control(self, control_id: int) -> Any:
        """Return a control's tkinter widget, which the window's public API does not expose."""

        return gui._default._controls[control_id].widget  # noqa: SLF001

    def context_rows(self, listview: int) -> list[tuple[str, ...]]:
        """Return a context table's rows as the tuples its ListView holds."""

        widget = self.gui_control(listview)
        return [
            tuple(str(part) for part in widget.item(item, "values"))
            for item in widget.get_children("")
        ]

    def show_data_tab(self) -> None:
        """Select the data tab, which is where the context views live."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._data_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(100)

    def select_context(self, index: int) -> None:
        """Choose a context in the list the way a click does."""

        listbox = gui._default._controls[self.window._contexts_select].value  # noqa: SLF001
        listbox.selection_clear(0, "end")
        listbox.selection_set(index)
        listbox.event_generate("<<ListboxSelect>>")

    def select_client_row(self, index: int = 0) -> None:
        """Select a row of the client list, which is what Connect acts on."""

        widget = self.gui_control(self.window._client_table.listview)  # noqa: SLF001
        widget.selection_set(widget.get_children("")[index])
        gui.Sleep(50)

    def test_refresh_replaces_the_client_list(self) -> None:
        """Refreshing finds the clients again; it does not leave the previous rows in place."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.Sleep(100)
        self.window._refresh_clients()  # noqa: SLF001
        first = len(self.rows())
        self.window._refresh_clients()  # noqa: SLF001
        second = len(self.rows())
        self.window._refresh_clients()  # noqa: SLF001
        third = len(self.rows())
        self.assertEqual(first, len(self.clients))
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_nothing_is_connected_without_an_elevated_shell(self) -> None:
        """An unelevated shell is refused before a client is looked at, by the list and by Connect.

        Measured from the library's own design: ``ConnectedClient.__init__`` asserts elevation
        before it resolves or writes anything, so an unelevated controller never reaches a client.
        The window asks that precondition itself -- so no connection is *attempted* at all -- and
        says why in the client list rather than reporting a refusal per row.
        """

        self.win32.elevated = False
        recorder = _ConnectionRecorder()
        original = main_module.ConnectedClient
        main_module.ConnectedClient = recorder  # type: ignore[assignment]
        try:
            self.window._refresh_clients()  # noqa: SLF001
            rows = self.rows()
            self.assertEqual(len(rows), len(self.clients))
            for row in rows:
                self.assertEqual(row[2], "(elevation required)")
                self.assertEqual(row[3], "not read: needs an elevated shell")
            self.assertIn(
                main_module.ELEVATION_REFUSAL,
                gui.GUICtrlRead(self.window._client_status.label),  # noqa: SLF001
            )
            self.select_client_row()
            self.window._connect_selected()  # noqa: SLF001
        finally:
            main_module.ConnectedClient = original  # type: ignore[assignment]
        self.assertEqual(recorder.calls, [])
        self.assertIsNone(self.window._connection)  # noqa: SLF001
        self.assertEqual(
            gui.GUICtrlRead(self.window._connected_label.label),  # noqa: SLF001
            main_module.ELEVATION_REFUSAL,
        )

    def test_a_failed_read_is_not_reported_as_the_selection_menus(self) -> None:
        """A read that fails says so; only a read that succeeds may report the selection menus."""

        self.win32.elevated = True
        recorder = _ConnectionRecorder(RuntimeError("the reader could not be built"))
        original = main_module.ConnectedClient
        main_module.ConnectedClient = recorder  # type: ignore[assignment]
        try:
            self.window._refresh_clients()  # noqa: SLF001
        finally:
            main_module.ConnectedClient = original  # type: ignore[assignment]
        rows = self.rows()
        self.assertEqual(len(recorder.calls), len(self.clients))
        for row in rows:
            self.assertEqual(row[2], "(unread)")
            self.assertEqual(row[3], "read failed: the reader could not be built")
        text = " ".join(" ".join(row) for row in rows)
        self.assertNotIn("in selection menus", text)

    def test_a_context_that_fails_to_display_is_named_and_the_rest_still_show(self) -> None:
        """A read the display makes must not escape as an unhandled Tk callback exception.

        Measured live: connecting made ``_show_text_parser`` read offset +0x180 of the TextParser as
        a pointer, the client held ``0x4C`` there, and the resulting
        ``OSError: [Errno 299] ReadProcessMemory(address=0x4C, size=0x4)`` came out of the Connect
        handler as "Exception in Tkinter callback". Each context is now displayed on its own, so one
        failing read names that context and the others are still shown.
        """

        self.win32.elevated = True
        connection = mock.MagicMock()
        connection.is_connected = True
        shown: list[str] = []

        def record(name: str) -> Any:
            return lambda _snapshot: shown.append(name)

        def refuse(snapshot: Any) -> None:
            del snapshot
            raise OSError(299, "ReadProcessMemory(address=0x4C, size=0x4) failed", 0x4C)

        for name in (
            "_show_pre_game_context",
            "_show_cinematic",
            "_show_camera",
            "_show_friend_list",
            "_show_chat_buffer",
            "_show_world_context",
            "_show_map_context",
            "_show_trade_context",
            "_show_item_context",
            "_show_account_context",
            "_show_gadget_context",
            "_show_gameplay_context",
            "_show_server_region",
            "_show_instance_info",
            "_show_available_characters",
            "_show_party_context",
            "_show_guild_context",
            "_show_acc_agent_context",
            "_show_game_context",
            "_show_context",
        ):
            setattr(self.window, name, record(name))
        self.window._show_text_parser = refuse  # noqa: SLF001

        original = main_module.ConnectedClient
        main_module.ConnectedClient = lambda *args, **kwargs: connection  # type: ignore[assignment]
        try:
            self.window._refresh_clients()  # noqa: SLF001
            self.select_client_row()
            self.window._connect_selected()  # noqa: SLF001
        finally:
            main_module.ConnectedClient = original  # type: ignore[assignment]

        label = gui.GUICtrlRead(self.window._connected_label.label)  # noqa: SLF001
        self.assertIn("could not display: TextParser", label)
        self.assertIn("0x4C", label)
        # The contexts after the failing one were still displayed, and the connection is still held:
        # the failure is a property of one context's read, not of the connection.
        self.assertIn("_show_context", shown)
        self.assertIn("_show_game_context", shown)
        self.assertIs(self.window._connection, connection)  # noqa: SLF001
        self.window._connection = None  # noqa: SLF001 - the stand-in has nothing to close
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_a_context_reader_that_fails_writes_its_own_status(self) -> None:
        """The context list and the Refresh buttons run their reader through the same guard."""

        views = self.window._context_views  # noqa: SLF001
        view = views[0]
        view.refresh = _raise_os_error  # type: ignore[method-assign]
        self.window._run_context_reader(view)  # noqa: SLF001
        status = gui.GUICtrlRead(view.status.label)
        self.assertIn(view.label, status)
        self.assertIn("could not be displayed", status)
        self.assertIn("0x4C", status)

    def test_the_text_parser_row_reads_offset_0x180_as_the_word_it_is(self) -> None:
        """The measured crash, reproduced: this client holds 0x4C at +0x180, and it is displayed.

        The record used to carry a ``sub_struct`` property that followed ``+0x180`` as a pointer;
        the interpreter's own error for that read was
        ``OSError: [Errno 299] ReadProcessMemory(address=0x4C, size=0x4) failed with Windows error
        299``. The record now carries the field the source declares -- ``sub_struct_ptr`` -- and the
        window shows it as the raw word, so a client holding 0x4C there displays normally.
        """

        raw = bytearray(ctypes.sizeof(TextParserStruct))
        struct.pack_into("<I", raw, 0x180, 0x4C)
        snapshot = TextParserStruct.from_buffer_copy(bytes(raw)).bind_reader(_RefusingReader())
        self.window._show_text_parser(snapshot)  # noqa: SLF001 - must not raise

        rows = self.context_rows(self.window._text_parser_table.listview)  # noqa: SLF001
        fields = {row[1]: row[2] for row in rows}
        self.assertEqual(fields["sub_struct_ptr"], "76")
        self.assertNotIn("sub_struct", fields)
        self.assertNotIn("cache", fields)
        self.assertEqual(
            gui.GUICtrlRead(self.window._text_parser_status.label),  # noqa: SLF001
            "TextParser refreshed",
        )

    def test_the_surface_tab_maps_the_library_and_runs_one_entry(self) -> None:
        """The map is in the window: groups, entries, detail, search, and Run this entry.

        The entry is found by *search* -- the way a caller looks a member up, since a member lives in
        the module that declares it -- and run with an argument, which is what the argument box is
        for. ``Player.GetPlayerStatusNameFromValue(0)`` answers without a client.
        """

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._surface_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(100)
        self.assertGreater(len(self.window._surface_entries), 10_000)  # noqa: SLF001
        groups = gui._default._controls[self.window._surface_groups].value  # noqa: SLF001
        self.assertGreater(groups.size(), 100)
        self.assertEqual(groups.get(0), "py4gw  (270)")

        gui.GUICtrlSetData(self.window._surface_search, "GetPlayerStatusNameFromValue")  # noqa: SLF001
        self.window._surface_searched()  # noqa: SLF001
        rows = self.context_rows(self.window._surface_table.listview)  # noqa: SLF001
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "GetPlayerStatusNameFromValue")

        table = self.gui_control(self.window._surface_table.listview)  # noqa: SLF001
        table.selection_set(table.get_children("")[0])
        gui.Sleep(50)
        self.window._surface_entry_selected()  # noqa: SLF001
        self.assertEqual(gui.GUICtrlRead(self.window._surface_arguments), "status")  # noqa: SLF001

        gui.GUICtrlSetData(self.window._surface_arguments, "0")  # noqa: SLF001
        self.window._run_selected_entry()  # noqa: SLF001
        result = gui.GUICtrlRead(self.window._surface_result.label)  # noqa: SLF001
        self.assertIn("answered", result)
        self.assertIn("'offline'", result)
        # The run is in the output pane as well, which is what the Tests tab shows.
        output = self.context_rows(self.window._output_table.listview)  # noqa: SLF001
        self.assertTrue(any("GetPlayerStatusNameFromValue" in row[2] for row in output))
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_test_all_methods_runs_the_whole_surface_and_reports_it(self) -> None:
        """The button runs every entry with nothing connected, and the summary counts them.

        The counts are asserted as *relationships* rather than numbers: something answered, every
        write was skipped, the entries that need arguments were reported as such, and a report of
        the whole surface -- every entry, and what was not answered grouped by reason -- is written
        where the button says it is.
        """

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._test_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(100)
        self.window._test_all_methods()  # noqa: SLF001
        outcomes = self.window._outcomes  # noqa: SLF001
        self.assertEqual(len(outcomes), len(self.window._surface_entries))  # noqa: SLF001
        statuses: dict[str, int] = {}
        for outcome in outcomes:
            statuses[outcome.status] = statuses.get(outcome.status, 0) + 1
        self.assertGreater(statuses.get("answered", 0), 5_000)
        self.assertGreater(statuses.get("skipped (classified as a write)", 0), 0)
        self.assertGreater(statuses.get("skipped (needs arguments)", 0), 0)
        self.assertEqual(statuses.get("failed", 0), 0)
        summary = gui.GUICtrlRead(self.window._test_status.label)  # noqa: SLF001
        self.assertIn("answered=", summary)
        # Every outcome is in the pane up to the cap the pane draws, and the status says the cap.
        # The window's own cap keeps a redraw at half a second; the report file has all of them.
        rows = self.context_rows(self.window._output_table.listview)  # noqa: SLF001
        self.assertEqual(rows[0][0], "summary")
        self.assertEqual(len(rows), main_module._OUTPUT_ROWS)  # noqa: SLF001
        self.assertGreater(len(outcomes), main_module._OUTPUT_ROWS)  # noqa: SLF001
        self.assertIn("Save report has them all", summary)
        target = Path(__file__).with_name(".report_test.txt")
        summary_target = Path(__file__).with_name(".summary_test.txt")
        original = main_module.REPORT_PATH
        original_summary = main_module.SUMMARY_REPORT_PATH
        main_module.REPORT_PATH = target
        main_module.SUMMARY_REPORT_PATH = summary_target
        try:
            self.window._save_report()  # noqa: SLF001
            text = target.read_text(encoding="utf-8")
            summary = summary_target.read_text(encoding="utf-8")
        finally:
            main_module.REPORT_PATH = original
            main_module.SUMMARY_REPORT_PATH = original_summary
            target.unlink(missing_ok=True)
            summary_target.unlink(missing_ok=True)
        self.assertIn("py4gw library surface", text)
        self.assertIn("what was not answered, by reason", text)
        self.assertIn("skipped (classified as a write)", text)
        # The short report is the one read first: the counts, a module table, and every entry that
        # did not answer -- with the reason and the classification behind it.
        self.assertIn("py4gw library surface -- summary", summary)
        self.assertIn("per module (entries / answered)", summary)
        self.assertIn("everything that did not answer, by status", summary)
        self.assertIn("py4gw.player", summary)
        self.assertLess(len(summary), len(text))
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_testing_one_group_or_one_class_runs_only_those_entries(self) -> None:
        """The surface tab's subset buttons run a module, or one class's members, and nothing else."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._surface_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(80)

        groups = gui._default._controls[self.window._surface_groups].value  # noqa: SLF001
        groups.selection_clear(0, "end")
        groups.selection_set(1)
        self.window._test_selected_group()  # noqa: SLF001
        group = self.window._selected_group()  # noqa: SLF001
        expected = {
            entry.label
            for entry in self.window._surface_entries  # noqa: SLF001
            if entry.group == group
        }
        self.assertTrue(expected)
        self.assertEqual({outcome.entry.label for outcome in self.window._outcomes}, expected)  # noqa: SLF001
        self.assertIn("ran", gui.GUICtrlRead(self.window._surface_status.label))  # noqa: SLF001

        # A class: pick a member, then run its owner. The window keeps a running record, so what the
        # run added is the difference from what was there before.
        before = {outcome.entry.label for outcome in self.window._outcomes}  # noqa: SLF001
        gui.GUICtrlSetData(self.window._surface_search, "Player.GetPlayerStatusName")  # noqa: SLF001
        self.window._surface_searched()  # noqa: SLF001
        table = self.gui_control(self.window._surface_table.listview)  # noqa: SLF001
        table.selection_set(table.get_children("")[0])
        gui.Sleep(50)
        self.window._surface_entry_selected()  # noqa: SLF001
        owner = self.window._surface_selected  # noqa: SLF001
        assert owner is not None
        self.window._test_selected_owner()  # noqa: SLF001
        added = {
            outcome.entry.label for outcome in self.window._outcomes  # noqa: SLF001
        } - before
        self.assertTrue(added)
        self.assertEqual({label.split(".")[-2] for label in added}, {owner.owner})
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_the_status_list_filters_the_output_and_counts_it(self) -> None:
        """Every status with its count is a row: choosing one shows exactly those results."""

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._test_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(80)
        self.window._test_all_methods()  # noqa: SLF001
        listbox = gui._default._controls[self.window._status_list].value  # noqa: SLF001
        rows = [str(listbox.get(index)) for index in range(listbox.size())]
        self.assertIn(f"all ({len(self.window._outcomes)})", rows)  # noqa: SLF001
        self.assertTrue(any(row.startswith("not answered (") for row in rows))

        write_row = next(
            index
            for index, row in enumerate(rows)
            if row.startswith("skipped (classified as a write)")
        )
        listbox.selection_clear(0, "end")
        listbox.selection_set(write_row)
        self.window._output_filter_changed()  # noqa: SLF001
        shown = self.context_rows(self.window._output_table.listview)  # noqa: SLF001
        self.assertTrue(shown)
        self.assertTrue(
            all(row[0] == "skipped (classified as a write)" for row in shown), shown[:3]
        )
        expected = test_surface.statuses(self.window._outcomes)["skipped (classified as a write)"]  # noqa: SLF001
        self.assertEqual(len(shown), expected)

        # A text filter narrows inside the status.
        gui.GUICtrlSetData(self.window._output_filter_input, "Map")  # noqa: SLF001
        self.window._output_filter_changed()  # noqa: SLF001
        narrowed = self.context_rows(self.window._output_table.listview)  # noqa: SLF001
        self.assertLessEqual(len(narrowed), len(shown))
        self.assertTrue(narrowed, "a text filter inside a status should still find rows")
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_the_include_writes_box_governs_what_the_button_runs(self) -> None:
        """Writes are skipped until the box is ticked: measured on a real write member.

        The engine is asked to run ``Player.Move`` -- a write -- through the entry path the button
        uses, with the box off and on. The member itself is replaced by a recorder, so nothing is
        called on any client even when the box is on.
        """

        from py4gw import Player

        entry = None
        for candidate in self.window._surface_entries:  # noqa: SLF001
            if candidate.name == "Move" and candidate.owner == "Player":
                entry = candidate
                break
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.access, "write")
        called: list[Any] = []
        with mock.patch.object(Player, "Move", staticmethod(lambda *a, **k: called.append(a))):
            off = test_surface.run_entry(entry, include_writes=False, args=(1.0, 2.0))
            on = test_surface.run_entry(entry, include_writes=True, args=(1.0, 2.0))
        self.assertEqual(off.status, "skipped (classified as a write)")
        self.assertEqual(on.status, "answered")
        self.assertEqual(len(called), 1)

    def test_refresh_all_contexts_runs_every_reader(self) -> None:
        """The data tab's Refresh all runs all 22 readers and says so."""

        self.show_data_tab()
        self.window._refresh_all_contexts()  # noqa: SLF001
        # One status label is shared by every context, so what it says at the end is the tab's
        # answer: each reader ran (with no client each reports "Connect a client first") and the
        # last word is the tab's own.
        self.assertEqual(
            gui.GUICtrlRead(self.window._data_status.label),  # noqa: SLF001
            f"all {len(self.window._context_views)} contexts refreshed",  # noqa: SLF001
        )
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_every_context_status_reaches_the_one_visible_label(self) -> None:
        """A context's status is written where the user can see it, not into a dead placeholder.

        The window keeps one status label for every context, and the aliases it writes through are
        made before the window is built -- so unless they are re-pointed at the real label, every
        "refreshed", "not available" and "read failed" line is silently dropped.
        """

        self.window._text_parser_status.set_text("TextParser refreshed")  # noqa: SLF001
        self.assertEqual(
            gui.GUICtrlRead(self.window._data_status.label),  # noqa: SLF001
            "TextParser refreshed",
        )
        self.window._camera_status.set_text("Camera is not available")  # noqa: SLF001
        self.assertEqual(
            gui.GUICtrlRead(self.window._data_status.label),  # noqa: SLF001
            "Camera is not available",
        )

    def test_choosing_a_context_shows_it_and_reads_it(self) -> None:
        """A selection shows that context's controls, hides the rest, and runs its reader."""

        self.show_data_tab()
        self.select_context(3)
        gui.Sleep(100)
        views = self.window._context_views  # noqa: SLF001
        visible = [view.label for view in views if view.visible]
        self.assertEqual(visible, [views[3].label])
        self.assertTrue(self.gui_control(views[3].listview).winfo_ismapped())
        self.assertFalse(self.gui_control(views[2].listview).winfo_ismapped())
        # No client is connected, so the reader's own answer is what the status shows -- which is
        # the proof that the reader ran.
        self.assertEqual(gui.GUICtrlRead(views[3].status.label), "Connect a client first")
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001

    def test_the_window_has_its_six_tabs_including_the_live_data_one(self) -> None:
        """Every tab the window promises exists, and the live-data tab holds its four-column table."""

        tabs = (
            self.window._client_tab,  # noqa: SLF001
            self.window._surface_tab,  # noqa: SLF001
            self.window._data_tab,  # noqa: SLF001
            self.window._test_tab,  # noqa: SLF001
            self.window._self_test_tab,  # noqa: SLF001
            self.window._live_tab,  # noqa: SLF001
        )
        self.assertTrue(all(tabs))
        self.assertEqual(len(set(tabs)), 6)
        table = self.window._live_data_table  # noqa: SLF001
        self.assertEqual(table.columns, main_module.LIVE_DATA_COLUMNS)
        widget = self.gui_control(table.listview)
        headings = [widget.heading(column)["text"] for column in widget["columns"]]
        self.assertEqual(headings, list(main_module.LIVE_DATA_COLUMNS))

    def test_the_connect_method_refuses_from_an_unelevated_shell(self) -> None:
        """The programmatic interface is refused exactly where the button is.

        A caller must not be able to reach a client the window itself refuses to touch, so
        ``connect()`` raises the refusal instead of returning: nothing is constructed, and no client
        is looked at.
        """

        self.win32.elevated = False
        recorder = _ConnectionRecorder()
        original = main_module.ConnectedClient
        main_module.ConnectedClient = recorder  # type: ignore[assignment]
        try:
            with self.assertRaises(PermissionError) as raised:
                self.window.connect(1111)  # noqa: SLF001
        finally:
            main_module.ConnectedClient = original  # type: ignore[assignment]
        self.assertIn(main_module.ELEVATION_REFUSAL, str(raised.exception))
        self.assertEqual(recorder.calls, [])
        self.assertIsNone(self.window._connection)  # noqa: SLF001

    def test_the_connect_method_names_a_pid_that_is_not_running(self) -> None:
        """An elevated shell asking for a client that is not there is told so, not given one."""

        self.win32.elevated = True
        recorder = _ConnectionRecorder()
        original = main_module.ConnectedClient
        main_module.ConnectedClient = recorder  # type: ignore[assignment]
        try:
            with self.assertRaises(OSError) as raised:
                self.window.connect(9999)  # noqa: SLF001
        finally:
            main_module.ConnectedClient = original  # type: ignore[assignment]
        self.assertIn("9999", str(raised.exception))
        self.assertEqual(recorder.calls, [])

    def test_the_live_data_tab_reports_that_nothing_was_read_without_a_client(self) -> None:
        """The live-data buttons say "no client" rather than showing invented rows.

        The table is filled from a battery run, so with nothing connected there is nothing to show
        -- and the report says exactly that, with ``connected`` false, instead of an empty file that
        could be mistaken for a client holding no values. The buttons are driven here, not the
        methods behind them, because pressing them is what a person does.
        """

        gui.GUISetState(gui.SW_SHOW, self.window._window)  # noqa: SLF001
        gui.GUICtrlSetState(self.window._live_tab, gui.GUI_SHOW)  # noqa: SLF001
        gui.Sleep(80)
        self.window._read_live_data_clicked()  # noqa: SLF001
        self.assertEqual(self.window._live_data_table.rows, [])  # noqa: SLF001
        status = gui.GUICtrlRead(self.window._live_data_status.label)  # noqa: SLF001
        self.assertIn("0 values", status)
        self.assertIn("no client connected", status)
        self.assertTrue(
            self.gui_control(self.window._live_data_table.listview).winfo_ismapped()  # noqa: SLF001
        )

        # The filter and Clear work over whatever rows the table holds, connected or not.
        gui.GUICtrlSetData(self.window._live_data_filter_input, "map")  # noqa: SLF001
        self.window._live_data_filter_changed()  # noqa: SLF001
        self.assertEqual(self.window._live_data_table.filter, "map")  # noqa: SLF001
        self.window._clear_live_data()  # noqa: SLF001
        self.assertIn("Read live data", gui.GUICtrlRead(self.window._live_data_status.label))  # noqa: SLF001

        target = Path(__file__).with_name(".live_data.txt")
        original = main_module.LIVE_DATA_REPORT_PATH
        main_module.LIVE_DATA_REPORT_PATH = target
        try:
            self.window._write_live_data_report()  # noqa: SLF001
            text = target.read_text(encoding="utf-8")
            payload = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
        finally:
            main_module.LIVE_DATA_REPORT_PATH = original
            target.unlink(missing_ok=True)
            target.with_suffix(".json").unlink(missing_ok=True)
        self.assertIn(str(target), gui.GUICtrlRead(self.window._live_data_status.label))  # noqa: SLF001
        self.assertIn("no context was read", text)
        self.assertIn("write members blocked while reading: 0", text)
        self.assertFalse(payload["connected"])
        self.assertEqual(payload["contexts"], {})
        self.assertEqual(payload["write_calls"], [])
        gui.GUISetState(gui.SW_HIDE, self.window._window)  # noqa: SLF001


class CommandLineTest(unittest.TestCase):
    """The command line is the same surface without the window: same checks, same report."""

    def test_the_checks_run_headlessly_and_write_their_report(self) -> None:
        """``--self-test`` runs named areas, prints nothing with ``--quiet``, and writes the report."""

        target = Path(__file__).with_name(".cli_report.txt")
        try:
            code = main_module.main(
                ["--self-test", "--quiet", "--areas", "pure members", "--report", str(target)]
            )
            text = target.read_text(encoding="utf-8")
        finally:
            target.unlink(missing_ok=True)
        self.assertEqual(code, 0)
        self.assertIn("py4gw self-test", text)
        self.assertIn("PASS", text)
        self.assertIn("DegToRad", text)

    def test_a_client_run_without_an_elevated_shell_is_refused(self) -> None:
        """``--client --data`` is refused from an unelevated shell, and writes nothing.

        The command line does not get to connect where the window may not: the refusal comes back as
        a non-zero exit code and no data file, rather than a run that quietly did nothing.
        """

        window = main_module.MainWindow()
        window._win32 = cast(Any, _Win32Stub([], elevated=False))  # noqa: SLF001
        target = Path(__file__).with_name(".cli_data.txt")
        original = main_module.MainWindow
        main_module.MainWindow = lambda: window  # type: ignore[assignment,return-value]
        try:
            code = main_module.main(["--data", str(target)])
        finally:
            main_module.MainWindow = original  # type: ignore[assignment]
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())


class _RefusingReader:
    """A reader that refuses every address, the way the client refuses 0x4C."""

    def read(self, address: int, size: int) -> bytes:
        del size
        raise OSError(299, f"ReadProcessMemory(address=0x{address:X}) failed", address)


def _raise_os_error() -> None:
    """Stand in for a context reader whose display reads an address the client does not map."""

    raise OSError(299, "ReadProcessMemory(address=0x4C, size=0x4) failed", 0x4C)


if __name__ == "__main__":
    unittest.main()
