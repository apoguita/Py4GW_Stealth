"""AutoIt-spelled GUI API for Py4GW Stealth, backed by tkinter.

The AutoIt v3 GUI reference is the specification: 67 functions across window creation,
control creation, and control update, plus the GUI options and the ``$GUI_*``, ``@SW_*``
and style constants they take. This package reproduces those names and signatures so an
AutoIt GUI script's statements read the same here::

    from py4gw.gui import *

    GUICreate("Hello World", 200, 100)
    GUICtrlCreateLabel("Hello world! How are you?", 30, 10)
    id_ok = GUICtrlCreateButton("OK", 70, 50, 60)
    GUISetState(SW_SHOW)

    while True:
        message = GUIGetMsg()
        if message == id_ok:
            GUICtrlSetData(id_label, "You pressed OK")
        elif message == GUI_EVENT_CLOSE:
            break

    GUIDelete()

Or in OnEvent mode, which is the same mode switch AutoIt uses::

    Opt("GUIOnEventMode", 1)
    GUICreate("Hello World", 200, 100)
    GUISetOnEvent(GUI_EVENT_CLOSE, on_close)
    id_ok = GUICtrlCreateButton("OK", 70, 50, 60)
    GUICtrlSetOnEvent(id_ok, on_ok)
    GUISetState(SW_SHOW)
    while True:
        Sleep(100)

AutoIt differences that a caller will notice are listed in ``docs/AUTOIT_GUI.md``; the
important ones are that an AutoIt event-function *name* (a string) is a Python callable
here, that ``None`` stands for AutoIt's ``Default`` keyword in optional positions, and that
functions tkinter cannot honestly back raise ``NotImplementedError`` naming what they need
instead of doing nothing.

Every name here is AutoIt's. The leading ``$`` of a constant and the ``@`` of a macro are
dropped because Python has no such prefix, which is the whole of the difference:
``$GUI_EVENT_CLOSE`` is :data:`GUI_EVENT_CLOSE` and ``@GUI_CtrlId`` is :data:`GUI_CtrlId`.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from py4gw.gui.constants import *  # noqa: F403 - the AutoIt constant surface, by design
from py4gw.gui.constants import (
    GUI_CURSOR_NOOVERRIDE,
    GUI_FONTNORMAL,
    GUI_READ_DEFAULT,
    SW_SHOW,
    TIP_INFOICON,
)
from py4gw.gui.gui import GUI
from py4gw.gui.objects import ComError, ComObject, IsObj, ObjCreate, ObjName

# The one GUI the module-level functions act on, which is what makes them AutoIt-like:
# AutoIt's GUI functions are global functions over one set of GUI state.
_default = GUI()

# AutoIt's macros (@GUI_CtrlId and friends) are read inside an OnEvent function. They live
# on the GUI instance; the module exposes the same names by delegating to it.
_MACROS = (
    "GUI_CtrlId",
    "GUI_CtrlHandle",
    "GUI_DragFile",
    "GUI_DragId",
    "GUI_DropId",
    "GUI_WinHandle",
    "error",
)


def __getattr__(name: str) -> Any:
    """Expose the GUI's AutoIt macros (@error, @GUI_CtrlId, ...) as module attributes."""

    if name in _MACROS:
        return getattr(_default, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def BitAND(value1: int, value2: int) -> int:
    """AutoIt's BitAND()."""

    return value1 & value2


def BitNOT(value: int) -> int:
    """AutoIt's BitNOT()."""

    return ~value


def BitOR(*values: int) -> int:
    """AutoIt's BitOR(), which AutoIt scripts use to combine styles."""

    result = 0
    for value in values:
        result |= value
    return result


def BitShift(value: int, shift: int) -> int:
    """AutoIt's BitShift(): a positive shift is left, a negative shift is right."""

    if shift >= 0:
        return value << shift
    return value >> -shift


def BitXOR(value1: int, value2: int) -> int:
    """AutoIt's BitXOR()."""

    return value1 ^ value2


def Opt(option: str, param: Any = None) -> Any:
    """Read or change a GUI option; returns the previous value.

    AutoIt calls this "AutoItSetOption", and its help documents ``Opt()`` as the same
    function. Only the reference's ``GUI*`` options are implemented.
    """

    return _default.Opt(option, param)


def AutoItSetOption(option: str, param: Any = None) -> Any:
    """AutoIt's other name for :func:`Opt`."""

    return _default.Opt(option, param)


def Sleep(milliseconds: int) -> None:
    """Wait, delivering GUI events while waiting.

    AutoIt's OnEvent page gives the idle loop as ``While 1 / Sleep(100) / WEnd``; a ported
    Sleep has to run tkinter's event loop while it waits, or no event would arrive.
    """

    _default.Sleep(milliseconds)


# --- GUI window functions ------------------------------------------------------------


def GUICreate(
    title: str,
    width: int = 400,
    height: int = 400,
    left: int = -1,
    top: int = -1,
    style: int = -1,
    exStyle: int = -1,
    parent: int = 0,
) -> int:
    """Create a GUI window and return its handle (initially hidden)."""

    return _default.GUICreate(title, width, height, left, top, style, exStyle, parent)


def GUISetState(flag: int = SW_SHOW, winhandle: int | None = None) -> int:
    """Show, hide, minimize, maximize, restore, enable or disable a window."""

    return _default.GUISetState(flag, winhandle)


def GUISetStyle(style: int, exStyle: int = -1, winhandle: int | None = None) -> int:
    """Change a window's styles (-1 leaves one unchanged)."""

    return _default.GUISetStyle(style, exStyle, winhandle)


def GUIGetStyle(winhandle: int | None = None) -> list[int]:
    """Return ``[style, exStyle]`` for a window."""

    return _default.GUIGetStyle(winhandle)


def GUISetCoord(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    winhandle: int | None = None,
) -> int:
    """Set the current position for the next control (GUICoordMode 2)."""

    return _default.GUISetCoord(left, top, width, height, winhandle)


def GUISetBkColor(background: int, winhandle: int | None = None) -> int:
    """Set a window's background colour."""

    return _default.GUISetBkColor(background, winhandle)


def GUISetFont(
    size: float,
    weight: int = 0,
    attribute: int = GUI_FONTNORMAL,
    fontname: str = "",
    winhandle: int | None = None,
    quality: int = 2,
) -> int:
    """Set a window's default font."""

    return _default.GUISetFont(size, weight, attribute, fontname, winhandle, quality)


def GUISetIcon(iconfile: str, iconID: int = -1, winhandle: int | None = None) -> int:
    """Set the icon used in a GUI window, out of an icon file or DLL."""

    return _default.GUISetIcon(iconfile, iconID, winhandle)


def GUISetCursor(
    cursorID: int = 0, override: int = GUI_CURSOR_NOOVERRIDE, winhandle: int | None = None
) -> None:
    """Set a window's mouse cursor."""

    return _default.GUISetCursor(cursorID, override, winhandle)


def GUISetHelp(helpfile: str, winhandle: int | None = None) -> int:
    """Set the file run when F1 is pressed."""

    return _default.GUISetHelp(helpfile, winhandle)


def GUISetAccelerators(
    accelerators: Sequence[Sequence[Any]] | None, winhandle: int | None = None
) -> int:
    """Set the accelerator table (a sequence of ``[key, controlID]`` pairs)."""

    return _default.GUISetAccelerators(accelerators, winhandle)


def GUIRegisterMsg(msgID: int, function: Any) -> int:
    """Register a function for a Windows message ID (a ``WM_*`` message)."""

    return _default.GUIRegisterMsg(msgID, function)


def GUIGetCursorInfo(winhandle: int | None = None) -> list[int]:
    """Return ``[x, y, primary down, secondary down, hovered control ID]``."""

    return _default.GUIGetCursorInfo(winhandle)


def GUIGetMsg(advanced: int = 0) -> Any:
    """Poll the GUI; returns a control ID, a ``GUI_EVENT_*`` value, or 0."""

    return _default.GUIGetMsg(advanced)


def GUIDelete(winhandle: int | None = None) -> int:
    """Delete a window and every control in it."""

    return _default.GUIDelete(winhandle)


def GUISwitch(winhandle: int, tabitemID: int | None = None) -> int:
    """Make a window current; returns the previous handle."""

    return _default.GUISwitch(winhandle, tabitemID)


def GUIStartGroup(winhandle: int | None = None) -> int:
    """Start a new control group (a radio-group boundary)."""

    return _default.GUIStartGroup(winhandle)


def GUISetOnEvent(specialID: int, function: Any, winhandle: int | None = None) -> int:
    """Register a window's system-event function (OnEvent mode)."""

    return _default.GUISetOnEvent(specialID, function, winhandle)


def GUICtrlSetOnEvent(controlID: int, function: Any) -> int:
    """Register a control's OnEvent function (OnEvent mode)."""

    return _default.GUICtrlSetOnEvent(controlID, function)


# --- control creation ----------------------------------------------------------------


def GUICtrlCreateAvi(
    filename: str,
    subfileid: int,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create an AVI control (raises: tkinter has no video widget)."""

    return _default.GUICtrlCreateAvi(
        filename, subfileid, left, top, width, height, style, exStyle
    )


def GUICtrlCreateButton(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Button control."""

    return _default.GUICtrlCreateButton(text, left, top, width, height, style, exStyle)


def GUICtrlCreateCheckbox(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Checkbox control."""

    return _default.GUICtrlCreateCheckbox(text, left, top, width, height, style, exStyle)


def GUICtrlCreateCombo(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a ComboBox control."""

    return _default.GUICtrlCreateCombo(text, left, top, width, height, style, exStyle)


def GUICtrlCreateContextMenu(controlID: int | None = None) -> int:
    """Create a context menu for a control or for the whole window."""

    return _default.GUICtrlCreateContextMenu(controlID)


def GUICtrlCreateDate(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a date control (raises: tkinter has no date picker)."""

    return _default.GUICtrlCreateDate(text, left, top, width, height, style, exStyle)


def GUICtrlCreateDummy() -> int:
    """Create a Dummy control, driven by :func:`GUICtrlSendToDummy`."""

    return _default.GUICtrlCreateDummy()


def GUICtrlCreateEdit(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create an Edit (multi-line) control."""

    return _default.GUICtrlCreateEdit(text, left, top, width, height, style, exStyle)


def GUICtrlCreateGraphic(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int | None = None,
) -> int:
    """Create a Graphic control, drawn into with :func:`GUICtrlSetGraphic`."""

    return _default.GUICtrlCreateGraphic(left, top, width, height, style)


def GUICtrlCreateGroup(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Group control."""

    return _default.GUICtrlCreateGroup(text, left, top, width, height, style, exStyle)


def GUICtrlCreateIcon(
    filename: str,
    iconName: int,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create an Icon control (raises: tkinter cannot read icon resources)."""

    return _default.GUICtrlCreateIcon(
        filename, iconName, left, top, width, height, style, exStyle
    )


def GUICtrlCreateInput(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create an Input (single-line) control."""

    return _default.GUICtrlCreateInput(text, left, top, width, height, style, exStyle)


def GUICtrlCreateLabel(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Label control."""

    return _default.GUICtrlCreateLabel(text, left, top, width, height, style, exStyle)


def GUICtrlCreateList(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a List control."""

    return _default.GUICtrlCreateList(text, left, top, width, height, style, exStyle)


def GUICtrlCreateListView(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a ListView control (columns separated by the data separator character)."""

    return _default.GUICtrlCreateListView(text, left, top, width, height, style, exStyle)


def GUICtrlCreateListViewItem(text: str, listviewID: int) -> int:
    """Create a ListView item."""

    return _default.GUICtrlCreateListViewItem(text, listviewID)


def GUICtrlCreateMenu(submenutext: str, menuID: int = -1, menuentry: int = -1) -> int:
    """Create a menu bar entry or a submenu."""

    return _default.GUICtrlCreateMenu(submenutext, menuID, menuentry)


def GUICtrlCreateMenuItem(
    text: str, menuID: int, menuentry: int = -1, menuradioitem: int = 0
) -> int:
    """Create a menu item (an empty text creates a separator)."""

    return _default.GUICtrlCreateMenuItem(text, menuID, menuentry, menuradioitem)


def GUICtrlCreateMonthCal(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a month calendar control (raises: tkinter has no such widget)."""

    return _default.GUICtrlCreateMonthCal(text, left, top, width, height, style, exStyle)


def GUICtrlCreateObj(
    ObjectVar: Any,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
) -> int:
    """Create an ActiveX control (raises: tkinter can host no OLE object)."""

    return _default.GUICtrlCreateObj(ObjectVar, left, top, width, height)


def GUICtrlCreatePic(
    filename: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Picture control."""

    return _default.GUICtrlCreatePic(filename, left, top, width, height, style, exStyle)


def GUICtrlCreateProgress(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Progress control."""

    return _default.GUICtrlCreateProgress(left, top, width, height, style, exStyle)


def GUICtrlCreateRadio(
    text: str,
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Radio control."""

    return _default.GUICtrlCreateRadio(text, left, top, width, height, style, exStyle)


def GUICtrlCreateSlider(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Slider control."""

    return _default.GUICtrlCreateSlider(left, top, width, height, style, exStyle)


def GUICtrlCreateTab(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a Tab control."""

    return _default.GUICtrlCreateTab(left, top, width, height, style, exStyle)


def GUICtrlCreateTabItem(text: str) -> int:
    """Create a TabItem; an empty text closes the tab structure."""

    return _default.GUICtrlCreateTabItem(text)


def GUICtrlCreateTreeView(
    left: int,
    top: int,
    width: int | None = None,
    height: int | None = None,
    style: int = -1,
    exStyle: int = -1,
) -> int:
    """Create a TreeView control."""

    return _default.GUICtrlCreateTreeView(left, top, width, height, style, exStyle)


def GUICtrlCreateTreeViewItem(text: str, treeviewID: int) -> int:
    """Create a TreeView item, under the tree or under another item."""

    return _default.GUICtrlCreateTreeViewItem(text, treeviewID)


def GUICtrlCreateUpdown(inputcontrolID: int, style: int = -1) -> int:
    """Create an UpDown control on an Input control."""

    return _default.GUICtrlCreateUpdown(inputcontrolID, style)


# --- control update and read functions -----------------------------------------------


def GUICtrlDelete(controlID: int) -> int:
    """Delete a control."""

    return _default.GUICtrlDelete(controlID)


def GUICtrlGetHandle(controlID: int) -> int:
    """Return a control's window handle, or 0 where AutoIt returns none."""

    return _default.GUICtrlGetHandle(controlID)


def GUICtrlGetState(controlID: int) -> int:
    """Return a control's state bits."""

    return _default.GUICtrlGetState(controlID)


def GUICtrlRead(controlID: int, advanced: int = GUI_READ_DEFAULT) -> Any:
    """Read a control's state or data."""

    return _default.GUICtrlRead(controlID, advanced)


def GUICtrlRecvMsg(
    controlID: int, msg: int, wParam: int = 0, lParamType: int = 0
) -> Any:
    """Send a Windows message to a control and read the result back."""

    return _default.GUICtrlRecvMsg(controlID, msg, wParam, lParamType)


def GUICtrlRegisterListViewSort(controlID: int, function: Callable[..., int]) -> int:
    """Register the function that sorts a ListView on a column-heading click."""

    return _default.GUICtrlRegisterListViewSort(controlID, function)


def GUICtrlSendMsg(controlID: int, msg: int, wParam: Any, lParam: Any) -> int:
    """Send a Windows message to a control, returning SendMessage's result."""

    return _default.GUICtrlSendMsg(controlID, msg, wParam, lParam)


def GUICtrlSendToDummy(controlID: int, state: Any = 0) -> int:
    """Send a value to a Dummy control, notifying as if it had been clicked."""

    return _default.GUICtrlSendToDummy(controlID, state)


def GUICtrlSetBkColor(controlID: int, backgroundcolor: int) -> int:
    """Set a control's background colour."""

    return _default.GUICtrlSetBkColor(controlID, backgroundcolor)


def GUICtrlSetColor(controlID: int, textcolor: int) -> int:
    """Set a control's text colour."""

    return _default.GUICtrlSetColor(controlID, textcolor)


def GUICtrlSetCursor(controlID: int, cursorID: int) -> int:
    """Set the cursor shown over a control."""

    return _default.GUICtrlSetCursor(controlID, cursorID)


def GUICtrlSetData(controlID: int, data: Any = "", default: Any = "") -> int:
    """Modify a control's data."""

    return _default.GUICtrlSetData(controlID, data, default)


def GUICtrlSetDefBkColor(defbkcolor: int, winhandle: int | None = None) -> int:
    """Set the default background colour of a window's controls."""

    return _default.GUICtrlSetDefBkColor(defbkcolor, winhandle)


def GUICtrlSetDefColor(deftextcolor: int, winhandle: int | None = None) -> int:
    """Set the default text colour of a window's controls."""

    return _default.GUICtrlSetDefColor(deftextcolor, winhandle)


def GUICtrlSetFont(
    controlID: int,
    size: float,
    weight: int = 0,
    attribute: int = GUI_FONTNORMAL,
    fontname: str = "",
    quality: int = 2,
) -> int:
    """Set a control's font."""

    return _default.GUICtrlSetFont(controlID, size, weight, attribute, fontname, quality)


def GUICtrlSetGraphic(controlID: int, type: int, *par: Any) -> int:
    """Draw into a Graphic control with the ``$GUI_GR_*`` command set."""

    return _default.GUICtrlSetGraphic(controlID, type, *par)


def GUICtrlSetImage(
    controlID: int, filename: str, iconname: int = -1, icontype: int = 1
) -> int:
    """Set the picture a control displays."""

    return _default.GUICtrlSetImage(controlID, filename, iconname, icontype)


def GUICtrlSetLimit(controlID: int, max: int, min: int = 0) -> int:
    """Limit characters, scroll extent, or a range."""

    return _default.GUICtrlSetLimit(controlID, max, min)


def GUICtrlSetPos(
    controlID: int,
    left: int,
    top: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> int:
    """Change a control's position (``None`` is AutoIt's ``Default`` keyword)."""

    return _default.GUICtrlSetPos(controlID, left, top, width, height)


def GUICtrlSetResizing(controlID: int, resizing: int) -> int:
    """Record a control's resizing (docking) value."""

    return _default.GUICtrlSetResizing(controlID, resizing)


def GUICtrlSetState(controlID: int, state: int) -> int:
    """Change a control's state (state values can be summed)."""

    return _default.GUICtrlSetState(controlID, state)


def GUICtrlSetStyle(controlID: int, style: int, exStyle: int = -1) -> int:
    """Change a control's style."""

    return _default.GUICtrlSetStyle(controlID, style, exStyle)


def GUICtrlSetTip(
    controlID: int,
    tiptext: str,
    title: str = "",
    icon: int = TIP_INFOICON,
    options: int = 0,
) -> int:
    """Set a control's tooltip text."""

    return _default.GUICtrlSetTip(controlID, tiptext, title, icon, options)
