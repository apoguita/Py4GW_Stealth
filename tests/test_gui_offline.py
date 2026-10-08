"""Offline tests for the AutoIt-compatible GUI layer (``py4gw.gui``).

Expected values marked ``(AutoIt: ...)`` were read from the AutoIt v3 interpreter installed
on this machine, not from the help file, by the probe scripts kept in
``tests/autoit_reference/``: default window and control sizes, ``GUICtrlRead`` and
``GUICtrlGetState`` values, the nature of control IDs, the menu-item state value and the
OnEvent delivery order. See ``docs/AUTOIT_GUI.md`` for the readings and their method.

The layer is a Stealth-owned component, so these tests assert against the AutoIt reference
and the interpreter rather than against a Reforged or Native class. They open tkinter
windows; only the event tests ever show one, and every test destroys what it created. No test
touches the game client.
"""

from __future__ import annotations

import base64
import ctypes
import os
import struct
import tempfile
import tkinter
import unittest
from pathlib import Path
from typing import Any

import py4gw.gui as gui_module
from py4gw.gui import GUI, native
from py4gw.gui.constants import (
    CBS_DROPDOWNLIST,
    DTS_SHORTDATEFORMAT,
    GUI_AVICLOSE,
    GUI_AVISTOP,
    GUI_CHECKED,
    GUI_DISABLE,
    GUI_DOCKALL,
    GUI_DOCKAUTO,
    GUI_DROPACCEPTED,
    GUI_ENABLE,
    GUI_EVENT_CLOSE,
    GUI_EVENT_MINIMIZE,
    GUI_EVENT_NONE,
    GUI_EXPAND,
    GUI_FOCUS,
    GUI_FONTNORMAL,
    GUI_GR_BEZIER,
    GUI_GR_COLOR,
    GUI_GR_LINE,
    GUI_GR_MOVE,
    GUI_HIDE,
    GUI_NODROPACCEPTED,
    GUI_NOFOCUS,
    GUI_READ_EXTENDED,
    GUI_SHOW,
    GUI_UNCHECKED,
    LVS_EX_CHECKBOXES,
    LVS_EX_FULLROWSELECT,
    SW_HIDE,
    SW_LOCK,
    SW_SHOW,
    SW_UNLOCK,
    TIP_BALLOON,
    TIP_CENTER,
    TIP_ERRORICON,
    TIP_FORCEVISIBLE,
    TIP_INFOICON,
    TIP_NOICON,
    TIP_WARNINGICON,
    WM_GETDLGCODE,
    WM_GETTEXT,
    WM_MOVE,
    WM_SIZE,
)

# A one-pixel GIF, because tkinter's PhotoImage reads a file rather than image bytes.
_DOT_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

#: A 6x4 BMP this file writes for the picture tests: BMP is a format tkinter's PhotoImage cannot
#: read, so what it decodes to is the oracle. The pixels are four 3x2 quadrants, top row first.
SAMPLE_BMP_PIXELS = [
    [(255, 0, 0), (255, 0, 0), (255, 0, 0), (0, 0, 255), (0, 0, 255), (0, 0, 255)],
    [(255, 0, 0), (255, 0, 0), (255, 0, 0), (0, 0, 255), (0, 0, 255), (0, 0, 255)],
    [(255, 255, 0), (255, 255, 0), (255, 255, 0), (0, 255, 255), (0, 255, 255), (0, 255, 255)],
    [(255, 255, 0), (255, 255, 0), (255, 255, 0), (0, 255, 255), (0, 255, 255), (0, 255, 255)],
]


def _write_sample_bmp(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    """Write a 24-bit BMP whose rows are given top-down, which is what the tests read back."""

    height = len(pixels)
    width = len(pixels[0])
    row_size = (width * 3 + 3) & ~3
    image = bytearray()
    for row in reversed(pixels):  # BMP stores its rows bottom-up
        line = bytearray()
        for red, green, blue in row:
            line += bytes((blue, green, red))
        line += b"\x00" * (row_size - len(line))
        image += line
    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(image), 0, 0, 14 + 40)
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(image), 2835, 2835, 0, 0)
    path.write_bytes(header + info + bytes(image))


SAMPLE_BMP = Path(tempfile.gettempdir()) / "py4gw_gui_test_sample.bmp"
_write_sample_bmp(SAMPLE_BMP, SAMPLE_BMP_PIXELS)

#: An icon that exists only when AutoIt is installed, and one that never exists.
AUTOIT_ICON = Path(r"C:\Program Files (x86)\AutoIt3\Icons\au3.ico")
MISSING_ICON = Path(r"C:\does\not\exist\nope.ico")

#: A DLL with icons in it, and the AVI clip the AutoIt installation ships. Both are Windows or
#: AutoIt files that the icon and animation controls can load.
SHELL32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "shell32.dll"
SAMPLE_AVI = Path(r"C:\Program Files (x86)\AutoIt3\Examples\GUI\sampleAVI.avi")


def _curve_y_at(points: list[tuple[int, int]], column: int) -> float | None:
    """Return where a flattened curve crosses a column, which is how its shape is compared."""

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 == x1:
            continue
        if min(x0, x1) <= column <= max(x0, x1):
            return y0 + (column - x0) / (x1 - x0) * (y1 - y0)
    return None


class _Configure:
    """A stand-in for tkinter's Configure event, for the tests that drive a window resize.

    A real resize needs a mapped window, which this desktop's window manager has refused while the
    suite ran; the port's handler only reads these three attributes.
    """

    def __init__(self, widget: Any, width: int, height: int) -> None:
        self.widget = widget
        self.width = width
        self.height = height


class GuiTestCase(unittest.TestCase):
    """Base class: one GUI per test, destroyed with its Tk interpreter afterwards."""

    gui: GUI

    def setUp(self) -> None:
        """Create a GUI instance for this test."""

        self.gui = GUI()

    def tearDown(self) -> None:
        """Delete every window this test created and destroy the Tk interpreter."""

        for handle in list(self.gui._windows):  # noqa: SLF001 - test cleanup
            self.gui.GUIDelete(handle)
        if self.gui._root is not None:  # noqa: SLF001 - test cleanup
            self.gui._root.destroy()

    def widget(self, control_id: int) -> Any:
        """Return a control's tkinter widget (tests only; the API returns IDs)."""

        return self.gui._controls[control_id].widget  # noqa: SLF001

    def value(self, control_id: int) -> Any:
        """Return a control's inner widget, where the port keeps one (List, Edit)."""

        return self.gui._controls[control_id].value  # noqa: SLF001


# --- constants ------------------------------------------------------------------------


class ConstantsTest(unittest.TestCase):
    """The constant surface is AutoIt's, with the values its include files assign."""

    def test_gui_constants(self) -> None:
        """The $GUI_* event, state and docking values are AutoIt's."""

        self.assertEqual(gui_module.GUI_EVENT_CLOSE, -3)
        self.assertEqual(gui_module.GUI_EVENT_NONE, 0)
        self.assertEqual(gui_module.GUI_CHECKED, 1)
        self.assertEqual(gui_module.GUI_UNCHECKED, 4)
        self.assertEqual(gui_module.GUI_SHOW, 16)
        self.assertEqual(gui_module.GUI_HIDE, 32)
        self.assertEqual(gui_module.GUI_ENABLE, 64)
        self.assertEqual(gui_module.GUI_DISABLE, 128)
        self.assertEqual(gui_module.GUI_FOCUS, 256)
        self.assertEqual(gui_module.GUI_EXPAND, 1024)
        self.assertEqual(gui_module.GUI_DOCKALL, 802)
        self.assertEqual(gui_module.GUI_READ_EXTENDED, 1)

    def test_style_constants(self) -> None:
        """The window and control style constants are AutoIt's."""

        self.assertEqual(gui_module.WS_EX_TOPMOST, 8)
        self.assertEqual(gui_module.WS_OVERLAPPEDWINDOW, 0x00CF0000)
        self.assertEqual(gui_module.CBS_DROPDOWNLIST, 3)
        self.assertEqual(gui_module.ES_PASSWORD, 32)
        self.assertEqual(gui_module.BS_ICON, 64)
        self.assertEqual(gui_module.LVS_EX_FULLROWSELECT, 32)
        self.assertEqual(gui_module.FW_BOLD, 700)
        self.assertEqual(gui_module.GUI_SS_DEFAULT_BUTTON, 0)

    def test_show_state_macros_match_the_interpreter(self) -> None:
        """@SW_* values are the interpreter's, including the AutoIt-specific four."""

        self.assertEqual(gui_module.SW_HIDE, 0)
        self.assertEqual(gui_module.SW_SHOW, 5)
        self.assertEqual(gui_module.SW_MINIMIZE, 6)
        self.assertEqual(gui_module.SW_RESTORE, 9)
        self.assertEqual(gui_module.SW_MAXIMIZE, 3)
        self.assertEqual(gui_module.SW_ENABLE, 64)
        self.assertEqual(gui_module.SW_DISABLE, 65)
        self.assertEqual(gui_module.SW_LOCK, 66)
        self.assertEqual(gui_module.SW_UNLOCK, 67)

    def test_bit_functions_are_autoits(self) -> None:
        """AutoIt's Bit* helpers exist for the style combinations its scripts write."""

        self.assertEqual(gui_module.BitOR(gui_module.CBS_DROPDOWN, 64), 66)
        self.assertEqual(gui_module.BitAND(0x000F, 0x0006), 0x0006)
        self.assertEqual(gui_module.BitXOR(0x000F, 0x0006), 0x0009)
        self.assertEqual(gui_module.BitNOT(0), -1)
        self.assertEqual(gui_module.BitShift(1, 4), 16)
        self.assertEqual(gui_module.BitShift(16, -4), 1)


# --- windows --------------------------------------------------------------------------


class WindowTest(GuiTestCase):
    """Window creation, state, style, switching and deletion."""

    def test_a_new_window_is_hidden_until_guisetstate(self) -> None:
        """GUICreate() makes a hidden window; GUISetState(SW_SHOW) shows it."""

        handle = self.gui.GUICreate("test", 200, 100)
        self.assertGreater(handle, 0)
        self.assertFalse(self.gui._windows[handle].visible)  # noqa: SLF001
        self.assertEqual(self.gui.GUISetState(gui_module.SW_SHOW, handle), 1)
        self.assertTrue(self.gui._windows[handle].visible)  # noqa: SLF001
        self.assertEqual(self.gui.GUISetState(SW_HIDE, handle), 1)
        self.assertFalse(self.gui._windows[handle].visible)  # noqa: SLF001

    def test_guicreate_defaults_to_400_by_400(self) -> None:
        """GUICreate() with no width or height is 400x400 (AutoIt: client 400x400)."""

        handle = self.gui.GUICreate("test")
        window = self.gui._windows[handle].widget  # noqa: SLF001
        window.update_idletasks()
        self.assertTrue(window.geometry().startswith("400x400"))

    def test_guigetstyle_reports_the_default_style_pair(self) -> None:
        """The default is $WS_POPUP|$WS_CAPTION|$WS_SYSMENU|$WS_MINIMIZEBOX plus
        $WS_CLIPSIBLINGS, with $WS_EX_WINDOWEDGE forced (AutoIt: -2067136512, 256)."""

        handle = self.gui.GUICreate("test")
        self.assertEqual(self.gui.GUIGetStyle(handle), [-2067136512, 256])
        self.assertEqual(self.gui.GUIGetStyle(999999), [])
        self.assertEqual(self.gui.error, 1)

    def test_guisetstyle_with_minus_one_leaves_a_style_alone(self) -> None:
        """GUISetStyle(-1, ...) keeps the current style, as the page says."""

        handle = self.gui.GUICreate("test", 200, 100)
        before = self.gui.GUIGetStyle(handle)
        self.assertEqual(self.gui.GUISetStyle(-1, -1, handle), 1)
        self.assertEqual(self.gui.GUIGetStyle(handle), before)
        self.assertEqual(self.gui.GUISetStyle(gui_module.WS_OVERLAPPEDWINDOW, -1, handle), 1)
        self.assertEqual(self.gui.GUIGetStyle(handle)[0], 0x00CF0000)

    def test_guidelete_removes_the_window_and_its_controls(self) -> None:
        """GUIDelete() returns 1, and 0 for a handle that is not a window."""

        handle = self.gui.GUICreate("test", 200, 100)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        self.assertEqual(self.gui.GUIDelete(handle), 1)
        self.assertNotIn(handle, self.gui._windows)  # noqa: SLF001
        self.assertNotIn(button, self.gui._controls)  # noqa: SLF001
        self.assertEqual(self.gui.GUIDelete(handle), 0)

    def test_guiswitch_returns_the_previous_handle(self) -> None:
        """GUISwitch() returns the handle of the window that was current."""

        first = self.gui.GUICreate("one", 100, 100)
        second = self.gui.GUICreate("two", 100, 100)
        self.assertEqual(self.gui.GUISwitch(first), second)
        self.assertEqual(self.gui.GUISwitch(second), first)
        self.assertEqual(self.gui.GUISwitch(999999), 0)

    def test_guiswitch_with_a_tabitem_places_controls_in_it(self) -> None:
        """GUISwitch($hWin, $tabitem) makes new controls belong to that tab item."""

        window = self.gui.GUICreate("test", 400, 300)
        self.gui.GUICtrlCreateTab(10, 10, 300, 200)
        first = self.gui.GUICtrlCreateTabItem("one")
        second = self.gui.GUICtrlCreateTabItem("two")
        self.gui.GUICtrlCreateTabItem("")
        self.gui.GUISwitch(window, second)
        button = self.gui.GUICtrlCreateButton("in two", 20, 40, 60, 25)
        self.gui.GUICtrlCreateTabItem("")
        self.assertEqual(
            str(self.widget(button).master), str(self.widget(second))
        )
        self.assertNotEqual(str(self.widget(button).master), str(self.widget(first)))

    def test_guisetbkcolor_and_font_apply_to_the_window(self) -> None:
        """GUISetBkColor() and GUISetFont() set the window's colour and default font."""

        handle = self.gui.GUICreate("test", 200, 100)
        self.assertEqual(self.gui.GUISetBkColor(0x00FF00, handle), 1)
        self.assertEqual(self.gui.GUISetFont(10, 700, 0, "Arial", handle), 1)
        window = self.gui._windows[handle]  # noqa: SLF001
        self.assertEqual(str(window.widget.cget("bg")), "#00ff00")
        self.assertEqual(window.default_font, ("Arial", 10, "bold"))

    def test_coordinates_and_coord_mode_2(self) -> None:
        """GUICoordMode 2 places controls relative to the cell GUISetCoord() sets."""

        self.gui.Opt("GUICoordMode", 2)
        self.gui.GUICreate("test", 400, 300)
        self.assertEqual(self.gui.GUISetCoord(20, 60), 1)
        button = self.gui.GUICtrlCreateButton("OK", -1, -1, 50, 25)
        info = self.widget(button).place_info()
        self.assertEqual((int(info["x"]), int(info["y"])), (20, 60))
        second = self.gui.GUICtrlCreateButton("Next", -1, -1, 50, 25)
        info = self.widget(second).place_info()
        self.assertEqual((int(info["x"]), int(info["y"])), (70, 60))


# --- control IDs ----------------------------------------------------------------------


class ControlIdTest(GuiTestCase):
    """Control IDs are AutoIt's own counter, not window handles."""

    def test_control_ids_are_autoits_own_counter(self) -> None:
        """Control IDs are positive, unique and start at 3 (AutoIt: first control was 3)."""

        self.gui.GUICreate("test", 300, 200)
        ids = [
            self.gui.GUICtrlCreateButton("one", 10, 10, 60, 25),
            self.gui.GUICtrlCreateButton("two", 10, 40, 60, 25),
            self.gui.GUICtrlCreateLabel("three", 10, 70),
        ]
        self.assertEqual(ids, [3, 4, 5])
        self.assertEqual(len(set(ids)), 3)

    def test_minus_one_names_the_last_created_control(self) -> None:
        """Every update function takes -1 for the last created control."""

        self.gui.GUICreate("test", 300, 200)
        label = self.gui.GUICtrlCreateLabel("before", 10, 10)
        self.assertEqual(self.gui.GUICtrlSetData(-1, "after"), 1)
        self.assertEqual(self.gui.GUICtrlRead(label), "after")
        self.assertEqual(self.gui.GUICtrlRead(-1), "after")

    def test_control_ids_are_not_window_handles(self) -> None:
        """GUICtrlGetHandle() returns a window handle that is not the control ID
        (AutoIt: button id 3, handle 0x00D20B34)."""

        self.gui.GUICreate("test", 300, 200)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        handle = self.gui.GUICtrlGetHandle(button)
        self.assertGreater(handle, 0)
        self.assertNotEqual(handle, button)
        self.assertEqual(self.gui.GUICtrlGetHandle(999999), 0)

    def test_controls_without_a_handle_report_zero(self) -> None:
        """Dummy, TabItem and ListViewItem return no handle, as the reference lists."""

        window = self.gui.GUICreate("test", 400, 300)
        self.gui.GUISwitch(window)
        dummy = self.gui.GUICtrlCreateDummy()
        tabs = self.gui.GUICtrlCreateTab(10, 10, 200, 100)
        tab_item = self.gui.GUICtrlCreateTabItem("one")
        self.gui.GUICtrlCreateTabItem("")
        listview = self.gui.GUICtrlCreateListView("A|B", 10, 130, 200, 100)
        list_item = self.gui.GUICtrlCreateListViewItem("a|b", listview)
        self.assertEqual(self.gui.GUICtrlGetHandle(dummy), 0)
        self.assertEqual(self.gui.GUICtrlGetHandle(tab_item), 0)
        self.assertEqual(self.gui.GUICtrlGetHandle(list_item), 0)
        self.assertGreater(self.gui.GUICtrlGetHandle(tabs), 0)


# --- reading controls -----------------------------------------------------------------


class ControlReadTest(GuiTestCase):
    """Read values are the ones the interpreter returned for the same controls."""

    def test_reads_match_autoit_for_every_control(self) -> None:
        """Every documented per-control read value matches AutoIt."""

        window = self.gui.GUICreate("test", 500, 500)
        self.gui.GUISwitch(window)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        label = self.gui.GUICtrlCreateLabel("Hello", 10, 40)
        checkbox = self.gui.GUICtrlCreateCheckbox("Check", 10, 70)
        radio = self.gui.GUICtrlCreateRadio("Radio", 10, 100)
        entry = self.gui.GUICtrlCreateInput("abc", 10, 130, 100, 20)
        edit = self.gui.GUICtrlCreateEdit("text", 10, 160, 100, 50)
        progress = self.gui.GUICtrlCreateProgress(10, 220, 100, 20)
        slider = self.gui.GUICtrlCreateSlider(10, 250, 100, 30)
        listbox = self.gui.GUICtrlCreateList("", 10, 290, 100, 60)
        combo = self.gui.GUICtrlCreateCombo("item1", 10, 360, 100, 20)
        dummy = self.gui.GUICtrlCreateDummy()

        self.assertEqual(self.gui.GUICtrlRead(button), "OK")
        self.assertEqual(self.gui.GUICtrlRead(label), "Hello")
        self.assertEqual(self.gui.GUICtrlRead(checkbox), GUI_UNCHECKED)  # AutoIt: 4
        self.assertEqual(self.gui.GUICtrlRead(radio), GUI_UNCHECKED)  # AutoIt: 4
        self.assertEqual(self.gui.GUICtrlRead(entry), "abc")
        self.assertEqual(self.gui.GUICtrlRead(edit), "text")
        self.assertEqual(self.gui.GUICtrlRead(dummy), 0)
        self.assertEqual(self.gui.GUICtrlSetState(checkbox, GUI_CHECKED), 1)
        self.assertEqual(self.gui.GUICtrlRead(checkbox), GUI_CHECKED)  # AutoIt: 1
        self.assertEqual(
            self.gui.GUICtrlRead(checkbox, GUI_READ_EXTENDED), "Check"
        )  # AutoIt: 'Check'
        self.gui.GUICtrlSetData(progress, 50)
        self.assertEqual(self.gui.GUICtrlRead(progress), 50)  # AutoIt: 50
        self.gui.GUICtrlSetData(slider, 30)
        self.assertEqual(self.gui.GUICtrlRead(slider), 30)  # AutoIt: 30
        self.gui.GUICtrlSetData(listbox, "a|b|c", "b")
        self.assertEqual(self.gui.GUICtrlRead(listbox), "b")  # AutoIt: 'b'
        self.gui.GUICtrlSetData(combo, "x|y|z", "z")
        self.assertEqual(self.gui.GUICtrlRead(combo), "z")  # AutoIt: 'z'
        self.assertEqual(self.gui.GUICtrlSendToDummy(dummy, 42), 1)
        self.assertEqual(self.gui.GUICtrlRead(dummy), 42)  # AutoIt: 42
        self.assertEqual(self.gui.GUICtrlRead(999999), 0)

    def test_advanced_mode_adds_the_text(self) -> None:
        """Advanced mode adds the control's text for Checkbox and Radio."""

        self.gui.GUICreate("test", 300, 200)
        checkbox = self.gui.GUICtrlCreateCheckbox("Check", 10, 10)
        radio = self.gui.GUICtrlCreateRadio("Radio", 10, 40)
        self.assertEqual(self.gui.GUICtrlRead(checkbox, GUI_READ_EXTENDED), "Check")
        self.assertEqual(self.gui.GUICtrlRead(radio, GUI_READ_EXTENDED), "Radio")

    def test_radio_grouping_follows_gui_start_group(self) -> None:
        """Only one Radio in a group is checked; GUIStartGroup() starts a new group."""

        self.gui.GUICreate("test", 400, 300)
        first = self.gui.GUICtrlCreateRadio("one", 10, 10)
        second = self.gui.GUICtrlCreateRadio("two", 10, 40)
        self.gui.GUIStartGroup()
        other = self.gui.GUICtrlCreateRadio("other", 10, 70)
        self.gui.GUICtrlSetState(first, GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlRead(first), GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlRead(second), GUI_UNCHECKED)
        self.gui.GUICtrlSetState(second, GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlRead(first), GUI_UNCHECKED)
        self.assertEqual(self.gui.GUICtrlRead(second), GUI_CHECKED)
        self.gui.GUICtrlSetState(other, GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlRead(second), GUI_CHECKED)

    def test_list_read_and_clear_use_the_data_separator(self) -> None:
        """A leading separator destroys the previous list (GUICtrlSetData remark)."""

        self.gui.GUICreate("test", 300, 200)
        listbox = self.gui.GUICtrlCreateList("", 10, 10, 150, 80)
        self.assertEqual(self.gui.Opt("GUIDataSeparatorChar"), "|")
        self.gui.GUICtrlSetData(listbox, "a|b|c")
        self.assertEqual(self.value(listbox).size(), 3)
        self.gui.GUICtrlSetData(listbox, "|x|y")
        self.assertEqual(self.value(listbox).size(), 2)
        self.assertEqual(self.gui.GUICtrlRead(listbox), "")

    def test_combo_dropdownlist_style_is_read_only(self) -> None:
        """$CBS_DROPDOWNLIST makes a Combo a read-only list, which is what the style means."""

        self.gui.GUICreate("test", 300, 200)
        combo = self.gui.GUICtrlCreateCombo("one", 10, 10, 120, 20, CBS_DROPDOWNLIST)
        self.gui.GUICtrlSetData(combo, "two|three")
        self.assertEqual(str(self.widget(combo).cget("state")), "readonly")

    def test_input_password_style_hides_the_text(self) -> None:
        """$ES_PASSWORD masks an Input, and $ES_READONLY makes it read-only."""

        self.gui.GUICreate("test", 300, 200)
        password = self.gui.GUICtrlCreateInput("secret", 10, 10, 120, 20, gui_module.ES_PASSWORD)
        readonly = self.gui.GUICtrlCreateInput("fixed", 10, 40, 120, 20, gui_module.ES_READONLY)
        self.assertEqual(str(self.widget(password).cget("show")), "*")
        self.assertEqual(str(self.widget(readonly).cget("state")), "readonly")

    def test_listview_items_read_with_a_trailing_separator(self) -> None:
        """A ListView item reads as its subitems plus a trailing separator
        (AutoIt: 'a|b|')."""

        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView("ColA|ColB|ColC", 10, 10, 200, 100)
        item = self.gui.GUICtrlCreateListViewItem("a|b|c", listview)
        self.assertEqual(self.gui.GUICtrlRead(listview), 0)
        self.assertEqual(self.gui.GUICtrlRead(item), "a|b|c|")
        # "To update a specific column just forget about the others ie "||update" to update
        # 3rd column."
        self.assertEqual(self.gui.GUICtrlSetData(item, "||update"), 1)
        self.assertEqual(self.gui.GUICtrlRead(item), "||update|")
        # Naming fewer columns leaves the rest alone.
        self.assertEqual(self.gui.GUICtrlSetData(item, "a"), 1)
        self.assertEqual(self.gui.GUICtrlRead(item), "a||update|")

    def test_treeview_items_read_state_and_text(self) -> None:
        """A TreeView reads the selected item's ID; an item reads its state and text."""

        self.gui.GUICreate("test", 400, 300)
        tree = self.gui.GUICtrlCreateTreeView(10, 10, 200, 150)
        item = self.gui.GUICtrlCreateTreeViewItem("root", tree)
        child = self.gui.GUICtrlCreateTreeViewItem("child", item)
        self.assertEqual(self.gui.GUICtrlRead(tree), 0)  # AutoIt: 0 with no selection
        self.assertEqual(self.gui.GUICtrlRead(item), 0)  # AutoIt: 0
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), "root")  # AutoIt: 'root'
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_EXPAND), 1)
        self.assertTrue(self.gui.GUICtrlRead(item) & GUI_EXPAND)
        self.gui.GUICtrlSetState(child, GUI_FOCUS)
        self.assertEqual(self.gui.GUICtrlRead(tree), child)

    def test_tab_reads_the_index_and_the_item_id(self) -> None:
        """A Tab reads the 0-based index, and the selected TabItem's ID in advanced mode
        (AutoIt: 0 and the tab item's control ID)."""

        self.gui.GUICreate("test", 400, 300)
        tabs = self.gui.GUICtrlCreateTab(10, 10, 300, 200)
        first = self.gui.GUICtrlCreateTabItem("one")
        second = self.gui.GUICtrlCreateTabItem("two")
        self.gui.GUICtrlCreateTabItem("")
        self.assertEqual(self.gui.GUICtrlRead(tabs), 0)  # AutoIt: 0
        self.assertEqual(self.gui.GUICtrlRead(tabs, GUI_READ_EXTENDED), first)
        self.gui.GUICtrlSetState(second, GUI_SHOW)
        self.assertEqual(self.gui.GUICtrlRead(tabs), 1)
        self.assertEqual(self.gui.GUICtrlRead(second), "")  # AutoIt returned ""

    def test_menu_items_read_their_state_and_text(self) -> None:
        """A menu and its item read 68 (enabled and unchecked) and their text
        (AutoIt: 68, 'File' / 'Open')."""

        self.gui.GUICreate("test", 400, 300)
        menu = self.gui.GUICtrlCreateMenu("File")
        item = self.gui.GUICtrlCreateMenuItem("Open", menu)
        separator = self.gui.GUICtrlCreateMenuItem("", menu)
        self.assertEqual(self.gui.GUICtrlRead(menu), 68)  # AutoIt: 68
        self.assertEqual(self.gui.GUICtrlRead(menu, GUI_READ_EXTENDED), "File")  # AutoIt: 'File'
        self.assertEqual(self.gui.GUICtrlRead(item), 68)  # AutoIt: 68
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), "Open")  # AutoIt: 'Open'
        self.assertGreater(separator, item)
        self.assertEqual(self.gui.GUICtrlSetData(item, "Close"), 1)
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), "Close")

    def test_menu_state_can_be_disabled_and_checked(self) -> None:
        """$GUI_DISABLE and $GUI_CHECKED change a menu item's state (State table)."""

        self.gui.GUICreate("test", 400, 300)
        menu = self.gui.GUICtrlCreateMenu("File")
        item = self.gui.GUICtrlCreateMenuItem("Open", menu)
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_DISABLE), 1)
        self.assertEqual(self.gui.GUICtrlRead(item), GUI_DISABLE | GUI_UNCHECKED)
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_ENABLE), 1)
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_CHECKED), 1)
        self.assertEqual(self.gui.GUICtrlRead(item), GUI_ENABLE | GUI_CHECKED)
        # "State of a 'menu' or a 'menuitem' control cannot be hidden."
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_HIDE), 0)

    def test_submenus_nest_under_a_menu(self) -> None:
        """GUICtrlCreateMenu() with a menu ID makes a submenu."""

        self.gui.GUICreate("test", 400, 300)
        menu = self.gui.GUICtrlCreateMenu("File")
        submenu = self.gui.GUICtrlCreateMenu("Recent", menu)
        item = self.gui.GUICtrlCreateMenuItem("one.txt", submenu)
        self.assertGreater(submenu, menu)
        self.assertEqual(self.gui.GUICtrlRead(submenu, GUI_READ_EXTENDED), "Recent")
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), "one.txt")


# --- control state --------------------------------------------------------------------


class ControlStateTest(GuiTestCase):
    """GUICtrlGetState() reports state bits, and GUICtrlSetPos() honours Default."""

    def test_guictrlgetstate_matches_autoit(self) -> None:
        """The state word is $GUI_SHOW|$GUI_ENABLE (80), 96 hidden and 144 disabled."""

        self.gui.GUICreate("test", 300, 200)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        self.assertEqual(self.gui.GUICtrlGetState(button), 80)  # AutoIt: 80
        self.assertEqual(self.gui.GUICtrlSetState(button, GUI_DISABLE), 1)
        self.assertEqual(self.gui.GUICtrlGetState(button), 144)  # AutoIt: 144
        self.assertEqual(self.gui.GUICtrlSetState(button, GUI_ENABLE), 1)
        self.assertEqual(self.gui.GUICtrlSetState(button, GUI_HIDE), 1)
        self.assertEqual(self.gui.GUICtrlGetState(button), 96)  # AutoIt: 96
        self.assertEqual(self.gui.GUICtrlSetState(button, GUI_SHOW), 1)
        self.assertEqual(self.gui.GUICtrlGetState(button), 80)  # AutoIt: 80
        self.assertEqual(self.gui.GUICtrlGetState(999999), -1)  # AutoIt: -1

    def test_checked_state_is_not_a_getstate_bit(self) -> None:
        """"this function returns ONLY the state ... enabled/disabled/hidden/show"."""

        self.gui.GUICreate("test", 300, 200)
        checkbox = self.gui.GUICtrlCreateCheckbox("Check", 10, 10)
        self.gui.GUICtrlSetState(checkbox, GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlGetState(checkbox), 80)  # AutoIt: 80

    def test_guictrlsetpos_default_keyword_keeps_a_value(self) -> None:
        """None is AutoIt's Default keyword: "the current value is not modified"."""

        self.gui.GUICreate("test", 400, 300)
        label = self.gui.GUICtrlCreateLabel("x", 10, 10, 50, 20)
        widget = self.widget(label)
        widget.update_idletasks()
        self.assertEqual(self.gui.GUICtrlSetPos(label, 30, None, None, None), 1)
        info = widget.place_info()
        self.assertEqual(
            (int(info["x"]), int(info["y"]), int(info["width"]), int(info["height"])),
            (30, 10, 50, 20),
        )
        self.assertEqual(self.gui.GUICtrlSetPos(label, 30, 10, 80, 25), 1)
        info = widget.place_info()
        self.assertEqual((int(info["width"]), int(info["height"])), (80, 25))

    def test_hiding_and_showing_a_control_keeps_its_geometry(self) -> None:
        """$GUI_HIDE and $GUI_SHOW change visibility only: the control keeps its place.

        AutoIt's hidden control keeps its coordinates and size, so showing it again puts it
        back where it was. tkinter's place_forget() discards them unless the layer remembers.
        """

        window = self.gui.GUICreate("test", 400, 300)
        self.gui.GUISetState(SW_SHOW, window)
        button = self.gui.GUICtrlCreateButton("OK", 40, 60, 90, 25)
        widget = self.widget(button)
        widget.update_idletasks()
        self.assertEqual(
            [
                self.gui.GUICtrlSetState(button, GUI_HIDE),
                self.gui.GUICtrlGetState(button),
            ],
            [1, 96],
        )
        self.assertEqual(self.gui.GUICtrlSetState(button, GUI_SHOW), 1)
        widget.update_idletasks()
        info = widget.place_info()
        self.assertEqual(
            (int(info["x"]), int(info["y"]), int(info["width"]), int(info["height"])),
            (40, 60, 90, 25),
        )
        self.assertTrue(widget.winfo_ismapped())
        self.gui.GUISetState(SW_HIDE, window)

    def test_guictrlsetresizing_records_the_docking_value(self) -> None:
        """GUICtrlSetResizing() records the docking value the reference documents."""

        self.gui.GUICreate("test", 400, 300)
        label = self.gui.GUICtrlCreateLabel("x", 10, 10, 50, 20)
        self.assertEqual(self.gui.GUICtrlSetResizing(label, gui_module.GUI_DOCKALL), 1)
        self.assertEqual(
            self.gui._controls[label].resizing, 802  # noqa: SLF001 - the recorded value
        )

    def test_guictrlsetlimit_sets_a_slider_range(self) -> None:
        """GUICtrlSetLimit() sets the range for a Slider and characters for an Input."""

        self.gui.GUICreate("test", 400, 300)
        slider = self.gui.GUICtrlCreateSlider(10, 40, 200, 30)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 100, 20)
        self.assertEqual(self.gui.GUICtrlSetLimit(slider, 20, 5), 1)
        self.assertEqual(self.gui.GUICtrlSetData(slider, 20), 1)
        self.assertEqual(self.gui.GUICtrlRead(slider), 20)
        self.assertEqual(self.gui.GUICtrlSetLimit(entry, 4), 1)
        widget = self.widget(entry)
        widget.delete(0, "end")
        for character in "12345":
            widget.insert("end", character)
            widget.event_generate("<Key>")
        self.assertLessEqual(len(widget.get()), 5)

    def test_guictrlsetgraphic_draws_into_the_control(self) -> None:
        """A Graphic control is drawn with the $GUI_GR_* command set."""

        self.gui.GUICreate("test", 400, 300)
        graphic = self.gui.GUICtrlCreateGraphic(10, 10)
        canvas = self.widget(graphic)
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, GUI_GR_COLOR, 0x0000FF), 1)
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, GUI_GR_MOVE, 0, 0), 1)
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, GUI_GR_LINE, 40, 40), 1)
        self.assertEqual(len(canvas.find_all()), 1)
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, 999), -1)

    def test_graphic_default_size_is_150_square(self) -> None:
        """GUICtrlCreateGraphic() with no size is 150x150 (AutoIt: 150x150)."""

        self.gui.GUICreate("test", 400, 300)
        graphic = self.gui.GUICtrlCreateGraphic(10, 10)
        info = self.widget(graphic).place_info()
        self.assertEqual((int(info["width"]), int(info["height"])), (150, 150))

    def test_button_and_label_size_themselves_to_their_text(self) -> None:
        """With no width or height the controls autofit their text, as the pages say."""

        self.gui.GUICreate("test", 400, 300)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10)
        info = self.widget(button).place_info()
        self.assertGreater(int(info["width"]), 0)
        self.assertGreater(int(info["height"]), 0)

    def test_guictrlsetimage_reads_what_tk_can_and_names_what_it_cannot(self) -> None:
        """tkinter reads PNG and GIF; an icon file is named as the gap it is."""

        self.gui.GUICreate("test", 400, 300)
        picture = self.gui.GUICtrlCreatePic("", 10, 10, 20, 20)
        gif = Path(tempfile.gettempdir()) / "py4gw_gui_test_dot.gif"
        icon = Path(tempfile.gettempdir()) / "py4gw_gui_test_dot.ico"
        gif.write_bytes(_DOT_GIF)
        icon.write_bytes(b"\x00\x00\x01\x00")
        try:
            self.assertEqual(self.gui.GUICtrlSetImage(picture, str(gif)), 1)
            with self.assertRaises(NotImplementedError) as context:
                self.gui.GUICtrlSetImage(picture, str(icon))
            self.assertIn("PNG and GIF", str(context.exception))
        finally:
            for path in (gif, icon):
                try:
                    path.unlink()
                except OSError:
                    pass

    def test_guictrlregister_listview_sort_uses_the_callback(self) -> None:
        """The sorting callback receives (listviewID, lParam1, lParam2, column) and
        returns -1, 0 or 1, as GUICtrlRegisterListViewSort.htm documents."""

        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView("Name", 10, 10, 200, 100)
        third = self.gui.GUICtrlCreateListViewItem("c", listview)
        first = self.gui.GUICtrlCreateListViewItem("a", listview)
        second = self.gui.GUICtrlCreateListViewItem("b", listview)
        calls: list[tuple[int, int, int, int]] = []

        def compare(listview_id: int, lparam1: int, lparam2: int, column: int) -> int:
            calls.append((listview_id, lparam1, lparam2, column))
            left = self.gui.GUICtrlRead(lparam1)[0]
            right = self.gui.GUICtrlRead(lparam2)[0]
            return -1 if left < right else 1 if left > right else 0

        self.assertEqual(self.gui.GUICtrlRegisterListViewSort(listview, compare), 1)
        self.gui._sort_listview(self.gui._controls[listview], 0)  # noqa: SLF001 - a heading click
        self.assertTrue(calls)
        self.assertEqual(calls[0][0], listview)
        rows = self.widget(listview).get_children("")
        self.assertEqual(
            [self.widget(listview).item(row, "values")[0] for row in rows], ["a", "b", "c"]
        )
        self.assertEqual(self.gui.GUICtrlGetState(listview), 0)  # the clicked column
        self.assertEqual(self.gui.GUICtrlRead(third), "c|")
        self.assertEqual(self.gui.GUICtrlRead(first), "a|")
        self.assertEqual(self.gui.GUICtrlRead(second), "b|")

    def test_guictrldelete_removes_a_control(self) -> None:
        """GUICtrlDelete() removes a control and reports 1; 0 for an unknown ID."""

        self.gui.GUICreate("test", 400, 300)
        label = self.gui.GUICtrlCreateLabel("x", 10, 10)
        self.assertEqual(self.gui.GUICtrlDelete(label), 1)
        self.assertEqual(self.gui.GUICtrlRead(label), 0)
        self.assertEqual(self.gui.GUICtrlDelete(999999), 0)

    def test_guictrldelete_removes_a_listview_or_treeview_item(self) -> None:
        """AutoIt: GUICtrlDelete on an item takes its row out of the control and returns 1.

        Measured (probe_autoit_delete_item_out.txt): three rows became two, the neighbours kept
        their text, the deleted item then read 0, deleting it again returned 0, and a TreeViewItem
        behaved the same way. The port deleted only the control record, so a table that is cleared
        and refilled grew a duplicate row on every redraw.
        """

        self.gui.GUICreate("test", 500, 300)
        listview = self.gui.GUICtrlCreateListView("A|B", 10, 10, 400, 120)
        tree = self.widget(listview)
        items = [
            self.gui.GUICtrlCreateListViewItem(f"row{index}|{index}", listview)
            for index in range(3)
        ]
        self.assertEqual(len(tree.get_children("")), 3)
        self.assertEqual(self.gui.GUICtrlDelete(items[1]), 1)
        self.assertEqual(len(tree.get_children("")), 2)
        self.assertEqual(self.gui.GUICtrlRead(items[0]), "row0|0|")
        self.assertEqual(self.gui.GUICtrlRead(items[2]), "row2|2|")
        self.assertEqual(self.gui.GUICtrlRead(items[1]), 0)
        self.assertEqual(self.gui.GUICtrlDelete(items[1]), 0)
        # Clearing and refilling -- what a redraw does -- leaves the new rows and nothing else.
        for item in (items[0], items[2]):
            self.gui.GUICtrlDelete(item)
        self.assertEqual(len(tree.get_children("")), 0)
        self.gui.GUICtrlCreateListViewItem("new|1", listview)
        self.gui.GUICtrlCreateListViewItem("new|2", listview)
        self.assertEqual(len(tree.get_children("")), 2)

        treeview = self.gui.GUICtrlCreateTreeView(10, 150, 200, 100)
        tree_item = self.gui.GUICtrlCreateTreeViewItem("alpha", treeview)
        self.gui.GUICtrlCreateTreeViewItem("beta", treeview)
        tree_widget = self.widget(treeview)
        self.assertEqual(len(tree_widget.get_children("")), 2)
        self.assertEqual(self.gui.GUICtrlDelete(tree_item), 1)
        self.assertEqual(len(tree_widget.get_children("")), 1)

    def test_a_list_and_an_edit_take_their_font_on_the_widget_that_shows_it(self) -> None:
        """A List and an Edit are a frame around the widget, and the font belongs to that widget."""

        self.gui.GUICreate("test", 400, 300)
        list_control = self.gui.GUICtrlCreateList("", 10, 10, 200, 120)
        edit = self.gui.GUICtrlCreateEdit("", 220, 10, 160, 120)
        self.assertEqual(
            self.gui.GUICtrlSetFont(list_control, 14, 700, GUI_FONTNORMAL, "Segoe UI"), 1
        )
        self.assertEqual(self.gui.GUICtrlSetFont(edit, 14, 700, GUI_FONTNORMAL, "Segoe UI"), 1)
        self.assertIn("14", str(self.value(list_control).cget("font")))
        self.assertIn("14", str(self.value(edit).cget("font")))
        self.assertEqual(self.gui.GUICtrlSetState(list_control, GUI_DISABLE), 1)
        self.assertEqual(str(self.value(list_control).cget("state")), "disabled")
        self.assertEqual(self.gui.GUICtrlSetState(list_control, GUI_ENABLE), 1)
        self.assertEqual(str(self.value(list_control).cget("state")), "normal")


# --- options --------------------------------------------------------------------------


class OptionTest(GuiTestCase):
    """Opt() reads and writes the reference's GUI options."""

    def test_opt_returns_the_previous_value_and_names_unknown_options(self) -> None:
        """Opt() returns the previous setting, and names an option it does not implement."""

        self.assertEqual(self.gui.Opt("GUIOnEventMode"), 0)
        self.assertEqual(self.gui.Opt("GUIOnEventMode", 1), 0)
        self.assertEqual(self.gui.Opt("GUIOnEventMode"), 1)
        self.assertEqual(self.gui.Opt("GUIOnEventMode", 0), 1)
        self.assertEqual(self.gui.AutoItSetOption("GUIResizeMode"), 0)
        self.assertEqual(self.gui.Opt("GUICloseOnESC"), 1)
        self.assertEqual(self.gui.Opt("GUICoordMode"), 1)
        self.assertEqual(self.gui.Opt("GUIDataSeparatorChar"), "|")
        with self.assertRaises(NotImplementedError):
            self.gui.Opt("WinTitleMatchMode")
        with self.assertRaises(NotImplementedError):
            self.gui.Opt("GUIEventCompatibilityMode")

    def test_guieventoptions_does_not_stop_the_docking(self) -> None:
        """AutoIt: Opt("GUIEventOptions", 1) suppresses a *window's* behaviour, not the docking.

        probe_autoit_resizing_out.txt set the option and resized the window anyway; every control
        docked exactly as it had with the option unset. The option's own effect is measured
        separately (a minimize request leaves the window at state 15 and still calls the function).
        """

        self.gui.Opt("GUIEventOptions", 1)
        window = self.gui.GUICreate("test", 500, 300)
        button = self.gui.GUICtrlCreateButton("c", 60, 45, 100, 30)
        self.gui._controls[button].dock_client = (398, 275)  # noqa: SLF001
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        record = self.gui._windows[window]  # noqa: SLF001
        record.layout_seen = True
        self.gui._window_configured(window, _Configure(record.widget, 684, 461))
        self.assertEqual(self.gui._controls[button].pos, (103, 75, 100, 30))  # noqa: SLF001

    def test_guidataseparatorchar_can_be_changed(self) -> None:
        """Opt("GUIDataSeparatorChar") changes what the port splits and joins with."""

        self.assertEqual(self.gui.Opt("GUIDataSeparatorChar"), "|")
        self.assertEqual(self.gui.Opt("GUIDataSeparatorChar", ","), "|")
        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView("ColA,ColB", 10, 10, 200, 100)
        item = self.gui.GUICtrlCreateListViewItem("a,b", listview)
        self.assertEqual(self.gui.GUICtrlRead(item), "a,b,")


# --- messages and events --------------------------------------------------------------


class EventTest(GuiTestCase):
    """The two AutoIt event modes and the messages they produce."""

    def test_guigetmsg_returns_zero_when_there_is_no_event(self) -> None:
        """No event is $GUI_EVENT_NONE (0); advanced mode returns the documented array."""

        self.gui.GUICreate("test", 200, 120)
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_NONE)  # AutoIt: 0
        advanced = self.gui.GUIGetMsg(1)
        self.assertIsInstance(advanced, list)
        self.assertEqual(len(advanced), 5)
        self.assertEqual(advanced[0], GUI_EVENT_NONE)

    def test_sending_to_a_dummy_notifies_the_message_loop(self) -> None:
        """A Dummy notifies as if clicked, but only while its window is shown
        (GUICtrlSendToDummy.htm)."""

        window = self.gui.GUICreate("test", 200, 120)
        dummy = self.gui.GUICtrlCreateDummy()
        self.assertEqual(self.gui.GUICtrlSendToDummy(dummy, 7), 1)
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_NONE)  # hidden window: no notification
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        self.assertEqual(self.gui.GUICtrlSendToDummy(dummy, 8), 1)
        self.assertEqual(self.gui.GUIGetMsg(), dummy)  # AutoIt: the dummy's control ID
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_NONE)
        self.gui.GUISetState(SW_HIDE, window)

    def test_clicking_a_button_reports_the_control_id(self) -> None:
        """A clicked control sends its control ID, as the message-loop page describes."""

        window = self.gui.GUICreate("test", 200, 120)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 80, 25)
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        self.widget(button).invoke()
        self.assertEqual(self.gui.GUIGetMsg(), button)
        self.gui.GUISetState(SW_HIDE, window)

    def test_an_input_change_is_a_control_event(self) -> None:
        """"When a control is clicked or changes a control event is sent"."""

        window = self.gui.GUICreate("test", 200, 120)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 20)
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        widget = self.widget(entry)
        widget.focus_set()
        self.gui.Sleep(20)
        widget.insert("end", "typed")
        widget.event_generate("<KeyRelease>")
        self.assertEqual(self.gui.GUIGetMsg(), entry)
        self.gui.GUISetState(SW_HIDE, window)

    def test_a_list_selection_is_a_control_event(self) -> None:
        """A List answers a selection with its own control ID, as the interpreter's does.

        Measured (probe_autoit_listview_event_out.txt): clicking a row of a List called the
        function registered on the List and set ``@GUI_CtrlId`` to the List's identifier. The port
        bound the event on the frame around the list box instead of the list box, so a selection
        fired nothing at all.
        """

        window = self.gui.GUICreate("test", 200, 160)
        control = self.gui.GUICtrlCreateList("", 10, 10, 120, 100)
        self.gui.GUICtrlSetData(control, "alpha")
        self.gui.GUICtrlSetData(control, "beta")
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        listbox = self.value(control)
        listbox.selection_clear(0, "end")
        listbox.selection_set(1)
        listbox.event_generate("<<ListboxSelect>>")
        self.assertEqual(self.gui.GUIGetMsg(), control)
        self.assertEqual(self.gui.GUICtrlRead(control), "beta")
        self.gui.GUISetState(SW_HIDE, window)

    def test_a_listview_selection_is_the_listview_s_control_event(self) -> None:
        """A ListView answers a row click with its *own* ID, and not the item's.

        Measured (probe_autoit_listview_event_out.txt): clicking either row called the function
        registered on the ListView with ``@GUI_CtrlId`` = the ListView's identifier, while the two
        functions registered on the items were never called. ``GUICtrlRead`` still reports the
        selected item's identifier, which is what its own page documents.
        """

        window = self.gui.GUICreate("test", 400, 200)
        listview = self.gui.GUICtrlCreateListView("A|B", 10, 10, 300, 120)
        first = self.gui.GUICtrlCreateListViewItem("a|1", listview)
        second = self.gui.GUICtrlCreateListViewItem("b|2", listview)
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        tree = self.widget(listview)
        tree.selection_set(tree.get_children("")[1])
        tree.event_generate("<<TreeviewSelect>>")
        self.assertEqual(self.gui.GUIGetMsg(), listview)
        self.assertEqual(self.gui.GUICtrlRead(listview), second)
        self.assertNotEqual(self.gui.GUICtrlRead(listview), first)
        self.gui.GUISetState(SW_HIDE, window)

    def test_an_edit_change_is_a_control_event(self) -> None:
        """An Edit reports its own change, which the port bound on the frame around the text box."""

        window = self.gui.GUICreate("test", 300, 200)
        edit = self.gui.GUICtrlCreateEdit("", 10, 10, 200, 100)
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUIGetMsg()
        text = self.value(edit)
        text.insert("end", "typed")
        text.event_generate("<<Modified>>")
        self.assertEqual(self.gui.GUIGetMsg(), edit)
        self.assertEqual(self.gui.GUICtrlRead(edit), "typed")
        self.gui.GUISetState(SW_HIDE, window)

    def test_close_and_escape_send_the_close_event(self) -> None:
        """$GUI_EVENT_CLOSE arrives from the close button and, with the default
        GUICloseOnESC, from ESC."""

        window = self.gui.GUICreate("test", 200, 120)
        self.gui.GUISetState(SW_SHOW, window)
        widget = self.gui._windows[window].widget  # noqa: SLF001
        self.gui.GUIGetMsg()
        widget.event_generate("<Escape>")
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_CLOSE)  # AutoIt: -3
        self.gui._window_close_requested(window)  # noqa: SLF001 - as the close button does
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_CLOSE)
        self.gui.GUISetState(SW_HIDE, window)

    def test_guicloseonesc_off_stops_escape_closing(self) -> None:
        """Opt("GUICloseOnESC", 0) stops ESC from sending $GUI_EVENT_CLOSE."""

        self.gui.Opt("GUICloseOnESC", 0)
        window = self.gui.GUICreate("test", 200, 120)
        self.gui.GUISetState(SW_SHOW, window)
        widget = self.gui._windows[window].widget  # noqa: SLF001
        self.gui.GUIGetMsg()
        widget.event_generate("<Escape>")
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_NONE)
        self.gui.GUISetState(SW_HIDE, window)

    def test_onevent_mode_calls_the_handler_and_getmsg_returns_zero(self) -> None:
        """OnEvent mode: the GUI calls the function, and "the return from GUIGetMsg is
        always 0 and the @error is set to 1"."""

        calls: list[tuple[int, int]] = []

        def handler() -> None:
            calls.append((self.gui.GUI_CtrlId, self.gui.GUI_WinHandle))

        self.assertEqual(self.gui.Opt("GUIOnEventMode", 1), 0)
        window = self.gui.GUICreate("test", 200, 120)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 80, 25)
        self.assertEqual(self.gui.GUICtrlSetOnEvent(button, handler), 1)
        self.assertEqual(self.gui.GUIGetMsg(), 0)
        self.assertEqual(self.gui.error, 1)
        self.gui.GUISetState(SW_SHOW, window)
        self.widget(button).invoke()
        self.assertEqual(calls, [(button, window)])
        self.assertEqual(self.gui.GUICtrlSetOnEvent(button, ""), 1)
        self.widget(button).invoke()
        self.assertEqual(calls, [(button, window)])
        self.gui.Opt("GUIOnEventMode", 0)
        self.gui.GUISetState(SW_HIDE, window)

    def test_onevent_system_event_handler_receives_the_event_id(self) -> None:
        """GUISetOnEvent() registers system events, and @GUI_CtrlId carries the event ID."""

        events: list[int] = []
        self.gui.Opt("GUIOnEventMode", 1)
        window = self.gui.GUICreate("test", 200, 120)
        self.assertEqual(
            self.gui.GUISetOnEvent(GUI_EVENT_CLOSE, lambda: events.append(self.gui.GUI_CtrlId)),
            1,
        )
        self.assertEqual(self.gui.GUISetOnEvent(GUI_EVENT_CLOSE, ""), 1)
        self.assertEqual(
            self.gui.GUISetOnEvent(GUI_EVENT_CLOSE, lambda: events.append(self.gui.GUI_CtrlId)),
            1,
        )
        self.gui._window_close_requested(window)  # noqa: SLF001 - as the close button does
        self.assertEqual(events, [GUI_EVENT_CLOSE])
        self.gui.Opt("GUIOnEventMode", 0)

    def test_on_event_functions_must_be_callables(self) -> None:
        """AutoIt passes a function name; Python needs the callable, and says so."""

        self.gui.GUICreate("test", 200, 120)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        with self.assertRaises(TypeError) as context:
            self.gui.GUICtrlSetOnEvent(button, "OnOK")
        self.assertIn("callable", str(context.exception))
        with self.assertRaises(TypeError):
            self.gui.GUISetOnEvent(GUI_EVENT_CLOSE, "OnClose")

    def test_accelerators_action_their_control(self) -> None:
        """An accelerator "action[s] their associated control which then fires the
        function using GUIGetMsg() or GUICtrlSetOnEvent()"."""

        window = self.gui.GUICreate("test", 200, 120)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 80, 25)
        self.assertEqual(self.gui.GUISetAccelerators([["^s", button]], window), 1)
        self.gui.GUISetState(SW_SHOW, window)
        widget = self.gui._windows[window].widget  # noqa: SLF001
        self.gui.GUIGetMsg()
        widget.focus_set()
        self.gui.Sleep(20)
        widget.event_generate("<Control-Key-s>")
        self.assertEqual(self.gui.GUIGetMsg(), button)
        self.assertEqual(self.gui.GUISetAccelerators(None, window), 1)
        # An unset accelerator no longer fires, which is what "unset all accelerators" means.
        widget.event_generate("<Control-Key-s>")
        self.assertEqual(self.gui.GUIGetMsg(), 0)
        # The Windows key (#) is AutoIt's, and tkinter cannot spell it: the base key is bound and
        # Windows is asked whether the key is held. The Windows key is not pressed here — that
        # would open the Start menu — so its state is stubbed; the real state was verified by hand
        # (docs/AUTOIT_GUI.md).
        self.assertEqual(self.gui.GUISetAccelerators([["#r", button]], window), 1)
        widget.event_generate("<KeyPress-r>")
        self.assertEqual(self.gui.GUIGetMsg(), 0)
        original = native.win_key_down
        native.win_key_down = lambda: True  # type: ignore[assignment]
        try:
            widget.event_generate("<KeyPress-r>")
        finally:
            native.win_key_down = original  # type: ignore[assignment]
        self.assertEqual(self.gui.GUIGetMsg(), button)
        self.gui.GUISetState(SW_HIDE, window)

    def test_sleep_delivers_events_in_on_event_mode(self) -> None:
        """The OnEvent idle loop is "While 1 / Sleep(100) / WEnd", so Sleep must pump."""

        calls: list[int] = []
        self.gui.Opt("GUIOnEventMode", 1)
        window = self.gui.GUICreate("test", 200, 120)
        dummy = self.gui.GUICtrlCreateDummy()
        self.gui.GUICtrlSetOnEvent(dummy, lambda: calls.append(self.gui.GUI_CtrlId))
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.GUICtrlSendToDummy(dummy, 1)
        self.assertEqual(calls, [dummy])  # AutoIt delivered it inside the SendToDummy call
        self.gui.Sleep(30)
        self.assertEqual(calls, [dummy])
        self.gui.Opt("GUIOnEventMode", 0)
        self.gui.GUISetState(SW_HIDE, window)

    def test_guigetcursorinfo_returns_five_elements(self) -> None:
        """GUIGetCursorInfo() returns the documented five-element array."""

        self.gui.GUICreate("test", 200, 120)
        info = self.gui.GUIGetCursorInfo()
        self.assertEqual(len(info), 5)
        self.assertIn(info[2], (0, 1))
        self.assertIn(info[3], (0, 1))

    def test_guisethelp_binds_f1_without_running_anything(self) -> None:
        """GUISetHelp() records the file F1 would run; the test never presses F1."""

        handle = self.gui.GUICreate("test", 200, 120)
        self.assertEqual(self.gui.GUISetHelp("help.txt", handle), 1)
        self.assertEqual(self.gui._windows[handle].help_file, "help.txt")  # noqa: SLF001
        self.assertEqual(self.gui.GUISetHelp("help.txt", 999999), 0)


# --- named gaps -----------------------------------------------------------------------


class DropAndStateTest(GuiTestCase):
    """The state-table entries that are applied rather than only recorded.

    A drag cannot be synthesized, so a drop is delivered the way Windows delivers one: a
    ``WM_DROPFILES`` message carrying an ``HDROP`` whose ``DROPFILES`` header names the file list
    and the point the drop happened at.
    """

    def _centre(self, control_id: int) -> tuple[int, int]:
        """Return a control's centre in screen coordinates, where a drop would land."""

        widget = self.widget(control_id)
        widget.update_idletasks()
        return (
            widget.winfo_rootx() + widget.winfo_width() // 2,
            widget.winfo_rooty() + widget.winfo_height() // 2,
        )

    def test_a_dropped_file_reaches_the_control_that_accepts_it(self) -> None:
        """$GUI_DROPACCEPTED sets the input's text and raises $GUI_EVENT_DROPPED."""

        self.gui.Opt("GUIOnEventMode", 1)
        window = self.gui.GUICreate("test", 500, 300)
        self.gui.GUISetState(SW_SHOW, window)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 200, 22)
        self.gui.Sleep(30)
        self.assertEqual(self.gui.GUICtrlSetState(entry, GUI_DROPACCEPTED), 1)
        self.assertTrue(self.gui.GUICtrlGetState(entry) & GUI_DROPACCEPTED)
        calls: list[int] = []
        self.gui.GUICtrlSetOnEvent(entry, lambda: calls.append(self.gui.GUI_CtrlId))

        payload = native.make_drop_payload(
            [r"C:\temp\dropped.txt"], self._centre(entry)
        )
        self.assertNotEqual(payload, 0)
        native.post_message(window, native.WM_DROPFILES, payload, 0)
        self.gui.Sleep(60)

        self.assertEqual(calls, [entry])
        self.assertEqual(self.gui.GUICtrlRead(entry), r"C:\temp\dropped.txt")
        self.assertEqual(self.gui.GUI_DragFile, r"C:\temp\dropped.txt")
        self.assertEqual(self.gui.GUI_DragId, -1)
        self.assertEqual(self.gui.GUI_DropId, entry)
        self.gui.GUISetState(SW_HIDE, window)

    def test_several_dropped_files_land_as_separate_lines_in_an_edit(self) -> None:
        """An Edit control takes a multiple-file drop as separate lines."""

        window = self.gui.GUICreate("test", 500, 300)
        self.gui.GUISetState(SW_SHOW, window)
        edit = self.gui.GUICtrlCreateEdit("", 10, 10, 200, 80)
        self.gui.Sleep(30)
        self.assertEqual(self.gui.GUICtrlSetState(edit, GUI_DROPACCEPTED), 1)
        payload = native.make_drop_payload(
            [r"C:\temp\one.txt", r"C:\temp\two.txt"], self._centre(edit)
        )
        native.post_message(window, native.WM_DROPFILES, payload, 0)
        self.gui.Sleep(60)
        self.assertEqual(
            self.gui.GUICtrlRead(edit), "C:\\temp\\one.txt\nC:\\temp\\two.txt"
        )
        self.gui.GUISetState(SW_HIDE, window)

    def test_drop_acceptance_can_be_turned_off_again(self) -> None:
        """$GUI_NODROPACCEPTED stops a control taking a drop."""

        self.gui.Opt("GUIOnEventMode", 1)
        window = self.gui.GUICreate("test", 500, 300)
        self.gui.GUISetState(SW_SHOW, window)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 200, 22)
        self.gui.Sleep(30)
        calls: list[int] = []
        self.gui.GUICtrlSetOnEvent(entry, lambda: calls.append(self.gui.GUI_CtrlId))
        self.assertEqual(self.gui.GUICtrlSetState(entry, GUI_DROPACCEPTED), 1)
        self.assertEqual(self.gui.GUICtrlSetState(entry, GUI_NODROPACCEPTED), 1)
        self.assertFalse(self.gui.GUICtrlGetState(entry) & GUI_DROPACCEPTED)
        payload = native.make_drop_payload([r"C:\temp\no.txt"], self._centre(entry))
        native.post_message(window, native.WM_DROPFILES, payload, 0)
        self.gui.Sleep(60)
        self.assertEqual(calls, [])
        self.assertEqual(self.gui.GUICtrlRead(entry), "")
        self.gui.GUISetState(SW_HIDE, window)

    def test_nofocus_gives_up_a_listview_selection(self) -> None:
        """$GUI_NOFOCUS: "Listview control will loose focus"."""

        self.gui.GUICreate("test", 500, 300)
        listview = self.gui.GUICtrlCreateListView("A|B", 10, 10, 200, 100)
        item = self.gui.GUICtrlCreateListViewItem("a|b", listview)
        self.widget(listview).selection_set(self.gui._controls[item].item)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlRead(listview), item)
        self.assertEqual(self.gui.GUICtrlSetState(listview, GUI_NOFOCUS), 1)
        self.assertEqual(self.gui.GUICtrlRead(listview), 0)


class NativeControlTest(GuiTestCase):
    """The controls the port hosts as the Win32 classes AutoIt uses.

    Date, MonthCal, Avi and Icon have no tkinter widget, so the port creates the same classes
    AutoIt creates — ``SysDateTimePick32``, ``SysMonthCal32``, ``SysAnimate32`` and ``Static``
    with ``$SS_ICON`` — as children of the tkinter frame. The expected values are the
    interpreter's (tests/autoit_reference/probe_parity2_out.txt).
    """

    def test_date_reads_and_sets_the_regional_date(self) -> None:
        """AutoIt: read 'Friday, January 2, 2026'; SetData gives 'Thursday, March 4, 2027';
        $DTS_SHORTDATEFORMAT reads '3/4/2027'."""

        self.gui.GUICreate("test", 500, 400)
        date = self.gui.GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
        self.assertEqual(self.gui.GUICtrlRead(date), "Friday, January 2, 2026")
        self.assertGreater(self.gui.GUICtrlGetHandle(date), 0)
        self.assertEqual(self.gui.GUICtrlSetData(date, "2027/03/04"), 1)
        self.assertEqual(self.gui.GUICtrlRead(date), "Thursday, March 4, 2027")
        self.assertEqual(self.gui.GUICtrlGetState(date), 80)  # AutoIt: 80
        self.assertEqual(self.gui.GUICtrlSetStyle(date, DTS_SHORTDATEFORMAT), 1)
        self.assertEqual(self.gui.GUICtrlRead(date), "3/4/2027")  # AutoIt: 3/4/2027
        self.assertEqual(self.gui.GUICtrlSetData(date, "not a date"), 0)

    def test_monthcal_reads_and_sets_yyyy_mm_dd(self) -> None:
        """AutoIt: a MonthCal reads "yyyy/mm/dd" — '2026/01/02' then '2027/03/04'."""

        self.gui.GUICreate("test", 500, 400)
        monthcal = self.gui.GUICtrlCreateMonthCal("2026/01/02", 10, 10, 220, 160)
        self.assertEqual(self.gui.GUICtrlRead(monthcal), "2026/01/02")
        self.assertGreater(self.gui.GUICtrlGetHandle(monthcal), 0)
        self.assertEqual(self.gui.GUICtrlGetState(monthcal), 80)
        self.assertEqual(self.gui.GUICtrlSetData(monthcal, "2027/03/04"), 1)
        self.assertEqual(self.gui.GUICtrlRead(monthcal), "2027/03/04")
        self.assertEqual(self.gui.GUICtrlSetData(monthcal, "nonsense"), 0)

    def test_icon_defaults_to_32_square_and_reads_empty(self) -> None:
        """AutoIt: an Icon control reads "" and is 32x32 when its size is omitted."""

        self.gui.GUICreate("test", 500, 400)
        icon = self.gui.GUICtrlCreateIcon(str(SHELL32), -1, 10, 10)
        self.assertEqual(self.gui.GUICtrlRead(icon), "")  # AutoIt: ""
        self.assertGreater(self.gui.GUICtrlGetHandle(icon), 0)
        self.assertEqual(self.gui._controls[icon].pos, (10, 10, 32, 32))  # noqa: SLF001
        self.assertNotEqual(self.gui._controls[icon].image, 0)  # noqa: SLF001

    def test_avi_reads_empty_and_takes_its_own_states(self) -> None:
        """AutoIt: an Avi control reads "", and $GUI_AVISTOP/$GUI_AVICLOSE return 1."""

        self.gui.GUICreate("test", 500, 400)
        avi = self.gui.GUICtrlCreateAvi(str(SAMPLE_AVI), 0, 10, 10, 120, 120)
        self.assertEqual(self.gui.GUICtrlRead(avi), "")  # AutoIt: ""
        self.assertGreater(self.gui.GUICtrlGetHandle(avi), 0)
        self.assertEqual(self.gui.GUICtrlSetState(avi, GUI_AVISTOP), 1)  # AutoIt: 1
        self.assertEqual(self.gui.GUICtrlSetState(avi, GUI_AVICLOSE), 1)  # AutoIt: 1

    def test_native_controls_move_hide_disable_and_delete(self) -> None:
        """A native control's window is placed, shown, hidden, disabled and destroyed."""

        window = self.gui.GUICreate("test", 500, 400)
        self.gui.GUISetState(SW_SHOW, window)
        date = self.gui.GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
        self.assertEqual(self.gui.GUICtrlSetPos(date, 200, 40, 160, 22), 1)
        self.assertEqual(self.gui._controls[date].pos, (200, 40, 160, 22))  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlSetState(date, GUI_HIDE), 1)
        self.assertEqual(self.gui.GUICtrlGetState(date), 96)  # AutoIt: 96
        self.assertEqual(self.gui.GUICtrlSetState(date, GUI_SHOW), 1)
        self.assertEqual(self.gui.GUICtrlGetState(date), 80)  # AutoIt: 80
        self.assertEqual(self.gui.GUICtrlSetState(date, GUI_DISABLE), 1)
        self.assertEqual(self.gui.GUICtrlGetState(date), 144)  # AutoIt: 144
        self.assertEqual(self.gui.GUICtrlDelete(date), 1)
        self.assertEqual(self.gui.GUICtrlRead(date), 0)
        self.gui.GUISetState(SW_HIDE, window)

    def test_updown_is_the_native_control_on_its_buddy_input(self) -> None:
        """AutoIt: an UpDown reads "", SetData returns -1, SetLimit 1, and it sits 18 wide at
        the input's right edge (probe_parity3_out.txt)."""

        self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        updown = self.gui.GUICtrlCreateUpdown(entry)
        self.assertEqual(self.gui.GUICtrlRead(updown), "")  # AutoIt: ""
        self.assertEqual(self.gui.GUICtrlRead(entry), "5")
        self.assertGreater(self.gui.GUICtrlGetHandle(updown), 0)
        self.assertEqual(self.gui.GUICtrlGetState(updown), 80)  # AutoIt: 80
        self.assertEqual(self.gui._controls[updown].pos, (10 + 120 - 2, 10, 18, 22))  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlSetData(updown, 12), -1)  # AutoIt: -1
        self.assertEqual(self.gui.GUICtrlRead(entry), "5")
        self.assertEqual(self.gui.GUICtrlSetLimit(updown, 30, 3), 1)  # AutoIt: 1

    def test_updown_writes_its_buddy_input(self) -> None:
        """$UDS_SETBUDDYINT puts the position into the buddy Input, which is what the user sees.

        The control writes it into the input's *window*, so the port asks the window rather than
        Tk's cached string — measured: after UDM_SETPOS32(20) the interpreter read "20".
        """

        window = self.gui.GUICreate("test", 500, 300)
        self.gui.GUISetState(SW_SHOW, window)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        updown = self.gui.GUICtrlCreateUpdown(entry)
        self.widget(entry).update_idletasks()
        handle = self.gui._controls[updown].native  # noqa: SLF001
        self.assertEqual(native.updown_get_position(handle), 0)
        native.updown_set_position(handle, 20)
        self.assertEqual(native.updown_get_position(handle), 20)
        self.assertEqual(self.gui.GUICtrlRead(entry), "20")  # AutoIt: '20'
        # The tkinter widget shows the same text, so the user sees the number the arrows moved.
        self.assertEqual(self.widget(entry).get(), "20")
        # The arrow buttons are the control's own: a click on them still moves the value.
        native.updown_set_position(handle, 4)
        self.assertEqual(self.gui.GUICtrlRead(entry), "4")
        self.assertEqual(self.gui.GUICtrlSetPos(updown, 50, 50), 1)
        self.assertEqual(self.gui._controls[updown].pos, (50, 50, 18, 22))  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlSetState(updown, GUI_HIDE), 1)
        self.assertEqual(self.gui.GUICtrlGetState(updown), 96)  # AutoIt: 96
        self.assertEqual(self.gui.GUICtrlDelete(updown), 1)
        self.assertEqual(self.gui.GUICtrlRead(updown), 0)

    def test_an_updown_buddys_input_reads_its_own_text(self) -> None:
        """AutoIt: an Input created with "5" reads "5", with or without an UpDown on it.

        tkinter keeps an Entry's string in Tk and not in the window (measured: ``GetWindowTextW``
        on the mapped window answers with nothing while Tk holds "5"), so reading the window
        whenever the input had a buddy returned "" and wrote it back into Tk, wiping the input.
        The window is read only after the control has moved, which is when it is the newer text.
        """

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        updown = self.gui.GUICtrlCreateUpdown(entry)
        self.assertEqual(self.gui.GUICtrlRead(entry), "5")  # AutoIt: '5'
        self.assertEqual(self.widget(entry).get(), "5")
        self.assertEqual(self.gui.GUICtrlRead(entry), "5")  # a second read changes nothing
        self.assertEqual(self.widget(entry).get(), "5")
        # After the control writes its position into the buddy, that is what the user sees.
        native.updown_set_position(self.gui._controls[updown].native, 20)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlRead(entry), "20")  # AutoIt: '20'
        self.assertEqual(self.widget(entry).get(), "20")
        self.gui.GUISetState(SW_HIDE, window)

    def test_the_window_is_hooked_for_a_native_controls_notifications(self) -> None:
        """Native controls report through WM_NOTIFY, so their window and frame are hooked.

        A control sends its notification to the window it is a child of — the tkinter frame it
        was placed in — which is not the GUI window, so both are hooked.
        """

        window = self.gui.GUICreate("test", 500, 300)
        self.assertEqual(self.gui._hooked_windows, set())  # noqa: SLF001
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        self.gui.GUICtrlCreateUpdown(entry)
        frame = int(self.gui._parent_widget(self.gui._windows[window]).winfo_id())  # noqa: SLF001
        self.assertIn(window, self.gui._hooked_windows)  # noqa: SLF001
        self.assertIn(frame, self.gui._hooked_windows)  # noqa: SLF001

    def test_a_notification_code_is_negative_and_fires_the_control_event(self) -> None:
        """AutoIt's notification codes are negative ($UDN_DELTAPOS is -722).

        Read as an unsigned word the same code is 4294966574, which matched none of the port's
        constants — so no native control event could ever fire. The notification is posted here,
        which is how the port's own tests deliver one; a real arrow click was verified by hand
        (recorded in docs/AUTOIT_GUI.md).
        """

        self.gui.Opt("GUIOnEventMode", 1)
        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        updown = self.gui.GUICtrlCreateUpdown(entry)
        events: list[int] = []
        self.gui.GUICtrlSetOnEvent(updown, lambda: events.append(self.gui.GUI_CtrlId))
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.Sleep(30)

        header = native.NMHDR()
        header.hwndFrom = self.gui.GUICtrlGetHandle(updown)
        header.idFrom = 0
        header.code = native.UDN_DELTAPOS
        native.post_message(self.gui._windows[window].widget_id, 0x004E, 0,  # noqa: SLF001
                            ctypes.addressof(header))
        # The values are read inside the hooked procedure and delivered by the pump, because a
        # procedure that calls tkinter can be re-entered with no interpreter state to restore.
        self.gui.Sleep(50)
        self.assertEqual(events, [updown])
        self.gui.GUISetState(SW_HIDE, window)

    def test_the_updown_window_is_where_the_control_says_it_is(self) -> None:
        """An UpDown aligns itself to its buddy, and the buddy is not laid out yet when it is made.

        Measured: the port's record said 18x22 at the input's right edge while the control's own
        window was 1x1 at the parent's origin, so the pointer could not reach the arrows. The
        record and the window must agree.
        """

        window = self.gui.GUICreate("test", 500, 300)
        self.gui.GUISetState(SW_SHOW, window)
        entry = self.gui.GUICtrlCreateInput("5", 10, 10, 120, 22)
        updown = self.gui.GUICtrlCreateUpdown(entry)
        self.gui.Sleep(30)
        record = self.gui._controls[updown].pos  # noqa: SLF001
        assert record is not None  # the control was placed, which is the point of the test
        self.assertEqual(record, (10 + 120 - 2, 10, 18, 22))
        left, top, right, bottom = native.window_rect(self.gui.GUICtrlGetHandle(updown))
        self.assertEqual((right - left, bottom - top), (record[2], record[3]))
        # It sits inside its parent's client area, at the box the port recorded.
        origin_left, origin_top, _right, _bottom = native.window_rect(
            self.gui._windows[window].widget_id  # noqa: SLF001
        )
        self.assertEqual((left - origin_left, top - origin_top), (record[0], record[1]))
        self.gui.GUISetState(SW_HIDE, window)

    def test_gui_event_options_suppresses_the_window_and_still_notifies(self) -> None:
        """AutoIt: with GUIEventOptions=1 a minimize request does not minimize, but notifies.

        Measured from the interpreter (probe_autoit_gui_event_options_out.txt): a $SC_MINIMIZE
        request left the window at state 15 and still called the $GUI_EVENT_MINIMIZE function, while
        with the option unset the window went to state 23 (minimised) and called it too.
        """

        window = self.gui.GUICreate("test", 300, 200)
        self.gui.GUISetState(SW_SHOW, window)
        widget = self.gui._windows[window].widget  # noqa: SLF001
        self.gui.Sleep(30)

        self.gui.Opt("GUIEventOptions", 1)
        native.post_message(window, 0x0112, 0xF020, 0)  # WM_SYSCOMMAND, SC_MINIMIZE
        self.gui.Sleep(60)
        self.assertEqual(widget.state(), "normal")  # AutoIt: state 15, not minimised
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_MINIMIZE)  # AutoIt: the function ran

        self.gui.Opt("GUIEventOptions", 0)
        native.post_message(window, 0x0112, 0xF020, 0)
        self.gui.Sleep(80)
        self.assertNotEqual(widget.state(), "normal")  # the request goes through
        widget.deiconify()
        self.gui.Sleep(30)
        self.gui.GUISetState(SW_HIDE, window)

    def test_font_quality_reaches_a_native_controls_own_font(self) -> None:
        """AutoIt's Font Quality table is GDI's, value for value, so the control reports it back.

        `GUICtrlSetFont`'s page gives quality as 0 default, 1 draft, 2 proof, 3 nonantialiased,
        4 antialiased, 5 cleartype — the same numbers as `lfQuality`. A native control is given a
        real GDI font through `WM_SETFONT` and the port keeps the handle alive; a tkinter-drawn
        control gets a Tk font instead, where the quality has no equivalent.
        """

        window = self.gui.GUICreate("test", 500, 300)
        date = self.gui.GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
        month = self.gui.GUICtrlCreateMonthCal("2026/01/02", 10, 40, 220, 160)
        entry = self.gui.GUICtrlCreateInput("", 10, 210, 120, 22)
        self.gui.GUISetState(SW_SHOW, window)
        self.gui.Sleep(20)
        self.assertEqual(
            self.gui.GUICtrlSetFont(date, 10, 700, 0, "Tahoma", 5), 1
        )
        self.assertEqual(native.window_font_quality(self.gui.GUICtrlGetHandle(date)), 5)
        self.assertEqual(self.gui.GUICtrlSetFont(month, 9, 400, 0, "Tahoma", 4), 1)
        self.assertEqual(native.window_font_quality(self.gui.GUICtrlGetHandle(month)), 4)
        # A tkinter control takes a Tk font, and the port says so rather than pretending.
        self.assertEqual(self.gui.GUICtrlSetFont(entry, 9, 400, 0, "Tahoma", 5), 1)
        self.assertTrue(str(self.widget(entry).cget("font")).startswith("Tahoma 9"))
        self.assertEqual(self.gui.GUICtrlSetFont(999999, 10), 0)
        self.gui.GUISetState(SW_HIDE, window)

    def test_the_bezier_follows_the_curve_the_interpreter_draws(self) -> None:
        """$GUI_GR_BEZIER is a cubic with two control points, and the port draws that curve.

        The reference gives the parameters as "x,y,x1,y1,x2,y2 — Draw a bezier curve with 2 control
        points", so the curve runs from the current position through both control points to x,y.
        The interpreter's own rendering of `MOVE 20,120` and `BEZIER 200,120,20,20,200,20` was read
        pixel by pixel (probe_autoit_graphic_out.txt): the rows below are where its curve runs in
        each column. The port's flattened cubic matches them to under a pixel, where Tk's smooth
        spline — which treats the points as control points of a different curve — was up to 57
        pixels away. The first column is left out: the curve is vertical there, so the darkest
        pixel of that column is not the curve's height.
        """

        rows = {40: 71, 60: 57, 80: 49, 100: 46, 120: 46, 140: 49, 160: 57, 180: 71}
        window = self.gui.GUICreate("test", 320, 220)
        graphic = self.gui.GUICtrlCreateGraphic(10, 10, 240, 160)
        self.widget(graphic).update_idletasks()
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, GUI_GR_COLOR, 0x000000), 1)
        self.assertEqual(self.gui.GUICtrlSetGraphic(graphic, GUI_GR_MOVE, 20, 120), 1)
        self.assertEqual(
            self.gui.GUICtrlSetGraphic(graphic, GUI_GR_BEZIER, 200, 120, 20, 20, 200, 20), 1
        )
        canvas = self.widget(graphic)
        item = canvas.find_all()[-1]
        coordinates = canvas.coords(item)
        points = [(int(coordinates[index]), int(coordinates[index + 1]))
                  for index in range(0, len(coordinates), 2)]
        self.assertEqual(points[0], (20, 120))
        # The curve ends at the point the command names, so the next drawing starts there.
        self.assertEqual(points[-1][0], 200)
        self.assertAlmostEqual(points[-1][1], 120, delta=1)
        for column, row in rows.items():
            crossing = _curve_y_at(points, column)
            self.assertIsNotNone(crossing, f"the curve does not cross column {column}")
            assert crossing is not None
            self.assertAlmostEqual(crossing, row, delta=1.0)
        self.gui.GUISetState(SW_HIDE, window)

    def test_a_picture_reads_the_formats_windows_reads_and_keeps_autoits_sizes(self) -> None:
        """A Pic takes BMP and JPG (the reference lists "BMP, JPG, GIF and TIF"), and its sizes are
        the interpreter's.

        Measured (probe_autoit_pic_out.txt): a Pic made from a 255x40 JPG with no width or height
        was 40x30 — the size the control before it used — and with width and height 0 it was 255x40,
        the file's own size, which is what the page's "To set the picture control to the same size
        as the file content set width and height to 0" asks for. The first control in a fresh window
        came back 150x150, not the window's 400. The BMP here is written by the test, so its pixels
        are the oracle for what the port decoded.
        """

        window = self.gui.GUICreate("test", 500, 400)
        # The first control in a fresh window: 150x150 (AutoIt), so the two after it inherit sizes.
        first = self.gui.GUICtrlCreatePic(str(SAMPLE_BMP), 10, 10)
        self.assertEqual(self.gui._controls[first].pos, (10, 10, 150, 150))  # noqa: SLF001
        sized = self.gui.GUICtrlCreatePic(str(SAMPLE_BMP), 10, 100, 40, 30)
        self.assertEqual(self.gui._controls[sized].pos, (10, 100, 40, 30))  # noqa: SLF001
        inherited = self.gui.GUICtrlCreatePic(str(SAMPLE_BMP), 10, 200)
        self.assertEqual(self.gui._controls[inherited].pos, (10, 200, 40, 30))  # noqa: SLF001
        file_sized = self.gui.GUICtrlCreatePic(str(SAMPLE_BMP), 10, 300, 0, 0)
        self.assertEqual(self.gui._controls[file_sized].pos, (10, 300, 6, 4))  # noqa: SLF001
        image = self.gui._controls[file_sized].image  # noqa: SLF001
        rows = SAMPLE_BMP_PIXELS
        for y, row in enumerate(rows):
            for x, expected in enumerate(row):
                self.assertEqual(tuple(image.get(x, y)), expected)
        self.assertEqual(self.gui.GUICtrlRead(file_sized), "")  # AutoIt: ""
        self.assertEqual(self.gui.GUICtrlSetImage(file_sized, str(SAMPLE_BMP)), 1)
        self.gui.GUISetState(SW_HIDE, window)

    def test_a_picture_file_that_cannot_be_read_names_what_it_needs(self) -> None:
        """A file no decoder reads still raises, naming the formats the reference lists."""

        self.gui.GUICreate("test", 500, 400)
        with self.assertRaises(NotImplementedError) as context:
            self.gui.GUICtrlCreatePic(str(MISSING_ICON), 10, 10)
        self.assertIn("BMP", str(context.exception))

    def test_a_control_with_no_size_takes_the_previously_used_one(self) -> None:
        """AutoIt: "width/height default is the previously used width/height" — measured.

        probe_autoit_default_size_out.txt: an Input with no size in a fresh window was 200x20; an
        Input with no size after an Input made 50x10 was 50x10; and after a Button, whose size is
        computed from its text ("OK" is 23x25), an Input with no size was **23x25** — so a control
        whose size was computed for it still counts as the size last used.
        """

        window = self.gui.GUICreate("test", 600, 400)
        first = self.gui.GUICtrlCreateInput("", 10, 10)
        self.assertEqual(self.gui._controls[first].pos, (10, 10, 200, 20))  # noqa: SLF001
        explicit = self.gui.GUICtrlCreateInput("", 10, 50, 50, 10)
        self.assertEqual(self.gui._controls[explicit].pos, (10, 50, 50, 10))  # noqa: SLF001
        after_explicit = self.gui.GUICtrlCreateInput("", 10, 90)
        self.assertEqual(self.gui._controls[after_explicit].pos,  # noqa: SLF001
                         (10, 90, 50, 10))
        button = self.gui.GUICtrlCreateButton("OK", 10, 130)
        button_box = self.gui._controls[button].pos  # noqa: SLF001
        assert button_box is not None
        last = self.gui.GUICtrlCreateInput("", 10, 170)
        self.assertEqual(self.gui._controls[last].pos,  # noqa: SLF001
                         (10, 170, button_box[2], button_box[3]))
        self.gui.GUISetState(SW_HIDE, window)

    def test_each_kind_of_control_has_the_default_size_the_interpreter_gives(self) -> None:
        """The kinds' own defaults, each created first in a window of its own (probe_autoit_defaults).

        AutoIt's readings: an Input 200x20, an Edit 200x150, a Combo 200x21, a List 200x149 (a list
        box snaps its height to whole items, so 150 is what it was asked for), a Progress and a
        Slider 0x0, a Tab, TreeView, ListView and Pic 150x150, a Date 200x20, a MonthCal 229x164 and
        a Group 200x150. Button, Label, Checkbox and Radio take their size from their text instead.
        """

        expected: dict[str, tuple[int, int]] = {
            "Input": (200, 20),
            "Edit": (200, 150),
            "Combo": (200, 21),
            "List": (200, 150),
            "Progress": (0, 0),
            "Slider": (0, 0),
            "Tab": (150, 150),
            "TreeView": (150, 150),
            "ListView": (150, 150),
            "Date": (200, 20),
            "MonthCal": (229, 164),
            "Group": (200, 150),
        }
        for kind, want in expected.items():
            gui = GUI()
            window = gui.GUICreate("fresh " + kind, 600, 400)
            created = {
                "Input": lambda: gui.GUICtrlCreateInput("", 10, 10),
                "Edit": lambda: gui.GUICtrlCreateEdit("", 10, 10),
                "Combo": lambda: gui.GUICtrlCreateCombo("", 10, 10),
                "List": lambda: gui.GUICtrlCreateList("", 10, 10),
                "Progress": lambda: gui.GUICtrlCreateProgress(10, 10),
                "Slider": lambda: gui.GUICtrlCreateSlider(10, 10),
                "Tab": lambda: gui.GUICtrlCreateTab(10, 10),
                "TreeView": lambda: gui.GUICtrlCreateTreeView(10, 10),
                "ListView": lambda: gui.GUICtrlCreateListView("A", 10, 10),
                "Date": lambda: gui.GUICtrlCreateDate("2026/01/02", 10, 10),
                "MonthCal": lambda: gui.GUICtrlCreateMonthCal("2026/01/02", 10, 10),
                "Group": lambda: gui.GUICtrlCreateGroup("g", 10, 10),
            }[kind]()
            box = gui._controls[created].pos  # noqa: SLF001
            assert box is not None
            self.assertEqual((box[2], box[3]), want, kind)
            gui.GUISetState(SW_HIDE, window)
            if gui._root is not None:
                gui._root.destroy()

    def test_native_controls_are_deleted_with_their_window(self) -> None:
        """GUIDelete() destroys the native windows too, so no child window is left behind."""

        window = self.gui.GUICreate("test", 500, 400)
        date = self.gui.GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
        handle = self.gui.GUICtrlGetHandle(date)
        self.assertEqual(self.gui.GUIDelete(window), 1)
        self.assertFalse(native.window_exists(handle))


class TipTest(GuiTestCase):
    """GUICtrlSetTip attaches the Windows tooltip control, which is what draws the tip.

    The port hosts ``tooltips_class32`` as AutoIt does, so the text, the title row and its icon
    are Windows' own. What AutoIt builds was read from the interpreter rather than assumed
    (``tests/autoit_reference/probe_autoit_gui_tip.au3`` and ``probe_autoit_gui_tip2.au3``): **one
    tooltip control per control**, created on the first ``GUICtrlSetTip`` for it and holding exactly
    one tool whose ``uId`` is that control's window; a second call for the same control replaces
    the window; style ``0x84000013`` (``0x84000053`` with ``$TIP_BALLOON``) and exStyle
    ``0x00080088``; the GUI window as the tooltip's parent; tool flags ``0x51``, and ``0x53`` after
    ``$TIP_CENTER`` (``$TTF_CENTERTIP`` on the tool, not a width on the control); and the tip goes
    when the control or the window does. Every expectation below is one of those readings.
    """

    def tip_text(self, window: int, control_id: int) -> str:
        """Read a control's tooltip text the way the control does, from its own tooltip window."""

        tooltip = self.gui._controls[control_id].tooltip  # noqa: SLF001
        return native.tooltip_text(tooltip, self.gui.GUICtrlGetHandle(control_id), window)

    def test_each_control_has_its_own_tooltip_with_one_tool(self) -> None:
        """AutoIt: two tipped controls are two tooltip windows, each holding one tool."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        button = self.gui.GUICtrlCreateButton("OK", 10, 40, 90, 25)
        self.assertEqual(self.gui.GUICtrlSetTip(entry, "first text", "First title", TIP_INFOICON), 1)
        self.assertEqual(self.gui.GUICtrlSetTip(button, "second text"), 1)
        entry_tip = self.gui._controls[entry].tooltip  # noqa: SLF001
        button_tip = self.gui._controls[button].tooltip  # noqa: SLF001
        self.assertNotEqual(entry_tip, 0)
        self.assertNotEqual(button_tip, 0)
        self.assertNotEqual(entry_tip, button_tip)
        for tip, control in ((entry_tip, entry), (button_tip, button)):
            self.assertEqual(native.tooltip_tool_count(tip), 1)  # AutoIt: 1
            uId, flags = native.tooltip_tool_info(tip)
            self.assertEqual(uId, self.gui.GUICtrlGetHandle(control))
            self.assertEqual(flags, 0x51)  # AutoIt: 0x51
            self.assertEqual(native.get_parent(tip), window)  # AutoIt: the GUI handle
            self.assertEqual(native.get_style(tip), 0x84000013)  # AutoIt: 0x84000013
            self.assertEqual(native.get_exstyle(tip), 0x00080088)  # AutoIt: 0x00080088
        self.assertEqual(self.tip_text(window, entry), "first text")
        self.assertEqual(self.tip_text(window, button), "second text")
        self.assertEqual(native.tooltip_title(entry_tip), (TIP_INFOICON, "First title"))
        # The untitled tip has no title, which is what the interpreter's had.
        self.assertEqual(native.tooltip_title(button_tip), (TIP_NOICON, ""))

    def test_a_title_is_the_controls_own(self) -> None:
        """AutoIt: titling the button's tip left the input's title alone."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        button = self.gui.GUICtrlCreateButton("OK", 10, 40, 90, 25)
        self.gui.GUICtrlSetTip(entry, "first text", "First title", TIP_INFOICON)
        self.gui.GUICtrlSetTip(button, "second text")
        self.assertEqual(self.gui.GUICtrlSetTip(button, "second text", "Second title",
                                                TIP_ERRORICON), 1)
        self.assertEqual(
            native.tooltip_title(self.gui._controls[entry].tooltip),  # noqa: SLF001
            (TIP_INFOICON, "First title"),
        )
        self.assertEqual(
            native.tooltip_title(self.gui._controls[button].tooltip),  # noqa: SLF001
            (TIP_ERRORICON, "Second title"),
        )

    def test_a_tip_set_again_replaces_that_controls_tooltip(self) -> None:
        """AutoIt: the tip window's handle changed on every GUICtrlSetTip call."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        button = self.gui.GUICtrlCreateButton("OK", 10, 40, 90, 25)
        self.gui.GUICtrlSetTip(entry, "first text", "First title", TIP_INFOICON)
        self.gui.GUICtrlSetTip(button, "second text", "Second title", TIP_INFOICON)
        before = self.gui._controls[entry].tooltip  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlSetTip(entry, "changed text", "Changed",
                                                TIP_WARNINGICON), 1)
        after = self.gui._controls[entry].tooltip  # noqa: SLF001
        self.assertNotEqual(after, before)
        self.assertFalse(native.window_exists(before))
        self.assertEqual(native.tooltip_title(after), (TIP_WARNINGICON, "Changed"))
        self.assertEqual(self.tip_text(window, entry), "changed text")
        # The other control's tip is untouched by it.
        self.assertEqual(
            native.tooltip_title(self.gui._controls[button].tooltip),  # noqa: SLF001
            (TIP_INFOICON, "Second title"),
        )

    def test_tip_holds_its_text_title_and_icon(self) -> None:
        """AutoIt: GUICtrlSetTip returns 1, and $TIP_INFOICON (1) is the title icon."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        self.assertEqual(
            self.gui.GUICtrlSetTip(entry, "an input tip", "Title here", TIP_INFOICON), 1
        )
        tooltip = self.gui._controls[entry].tooltip  # noqa: SLF001
        self.assertNotEqual(tooltip, 0)
        self.assertEqual(self.tip_text(window, entry), "an input tip")
        self.assertEqual(native.tooltip_title(tooltip), (TIP_INFOICON, "Title here"))

    def test_tip_on_a_native_control_and_its_icon_values(self) -> None:
        """The native controls are tool targets too, and each $TIP_*ICON is the title's icon."""

        window = self.gui.GUICreate("test", 500, 300)
        date = self.gui.GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
        for icon in (TIP_NOICON, TIP_INFOICON, TIP_WARNINGICON, TIP_ERRORICON):
            self.assertEqual(self.gui.GUICtrlSetTip(date, "a date", "When", icon), 1)
            tooltip = self.gui._controls[date].tooltip  # noqa: SLF001
            self.assertEqual(native.tooltip_title(tooltip), (icon, "When"))
            self.assertEqual(native.tooltip_tool_info(tooltip)[0], self.gui.GUICtrlGetHandle(date))
            self.assertEqual(self.tip_text(window, date), "a date")

    def test_a_title_is_only_set_when_one_is_given(self) -> None:
        """The reference: "icon: Pre-defined icon ... requires a title"."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        self.assertEqual(self.gui.GUICtrlSetTip(entry, "no title", "", TIP_WARNINGICON), 1)
        tooltip = self.gui._controls[entry].tooltip  # noqa: SLF001
        self.assertEqual(self.tip_text(window, entry), "no title")
        self.assertEqual(native.tooltip_title(tooltip), (TIP_NOICON, ""))

    def test_balloon_is_the_controls_own_style(self) -> None:
        """$TIP_BALLOON (1) is $TTS_BALLOON on that control's tooltip: AutoIt's 0x84000053."""

        self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        button = self.gui.GUICtrlCreateButton("OK", 10, 40, 90, 25)
        self.assertEqual(self.gui.GUICtrlSetTip(entry, "plain"), 1)
        self.assertEqual(self.gui.GUICtrlSetTip(button, "balloon", "T", TIP_INFOICON,
                                                TIP_BALLOON), 1)
        ballooned = native.get_style(self.gui._controls[button].tooltip)  # noqa: SLF001
        plain = native.get_style(self.gui._controls[entry].tooltip)  # noqa: SLF001
        self.assertEqual(ballooned, 0x84000053)  # AutoIt: 0x84000053
        self.assertEqual(plain, 0x84000013)  # AutoIt: 0x84000013
        self.assertEqual(ballooned & native.TTS_BALLOON, native.TTS_BALLOON)
        self.assertEqual(plain & native.TTS_BALLOON, 0)

    def test_center_is_the_tools_flag(self) -> None:
        """AutoIt: $TIP_CENTER made the tool's flags 0x53 — $TTF_CENTERTIP on the tool."""

        self.gui.GUICreate("test", 500, 300)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 90, 25)
        self.assertEqual(self.gui.GUICtrlSetTip(button, "centred", "Centre", TIP_NOICON,
                                                TIP_CENTER), 1)
        tooltip = self.gui._controls[button].tooltip  # noqa: SLF001
        self.assertEqual(native.tooltip_tool_info(tooltip)[1], 0x53)  # AutoIt: 0x53
        self.assertEqual(native.get_style(tooltip), 0x84000013)  # AutoIt: not a balloon

    def test_forcevisible_leaves_the_control_as_it_was(self) -> None:
        """AutoIt: $TIP_FORCEVISIBLE left the tool flags at 0x51 and the style unchanged."""

        self.gui.GUICreate("test", 500, 300)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 90, 25)
        self.assertEqual(self.gui.GUICtrlSetTip(button, "forced", "Force", TIP_NOICON,
                                                TIP_FORCEVISIBLE), 1)
        tooltip = self.gui._controls[button].tooltip  # noqa: SLF001
        self.assertEqual(native.tooltip_tool_info(tooltip)[1], 0x51)  # AutoIt: 0x51
        self.assertEqual(native.get_style(tooltip), 0x84000013)  # AutoIt: 0x84000013

    def test_deleting_a_control_or_window_removes_its_tips(self) -> None:
        """AutoIt: GUICtrlDelete took the control's tip window, GUIDelete took the rest."""

        window = self.gui.GUICreate("test", 500, 300)
        entry = self.gui.GUICtrlCreateInput("", 10, 10, 120, 22)
        button = self.gui.GUICtrlCreateButton("OK", 10, 40, 90, 25)
        self.gui.GUICtrlSetTip(entry, "first text", "First title", TIP_INFOICON)
        self.gui.GUICtrlSetTip(button, "second text", "Second title", TIP_INFOICON)
        entry_tip = self.gui._controls[entry].tooltip  # noqa: SLF001
        button_tip = self.gui._controls[button].tooltip  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlDelete(entry), 1)
        self.assertFalse(native.window_exists(entry_tip))
        self.assertTrue(native.window_exists(button_tip))
        self.assertEqual(self.gui.GUIDelete(window), 1)
        self.assertFalse(native.window_exists(button_tip))

    def test_tip_on_an_unknown_control_returns_zero(self) -> None:
        """AutoIt: GUICtrlSetTip on an id that does not exist returns 0."""

        self.gui.GUICreate("test", 500, 300)
        self.assertEqual(self.gui.GUICtrlSetTip(999999, "x", "y", TIP_INFOICON), 0)


class ResizingTest(GuiTestCase):
    """GUICtrlSetResizing and GUIResizeMode: how a window's resize moves its controls.

    Every box below was read from the interpreter, whose window went from a 398x275 client to a
    684x461 one with a control at 60,45 100x30 (``tests/autoit_reference/probe_autoit_resizing3_out.txt``
    and ``probe_autoit_resizing9_out.txt``): ``$GUI_DOCKAUTO`` gave 103,75,171,50,
    ``$GUI_DOCKBORDERS`` 60,45,386,216, ``$GUI_DOCKWIDTH|$GUI_DOCKHCENTER`` 203,75,100,50, and a
    value of 1024 or more behaved as the control's own default. The docking arithmetic was compared
    against all 123 of those readings; the cases here are the ones that pin each branch.

    The resize is delivered to the port's own handler, because a real window resize needs a mapped
    window: the probe scripts measure the interpreter's, and this desktop's window manager has been
    refusing to map windows (recorded in docs/AUTOIT_GUI.md). Everything after the event — which
    control the handler docks, from which base, and where it lands — is the port's real path.
    """

    def configure(self, window: int, width: int, height: int) -> None:
        """Deliver a window resize to the port, as tkinter's Configure event does."""

        record = self.gui._windows[window]  # noqa: SLF001
        record.layout_seen = True  # a mapped window's first configure is the layout one
        self.gui._window_configured(window, _Configure(record.widget, width, height))

    def box(self, control_id: int) -> str:
        """Return a control's box as "left,top,width,height"."""

        return ",".join(str(part) for part in (self.gui._controls[control_id].pos or ()))  # noqa: SLF001

    def test_each_docking_value_lands_where_the_interpreter_put_it(self) -> None:
        """The whole docking table, with the interpreter's own boxes."""

        expected = {
            0: "103,75,100,30",     # 0 = the Button's own default, $GUI_DOCKSIZE
            1: "103,75,171,50",     # $GUI_DOCKAUTO
            2: "60,75,171,50",      # $GUI_DOCKLEFT
            4: "275,75,171,50",     # $GUI_DOCKRIGHT
            8: "103,75,171,50",     # $GUI_DOCKHCENTER alone left the position scaled
            16: "103,75,171,50",    # a value the reference's table does not list, but 0x10 is read
            32: "103,45,171,50",    # $GUI_DOCKTOP
            64: "103,211,171,50",   # $GUI_DOCKBOTTOM
            128: "103,75,171,50",   # $GUI_DOCKVCENTER alone
            256: "103,75,100,50",   # $GUI_DOCKWIDTH
            512: "103,75,171,30",   # $GUI_DOCKHEIGHT
            768: "103,75,100,30",   # $GUI_DOCKSIZE
            802: "60,45,100,30",    # $GUI_DOCKALL
            102: "60,45,386,216",   # $GUI_DOCKBORDERS
            544: "103,45,171,30",   # $GUI_DOCKMENUBAR
            576: "103,231,171,30",  # $GUI_DOCKSTATEBAR
            264: "203,75,100,50",   # $GUI_DOCKWIDTH + $GUI_DOCKHCENTER
            640: "103,138,171,30",  # $GUI_DOCKHEIGHT + $GUI_DOCKVCENTER
            68: "275,211,171,50",   # $GUI_DOCKRIGHT + $GUI_DOCKBOTTOM
            260: "346,75,100,50",   # $GUI_DOCKWIDTH + $GUI_DOCKRIGHT
            358: "60,45,386,216",   # $GUI_DOCKBORDERS + $GUI_DOCKWIDTH: the edges win
            900: "346,138,100,30",  # $GUI_DOCKSIZE + $GUI_DOCKRIGHT + $GUI_DOCKVCENTER
            1023: "60,45,386,216",  # every low bit set
            803: "60,45,100,30",    # $GUI_DOCKALL + 1
            819: "60,45,100,30",    # $GUI_DOCKALL + 16
            1024: "103,75,100,30",  # 1024 and above: the control's default
            1040: "103,75,100,30",  # 16 + 1024 is not 16: the value is taken whole
            1826: "103,75,100,30",
            4096: "103,75,100,30",
            5120: "103,75,100,30",
        }
        window = self.gui.GUICreate("test", 500, 300)
        controls = {}
        for dock in expected:
            control = self.gui.GUICtrlCreateButton("c", 60, 45, 100, 30)
            self.assertEqual(self.gui.GUICtrlSetResizing(control, dock), 1)
            controls[dock] = control
        # The creation client is the window's, which is what the probe's 398x275 corresponds to.
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        for control in controls.values():
            self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 684, 461)
        for dock, want in expected.items():
            self.assertEqual(self.box(controls[dock]), want, f"docking value {dock}")

    def test_the_docking_arithmetic_truncates_like_the_interpreter(self) -> None:
        """AutoIt: an odd box of 61,46,101,31 in a 683x460 client (probe_autoit_resizing9 part 3)."""

        expected = {
            0: "104,76,101,31",
            1: "104,76,173,51",
            2: "61,76,173,51",
            4: "274,76,173,51",
            8: "104,76,173,51",
            32: "104,46,173,51",
            64: "104,211,173,51",
            128: "104,76,173,51",
            256: "104,76,101,51",
            512: "104,76,173,31",
            802: "61,46,101,31",
            102: "61,46,386,216",
            264: "203,76,101,51",
            640: "104,138,173,31",
            257: "104,76,101,51",
            514: "61,76,173,31",
        }
        window = self.gui.GUICreate("test", 500, 300)
        controls = {}
        for dock in expected:
            control = self.gui.GUICtrlCreateButton("c", 61, 46, 101, 31)
            self.gui.GUICtrlSetResizing(control, dock)
            controls[dock] = control
        for control in controls.values():
            self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        self.configure(window, 683, 460)
        for dock, want in expected.items():
            self.assertEqual(self.box(controls[dock]), want, f"docking value {dock}")

    def test_a_single_shrink_lands_where_the_interpreter_put_it(self) -> None:
        """AutoIt: one resize from the creation client to 284x161 (probe_autoit_resizing10).

        The interpreter's own boxes, including the two things a shrink makes possible: a position
        past a pinned edge is negative (``$GUI_DOCKRIGHT`` gave -25), and a stretched size stops at
        0 (``$GUI_DOCKBORDERS`` gave 0,0 where the gap between its pinned edges is -14x-84).
        """

        expected = {
            0: "42,26,100,30",
            1: "42,26,71,17",
            2: "60,26,71,17",
            4: "-25,26,71,17",
            8: "42,26,71,17",
            32: "42,45,71,17",
            64: "42,-56,71,17",
            128: "42,26,71,17",
            256: "42,26,100,17",
            512: "42,26,71,30",
            768: "42,26,100,30",
            802: "60,45,100,30",
            102: "60,45,0,0",
            1023: "60,45,0,0",
            358: "60,45,0,0",
            264: "3,26,100,17",
            640: "42,-12,71,30",
            68: "-25,-56,71,17",
            900: "-54,-12,100,30",
            260: "-54,26,100,17",
            1024: "42,26,100,30",
        }
        window = self.gui.GUICreate("test", 500, 300)
        controls = {}
        for dock in expected:
            control = self.gui.GUICtrlCreateButton("c", 60, 45, 100, 30)
            self.gui.GUICtrlSetResizing(control, dock)
            controls[dock] = control
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        for control in controls.values():
            self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 284, 161)
        for dock, want in expected.items():
            self.assertEqual(self.box(controls[dock]), want, f"docking value {dock}")

    def test_zero_and_large_values_mean_the_control_types_own_default(self) -> None:
        """AutoIt: GUICtrlSetResizing(control, 0) and (control, 1024) give the kind's default.

        probe_autoit_resizing6 measured each kind: a Label, an Edit and a ListView docked as
        ``$GUI_DOCKAUTO``, an Input and a Date as ``$GUI_DOCKHEIGHT``, a Button and a Pic as
        ``$GUI_DOCKSIZE``.
        """

        expected = {
            "Label": "103,75,171,50",
            "Edit": "103,75,171,50",
            "ListView": "103,75,171,50",
            "Input": "103,75,171,30",
            "Date": "103,75,171,30",
            "Button": "103,75,100,30",
            "Pic": "103,75,100,30",
        }
        window = self.gui.GUICreate("test", 500, 300)
        created: dict[str, tuple[int, int]] = {}
        for kind in expected:
            created[kind] = (
                self.create_kind(kind, 60, 45, 100, 30),
                self.create_kind(kind, 60, 45, 100, 30),
            )
        for first, second in created.values():
            self.assertEqual(self.gui.GUICtrlSetResizing(first, 0), 1)
            self.assertEqual(self.gui.GUICtrlSetResizing(second, 1024), 1)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        for pair in created.values():
            for control in pair:
                self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 684, 461)
        for kind, (first, second) in created.items():
            self.assertEqual(self.box(first), expected[kind], f"{kind} with 0")
            self.assertEqual(self.box(second), expected[kind], f"{kind} with 1024")

    def create_kind(self, kind: str, left: int, top: int, width: int, height: int) -> int:
        """Create one control of a kind, at a known box."""

        if kind == "Label":
            return self.gui.GUICtrlCreateLabel("label", left, top, width, height)
        if kind == "Button":
            return self.gui.GUICtrlCreateButton("button", left, top, width, height)
        if kind == "Input":
            return self.gui.GUICtrlCreateInput("input", left, top, width, height)
        if kind == "Edit":
            return self.gui.GUICtrlCreateEdit("edit", left, top, width, height)
        if kind == "ListView":
            return self.gui.GUICtrlCreateListView("col", left, top, width, height)
        if kind == "Pic":
            return self.gui.GUICtrlCreatePic("", left, top, width, height)
        if kind == "Date":
            return self.gui.GUICtrlCreateDate("2026/01/02", left, top, width, height)
        raise AssertionError(f"no creator for {kind}")

    def test_guiresizemode_is_the_default_for_controls_created_while_it_is_set(self) -> None:
        """AutoIt: with GUIResizeMode = $GUI_DOCKALL a new control did not move at all, and a
        control created before the option was set kept its own default (probe_autoit_resizing7)."""

        self.gui.Opt("GUIResizeMode", GUI_DOCKALL)
        window = self.gui.GUICreate("test", 500, 300)
        window_control = self.gui.GUICtrlCreateButton("early", 60, 45, 100, 30)
        self.gui.Opt("GUIResizeMode", 0)
        after = self.gui.GUICtrlCreateButton("late", 60, 45, 100, 30)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        for control in (window_control, after):
            self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 684, 461)
        # Created while GUIResizeMode was $GUI_DOCKALL: the interpreter left it at 60,45 100x30.
        self.assertEqual(self.box(window_control), "60,45,100,30")
        # Created with GUIResizeMode 0: the Button's own default, $GUI_DOCKSIZE.
        self.assertEqual(self.box(after), "103,75,100,30")

    def test_the_docking_base_is_where_guictrlsetpos_put_the_control(self) -> None:
        """AutoIt: a control moved to 200,100 docked from there, giving 343,167,171,50."""

        window = self.gui.GUICreate("test", 500, 300)
        control = self.gui.GUICtrlCreateButton("b", 60, 45, 100, 30)
        self.gui.GUICtrlSetResizing(control, GUI_DOCKAUTO)
        self.assertEqual(self.gui.GUICtrlSetPos(control, 200, 100), 1)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 684, 461)
        self.assertEqual(self.box(control), "343,167,171,50")

    def test_repeated_resizes_compute_from_the_base_not_the_last_box(self) -> None:
        """AutoIt: two resizes and back gave 60,52,121,39 then 50,43,100,32 (probe 2 part A)."""

        window = self.gui.GUICreate("test", 500, 300)
        control = self.gui.GUICtrlCreateButton("b", 50, 40, 100, 30)
        self.gui.GUICtrlSetResizing(control, GUI_DOCKAUTO)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.configure(window, 684, 461)
        self.assertEqual(self.box(control), "85,67,171,50")
        self.configure(window, 484, 361)
        self.assertEqual(self.box(control), "60,52,121,39")
        self.configure(window, 400, 300)
        self.assertEqual(self.box(control), "50,43,100,32")

    def test_a_childs_configure_is_not_a_window_resize(self) -> None:
        """A toplevel is in its children's bindtags, so their Configure events reach the handler.

        Traced on this machine: a 500x300 window's handler was called with the frame's, the
        scrollbar's and the text's sizes, down to 1x1. None of those is a window resize, and a
        control that docked on them would be moved for nothing.
        """

        window = self.gui.GUICreate("test", 500, 300)
        control = self.gui.GUICtrlCreateButton("b", 60, 45, 100, 30)
        self.gui.GUISetState(SW_SHOW, window)
        record = self.gui._windows[window]  # noqa: SLF001
        record.width, record.height = 398, 275
        self.gui._controls[control].dock_client = (398, 275)  # noqa: SLF001
        self.gui._window_configured(window, _Configure(record.widget.winfo_children()[0], 1, 1))
        self.assertEqual(self.box(control), "60,45,100,30")
        self.assertEqual((record.width, record.height), (398, 275))
        self.gui.GUISetState(SW_HIDE, window)

    def test_controls_without_a_window_are_not_docked(self) -> None:
        """A Dummy has an ID and no geometry, so a resize leaves it alone."""

        window = self.gui.GUICreate("test", 500, 300)
        dummy = self.gui.GUICtrlCreateDummy()
        self.assertEqual(self.gui.GUICtrlSetResizing(dummy, GUI_DOCKALL), 1)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        self.configure(window, 684, 461)
        self.assertIsNone(self.gui._controls[dummy].pos)  # noqa: SLF001

    def test_resizing_an_unknown_control_returns_zero(self) -> None:
        """AutoIt: GUICtrlSetResizing on an id that does not exist returns 0."""

        self.gui.GUICreate("test", 500, 300)
        self.assertEqual(self.gui.GUICtrlSetResizing(999999, GUI_DOCKALL), 0)


class MessageAndResourceTest(GuiTestCase):
    """The Win32 side of AutoIt's GUI: messages, icons and the painting lock.

    AutoIt's GUI is Win32, and tkinter's widgets are windows, so these functions call the same
    APIs AutoIt calls. The expected values were read from the AutoIt interpreter
    (tests/autoit_reference/probe_parity_out.txt).
    """

    def test_guictrlsendmsg_reaches_the_control(self) -> None:
        """GUICtrlSendMsg is SendMessage on the control (AutoIt: BM_CLICK returned 0)."""

        self.gui.GUICreate("test", 400, 300)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        self.assertEqual(self.gui.GUICtrlSendMsg(button, WM_GETDLGCODE, 0, 0) >= 0, True)
        self.assertEqual(self.gui.GUICtrlSendMsg(button, 0x00F5, 0, 0), 0)  # BM_CLICK
        self.assertEqual(self.gui.GUICtrlSendMsg(999999, 0x00F5, 0, 0), 0)

    def test_guictrlrecvmsg_returns_the_documented_shapes(self) -> None:
        """lParamType 0 gives [wParam, lParam], 1 a string and 2 a RECT."""

        self.gui.GUICreate("test", 400, 300)
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        pair = self.gui.GUICtrlRecvMsg(button, WM_GETDLGCODE, 0, 0)
        self.assertEqual(len(pair), 2)
        self.assertIsInstance(pair[0], int)
        self.assertIsInstance(self.gui.GUICtrlRecvMsg(button, WM_GETTEXT, 8, 1), str)
        rect = self.gui.GUICtrlRecvMsg(button, WM_GETTEXT, 0, 2)
        self.assertEqual(len(rect), 4)

    def test_guisetstate_lock_is_lockwindowupdate(self) -> None:
        """$SW_LOCK locks the window's painting; $SW_UNLOCK unlocks any locked window."""

        window = self.gui.GUICreate("test", 200, 120)
        self.assertEqual(self.gui.GUISetState(SW_LOCK, window), 1)
        self.assertTrue(self.gui._windows[window].locked)  # noqa: SLF001
        self.assertEqual(self.gui.GUISetState(SW_UNLOCK, window), 1)
        self.assertFalse(self.gui._windows[window].locked)  # noqa: SLF001

    def test_guiseticon_loads_a_real_icon_resource(self) -> None:
        """GUISetIcon loads an icon out of a file, and reports 0 when it cannot."""

        window = self.gui.GUICreate("test", 200, 120)
        self.assertEqual(self.gui.GUISetIcon(str(MISSING_ICON), -1, window), 0)
        if AUTOIT_ICON.is_file():
            self.assertEqual(self.gui.GUISetIcon(str(AUTOIT_ICON), -1, window), 1)
            self.assertNotEqual(self.gui._windows[window].icon, 0)  # noqa: SLF001

    def test_guiregistermsg_sees_the_window_messages(self) -> None:
        """GUIRegisterMsg hooks the window procedure and chains to the window's own.

        The message is posted and then pumped, the way Windows delivers one, and the function is
        handed the GUI's own window handle as AutoIt hands it.
        """

        window = self.gui.GUICreate("test", 300, 200)
        seen: list[tuple[int, int, int, int]] = []
        handler = lambda hwnd, message, wparam, lparam: seen.append(  # noqa: E731
            (hwnd, message, wparam, lparam)
        )
        self.assertEqual(self.gui.GUIRegisterMsg(WM_SIZE, handler), 1)
        native.post_message(window, WM_SIZE, 0, 0)
        self.gui.Sleep(60)
        self.assertEqual(seen, [(window, WM_SIZE, 0, 0)])
        # The window keeps working: the hook chains to tkinter's own procedure.
        button = self.gui.GUICtrlCreateButton("OK", 10, 10, 60, 25)
        self.assertEqual(self.gui.GUICtrlRead(button), "OK")
        # A function declared with two parameters is called with two, as the page says.
        two_arguments: list[tuple[int, int]] = []
        self.assertEqual(
            self.gui.GUIRegisterMsg(
                WM_MOVE, lambda hwnd, message: two_arguments.append((hwnd, message))
            ),
            1,
        )
        native.post_message(window, WM_MOVE, 0, 0)
        self.gui.Sleep(60)
        self.assertEqual(two_arguments, [(window, WM_MOVE)])
        self.assertEqual(self.gui.GUIRegisterMsg(WM_SIZE, ""), 1)
        seen.clear()
        native.post_message(window, WM_SIZE, 0, 0)
        self.gui.Sleep(60)
        self.assertEqual(seen, [])
        # Deleting the window releases its hooked procedure.
        self.assertEqual(self.gui.GUIDelete(window), 1)
        self.assertNotIn(window, self.gui._hooked_windows)  # noqa: SLF001

    def test_guiregistermsg_requires_a_callable(self) -> None:
        """AutoIt passes a function name; Python needs the callable, and says so."""

        self.gui.GUICreate("test", 200, 120)
        with self.assertRaises(TypeError) as context:
            self.gui.GUIRegisterMsg(WM_SIZE, "OnSize")
        self.assertIn("callable", str(context.exception))


class ListViewParityTest(GuiTestCase):
    """ListView behaviour measured from the AutoIt interpreter."""

    def test_guictrlsetdata_sets_the_column_headings(self) -> None:
        """AutoIt: GUICtrlSetData(ListView, "X|Y") replaces the headings and keeps the items."""

        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView("ColA|ColB", 10, 10, 300, 120)
        item = self.gui.GUICtrlCreateListViewItem("a|b", listview)
        widget = self.widget(listview)
        self.assertEqual(widget.heading("c0")["text"], "ColA")
        self.assertEqual(self.gui.GUICtrlSetData(listview, "X|Y"), 1)
        self.assertEqual(widget.heading("c0")["text"], "X")
        self.assertEqual(widget.heading("c1")["text"], "Y")
        self.assertEqual(len(widget.get_children("")), 1)
        self.assertEqual(len(self.gui._controls[listview].columns), 2)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlRead(item), "a|b|")

    def test_listview_item_check_state_is_read_in_advanced_mode(self) -> None:
        """AutoIt: GUICtrlRead(item, 1) is $GUI_CHECKED when checked, $GUI_UNCHECKED when not,
        while the default read stays the item's text."""

        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView(
            "A|B", 10, 10, 200, 100, -1, LVS_EX_FULLROWSELECT | LVS_EX_CHECKBOXES
        )
        item = self.gui.GUICtrlCreateListViewItem("a|b", listview)
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), GUI_UNCHECKED)
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_CHECKED), 1)
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), GUI_CHECKED)
        self.assertEqual(self.gui.GUICtrlRead(item), "a|b|")
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_UNCHECKED), 1)
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), GUI_UNCHECKED)
        # $LVS_EX_CHECKBOXES gives the control its check column, and the item's values are not
        # part of it.
        widget = self.widget(listview)
        self.assertEqual(widget.item(self.gui._controls[item].item, "values"), ("a", "b"))  # noqa: SLF001
        self.assertEqual(
            tuple(str(part) for part in widget.cget("show")), ("tree", "headings")
        )

    def test_check_state_works_without_the_checkbox_style(self) -> None:
        """The state is recorded whatever the style, as the reference's remark describes."""

        self.gui.GUICreate("test", 400, 300)
        listview = self.gui.GUICtrlCreateListView("A|B", 10, 10, 200, 100)
        item = self.gui.GUICtrlCreateListViewItem("a|b", listview)
        self.assertEqual(self.gui.GUICtrlSetState(item, GUI_CHECKED), 1)
        self.assertEqual(self.gui.GUICtrlRead(item, GUI_READ_EXTENDED), GUI_CHECKED)
        self.assertNotEqual(self.widget(listview).cget("show"), ("tree", "headings"))


# --- objects: ObjCreate, and the control GUICtrlCreateObj makes of one -----------------


class ObjectTest(unittest.TestCase):
    """``ObjCreate`` and the object variable it returns -- the half GUICtrlCreateObj needs.

    Every reading here is the interpreter's (probe_autoit_obj_out.txt): ``ObjName`` of
    ``ObjCreate("Shell.Explorer.2")`` is "WebBrowser" and of ``ObjCreate("Scripting.Dictionary")``
    is "Dictionary", a class name that does not exist comes back as 0, and an object is driven
    through its own members.
    """

    def test_objcreate_names_the_object_the_way_autoiit_does(self) -> None:
        """AutoIt: ObjName(ObjCreate("Shell.Explorer.2")) is "WebBrowser", not the ProgID."""

        browser = gui_module.ObjCreate("Shell.Explorer.2")
        self.assertTrue(gui_module.IsObj(browser))
        self.assertEqual(gui_module.ObjName(browser), "WebBrowser")
        dictionary = gui_module.ObjCreate("Scripting.Dictionary")
        self.assertEqual(gui_module.ObjName(dictionary), "Dictionary")

    def test_a_class_name_that_does_not_exist_returns_zero(self) -> None:
        """AutoIt: "Failure: sets the @error flag to non-zero" -- and the interpreter returned 0."""

        missing = gui_module.ObjCreate("No.Such.Class.Here")
        self.assertEqual(missing, 0)
        self.assertFalse(gui_module.IsObj(missing))
        self.assertEqual(gui_module.ObjName(missing), "")
        self.assertFalse(gui_module.IsObj("not an object"))

    def test_a_clsid_string_is_a_class_name_too(self) -> None:
        """AutoIt: the classname "can also be a string representation of the CLSID"."""

        by_clsid = gui_module.ObjCreate("{EE09B103-97E0-11CF-978F-00A02463E06F}")
        self.assertTrue(gui_module.IsObj(by_clsid))
        self.assertEqual(gui_module.ObjName(by_clsid), "Dictionary")

    def test_an_object_is_driven_through_its_own_methods_and_properties(self) -> None:
        """The reference's own remark for the control: it is used through the object variable.

        The arguments' order is the check that matters here: ``Dictionary.Add(Key, Item)`` is called
        with two strings, and only the order Windows' ``DISPPARAMS`` carries them in decides which
        of the two the dictionary keeps as its key.
        """

        dictionary = gui_module.ObjCreate("Scripting.Dictionary")
        assert isinstance(dictionary, gui_module.ComObject)
        # A property write, which the object only takes while it holds nothing: its own rule, not
        # the port's -- measured, the same call after Add() comes back as DISP_E_EXCEPTION.
        dictionary.CompareMode = 1
        self.assertEqual(dictionary.CompareMode, 1)
        self.assertEqual(dictionary.Add("answer", "42"), None)
        self.assertEqual(dictionary.Count, 1)
        self.assertEqual(dictionary.Item("answer"), "42")
        self.assertTrue(dictionary.Exists("answer"))

    def test_a_member_the_object_does_not_have_is_refused(self) -> None:
        """A name the object has no dispatch identifier for is an AttributeError, as in Python."""

        dictionary = gui_module.ObjCreate("Scripting.Dictionary")
        assert isinstance(dictionary, gui_module.ComObject)
        with self.assertRaises(AttributeError):
            dictionary.NoSuchMember


class ObjectControlTest(GuiTestCase):
    """``GUICtrlCreateObj``: the interpreter's readings, one by one.

    The port hosts the caller's own object, which is what the identity check asserts: the control
    the host window holds is the same ``IDispatch`` pointer ``ObjCreate`` returned, so a call on the
    caller's variable is a call on the embedded control.
    """

    def _browser(self) -> Any:
        """Return a fresh Shell.Explorer.2 object, which is embeddable."""

        browser = gui_module.ObjCreate("Shell.Explorer.2")
        self.assertTrue(gui_module.IsObj(browser))
        return browser

    def _frame(self, control_id: int) -> int:
        """Return the object control's frame handle, which is its host window."""

        return int(self.widget(control_id).winfo_id())

    def test_the_caller_s_own_object_is_the_one_hosted(self) -> None:
        """The control's host window holds the very object the caller created."""

        self.gui.GUICreate("test", 500, 400)
        browser = self._browser()
        assert isinstance(browser, gui_module.ComObject)
        control = self.gui.GUICtrlCreateObj(browser, 10, 10, 200, 150)
        self.assertNotEqual(control, 0)
        hosted = native.host_control(self._frame(control))
        self.assertIsNotNone(hosted)
        assert hosted is not None
        self.assertEqual(hosted.pointer, browser.dispatch.pointer)

    def test_the_control_reads_empty_and_has_no_handle(self) -> None:
        """AutoIt: GUICtrlGetHandle returns 0 for it, GUICtrlRead reads "", and its state is 80."""

        self.gui.GUICreate("test", 500, 400)
        control = self.gui.GUICtrlCreateObj(self._browser(), 10, 10, 200, 150)
        self.assertEqual(self.gui.GUICtrlGetHandle(control), 0)
        self.assertEqual(self.gui.GUICtrlRead(control), "")
        self.assertEqual(self.gui.GUICtrlGetState(control), 80)
        self.gui.GUICtrlSetState(control, GUI_HIDE)
        self.assertEqual(self.gui.GUICtrlGetState(control), 96)
        self.assertFalse(self.widget(control).winfo_ismapped())
        self.gui.GUICtrlSetState(control, GUI_SHOW)
        self.assertEqual(self.gui.GUICtrlGetState(control), 80)

    def test_guictrlsetdata_and_setstyle_return_one_and_change_nothing(self) -> None:
        """AutoIt: "GUICtrlSet has no effect on this control"; the interpreter returned 1 for both."""

        self.gui.GUICreate("test", 500, 400)
        control = self.gui.GUICtrlCreateObj(self._browser(), 10, 10, 200, 150)
        box = self.gui._controls[control].pos  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlSetData(control, "text"), 1)
        self.assertEqual(self.gui.GUICtrlSetStyle(control, 0x00800000), 1)
        self.assertEqual(self.gui._controls[control].pos, box)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlRead(control), "")

    def test_an_object_that_is_not_a_control_returns_zero(self) -> None:
        """AutoIt: a Scripting.Dictionary makes the function return 0 and leaves no control.

        Measured: ``ObjCreate`` itself succeeded (@error 0) and ``GUICtrlCreateObj`` returned 0 with
        @error 1, and the window held no control of it afterwards.
        """

        window = self.gui.GUICreate("test", 500, 400)
        dictionary = gui_module.ObjCreate("Scripting.Dictionary")
        before = len(self.gui._controls)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlCreateObj(dictionary, 10, 10, 100, 100), 0)
        self.assertEqual(len(self.gui._controls), before)  # noqa: SLF001
        self.assertEqual(self.gui.GUICtrlCreateObj("not an object", 10, 10, 10, 10), 0)
        self.assertEqual(self.gui.GUICtrlCreateObj(0, 10, 10, 10, 10), 0)
        self.assertEqual(self.gui.GUIGetMsg(), GUI_EVENT_NONE)
        self.gui.GUISetState(SW_HIDE, window)

    def test_the_size_defaults_are_the_interpreters(self) -> None:
        """AutoIt: an object control with no size is 8x8, and that stands as the used size.

        Measured (probe_autoit_obj3/obj4): an object with no width or height was 8x8 whatever the
        last control's size was; an explicit size was used; an object with no size after an explicit
        60x40 took 60x40; and the *next* control with no size inherited the object's size -- an
        Input after an 8x8 object came out 8x8, not 200x20.
        """

        self.gui.GUICreate("test", 500, 400)
        first = self.gui.GUICtrlCreateObj(self._browser(), 10, 10)
        self.assertEqual(self.gui._controls[first].pos, (10, 10, 8, 8))  # noqa: SLF001
        input_after = self.gui.GUICtrlCreateInput("", 10, 50)
        self.assertEqual(self.gui._controls[input_after].pos, (10, 50, 8, 8))  # noqa: SLF001
        sized = self.gui.GUICtrlCreateObj(self._browser(), 200, 10, 60, 40)
        self.assertEqual(self.gui._controls[sized].pos, (200, 10, 60, 40))  # noqa: SLF001
        after_sized = self.gui.GUICtrlCreateObj(self._browser(), 300, 10)
        self.assertEqual(self.gui._controls[after_sized].pos, (300, 10, 60, 40))  # noqa: SLF001

    def test_the_object_control_docks_as_the_interpreter_docks_it(self) -> None:
        """Measured: its size stays and its position scales, which is the kind's default resizing."""

        window = self.gui.GUICreate("test", 500, 300)
        control = self.gui.GUICtrlCreateObj(self._browser(), 60, 45, 100, 30)
        button = self.gui.GUICtrlCreateButton("c", 60, 45, 100, 30)
        self.gui._windows[window].width = 398  # noqa: SLF001
        self.gui._windows[window].height = 275  # noqa: SLF001
        for created in (control, button):
            self.gui._controls[created].dock_client = (398, 275)  # noqa: SLF001
        self._resize(window, 684, 461)
        self.assertEqual(self.gui._controls[control].pos,  # noqa: SLF001
                         self.gui._controls[button].pos)  # noqa: SLF001
        self.assertEqual(self.gui._controls[control].pos, (103, 75, 100, 30))  # noqa: SLF001

    def test_deleting_the_control_takes_the_hosted_object_with_it(self) -> None:
        """AutoIt: after GUICtrlDelete the GUI holds no window of the object any more."""

        self.gui.GUICreate("test", 500, 400)
        control = self.gui.GUICtrlCreateObj(self._browser(), 10, 10, 200, 150)
        frame = self._frame(control)
        self.gui.GUICtrlDelete(control)
        self.assertIsNone(native.host_control(frame))
        self.assertEqual(self.gui.GUICtrlGetState(control), -1)

    def _resize(self, window: int, width: int, height: int) -> None:
        """Deliver a resize to the port, as tkinter's Configure event does."""

        record = self.gui._windows[window]  # noqa: SLF001
        record.layout_seen = True
        self.gui._window_configured(window, _Configure(record.widget, width, height))


class NamedGapTest(GuiTestCase):
    """AutoIt's functions are all backed now, and where the reference states nothing, the port says so.

    ``GUICtrlCreateObj`` was the last function that raised for a missing mechanism; its failures are
    values, not exceptions, and the tests below pin both of them.
    """

    def test_the_object_control_is_no_longer_a_gap(self) -> None:
        """The interpreter's failures are values: 0 for a non-object and 0 for a non-embeddable one."""

        self.gui.GUICreate("test", 400, 300)
        self.assertEqual(self.gui.GUICtrlCreateObj(object(), 10, 10), 0)
        self.assertEqual(self.gui.GUICtrlCreateObj(None, 10, 10), 0)
        self.assertEqual(self.gui.GUICtrlCreateObj(gui_module.ObjCreate("Scripting.Dictionary"),
                                                   10, 10, 50, 50), 0)


# --- the module-level AutoIt functions -------------------------------------------------


class ModuleLevelTest(unittest.TestCase):
    """``py4gw.gui``'s module functions are AutoIt's own statement set."""

    def test_module_level_functions_are_autoits_own_names(self) -> None:
        """The module functions act on one GUI, as AutoIt's global functions do."""

        window = gui_module.GUICreate("module level", 200, 120)
        label = gui_module.GUICtrlCreateLabel("hello", 10, 10)
        try:
            self.assertEqual(gui_module.GUICtrlRead(label), "hello")
            self.assertEqual(gui_module.GUICtrlSetData(label, "world"), 1)
            self.assertEqual(gui_module.GUICtrlRead(label), "world")
            self.assertEqual(gui_module.GUIGetMsg(), GUI_EVENT_NONE)
            self.assertEqual(gui_module.GUIGetStyle(window)[1], 256)
        finally:
            gui_module.GUIDelete(window)

    def test_every_reference_function_is_present(self) -> None:
        """All 71 names of the AutoIt GUI reference exist under their AutoIt spellings."""

        expected = {
            "GUICreate",
            "GUISetState",
            "GUISetStyle",
            "GUIGetStyle",
            "GUISetCoord",
            "GUISetBkColor",
            "GUISetFont",
            "GUISetIcon",
            "GUISetCursor",
            "GUISetHelp",
            "GUISetAccelerators",
            "GUIRegisterMsg",
            "GUIGetCursorInfo",
            "GUIGetMsg",
            "GUIDelete",
            "GUISwitch",
            "GUIStartGroup",
            "GUISetOnEvent",
            "GUICtrlSetOnEvent",
            "GUICtrlCreateAvi",
            "GUICtrlCreateButton",
            "GUICtrlCreateCheckbox",
            "GUICtrlCreateCombo",
            "GUICtrlCreateContextMenu",
            "GUICtrlCreateDate",
            "GUICtrlCreateDummy",
            "GUICtrlCreateEdit",
            "GUICtrlCreateGraphic",
            "GUICtrlCreateGroup",
            "GUICtrlCreateIcon",
            "GUICtrlCreateInput",
            "GUICtrlCreateLabel",
            "GUICtrlCreateList",
            "GUICtrlCreateListView",
            "GUICtrlCreateListViewItem",
            "GUICtrlCreateMenu",
            "GUICtrlCreateMenuItem",
            "GUICtrlCreateMonthCal",
            "GUICtrlCreateObj",
            "GUICtrlCreatePic",
            "GUICtrlCreateProgress",
            "GUICtrlCreateRadio",
            "GUICtrlCreateSlider",
            "GUICtrlCreateTab",
            "GUICtrlCreateTabItem",
            "GUICtrlCreateTreeView",
            "GUICtrlCreateTreeViewItem",
            "GUICtrlCreateUpdown",
            "GUICtrlDelete",
            "GUICtrlGetHandle",
            "GUICtrlGetState",
            "GUICtrlRead",
            "GUICtrlRecvMsg",
            "GUICtrlRegisterListViewSort",
            "GUICtrlSendMsg",
            "GUICtrlSendToDummy",
            "GUICtrlSetBkColor",
            "GUICtrlSetColor",
            "GUICtrlSetCursor",
            "GUICtrlSetData",
            "GUICtrlSetDefBkColor",
            "GUICtrlSetDefColor",
            "GUICtrlSetFont",
            "GUICtrlSetGraphic",
            "GUICtrlSetImage",
            "GUICtrlSetLimit",
            "GUICtrlSetPos",
            "GUICtrlSetResizing",
            "GUICtrlSetState",
            "GUICtrlSetStyle",
            "GUICtrlSetTip",
        }
        missing = {name for name in expected if not callable(getattr(gui_module, name, None))}
        self.assertEqual(missing, set())
        self.assertEqual(len(expected), 71)

    def test_the_macros_are_readable_from_the_module(self) -> None:
        """@GUI_CtrlId and @error are module attributes, as AutoIt's macros are."""

        self.assertEqual(gui_module.GUI_CtrlId, 0)
        self.assertIsInstance(gui_module.GUI_WinHandle, int)
        self.assertIsInstance(gui_module.error, int)

    def test_tkinter_is_available(self) -> None:
        """The layer's premise: a Tk interpreter exists in this session."""

        self.assertGreaterEqual(tkinter.TkVersion, 8.6)


if __name__ == "__main__":
    unittest.main()
