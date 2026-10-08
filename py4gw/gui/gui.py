"""The AutoIt-compatible GUI class, backed by tkinter.

This is a Stealth-owned component, not a port: neither Reforged nor Reforged Native has
a host-window toolkit (Reforged's UI is in-client ImGui), so the specification is the
AutoIt v3 GUI reference itself, read from the AutoIt installation on this machine:

* ``AutoIt.chm`` (decompiled): ``guiref/GUIRef.htm``, ``guiref/GUIRef_MessageLoopMode.htm``,
  ``guiref/GUIRef_OnEventMode.htm``, the 67 ``functions/GUI*.htm`` pages, and
  ``appendix/GUIStyles.htm``.
* The constants in :mod:`py4gw.gui.constants`, copied from ``Include\\*.au3``.
* The AutoIt interpreter itself, which answered the questions the help file leaves open
  (default window and control sizes, ``GUICtrlRead`` and ``GUICtrlGetState`` values, the
  nature of control IDs, and OnEvent delivery). Those readings are recorded in
  ``docs/AUTOIT_GUI.md``, and the probe scripts are in ``.scratch/probe_autoit_*.au3``.

What the class reproduces
-------------------------

* Control IDs are positive, unique for the life of the script and **not** window handles.
  AutoIt assigns its own counter (the probe's first control was 3) and returns the real
  handle only from ``GUICtrlGetHandle``; this port does the same.
* A window is created hidden; ``GUISetState(SW_SHOW)`` shows it.
* Two event modes, exactly as AutoIt has them: the default message loop, where the script
  polls ``GUIGetMsg()``, and OnEvent mode, where ``Opt("GUIOnEventMode", 1)`` makes the GUI
  call registered functions. In OnEvent mode ``GUIGetMsg()`` returns 0 and sets ``error``.
* Control events carry the control's ID; system events are the documented negative
  ``GUI_EVENT_*`` values; ``GUIGetMsg(1)`` returns the advanced array.

What it cannot reproduce is named, never faked: see ``docs/AUTOIT_GUI.md`` for the list of
AutoIt styles, states and functions that tkinter has no equivalent for, and the functions
that raise ``NotImplementedError`` naming what they need.
"""

from __future__ import annotations

import ctypes
import inspect
import os
import time
import tkinter
from collections import deque
from dataclasses import dataclass, field
from functools import cmp_to_key
from tkinter import ttk
from typing import Any, Callable, Sequence

from py4gw.gui import native, objects, styles
from py4gw.gui.constants import (
    ACN_START,
    ACN_STOP,
    ACS_NONTRANSPARENT,
    ACS_TRANSPARENT,
    DTN_DATETIMECHANGE,
    DTS_LONGDATEFORMAT,
    DTS_SHORTDATECENTURYFORMAT,
    DTS_TIMEFORMAT,
    ES_LOWERCASE,
    ES_NUMBER,
    ES_UPPERCASE,
    GUI_BKCOLOR_DEFAULT,
    GUI_BKCOLOR_TRANSPARENT,
    GUI_AVICLOSE,
    GUI_AVISTART,
    GUI_AVISTOP,
    GUI_CHECKED,
    GUI_CURSOR_NOOVERRIDE,
    GUI_CURSOR_OVERRIDE,
    GUI_DEFBUTTON,
    GUI_DISABLE,
    GUI_DOCKAUTO,
    GUI_DOCKBORDERS,
    GUI_DOCKBOTTOM,
    GUI_DOCKHCENTER,
    GUI_DOCKHEIGHT,
    GUI_DOCKLEFT,
    GUI_DOCKRIGHT,
    GUI_DOCKSIZE,
    GUI_DOCKTOP,
    GUI_DOCKVCENTER,
    GUI_DOCKWIDTH,
    GUI_DROPACCEPTED,
    GUI_ENABLE,
    GUI_EVENT_ARRAY,
    GUI_EVENT_CLOSE,
    GUI_EVENT_DROPPED,
    GUI_EVENT_MAXIMIZE,
    GUI_EVENT_MINIMIZE,
    GUI_EVENT_MOUSEMOVE,
    GUI_EVENT_NONE,
    GUI_EVENT_PRIMARYDOWN,
    GUI_EVENT_PRIMARYUP,
    GUI_EVENT_RESIZED,
    GUI_EVENT_RESTORE,
    GUI_EVENT_SECONDARYDOWN,
    GUI_EVENT_SECONDARYUP,
    GUI_EXPAND,
    GUI_FOCUS,
    GUI_FONTNORMAL,
    GUI_GR_BEZIER,
    GUI_GR_CLOSE,
    GUI_GR_COLOR,
    GUI_GR_DOT,
    GUI_GR_ELLIPSE,
    GUI_GR_HINT,
    GUI_GR_LINE,
    GUI_GR_MOVE,
    GUI_GR_NOBKCOLOR,
    GUI_GR_PENSIZE,
    GUI_GR_PIE,
    GUI_GR_PIXEL,
    GUI_GR_RECT,
    GUI_GR_REFRESH,
    GUI_HIDE,
    GUI_INDETERMINATE,
    GUI_NODROPACCEPTED,
    GUI_NOFOCUS,
    GUI_ONTOP,
    GUI_READ_DEFAULT,
    GUI_READ_EXTENDED,
    GUI_SHOW,
    GUI_UNCHECKED,
    GUI_WS_EX_PARENTDRAG,
    LBS_SORT,
    LVS_EX_CHECKBOXES,
    MCN_SELCHANGE,
    MCN_SELECT,
    MCN_VIEWCHANGE,
    PBS_MARQUEE,
    SC_MAXIMIZE,
    SC_MINIMIZE,
    SC_RESTORE,
    SW_DISABLE,
    SW_ENABLE,
    SW_HIDE,
    SW_LOCK,
    SW_MAXIMIZE,
    SW_MINIMIZE,
    SW_RESTORE,
    SW_SHOW,
    SW_SHOWDEFAULT,
    SW_SHOWMAXIMIZED,
    SW_SHOWMINIMIZED,
    SW_SHOWMINNOACTIVE,
    SW_SHOWNA,
    SW_SHOWNOACTIVATE,
    SW_SHOWNORMAL,
    SW_UNLOCK,
    SS_ICON,
    TIP_BALLOON,
    TIP_CENTER,
    TIP_INFOICON,
    UDS_ALIGNLEFT,
    UDS_ALIGNRIGHT,
    UDS_SETBUDDYINT,
    UDS_WRAP,
    WS_CAPTION,
    WS_CHILD,
    WS_TABSTOP,
    WS_VISIBLE,
    WM_NOTIFY,
    WS_DISABLED,
    WS_EX_ACCEPTFILES,
    WS_EX_CLIENTEDGE,
    WS_EX_MDICHILD,
    WS_EX_TOPMOST,
    WS_MAXIMIZEBOX,
    WS_MINIMIZEBOX,
    WS_POPUP,
    WM_SYSCOMMAND,
    WS_SIZEBOX,
    WS_SYSMENU,
    WS_CLIPSIBLINGS,
    WS_EX_WINDOWEDGE,
)

# --- Named gaps ---------------------------------------------------------------------------
# Every AutoIt function or value the port cannot honestly back raises NotImplementedError
# carrying one of these sentences, so the missing mechanism is named at the call site.
# GUICtrlCreateObj was the last one and is implemented now: it needed an object variable, which is
# py4gw/gui/objects.py, and a host for it, which is native.attach_object_host.

# GUICreate()'s default style, as the reference states it and as the interpreter reported
# it: "$WS_MINIMIZEBOX, $WS_CAPTION, $WS_POPUP, $WS_SYSMENU" with "$WS_CLIPSIBLINGS always
# included", which the probe read back from GUIGetStyle() as 0x84CA0000 with the forced
# $WS_EX_WINDOWEDGE (0x100).
_DEFAULT_WINDOW_STYLE = (
    WS_MINIMIZEBOX | WS_CAPTION | WS_POPUP | WS_SYSMENU | WS_CLIPSIBLINGS
)
_DEFAULT_WINDOW_EXSTYLE = WS_EX_WINDOWEDGE

# AutoIt's own control-ID counter starts at 3: the probe's first control in a fresh script
# was 3 (AutoIt reserves 1 and 2). The value is not documented, only observed.
_FIRST_CONTROL_ID = 3

# GUICreate() with no width or height produced a 400x400 client area (probe).
_DEFAULT_WINDOW_SIZE = 400

# What a control gets when it is created with no width or height and no control has been made yet in
# that window: each kind has its own default. Measured per kind, each control created first in a
# window of its own (probe_autoit_defaults_out.txt): an Input 200x20, an Edit 200x150, a Combo
# 200x21, a List 200x149 (a list box snaps its height to whole items, and 150 is what was asked
# for), a Progress and a Slider 0x0 — no size at all — a Tab, a TreeView, a ListView, a Pic and a
# Graphic 150x150, a Date 200x20, a MonthCal 229x164 and a Group 200x150. The kinds that autofit
# their text are not here: Button, Label, Checkbox and Radio take their size from their text.
_DEFAULT_CONTROL_SIZE: dict[str, tuple[int, int]] = {
    "Combo": (200, 21),
    "Date": (200, 20),
    "Edit": (200, 150),
    "Graphic": (150, 150),
    "Group": (200, 150),
    # An Icon control: "32x32" is the reference's own default (GUICtrlCreateIcon.htm), not a reading.
    "Icon": (32, 32),
    "Input": (200, 20),
    "List": (200, 150),
    "ListView": (150, 150),
    "MonthCal": (229, 164),
    "Obj": (8, 8),
    "Pic": (150, 150),
    "Progress": (0, 0),
    "Slider": (0, 0),
    "Tab": (150, 150),
    "TreeView": (150, 150),
}

#: What a kind with no measured default gets, which is what the probe read for the kinds whose own
#: default is the plain "previously used" value.
_DEFAULT_CONTROL_FALLBACK = (200, 20)


def _default_control_size(kind: str) -> tuple[int, int]:
    """Return the size a kind of control gets when its size is omitted and none was used yet."""

    return _DEFAULT_CONTROL_SIZE.get(kind, _DEFAULT_CONTROL_FALLBACK)

# GUICtrlCreateGraphic() with no width or height produced 150x150 (probe).
_DEFAULT_GRAPHIC_SIZE = 150

# GUIGetMsg() "automatically idles the CPU when required" (GUIGetMsg.htm). tkinter has no
# MsgWaitForMultipleObjects equivalent, so the port idles for this long when the queue is
# empty. See docs/AUTOIT_GUI.md.
_IDLE_SECONDS = 0.01

# AutoIt's control types, spelled as the reference spells them.
_KINDS = (
    "Avi",
    "Button",
    "Checkbox",
    "Combo",
    "ContextMenu",
    "Date",
    "Dummy",
    "Edit",
    "Graphic",
    "Group",
    "Icon",
    "Input",
    "Label",
    "List",
    "ListView",
    "ListViewItem",
    "Menu",
    "MenuItem",
    "MonthCal",
    "Obj",
    "Pic",
    "Progress",
    "Radio",
    "Slider",
    "Tab",
    "TabItem",
    "TreeView",
    "TreeViewItem",
    "Updown",
)

# GUICtrlSetResizing()/GUIResizeMode: the docking values, and where the interpreter's own limits
# are. The reference's table gives the bits ($GUI_DOCKAUTO, LEFT, RIGHT, HCENTER, TOP, BOTTOM,
# VCENTER, WIDTH, HEIGHT and the composites); what it does not state, the probes measured:
# a value of 0 or of 1024 and above means "keep the control's default resizing", which is the same
# boundary Opt("GUIResizeMode") documents as "<1024" (GUIResizeMode's page: "0 = (default) keep
# default control resizing, <1024 = any type of resizing"). probe_autoit_resizing5 shows it:
# 802 and 803 and 819 behaved as $GUI_DOCKALL, while 1024, 1040 (= 16 + 1024) and 1826 behaved as 0.
_DOCK_LIMIT = 1024

#: Each control type's default resizing, as its own reference page states it. The pages that state
#: none were measured: ListView and TreeView came back with $GUI_DOCKAUTO's box, and the controls
#: with no window of their own (Dummy, Menu, MenuItem, TabItem, List, ...-Item) have nothing to
#: dock — only the ones a resize can move are listed.
_DEFAULT_DOCKING: dict[str, int] = {
    "Avi": GUI_DOCKSIZE,
    "Button": GUI_DOCKSIZE,
    "Checkbox": GUI_DOCKHEIGHT,
    "Combo": GUI_DOCKHEIGHT,
    "Date": GUI_DOCKHEIGHT,
    "Edit": GUI_DOCKAUTO,
    "Group": GUI_DOCKAUTO,
    "Icon": GUI_DOCKSIZE,
    "Input": GUI_DOCKHEIGHT,
    "Label": GUI_DOCKAUTO,
    "List": GUI_DOCKAUTO,
    "ListView": GUI_DOCKAUTO,
    "MonthCal": GUI_DOCKSIZE,
    "Obj": GUI_DOCKSIZE,
    "Pic": GUI_DOCKSIZE,
    "Progress": GUI_DOCKAUTO,
    "Radio": GUI_DOCKHEIGHT,
    "Slider": GUI_DOCKAUTO,
    "Tab": GUI_DOCKSIZE,
    "TreeView": GUI_DOCKAUTO,
}

# GUIGetCursorInfo() and GUICtrlSetCursor()/GUISetCursor() take "cursor ID as used by
# Windows SetCursor API". tkinter has no way to use a Win32 handle, so the standard IDs are
# mapped to Tk cursor names; an ID outside the table gets Tk's arrow, which is what AutoIt
# documents for an invalid cursor ID ("If the cursorID is invalid the standard arrow will
# be displayed").
_CURSOR_BY_ID: dict[int, str] = {
    0: "arrow",
    32512: "arrow",
    32513: "xterm",
    32514: "watch",
    32515: "crosshair",
    32516: "center_ptr",
    32642: "size_nw_se",
    32643: "size_ne_sw",
    32644: "sb_h_double_arrow",
    32645: "sb_v_double_arrow",
    32646: "fleur",
    32648: "X_cursor",
    32649: "hand2",
    32650: "watch",
    32651: "question_arrow",
}
_CURSOR_HIDDEN_ID = 16

# The accelerator keys AutoIt's GUISetAccelerators() accepts in HotKeySet() format:
# "^" ctrl, "!" alt, "+" shift, then a key name. tkinter handles all of them except the
# Windows key ("#") and AutoIt's {LWIN}/{RWIN}, which are listed as a gap in the docs.
_ACCELERATOR_KEYS: dict[str, str] = {
    "ENTER": "Return",
    "ESC": "Escape",
    "TAB": "Tab",
    "SPACE": "space",
    "BACKSPACE": "BackSpace",
    "DELETE": "Delete",
    "INSERT": "Insert",
    "HOME": "Home",
    "END": "End",
    "PGUP": "Prior",
    "PGDN": "Next",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
}


# $ES_NUMBER and the case-fold styles have no Entry option: they are applied through a
# validation callback instead (docs/AUTOIT_GUI.md).
ES_NUMBER_OR_CASE = ES_NUMBER | ES_LOWERCASE | ES_UPPERCASE

# GUICtrlRecvMsg's string buffer: AutoIt does not document the size it offers a control for an
# lParam string, so the port states its own (documented in docs/AUTOIT_GUI.md).
_RECV_TEXT_SIZE = 1024


#: What the interpreter produced for an UpDown attached to a 120x22 Input: the arrows are 18
#: pixels wide, as tall as the input, and start two pixels inside the input's right edge
#: (tests/autoit_reference/probe_parity3_out.txt).
_UPDOWN_ARROW_WIDTH = 18
_UPDOWN_OVERLAP = 2
_UPDOWN_DEFAULT_HEIGHT = 22


@dataclass
class _control:
    """One AutoIt control: its ID, its type, its widget and its recorded properties."""

    control_id: int
    kind: str
    window: int
    widget: Any = None
    style: int = -1
    ex_style: int = -1
    resizing: int = 0
    #: The docking value the control was created with: GUIResizeMode while it was set, or the
    #: control type's own default. A GUICtrlSetResizing value of 0 or 1024 and above selects this.
    dock_default: int = 0
    #: The box and the window client size the control's docking is computed from: its geometry
    #: when it was created or last moved with GUICtrlSetPos.
    dock_base: tuple[int, int, int, int] | None = None
    dock_client: tuple[int, int] | None = None
    text: str = ""
    value: Any = None
    parent: int | None = None
    item: str = ""
    subitems: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    #: This control's own tooltip window, created by GUICtrlSetTip and replaced by the next call
    #: for the same control, as AutoIt's is (one tooltip control per control, one tool each).
    tooltip: int = 0
    entries: list[int] = field(default_factory=list)
    clicked_column: int = 0
    states: int = 0
    image: Any = None
    #: The last geometry this control was placed with. Tk forgets a widget's geometry when
    #: place_forget() hides it, and AutoIt does not: a hidden control keeps its position and
    #: size, and GUICtrlSetState($GUI_SHOW) brings it back exactly where it was.
    pos: tuple[int, int, int, int] | None = None
    sort_function: Callable[..., Any] | None = None
    on_event: Callable[..., Any] | None = None
    #: Whether the control was created with $LVS_EX_CHECKBOXES (the styles that need a column
    #: of their own, which list views and tree views do).
    checkboxes: bool = False
    #: The window handle of a control that is a native Win32 control rather than a tkinter
    #: widget (Date, MonthCal, Avi and Icon), 0 for everything else.
    native: int = 0
    #: For an UpDown, the position its buddy Input was last read at: the control writes its
    #: position into the buddy's *window*, so that window is newer only after the control moved.
    synced_position: int = 0
    #: The GDI font a native control was given with GUICtrlSetFont, 0 for none. Windows draws with
    #: the handle, so it is kept until the control is deleted.
    font: int = 0


@dataclass
class _window:
    """One AutoIt GUI window and everything the reference keeps per window."""

    handle: int
    widget: Any
    style: int
    ex_style: int
    parent: int
    width: int
    height: int
    left: int
    top: int
    #: The tkinter widget's own window handle, read once. A hooked procedure must not call tkinter:
    #: ``winfo_id`` runs Tcl, which releases the interpreter's thread state, and a message that
    #: arrives while that is happening re-enters the ctypes procedure with no thread state to
    #: restore — a fatal error (measured: a real click on a plain tkinter Button in a window whose
    #: hook made one Tcl call killed the process, while the same click with a hook that only reads
    #: cached values survived).
    widget_id: int = 0
    visible: bool = False
    locked: bool = False
    disabled: bool = False
    state: str = "normal"
    layout_seen: bool = False
    default_font: tuple[str, int, str] | None = None
    default_text_color: int | None = None
    default_bk_color: int | None = None
    on_events: dict[int, Callable[..., Any]] = field(default_factory=dict)
    accelerators: list[tuple[str, int]] = field(default_factory=list)
    help_file: str = ""
    icon: int = 0
    registered_messages: dict[int, Any] = field(default_factory=dict)
    menu: Any = None
    menu_entries: list[int] = field(default_factory=list)
    context_menus: dict[int, Any] = field(default_factory=dict)
    last_left: int = 0
    last_top: int = 0
    #: The size the last control of this window used, which a control created with no size takes.
    #: ``None`` until a control exists, so that a size of 0 is remembered as 0 rather than read as
    #: "nothing used yet" (the interpreter inherits a 0x0 control's size the same way).
    last_width: int | None = None
    last_height: int | None = None
    cell_left: int = 0
    cell_top: int = 0
    radio_variable: Any = None
    tab_frame: Any = None
    tab_item: int | None = None
    graphic_state: dict[int, Any] = field(default_factory=dict)


class GUI:
    """Create AutoIt GUI windows and controls on tkinter.

    The class is the whole state of the AutoIt GUI system: the windows it created, the
    controls in them, the current window, the control-ID counter, the pending messages and
    the GUI options. ``py4gw.gui`` builds one instance and exposes its methods as
    module-level functions under AutoIt's own names, so an AutoIt script's statement
    ``GUICreate("Title", 200, 100)`` is ``py4gw.gui.GUICreate("Title", 200, 100)``.
    """

    def __init__(self) -> None:
        """Create the GUI state without creating any window."""

        self._root: tkinter.Tk | None = None
        self._windows: dict[int, _window] = {}
        self._controls: dict[int, _control] = {}
        self._controls_by_widget: dict[str, int] = {}
        self._current_window: int | None = None
        self._last_control: int | None = None
        self._next_control_id = _FIRST_CONTROL_ID
        self._messages: deque[tuple[int, int, int, int, int]] = deque()
        self._images: list[Any] = []
        #: What the hooked window procedure queued for the next pump: a control notification, a
        #: dropped file, or a message a registered function is waiting for.
        self._pending: list[tuple[Any, ...]] = []
        #: The GDI fonts GUICtrlSetFont created for native controls, kept because Windows draws with
        #: the handle rather than with a copy of it.
        self._fonts: list[int] = []
        #: The windows whose message procedure the port has hooked, so that a native control's
        #: WM_NOTIFY notification can become a control event.
        self._hooked_windows: set[int] = set()
        self._primary_down = 0
        self._secondary_down = 0
        self._options: dict[str, Any] = {
            "GUICloseOnESC": 1,
            "GUICoordMode": 1,
            "GUIDataSeparatorChar": "|",
            "GUIEventOptions": 0,
            "GUIOnEventMode": 0,
            "GUIResizeMode": 0,
        }
        # AutoIt's @error and its GUI macros, which the reference documents as read inside
        # an OnEvent function (@GUI_CtrlId, @GUI_WinHandle, @GUI_CtrlHandle) or after a call
        # (@error, @GUI_DragId, @GUI_DragFile, @GUI_DropId).
        self.error = 0
        self.GUI_CtrlId = 0
        self.GUI_WinHandle = 0
        self.GUI_CtrlHandle = 0
        self.GUI_DragId = 0
        self.GUI_DragFile = ""
        self.GUI_DropId = 0

    # ---------------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------------

    def _ensure_root(self) -> tkinter.Tk:
        """Create the hidden Tk root that owns every GUI window, once."""

        if self._root is None:
            root = tkinter.Tk()
            root.withdraw()
            self._root = root
        return self._root

    def _window_of(self, window: tkinter.Misc) -> int:
        """Return the AutoIt window handle for a Tk toplevel.

        AutoIt's GUICreate() returns a real window handle ("the handle returned from this
        function is a real windows handle" — GUICreate.htm), so this asks Tk for the
        window manager's frame window, which is the window the user sees, and falls back to
        the widget's own window handle.
        """

        try:
            frame = int(str(window.tk.call("wm", "frame", str(window))), 16)
        except (tkinter.TclError, ValueError, TypeError):
            frame = 0
        if frame > 0:
            return frame
        return int(window.winfo_id())

    def _resolve_window(self, winhandle: int | None) -> _window:
        """Return the window a function works on, or raise like AutoIt returns 0."""

        if winhandle is None or winhandle == -1:
            handle = self._current_window
        else:
            handle = winhandle
        if handle is None or handle not in self._windows:
            raise _WindowNotFound(
                f"no GUI window for handle {winhandle!r}; GUICreate() a window first"
            )
        return self._windows[handle]

    def _resolve_control(self, control_id: int) -> _control:
        """Return a control, resolving AutoIt's -1 to the last created control."""

        if control_id == -1:
            if self._last_control is None:
                raise _ControlNotFound("no control has been created yet (-1 is the last one)")
            control_id = self._last_control
        control = self._controls.get(control_id)
        if control is None:
            raise _ControlNotFound(f"no control with controlID {control_id}")
        return control

    def _new_control_id(self) -> int:
        """Allocate the next AutoIt control ID (positive, unique)."""

        control_id = self._next_control_id
        self._next_control_id += 1
        return control_id

    def _register_control(
        self,
        kind: str,
        window: _window,
        widget: Any | None,
        style: int,
        ex_style: int,
    ) -> _control:
        """Record a new control and return it."""

        control_id = self._new_control_id()
        # GUIResizeMode is read when the control is created, not when the window is resized: the
        # probe set the option after creating a Button and the resize still used the Button's own
        # default (probe_autoit_resizing7, part 2). 0 and values of 1024 and above mean "the
        # control type's default".
        mode = self._options["GUIResizeMode"]
        control = _control(
            control_id=control_id,
            kind=kind,
            window=window.handle,
            widget=widget,
            style=style,
            ex_style=ex_style,
            dock_default=mode if 0 < mode < _DOCK_LIMIT else _DEFAULT_DOCKING.get(kind, GUI_DOCKAUTO),
        )
        self._controls[control_id] = control
        self._last_control = control_id
        if widget is not None:
            self._controls_by_widget[str(widget)] = control_id
        return control

    def _parent_widget(self, window: _window) -> Any:
        """Return the widget new controls should be placed in (a tab frame when open)."""

        if window.tab_frame is not None:
            return window.tab_frame
        return window.widget

    def _allocate_position(
        self,
        window: _window,
        left: int,
        top: int,
        width: int | None,
        height: int | None,
        kind: str = "",
    ) -> tuple[int, int, int, int]:
        """Resolve control coordinates and size the way AutoIt documents them.

        The reference states, for every control: "-1 for left/top means computed according
        to GUICoordMode", "width/height default is the previously used width/height" (text
        autofit for Button, Checkbox, Label and Radio). ``GUIDataSeparatorChar``-style
        option ``GUICoordMode`` selects the frame of reference: 1 is absolute coordinates
        relative to the dialog box (the default), 0 is relative to the start of the last
        control, and 2 is cell positioning where -1 means "do not increment".

        "The previously used width/height" is measured, not assumed (probe_autoit_default_size_
        out.txt): a control with no size takes the size the *last* control was created with, and
        that includes a control whose size was computed for it — an Input after a Button ("OK",
        23x25) came out 23x25. Before anything has been created, each kind has its own default
        (``_DEFAULT_CONTROL_SIZE``), which the same probe measured per kind.

        A width or height the caller *gives* is used as it stands, zero included
        (probe_autoit_zero_size_out.txt: an Input, Edit, List, Label, Button and Group created with
        ``0, 0`` all came out 0x0, and the next control with no size inherited that 0x0 rather than
        the kind's default). Only an omitted size consults the kind's default.
        """

        mode = self._options["GUICoordMode"]
        if left == -1 or top == -1:
            if mode == 2:
                resolved_left = window.cell_left if left == -1 else window.cell_left + left
                resolved_top = window.cell_top if top == -1 else window.cell_top + top
            elif mode == 0:
                resolved_left = window.last_left + (0 if left == -1 else left)
                resolved_top = window.last_top + (0 if top == -1 else top)
            else:
                resolved_left = window.last_left if left == -1 else left
                resolved_top = window.last_top if top == -1 else top
        else:
            if mode == 0:
                resolved_left = window.last_left + left
                resolved_top = window.last_top + top
            elif mode == 2:
                resolved_left = window.cell_left + left
                resolved_top = window.cell_top + top
            else:
                resolved_left = left
                resolved_top = top

        default_width, default_height = _default_control_size(kind)
        resolved_width = window.last_width if width is None else width
        resolved_height = window.last_height if height is None else height
        if resolved_width is None:
            resolved_width = default_width
        if resolved_height is None:
            resolved_height = default_height
        return resolved_left, resolved_top, resolved_width, resolved_height

    def _place(
        self,
        window: _window,
        control: _control,
        left: int,
        top: int,
        width: int,
        height: int,
        record_base: bool = True,
    ) -> None:
        """Place a control, then update the window's coordinate and size memory.

        ``record_base`` is what the docking arithmetic docks *from*: the geometry a control was
        created or moved to, with the client size of that moment. A window resize places controls
        without recording a new base, because the probe showed every resize computing from the box
        the control was last put at by GUICtrlCreate.../GUICtrlSetPos — repeated resizes do not
        drift (tests/autoit_reference/probe_autoit_resizing2_out.txt, `probe_autoit_resizing7`).
        """

        if control.native:
            native.move_window(control.native, left, top, width, height)
        else:
            widget = control.widget
            widget.place(x=left, y=top, width=width, height=height)
        control.pos = (left, top, width, height)
        if record_base:
            control.dock_base = (left, top, width, height)
            control.dock_client = (window.width, window.height)
        window.last_left = left
        window.last_top = top
        window.last_width = width
        window.last_height = height
        if self._options["GUICoordMode"] == 2:
            window.cell_left = left + width
            window.cell_top = top

    def _autofit(self, widget: Any) -> tuple[int, int]:
        """Return the size tkinter needs to show a widget's text (AutoIt's text autofit)."""

        widget.update_idletasks()
        return int(widget.winfo_reqwidth()), int(widget.winfo_reqheight())

    def _apply_defaults(self, window: _window, control: _control) -> None:
        """Apply the window's default font and colours to a control."""

        widget = _content_widget(control)
        if widget is None:
            return
        if window.default_font is not None and _supports(widget, "font"):
            widget.configure(font=window.default_font)
        if window.default_text_color is not None:
            self._set_widget_text_color(window, control, window.default_text_color)
        if window.default_bk_color is not None:
            self._set_widget_bk_color(window, control, window.default_bk_color)

    def _set_widget_text_color(self, window: _window, control: _control, color: int) -> None:
        """Apply a text colour to a control where tkinter supports one."""

        widget = _content_widget(control)
        if widget is None or not _supports(widget, "fg"):
            return
        tk_color = styles.colorref_to_tk(color)
        if tk_color is None:
            return
        widget.configure(fg=tk_color)

    def _set_widget_bk_color(self, window: _window, control: _control, color: int) -> None:
        """Apply a background colour to a control where tkinter supports one.

        ``$GUI_BKCOLOR_TRANSPARENT`` (-2) is documented for Label, Group, Radio and
        Checkbox: tkinter has no transparent background, and the way a tkinter widget looks
        transparent is to paint it in its parent's colour, which is what this does.
        """

        widget = control.widget
        if widget is None:
            return
        if color == GUI_BKCOLOR_TRANSPARENT:
            if control.kind in ("Label", "Group", "Radio", "Checkbox", "Pic", "Graphic"):
                if _supports(widget, "bg"):
                    widget.configure(bg=window.widget.cget("bg"))
            return
        tk_color = styles.colorref_to_tk(color)
        if tk_color is None:
            return
        self._configure_widget_color(widget, control, tk_color, background=True)
        inner = _content_widget(control)
        if inner is not None and inner is not widget:
            # A List or an Edit is a frame around the widget that shows the colour, so both are
            # painted: the frame fills the space the scrollbar does not use.
            self._configure_widget_color(inner, control, tk_color, background=True)

    def _configure_widget_color(
        self,
        widget: Any,
        control: _control,
        tk_color: str,
        background: bool,
    ) -> None:
        """Set a widget's foreground or background colour, ttk included."""

        option = "bg" if background else "fg"
        if _supports(widget, option):
            widget.configure(**{option: tk_color})
            return
        ttk_class = _TTK_CLASS_BY_KIND.get(control.kind)
        if ttk_class is None:
            return
        style_name = f"Py4GW{control.control_id}.{ttk_class}"
        option_name = "background" if background else "foreground"
        ttk.Style(widget).configure(style_name, **{option_name: tk_color})
        widget.configure(style=style_name)

    def _bind_control_events(self, control: _control) -> None:
        """Bind the tkinter event that AutoIt reports as a control event.

        The event goes on the widget the user acts on, which for a List and an Edit is the widget
        inside the frame the port places (``_content_widget``): binding it on the frame instead
        left the event unfired, so a List control answered nothing at all (measured: a
        ``<<ListboxSelect>>`` binding on the frame, and a selection that fired no OnEvent call).
        """

        widget = _content_widget(control)
        if widget is None:
            return
        control_id = control.control_id
        if control.kind in ("Button", "Checkbox", "Radio"):
            widget.configure(command=lambda: self._control_event(control_id))
        elif control.kind == "Combo":
            widget.bind("<<ComboboxSelected>>", lambda _event: self._control_event(control_id))
        elif control.kind == "List":
            widget.bind("<<ListboxSelect>>", lambda _event: self._control_event(control_id))
        elif control.kind in ("Slider", "Updown"):
            widget.configure(command=lambda _value, cid=control_id: self._control_event(cid))
        elif control.kind == "Input":
            variable = widget.cget("textvariable")
            if variable:
                widget.tk.globalgetvar(variable)  # ensure the variable exists
            widget.bind("<KeyRelease>", lambda _event: self._control_event(control_id))
        elif control.kind == "Edit":
            widget.bind("<<Modified>>", lambda _event: self._edit_changed(control))
        elif control.kind == "TreeView":
            widget.bind("<<TreeviewSelect>>", lambda _event: self._control_event(control_id))
            widget.bind("<<TreeviewOpen>>", lambda _event: self._control_event(control_id))
        elif control.kind == "ListView":
            widget.bind("<<TreeviewSelect>>", lambda _event: self._control_event(control_id))

    def _edit_changed(self, control: _control) -> None:
        """Report an Edit control change, resetting Tk's modified flag as we go."""

        widget = _content_widget(control)
        if widget is None:
            return
        if not widget.edit_modified():
            return
        widget.edit_modified(False)
        self._control_event(control.control_id)

    def _listview_selected_item(self, control: _control) -> int | None:
        """Return the control ID of the ListView's selected item, or None.

        This is what ``GUICtrlRead`` reports for the control ("Control identifier (controlID) of
        the selected ListViewItem. 0 means no item is selected", GUICtrlRead.htm). The *event* a
        click delivers is the ListView's own identifier, not this one -- measured from the
        interpreter, which answered ``@GUI_CtrlId = 4`` (the ListView) for clicks on both of its
        rows while the functions registered on the two items were never called
        (probe_autoit_listview_event_out.txt).
        """

        widget = control.widget
        selection = widget.selection()
        if not selection:
            return None
        for item in self._controls.values():
            if item.parent == control.control_id and item.item == selection[0]:
                return item.control_id
        return None

    # --- events and the message queue -------------------------------------------------

    def _control_event(self, control_id: int) -> None:
        """Deliver a control event: an OnEvent call, or a message for GUIGetMsg()."""

        control = self._controls.get(control_id)
        window = self._windows.get(control.window if control else -1)
        handle = window.handle if window else 0
        control_handle = 0
        if control is not None and control.widget is not None:
            control_handle = int(control.widget.winfo_id())
        if self._options["GUIOnEventMode"] == 1:
            handler = self._on_event_handler(window, control_id)
            if handler is not None:
                self._invoke_handler(handler, control_id, handle, control_handle)
            return
        self._enqueue(control_id, handle, control_handle)

    def _on_event_handler(
        self, window: _window | None, control_id: int
    ) -> Callable[[], None] | None:
        """Return the OnEvent function registered for a control ID."""

        if window is None:
            return None
        control = self._controls.get(control_id)
        if control is not None:
            return control.on_event
        return None

    def _invoke_handler(
        self,
        handler: Callable[[], None],
        control_id: int,
        window_handle: int,
        control_handle: int,
    ) -> None:
        """Call an OnEvent function with AutoIt's @GUI_* macros set for it."""

        self.GUI_CtrlId = control_id
        self.GUI_WinHandle = window_handle
        self.GUI_CtrlHandle = control_handle
        handler()

    def _enqueue(self, event: int, window: int, control_handle: int) -> None:
        """Add an event to the queue GUIGetMsg() drains."""

        mouse_x, mouse_y = self._mouse_position(window)
        if event == GUI_EVENT_MOUSEMOVE and self._messages:
            last = self._messages[-1]
            if last[0] == GUI_EVENT_MOUSEMOVE and last[1] == window:
                self._messages[-1] = (event, window, control_handle, mouse_x, mouse_y)
                return
        self._messages.append((event, window, control_handle, mouse_x, mouse_y))

    def _mouse_position(self, window: int) -> tuple[int, int]:
        """Return the pointer position relative to a window's client area."""

        record = self._windows.get(window)
        if record is None or self._root is None:
            return (0, 0)
        try:
            pointer_x, pointer_y = self._root.winfo_pointerxy()
            return (
                int(pointer_x) - record.widget.winfo_rootx(),
                int(pointer_y) - record.widget.winfo_rooty(),
            )
        except tkinter.TclError:
            return (0, 0)

    def _system_event(self, window: _window, event: int) -> None:
        """Deliver a system event (close, resize, mouse) the way AutoIt does."""

        if self._options["GUIOnEventMode"] == 1:
            handler = window.on_events.get(event)
            if handler is not None:
                self._invoke_handler(handler, event, window.handle, 0)
            return
        self._enqueue(event, window.handle, 0)

    def _pump(self) -> None:
        """Process pending tkinter events, which is what fills the message queue."""

        if self._root is None:
            return
        try:
            # tkinter's public way to drain the pending events and idle work. AutoIt's
            # GUIGetMsg() pumps the Win32 message queue the same way.
            self._root.update()
        except tkinter.TclError:
            return
        # What the hooked procedure queued is delivered here, where no Windows message is being
        # handled and a handler may call tkinter freely.
        self._deliver_pending()
        for window in list(self._windows.values()):
            self._note_window_state(window)

    def _note_window_state(self, window: _window) -> None:
        """Report minimize/restore/maximize by comparing the window's state."""

        try:
            state = window.widget.state()
        except tkinter.TclError:
            return
        if state == window.state:
            return
        previous = window.state
        window.state = state
        if state == "iconic":
            self._system_event(window, GUI_EVENT_MINIMIZE)
        elif state == "zoomed":
            self._system_event(window, GUI_EVENT_MAXIMIZE)
        elif previous in ("iconic", "zoomed"):
            self._system_event(window, GUI_EVENT_RESTORE)

    def Sleep(self, milliseconds: int) -> None:
        """Wait, delivering GUI events while waiting, as AutoIt's OnEvent idiom needs.

        The reference's OnEvent page gives the idle loop as ``While 1 / Sleep(100) /
        WEnd`` and states that no GUI action happens inside it. A ported ``Sleep`` therefore
        has to run tkinter's event loop while it waits, or no event would ever arrive.
        """

        deadline = time.monotonic() + (milliseconds / 1000.0)
        while time.monotonic() < deadline:
            self._pump()
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(0.005, remaining))

    def Opt(self, option: str, param: Any = None) -> Any:
        """Read or change a GUI option, as AutoIt's ``Opt()``/``AutoItSetOption()`` does.

        Returns the previous value. ``None`` stands for AutoIt's ``Default`` keyword: it
        resets the option. Only the ``GUI*`` options of the reference are implemented; any
        other AutoIt option raises naming the gap.
        """

        if option not in self._options:
            if option.startswith("GUI"):
                raise NotImplementedError(
                    f"Opt({option!r}): AutoIt documents this GUI option, but this port has "
                    "no behaviour for it; the implemented options are "
                    f"{sorted(self._options)}"
                )
            raise NotImplementedError(
                f"Opt({option!r}): only the GUI options of the AutoIt reference are "
                f"implemented ({sorted(self._options)}); {option!r} is an option of another "
                "AutoIt function family"
            )
        previous = self._options[option]
        if param is not None:
            self._options[option] = param
        if option == "GUIEventOptions" and param == 1:
            # Suppressing the window's own minimize/maximize/restore means seeing the system
            # command first, which is a window procedure's job: AutoIt's GUI has one always, so the
            # port installs its hook when this option asks for it (it otherwise hooks only a window
            # that has a native control, whose notifications need it).
            for window in list(self._windows.values()):
                self._hook_window(window)
        return previous

    def AutoItSetOption(self, option: str, param: Any = None) -> Any:
        """AutoIt's other name for :meth:`Opt` (the reference documents both)."""

        return self.Opt(option, param)

    # ---------------------------------------------------------------------------------
    # GUI window functions
    # ---------------------------------------------------------------------------------

    def GUICreate(
        self,
        title: str,
        width: int = _DEFAULT_WINDOW_SIZE,
        height: int = _DEFAULT_WINDOW_SIZE,
        left: int = -1,
        top: int = -1,
        style: int = -1,
        exStyle: int = -1,
        parent: int = 0,
    ) -> int:
        """Create a GUI window, hidden, and return its handle.

        The default style is the reference's ``$WS_MINIMIZEBOX | $WS_CAPTION | $WS_POPUP |
        $WS_SYSMENU`` with ``$WS_CLIPSIBLINGS`` forced, which the AutoIt interpreter
        reported as ``0x84CA0000`` with ``$WS_EX_WINDOWEDGE`` (0x100) forced.
        """

        root = self._ensure_root()
        if parent:
            parent_window = self._windows.get(parent)
            if parent_window is None:
                self.error = 1
                return 0
            widget = tkinter.Toplevel(parent_window.widget)
            if exStyle != -1 and exStyle & WS_EX_MDICHILD and left != -1 and top != -1:
                left += parent_window.widget.winfo_rootx()
                top += parent_window.widget.winfo_rooty()
        else:
            widget = tkinter.Toplevel(root)
        widget.withdraw()
        widget.title(title)
        if left == -1 or top == -1:
            # "-1 (default), the window is centered" (GUICreate.htm).
            widget.geometry(f"{width}x{height}")
        else:
            widget.geometry(f"{width}x{height}+{left}+{top}")
        if exStyle != -1 and exStyle & WS_EX_TOPMOST:
            widget.attributes("-topmost", True)
        resizable = bool(style != -1 and style & (WS_SIZEBOX | WS_MAXIMIZEBOX))
        widget.resizable(resizable, resizable)
        widget.update_idletasks()
        handle = self._window_of(widget)
        resolved_style = _DEFAULT_WINDOW_STYLE if style == -1 else style
        resolved_ex_style = _DEFAULT_WINDOW_EXSTYLE if exStyle == -1 else exStyle
        record = _window(
            handle=handle,
            widget=widget,
            widget_id=int(widget.winfo_id()),
            style=resolved_style,
            ex_style=resolved_ex_style,
            parent=parent,
            width=width,
            height=height,
            left=left,
            top=top,
        )
        self._windows[handle] = record
        self._current_window = handle
        widget.protocol("WM_DELETE_WINDOW", lambda h=handle: self._window_close_requested(h))
        if self._options["GUICloseOnESC"] == 1:
            widget.bind("<Escape>", lambda _event, h=handle: self._escape_pressed(h))
        widget.bind("<Configure>", lambda event, h=handle: self._window_configured(h, event))
        widget.bind(
            "<Motion>",
            lambda _event, h=handle: self._motion(h),
        )
        widget.bind("<Button-1>", lambda _event, h=handle: self._mouse_button(h, True, True))
        widget.bind(
            "<ButtonRelease-1>", lambda _event, h=handle: self._mouse_button(h, True, False)
        )
        widget.bind("<Button-3>", lambda _event, h=handle: self._mouse_button(h, False, True))
        widget.bind(
            "<ButtonRelease-3>", lambda _event, h=handle: self._mouse_button(h, False, False)
        )
        self.error = 0
        return handle

    def _motion(self, handle: int) -> None:
        """Deliver $GUI_EVENT_MOUSEMOVE for a window."""

        record = self._windows.get(handle)
        if record is not None:
            self._system_event(record, GUI_EVENT_MOUSEMOVE)

    def _window_close_requested(self, handle: int) -> None:
        """Deliver $GUI_EVENT_CLOSE for a window's system menu or close button."""

        record = self._windows.get(handle)
        if record is not None:
            self._system_event(record, GUI_EVENT_CLOSE)

    def _escape_pressed(self, handle: int) -> None:
        """Deliver $GUI_EVENT_CLOSE when ESC is pressed (Opt("GUICloseOnESC") is 1)."""

        if self._options["GUICloseOnESC"] == 1:
            record = self._windows.get(handle)
            if record is not None:
                self._system_event(record, GUI_EVENT_CLOSE)

    def _window_configured(self, handle: int, event: Any) -> None:
        """Deliver $GUI_EVENT_RESIZED when a window's size actually changes.

        Tk reports a configure event when a window is first mapped, which is not a resize
        the user made; the first configure after a window becomes visible therefore only
        records the size.
        """

        record = self._windows.get(handle)
        if record is None:
            return
        # A toplevel is in the bindtags of every widget inside it, so a binding on the window also
        # receives its children's Configure events (traced: a 500x300 window's handler was called
        # with the frame's, scrollbar's and text's sizes, ending at 1x1). Only the window's own
        # configure is a window resize.
        if event.widget is not record.widget:
            return
        changed = int(event.width) != record.width or int(event.height) != record.height
        record.width = int(event.width)
        record.height = int(event.height)
        if not record.layout_seen:
            record.layout_seen = True
            return
        if changed and record.visible:
            # AutoIt moves the controls on the resize itself, so a handler that reads a control's
            # position sees the docked one.
            self._dock_controls(record)
            self._system_event(record, GUI_EVENT_RESIZED)
        elif changed:
            self._dock_controls(record)

    def _dock_controls(self, window: _window) -> None:
        """Reposition every control of a resized window the way GUICtrlSetResizing docks them.

        The rule is the interpreter's, measured flag by flag
        (tests/autoit_reference/probe_autoit_resizing3_out.txt and `probe_autoit_resizing4`):

        * a value of ``0`` or one of ``1024`` or more means "the control's own default resizing",
          which is per control type (Button and Pic ``$GUI_DOCKSIZE``, Input/Checkbox/Radio/Combo/
          Date ``$GUI_DOCKHEIGHT``, Label/Edit/List/Progress/Slider/Group ``$GUI_DOCKAUTO``, and
          ListView/TreeView measured as ``$GUI_DOCKAUTO``);
        * every position scales by the client ratio, truncated;
        * ``$GUI_DOCKWIDTH``/``$GUI_DOCKHEIGHT`` keep the size, and without them the size scales;
        * ``$GUI_DOCKLEFT``/``$GUI_DOCKRIGHT``/``$GUI_DOCKTOP``/``$GUI_DOCKBOTTOM`` pin that edge,
          with the opposite margin kept — and when both horizontal edges are pinned the width is
          what is left between them (``$GUI_DOCKBORDERS`` measured 386x216);
        * ``$GUI_DOCKHCENTER``/``$GUI_DOCKVCENTER`` pin the control relative to the client centre,
          and the probe showed them taking effect together with ``$GUI_DOCKWIDTH``/
          ``$GUI_DOCKHEIGHT`` (alone they left the position scaled).
        """

        client = (window.width, window.height)
        for control in list(self._controls.values()):
            if control.window != window.handle:
                continue
            base = control.dock_base
            before = control.dock_client
            if base is None or before is None:
                continue
            dock = control.resizing if 0 < control.resizing < _DOCK_LIMIT else control.dock_default
            if dock <= 0:
                continue
            box = _docked_box(base, before, client, dock)
            if box != control.pos:
                self._place(window, control, *box, record_base=False)

    def _mouse_button(self, handle: int, primary: bool, pressed: bool) -> None:
        """Deliver a mouse-button system event and remember the button state."""

        record = self._windows.get(handle)
        if record is None:
            return
        if primary:
            self._primary_down = 1 if pressed else 0
            event = GUI_EVENT_PRIMARYDOWN if pressed else GUI_EVENT_PRIMARYUP
        else:
            self._secondary_down = 1 if pressed else 0
            event = GUI_EVENT_SECONDARYDOWN if pressed else GUI_EVENT_SECONDARYUP
        self._system_event(record, event)

    def GUISetState(self, flag: int = SW_SHOW, winhandle: int | None = None) -> int:
        """Change the state of a GUI window: show, hide, minimize, maximize or restore."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        widget = window.widget
        if flag == SW_SHOW:
            widget.deiconify()
            widget.lift()
            window.visible = True
        elif flag == SW_HIDE:
            widget.withdraw()
            window.visible = False
            window.layout_seen = False
        elif flag == SW_MINIMIZE:
            widget.iconify()
        elif flag == SW_RESTORE:
            widget.deiconify()
            widget.state("normal")
        elif flag == SW_MAXIMIZE:
            widget.state("zoomed")
        elif flag == SW_ENABLE or flag == SW_DISABLE:
            enabled = flag == SW_ENABLE
            window.disabled = not enabled
            for control in self._controls.values():
                if control.window != window.handle or control.widget is None:
                    continue
                try:
                    control.widget.configure(state="normal" if enabled else "disabled")
                except tkinter.TclError:
                    continue
        elif flag == SW_LOCK:
            # AutoIt's $SW_LOCK is LockWindowUpdate on the window, and $SW_UNLOCK is the same
            # call with no window: "Only one window can be locked with @SW_LOCK... @SW_UNLOCK
            # just ignored the winhandle to unlock any locked window."
            if not native.lock_window_update(window.handle):
                return 0
            window.locked = True
        elif flag == SW_UNLOCK:
            native.unlock_window_update()
            for other in self._windows.values():
                other.locked = False
        elif flag in (SW_SHOWNORMAL, SW_SHOWDEFAULT, SW_SHOWNA, SW_SHOWNOACTIVATE):
            widget.deiconify()
            window.visible = True
        elif flag in (SW_SHOWMINIMIZED, SW_SHOWMINNOACTIVE):
            widget.iconify()
        elif flag == SW_SHOWMAXIMIZED:
            widget.state("zoomed")
        else:
            return 0
        return 1

    def GUISetStyle(self, style: int, exStyle: int = -1, winhandle: int | None = None) -> int:
        """Change the styles of a GUI window; -1 leaves a style unchanged."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        if style != -1:
            window.style = style
        if exStyle != -1:
            window.ex_style = exStyle
        if exStyle != -1:
            window.widget.attributes("-topmost", bool(exStyle & WS_EX_TOPMOST))
        resizable = bool(window.style != -1 and window.style & (WS_SIZEBOX | WS_MAXIMIZEBOX))
        window.widget.resizable(resizable, resizable)
        return 1

    def GUIGetStyle(self, winhandle: int | None = None) -> list[int]:
        """Return a two-element array: [style, exStyle]."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            self.error = 1
            return []
        # AutoIt reports the style word as a signed 32-bit value: the interpreter returned
        # -2067136512 for its default window, which is 0x84CA0000.
        return [_signed_32(window.style), _signed_32(window.ex_style)]

    def GUISetCoord(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        winhandle: int | None = None,
    ) -> int:
        """Set the current position for the next control (GUICoordMode 2's cell)."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.cell_left = left
        window.cell_top = top
        if width is not None:
            window.last_width = width
        if height is not None:
            window.last_height = height
        return 1

    def GUISetBkColor(self, background: int, winhandle: int | None = None) -> int:
        """Set the background colour of a GUI window (AutoIt colour, ``0x00BBGGRR``)."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        tk_color = styles.colorref_to_tk(background)
        if tk_color is None:
            return 0
        window.widget.configure(bg=tk_color)
        return 1

    def GUISetFont(
        self,
        size: float,
        weight: int = 0,
        attribute: int = GUI_FONTNORMAL,
        fontname: str = "",
        winhandle: int | None = None,
        quality: int = 2,
    ) -> int:
        """Set the default font for a GUI window and its controls."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.default_font = styles.font_tuple(size, weight, attribute, fontname, quality)
        for control in self._controls.values():
            if control.window != window.handle or control.widget is None:
                continue
            if _supports(control.widget, "font"):
                control.widget.configure(font=window.default_font)
        return 1

    def GUISetIcon(
        self, iconfile: str, iconID: int = -1, winhandle: int | None = None
    ) -> int:
        """Set the icon used in a GUI window.

        The reference sets the window's icon out of an icon file or DLL, "Passing a negative
        number causes 1-based index behaviour"; that is ``ExtractIconEx``/``LoadImage`` plus
        ``WM_SETICON`` on the window, which is what this does.
        """

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        icon = native.load_icon(iconfile, iconID)
        if not icon:
            return 0
        window.icon = icon
        return 1 if native.set_window_icon(window.handle, icon) else 0

    def GUISetCursor(
        self, cursorID: int = 0, override: int = GUI_CURSOR_NOOVERRIDE, winhandle: int | None = None
    ) -> None:
        """Set the mouse cursor for a GUI window (returns nothing, as AutoIt does)."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return None
        name = "none" if cursorID == _CURSOR_HIDDEN_ID else _CURSOR_BY_ID.get(cursorID, "arrow")
        try:
            window.widget.configure(cursor=name)
        except tkinter.TclError:
            window.widget.configure(cursor="arrow")
        if override == GUI_CURSOR_OVERRIDE:
            for control in self._controls.values():
                if control.window == window.handle and control.widget is not None:
                    try:
                        control.widget.configure(cursor=name)
                    except tkinter.TclError:
                        continue
        return None

    def GUISetHelp(self, helpfile: str, winhandle: int | None = None) -> int:
        """Set the file run when F1 is pressed while the GUI is active."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.help_file = helpfile
        window.widget.bind("<F1>", lambda _event, h=window.handle: self._open_help(h))
        return 1

    def _open_help(self, handle: int) -> None:
        """Run the window's help file, the way AutoIt runs GUISetHelp()'s file."""

        window = self._windows.get(handle)
        if window is None or not window.help_file:
            return
        os.startfile(window.help_file)  # noqa: S606 - AutoIt runs the file the caller set

    def GUISetAccelerators(
        self, accelerators: Sequence[Sequence[Any]] | None, winhandle: int | None = None
    ) -> int:
        """Set the accelerator table, a sequence of ``[key, controlID]`` pairs.

        AutoIt's keys are in ``HotKeySet()`` format; passing no table (AutoIt passes a
        non-array) unsets every accelerator. An accelerator "action[s] their associated
        control which then fires the function using GUIGetMsg() or GUICtrlSetOnEvent()".
        ``#`` is the Windows key, which tkinter has no modifier for: the base key is bound and the
        key's own state decides (see ``_accelerator_fired``).
        """

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        # "Passing this function a non-array parameter will unset all accelerators": unsets the
        # bindings too, or an unset accelerator would keep firing. The port's own Escape binding
        # ("$GUICloseOnESC") is left alone, since an accelerator can name the same key.
        for sequence, _control_id in window.accelerators:
            if sequence != "<Escape>":
                window.widget.unbind(sequence)
        window.accelerators = []
        if accelerators is None:
            return 1
        for index, entry in enumerate(accelerators):
            key = str(entry[0])
            control_id = int(entry[1])
            translated = _accelerator_sequence(key)
            if translated is None:
                raise NotImplementedError(
                    f"GUISetAccelerators needs a tkinter binding for accelerator {key!r}; "
                    "the port translates AutoIt's HotKeySet() syntax (^ ! + # and named keys) "
                    "and has none for this key"
                )
            sequence, needs_win = translated
            window.accelerators.append((sequence, control_id))
            window.widget.bind(
                sequence,
                lambda _event, cid=control_id, win=needs_win: self._accelerator_fired(cid, win),
                add=f"+{index}" if index else "+",
            )
        return 1

    def _accelerator_fired(self, control_id: int, needs_win: bool = False) -> None:
        """Act on an accelerator's control, as AutoIt's accelerators do.

        ``#`` is AutoIt's Windows key, and tkinter has no modifier for it — a Tk binding cannot
        spell it. The base key is bound instead and this asks Windows whether the key is held, which
        is the same thing the modifier means; a press without it is not the accelerator.
        """

        if needs_win and not native.win_key_down():
            return
        self._control_event(control_id)

    def GUIRegisterMsg(self, msgID: int, function: Any) -> int:
        """Register a function for a Windows message ID (``WM_*``).

        AutoIt receives the window's messages in its own window procedure and calls the
        registered function with up to four parameters (``$hWndGUI, $MsgID, $WParam,
        $LParam``); a function declared with two parameters is called with two, exactly as the
        reference describes. The port hooks the window's procedure with
        ``SetWindowLongPtr``/``SetWindowLong`` and chains to the window's own procedure, so
        tkinter keeps working, unless the function returns something other than
        ``$GUI_RUNDEFMSG``.
        """

        try:
            window = self._resolve_window(None)
        except _WindowNotFound:
            return 0
        if function == "":
            window.registered_messages.pop(msgID, None)
            if not window.registered_messages:
                native.unhook_messages(window.handle)
            return 1
        if not callable(function):
            raise TypeError(
                "GUIRegisterMsg takes a Python callable: AutoIt passes the *name* of an "
                "AutoIt function as a string (GUIRegisterMsg.htm). Pass \"\" to unregister."
            )
        window.registered_messages[msgID] = function
        if not self._hook_window(window):
            window.registered_messages.pop(msgID, None)
            return 0
        return 1

    def _dispatch_message(self, hwnd: int, message: int, wparam: int, lparam: int) -> Any:
        """Answer a window message: a control's notification, or a registered function.

        Native controls report themselves through ``WM_NOTIFY`` (an UpDown's arrows, a Date's
        changed date, a month calendar's chosen day, an Avi's start and stop), which is what
        AutoIt turns into the control events its scripts see.

        **Nothing is done here but reading what the message carries.** A hooked procedure runs on
        Windows' terms, in the middle of another window's message; anything that calls tkinter
        releases the interpreter's thread state, and a message arriving during that window
        re-enters this procedure with nothing to restore — a fatal ``PyEval_RestoreThread``. So
        the values the message points at are copied out (they are only valid for the length of the
        call) and the work that follows — a control's event, a drop, a registered function — is
        queued for the next pump, which runs outside the procedure. The readings behind this are in
        ``docs/AUTOIT_GUI.md``.
        """

        if message == WM_SYSCOMMAND and self._options["GUIEventOptions"] == 1:
            # "0 = (default) Windows behavior on click on Minimize,Restore, Maximize, Resize.
            # 1 = suppress windows behavior on minimize, restore or maximize click button or window
            # resize. Just sends the notification." Measured from the interpreter (probe_autoit_gui_
            # event_options_out.txt): with the option set, a $SC_MINIMIZE request left the window at
            # state 15 and still called the $GUI_EVENT_MINIMIZE function; with it unset the window
            # went to state 23 (minimised) and called it too. The command is swallowed here and the
            # notification queued, because nothing but reading may happen inside this procedure.
            event = {
                SC_MINIMIZE: GUI_EVENT_MINIMIZE,
                SC_MAXIMIZE: GUI_EVENT_MAXIMIZE,
                SC_RESTORE: GUI_EVENT_RESTORE,
            }.get(wparam & 0xFFF0)
            if event is not None:
                self._pending.append(("system", hwnd, event))
                return 0
        if message == WM_NOTIFY:
            header = native.notify_header(lparam)
            if header is not None:
                source, code = header
                chosen = native.notify_selected_date(lparam) if code in (MCN_SELECT, MCN_SELCHANGE) else None
                self._pending.append(("notify", source, code, chosen))
            return native.GUI_RUNDEFMSG
        if message == native.WM_DROPFILES:
            # The drop's point is read before its file list, because reading the list releases the
            # payload Windows handed over.
            point = native.dropped_point(wparam)
            names = tuple(native.dropped_files(wparam))
            if names:
                self._pending.append(("drop", hwnd, point, names))
            return 0
        if any(window.registered_messages.get(message) is not None for window in self._windows.values()):
            self._pending.append(("message", hwnd, message, wparam, lparam))
        return native.GUI_RUNDEFMSG

    def _deliver_pending(self) -> None:
        """Deliver what the hooked procedure queued, outside the procedure."""

        while self._pending:
            item = self._pending.pop(0)
            kind = item[0]
            if kind == "notify":
                self._notify_control(item[1], item[2], item[3])
            elif kind == "drop":
                self._files_dropped(item[1], item[2], item[3])
            elif kind == "message":
                self._call_registered_message(item[1], item[2], item[3], item[4])
            elif kind == "system":
                window = self._window_for_handle(item[1])
                if window is not None:
                    self._system_event(window, item[2])

    def _call_registered_message(
        self, hwnd: int, message: int, wparam: int, lparam: int
    ) -> None:
        """Call the function registered for a message ID."""

        window = self._window_for_handle(hwnd)
        if window is None:
            return
        function = window.registered_messages.get(message)
        if function is None:
            return
        # AutoIt's functions are handed the GUI's own window handle, which is the record's.
        self.GUI_WinHandle = window.handle
        count = _positional_parameter_count(function)
        if count >= 4:
            function(window.handle, message, wparam, lparam)
        else:
            function(window.handle, message)

    def _files_dropped(self, hwnd: int, point: tuple[int, int], names: tuple[str, ...]) -> None:
        """Report a dropped file the way the reference describes it.

        "For other controls on reception of $GUI_EVENT_DROPPED, @GUI_DragId will return the
        controlID from where the drag start (-1 if from a file, @GUI_DragFile contain the filename
        being dropped) and @GUI_DropId returns the controlID of the dropped control", and an
        Edit or Input control "will be set with the filename". The control that receives it is the
        one that accepted drops and lies under the point the drop carries.
        """

        # The drop's point and file list were read inside the hooked procedure, before the payload
        # Windows handed over was released.
        target = self._drop_target(hwnd, point)
        self.GUI_DragFile = names[0]
        self.GUI_DragId = -1
        self.GUI_DropId = target.control_id if target is not None else 0
        if target is not None and target.kind in ("Input", "Edit"):
            # "Multiple selected files will be dropped as separate lines."
            _set_text(target, "\n".join(names) if target.kind == "Edit" else "|".join(names))
        if target is not None:
            self._control_event(target.control_id)
        else:
            self._enqueue(GUI_EVENT_DROPPED, hwnd, 0)

    def _drop_target(self, hwnd: int, point: tuple[int, int]) -> _control | None:
        """Return the control a drop belongs to: the accepting control under its point.

        The control is found from the geometry the port recorded rather than from tkinter's
        hit-test, which answers nothing while another window covers the GUI.
        """

        window = self._window_for_handle(hwnd)
        if window is None:
            return None
        for control in reversed(list(self._controls.values())):
            if control.window != window.handle or control.widget is None:
                continue
            if not control.states & GUI_DROPACCEPTED:
                continue
            left, top, width, height = control.pos or (0, 0, 0, 0)
            try:
                origin_x = control.widget.winfo_rootx()
                origin_y = control.widget.winfo_rooty()
            except tkinter.TclError:
                continue
            if (
                origin_x <= point[0] <= origin_x + width
                and origin_y <= point[1] <= origin_y + height
            ):
                return control
        return None

    def _window_for_handle(self, hwnd: int) -> _window | None:
        """Find the window record a native handle belongs to.

        A GUI has more than one: the handle ``GUICreate`` returns is the top-level frame window,
        the tkinter widget is a window inside it, and a control's notifications arrive at the
        widget the control is a child of. A message from any of them is that GUI's.

        Both handles are stored, because this runs inside the hooked window procedure, where no
        tkinter call may be made (see ``_window.widget_id``).
        """

        for window in self._windows.values():
            if hwnd == window.handle or (window.widget_id and hwnd == window.widget_id):
                return window
        return None

    def _notify_control(self, source: int, code: int, chosen: tuple[int, int, int] | None) -> None:
        """Turn a native control's notification into the control event AutoIt reports.

        The notification's own values were copied while the message was being handled, because
        what its ``lParam`` points at is only valid then.
        """

        control = next(
            (item for item in self._controls.values() if item.native == source), None
        )
        if control is None:
            return
        if control.kind == "MonthCal" and code in (MCN_SELECT, MCN_SELCHANGE):
            # The user has chosen a day: the control keeps no programmatic selection, so its
            # notification is what carries the date, and the port records it.
            if chosen is not None:
                control.value = chosen
        if control.kind == "MonthCal" and code == MCN_VIEWCHANGE:
            # A view change carries no date, but it is a change to the control all the same.
            self._control_event(control.control_id)
            return
        if code in (
            native.UDN_DELTAPOS,
            DTN_DATETIMECHANGE,
            MCN_SELECT,
            MCN_SELCHANGE,
            ACN_START,
            ACN_STOP,
        ):
            self._control_event(control.control_id)

    def _hook_window(self, window: _window) -> bool:
        """Hook a window's messages, once, so its native controls can report themselves.

        A control sends its notifications to the window it is a *child of*, which for this port
        is the tkinter frame a control was placed in, and not the GUI window itself — so both are
        hooked. Without this an UpDown's arrows would move the value with no control event, which
        AutoIt's scripts do see.
        """

        handles = {window.handle}
        if window.widget_id:
            handles.add(window.widget_id)
        hooked_any = False
        for handle in handles:
            if handle in self._hooked_windows:
                hooked_any = True
                continue
            if native.hook_messages(handle, self._dispatch_message):
                self._hooked_windows.add(handle)
                hooked_any = True
        return hooked_any

    def GUIGetCursorInfo(self, winhandle: int | None = None) -> list[int]:
        """Return [x, y, primary down, secondary down, hovered control ID]."""

        window = self._resolve_window(winhandle)
        mouse_x, mouse_y = self._mouse_position(window.handle)
        hovered = self._hovered_control(window, mouse_x, mouse_y)
        return [mouse_x, mouse_y, self._primary_down, self._secondary_down, hovered]

    def _hovered_control(self, window: _window, mouse_x: int, mouse_y: int) -> int:
        """Return the control ID under a client-area point, or 0."""

        if not window.visible:
            return 0
        widget = window.widget.winfo_containing(
            window.widget.winfo_rootx() + mouse_x, window.widget.winfo_rooty() + mouse_y
        )
        if widget is None:
            return 0
        while widget is not None:
            control_id = self._controls_by_widget.get(str(widget))
            if control_id is not None:
                control = self._controls[control_id]
                # "ListViewItem or TreeViewItem controlID will never be returned, only the
                # parent Listview or TreeView control ID is" (GUIGetCursorInfo.htm).
                if control.kind in ("ListViewItem", "TreeViewItem") and control.parent:
                    return control.parent
                return control_id
            widget = getattr(widget, "master", None)
        return 0

    def GUIGetMsg(self, advanced: int = 0) -> Any:
        """Poll the GUI for events; returns a control ID, a system event, or 0.

        With ``advanced`` set the return is the array the reference documents:
        ``[event, winhandle, ctrlhandle, mouse x, mouse y]``. In OnEvent mode the return is
        always 0 and ``error`` is set to 1, exactly as documented.
        """

        if self._options["GUIOnEventMode"] == 1:
            self.error = 1
            return 0
        self._pump()
        if not self._messages:
            # "This function automatically idles the CPU when required so that it can be
            # safely used in tight loops without hogging all the CPU" (GUIGetMsg.htm).
            time.sleep(_IDLE_SECONDS)
            self._pump()
        if advanced:
            if not self._messages:
                return [GUI_EVENT_NONE, 0, 0, 0, 0]
            event, window, control_handle, mouse_x, mouse_y = self._messages.popleft()
            return [event, window, control_handle, mouse_x, mouse_y]
        if not self._messages:
            return GUI_EVENT_NONE
        event, _window_handle, _control_handle, _mouse_x, _mouse_y = self._messages.popleft()
        return event

    def GUIDelete(self, winhandle: int | None = None) -> int:
        """Delete a GUI window and all the controls it contains."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        handle = window.handle
        # A hooked window's procedure must be restored before its window goes away.
        if handle in self._hooked_windows:
            native.unhook_messages(handle)
            self._hooked_windows.discard(handle)
        for control_id in [
            control.control_id for control in self._controls.values() if control.window == handle
        ]:
            control = self._controls[control_id]
            # A control's own tooltip window goes with the window, as AutoIt's does.
            if control.tooltip:
                native.destroy_window(control.tooltip)
            del self._controls[control_id]
        window.widget.destroy()
        del self._windows[handle]
        self._messages = deque(
            message for message in self._messages if message[1] != handle
        )
        if self._current_window == handle:
            self._current_window = next(iter(self._windows), None)
        if self._last_control is not None and self._last_control not in self._controls:
            self._last_control = next(reversed(self._controls), None)
        return 1

    def GUISwitch(self, winhandle: int, tabitemID: int | None = None) -> int:
        """Make a window current for the GUI functions; returns the previous handle."""

        if winhandle not in self._windows:
            return 0
        previous = self._current_window or 0
        self._current_window = winhandle
        window = self._windows[winhandle]
        window.tab_frame = None
        window.tab_item = None
        if tabitemID is not None:
            control = self._controls.get(tabitemID)
            if control is not None and control.kind == "TabItem":
                window.tab_frame = control.widget
                window.tab_item = tabitemID
        return previous

    def GUIStartGroup(self, winhandle: int | None = None) -> int:
        """Start a new control group; the next Radio controls form one group."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.radio_variable = None
        return 1

    def GUISetOnEvent(
        self, specialID: int, function: Any, winhandle: int | None = None
    ) -> int:
        """Register a function for a system event of a window (OnEvent mode only)."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        if function == "":
            window.on_events.pop(specialID, None)
            return 1
        if not callable(function):
            raise TypeError(
                "GUISetOnEvent takes a Python callable: AutoIt passes the *name* of an "
                "AutoIt function as a string (GUISetOnEvent.htm), which does not name a "
                "Python object. Pass \"\" to unregister."
            )
        window.on_events[specialID] = function
        return 1

    def GUICtrlSetOnEvent(self, controlID: int, function: Any) -> int:
        """Define the function called when a control is clicked (OnEvent mode only)."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if function == "":
            # "If the function is an empty string "" the previous user-defined is disabled."
            control.on_event = None
            return 1
        if not callable(function):
            raise TypeError(
                "GUICtrlSetOnEvent takes a Python callable: AutoIt passes the *name* of an "
                "AutoIt function as a string (GUICtrlSetOnEvent.htm), which does not name a "
                "Python object. Pass \"\" to unregister."
            )
        control.on_event = function
        return 1

    # ---------------------------------------------------------------------------------
    # Control creation
    # ---------------------------------------------------------------------------------

    def _create_widget_control(
        self,
        window: _window,
        kind: str,
        factory: Callable[[Any], Any],
        left: int,
        top: int,
        width: int | None,
        height: int | None,
        style: int,
        ex_style: int,
        autofit: bool = False,
        text: str = "",
        inner: Callable[[Any], Any] | None = None,
    ) -> _control:
        """Create a widget-backed control at the position and size AutoIt computes.

        ``inner`` names the widget inside the created one that carries the control's content, for
        the kinds whose widget is a frame around it (a List and an Edit, each with its scrollbar).
        It is read here, before the control's own events are bound and its defaults applied, so
        those reach the widget the user acts on rather than the frame (``_content_widget``).
        """

        parent = self._parent_widget(window)
        widget = factory(parent)
        if text:
            widget.configure(text=text)
        resolved_left, resolved_top, resolved_width, resolved_height = self._allocate_position(
            window, left, top, width, height, kind
        )
        control = self._register_control(kind, window, widget, style, ex_style)
        if inner is not None:
            control.value = inner(widget)
        control.text = text
        if autofit and (width is None or height is None):
            fit_width, fit_height = self._autofit(widget)
            if width is None:
                resolved_width = fit_width
            if height is None:
                resolved_height = fit_height
        self._place(window, control, resolved_left, resolved_top, resolved_width, resolved_height)
        self._apply_defaults(window, control)
        self._bind_control_events(control)
        return control

    def GUICtrlCreateLabel(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a static Label control."""

        window = self._resolve_window(self._current_window)
        options = styles.label_options(0 if style == -1 else style)
        control = self._create_widget_control(
            window,
            "Label",
            lambda parent: tkinter.Label(parent, anchor="w", **options),
            left,
            top,
            width,
            height,
            style,
            exStyle,
            autofit=True,
            text=text,
        )
        return control.control_id

    def GUICtrlCreateButton(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Button control."""

        window = self._resolve_window(self._current_window)
        options = styles.button_options(0 if style == -1 else style)
        control = self._create_widget_control(
            window,
            "Button",
            lambda parent: tkinter.Button(parent, **options),
            left,
            top,
            width,
            height,
            style,
            exStyle,
            autofit=True,
            text=text,
        )
        return control.control_id

    def GUICtrlCreateInput(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create an Input (single-line) control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.entry_options(resolved_style)

        def factory(parent: Any) -> Any:
            widget = tkinter.Entry(parent, **options)
            widget.insert(0, text)
            if resolved_style & ES_NUMBER_OR_CASE:
                widget.configure(validate="key")
                widget.configure(
                    validatecommand=(
                        widget.register(lambda proposed: _valid_input(proposed, resolved_style)),
                        "%P",
                    )
                )
            return widget

        control = self._create_widget_control(
            window, "Input", factory, left, top, width, height, style, exStyle
        )
        control.text = text
        return control.control_id

    def GUICtrlCreateEdit(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create an Edit (multi-line) control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.text_options(resolved_style)
        created: dict[str, Any] = {}

        def factory(parent: Any) -> Any:
            frame = tkinter.Frame(parent)
            text_widget = tkinter.Text(frame, **options)
            scrollbar = tkinter.Scrollbar(frame, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            text_widget.pack(side="left", fill="both", expand=True)
            text_widget.insert("1.0", text)
            created["text"] = text_widget
            return frame

        control = self._create_widget_control(
            window, "Edit", factory, left, top, width, height, style, exStyle,
            inner=lambda _frame: created["text"],
        )
        control.text = text
        return control.control_id

    def GUICtrlCreateCheckbox(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Checkbox control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.checkbox_options(resolved_style)
        options.pop("_auto_toggle", None)
        created: dict[str, Any] = {}

        def factory(parent: Any) -> Any:
            variable = tkinter.IntVar(master=window.widget, value=GUI_UNCHECKED)
            created["variable"] = variable
            return tkinter.Checkbutton(
                parent,
                text=text,
                variable=variable,
                onvalue=GUI_CHECKED,
                offvalue=GUI_UNCHECKED,
                **options,
            )

        control = self._create_widget_control(
            window, "Checkbox", factory, left, top, width, height, style, exStyle, autofit=True
        )
        control.text = text
        control.value = created["variable"]
        return control.control_id

    def GUICtrlCreateRadio(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Radio control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.radio_options(resolved_style)
        if window.radio_variable is None:
            window.radio_variable = tkinter.IntVar(master=window.widget, value=0)
        variable = window.radio_variable

        def factory(parent: Any) -> Any:
            return tkinter.Radiobutton(parent, text=text, variable=variable, **options)

        control = self._create_widget_control(
            window, "Radio", factory, left, top, width, height, style, exStyle, autofit=True
        )
        control.text = text
        control.value = variable
        control.states = control.control_id
        return control.control_id

    def GUICtrlCreateCombo(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a ComboBox control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.combo_options(resolved_style)

        def factory(parent: Any) -> Any:
            widget = ttk.Combobox(parent, **options)
            if text:
                widget.set(text)
            return widget

        control = self._create_widget_control(
            window, "Combo", factory, left, top, width, height, style, exStyle
        )
        control.text = text
        return control.control_id

    def GUICtrlCreateList(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a List control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.list_options(resolved_style)
        created: dict[str, Any] = {}

        def factory(parent: Any) -> Any:
            frame = tkinter.Frame(parent)
            listbox = tkinter.Listbox(frame, **options)
            scrollbar = tkinter.Scrollbar(frame, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            listbox.pack(side="left", fill="both", expand=True)
            if text:
                listbox.insert("end", text)
            created["listbox"] = listbox
            return frame

        control = self._create_widget_control(
            window, "List", factory, left, top, width, height, style, exStyle,
            inner=lambda _frame: created["listbox"],
        )
        return control.control_id

    def GUICtrlCreateListView(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a ListView control (a ttk.Treeview in report mode).

        With ``$LVS_EX_CHECKBOXES`` the control gains the check column AutoIt's style asks for,
        which the port draws as a narrow first column holding a check mark: the item's own
        values stay exactly what ``GUICtrlRead`` returns.
        """

        window = self._resolve_window(self._current_window)
        columns = _split_items(text, self._options["GUIDataSeparatorChar"]) if text else []
        resolved_ex_style = 0 if exStyle == -1 else exStyle
        checkboxes = bool(resolved_ex_style & LVS_EX_CHECKBOXES)

        def factory(parent: Any) -> Any:
            widget = ttk.Treeview(
                parent,
                columns=[f"c{index}" for index in range(len(columns))],
                show="tree headings" if checkboxes else "headings",
            )
            for index, column in enumerate(columns):
                widget.heading(f"c{index}", text=column)
                widget.column(f"c{index}", width=max(20, len(column) * 8))
            if checkboxes:
                widget.heading("#0", text="")
                widget.column("#0", width=24, stretch=False)
            return widget

        control = self._create_widget_control(
            window, "ListView", factory, left, top, width, height, style, exStyle
        )
        control.columns = columns
        control.states = GUI_SHOW | GUI_ENABLE
        control.checkboxes = checkboxes
        return control.control_id

    def GUICtrlCreateListViewItem(self, text: str, listviewID: int) -> int:
        """Create a ListView item inside an existing ListView control."""

        parent_control = self._resolve_control(listviewID)
        if parent_control.kind != "ListView":
            return 0
        separator = self._options["GUIDataSeparatorChar"]
        subitems = text.split(separator)
        widget = parent_control.widget
        values = _pad_columns(subitems, len(parent_control.columns))
        item = widget.insert("", "end", values=values)
        control = self._register_control(
            "ListViewItem", self._windows[parent_control.window], None, -1, -1
        )
        control.parent = parent_control.control_id
        control.item = item
        control.subitems = subitems
        control.text = text
        control.value = widget
        control.states = GUI_UNCHECKED
        if parent_control.checkboxes:
            widget.item(item, text=_check_mark(GUI_UNCHECKED))
        return control.control_id

    def GUICtrlCreateTreeView(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a TreeView control."""

        window = self._resolve_window(self._current_window)

        def factory(parent: Any) -> Any:
            return ttk.Treeview(parent, show="tree headings", columns=("c0",))

        control = self._create_widget_control(
            window, "TreeView", factory, left, top, width, height, style, exStyle
        )
        control.widget.column("#0", width=200)
        control.widget.heading("#0", text="")
        return control.control_id

    def GUICtrlCreateTreeViewItem(self, text: str, treeviewID: int) -> int:
        """Create a TreeView item, under the tree or under another item."""

        parent_control = self._resolve_control(treeviewID)
        if parent_control.kind == "TreeViewItem":
            tree_control = self._controls[parent_control.parent or 0]
            parent_item = parent_control.item
        elif parent_control.kind == "TreeView":
            tree_control = parent_control
            parent_item = ""
        else:
            return 0
        item = tree_control.widget.insert(parent_item, "end", text=text)
        control = self._register_control("TreeViewItem", self._windows[tree_control.window],
                                         None, -1, -1)
        control.parent = tree_control.control_id
        control.item = item
        control.text = text
        control.value = tree_control.widget
        return control.control_id

    def GUICtrlCreatePic(
        self,
        filename: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Picture control from an image file.

        The file may be any format Windows reads (tkinter alone reads PNG and GIF, so BMP, JPG,
        GIF and TIF come from GDI+ — see ``_load_image``).

        Its size is the reference's: a width and height the caller gives are used, **0 for either
        means the file's own size** ("To set the picture control to the same size as the file
        content set width and height to 0"), and omitting them takes the previously used size like
        every other control. Measured from the interpreter (probe_autoit_pic_out.txt): a Pic made
        from a 255x40 JPG with no width or height was 40x30, the size the control before it had
        used, and with width and height 0 it was 255x40.
        """

        window = self._resolve_window(self._current_window)
        options = styles.label_options(0 if style == -1 else style)
        image = self._load_image(filename)
        if width == 0 or height == 0:
            width = image.width()
            height = image.height()

        def factory(parent: Any) -> Any:
            return tkinter.Label(parent, image=image, **options)

        control = self._create_widget_control(
            window, "Pic", factory, left, top, width, height, style, exStyle
        )
        control.image = image
        return control.control_id

    def _load_image(self, filename: str) -> Any:
        """Load an image, with tkinter where it can and Windows' own decoder where it cannot.

        The image is created in *this* GUI's interpreter. Without a master tkinter attaches it to
        ``tkinter._default_root``, which is whichever window was created last — so with a second GUI
        in the process (the module-level one, for instance) a picture would be an image of another
        interpreter and the widget taking it would fail (measured: the suite's picture test passes
        alone and raised once a later test had made the module-level GUI the default root).

        tkinter's ``PhotoImage`` reads PNG and GIF; the reference's Pic control "supports BMP, JPG,
        GIF and TIF images" (GUICtrlCreatePic.htm). For anything tkinter refuses, the file is read
        with GDI+ — the same decoder Windows and AutoIt use — and the pixels are handed to Tk as a
        PPM, which is the one raw format Tk's photo image takes.
        """

        try:
            image = tkinter.PhotoImage(master=self._ensure_root(), file=filename)
        except tkinter.TclError as error:
            pixels = native.load_image_pixels(filename)
            if pixels is None:
                raise NotImplementedError(
                    f"picture {filename!r}: tkinter's PhotoImage reads PNG and GIF only, and "
                    f"Windows' own decoder could not read it either (GUICtrlCreatePic.htm lists "
                    f"BMP, JPG, GIF and TIF); Tk reported {error}"
                ) from error
            width, height, rows = pixels
            ppm = b"P6\n%d %d\n255\n" % (width, height) + rows
            image = tkinter.PhotoImage(master=self._ensure_root(), data=ppm)
        self._images.append(image)
        return image

    def GUICtrlCreateGraphic(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int | None = None,
    ) -> int:
        """Create a Graphic control; draw into it with :meth:`GUICtrlSetGraphic`."""

        window = self._resolve_window(self._current_window)
        resolved_width = _DEFAULT_GRAPHIC_SIZE if width is None else width
        resolved_height = _DEFAULT_GRAPHIC_SIZE if height is None else height
        canvas = tkinter.Canvas(self._parent_widget(window), highlightthickness=0)
        canvas.configure(bg=window.widget.cget("bg"))
        control = self._register_control("Graphic", window, canvas, -1 if style is None else style,
                                         -1)
        resolved_left, resolved_top, _, _ = self._allocate_position(
            window, left, top, resolved_width, resolved_height
        )
        self._place(window, control, resolved_left, resolved_top, resolved_width, resolved_height)
        window.graphic_state[control.control_id] = {
            "x": 0,
            "y": 0,
            "color": "#000000",
            "bk_color": None,
            "pen_size": 1,
            "points": [],
        }
        self._bind_control_events(control)
        return control.control_id

    def GUICtrlCreateProgress(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Progress control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.progress_options(resolved_style)

        def factory(parent: Any) -> Any:
            return ttk.Progressbar(parent, maximum=100, **options)

        control = self._create_widget_control(
            window, "Progress", factory, left, top, width, height, style, exStyle
        )
        control.value = 0
        if resolved_style & PBS_MARQUEE:
            control.widget.start(50)
        return control.control_id

    def GUICtrlCreateSlider(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Slider control."""

        window = self._resolve_window(self._current_window)
        resolved_style = 0 if style == -1 else style
        options = styles.slider_options(resolved_style)

        def factory(parent: Any) -> Any:
            return tkinter.Scale(parent, from_=0, to=100, **options)

        control = self._create_widget_control(
            window, "Slider", factory, left, top, width, height, style, exStyle
        )
        control.value = 0
        return control.control_id

    def GUICtrlCreateGroup(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Group control (the thin line around a set of controls)."""

        window = self._resolve_window(self._current_window)

        def factory(parent: Any) -> Any:
            return tkinter.LabelFrame(parent, text=text)

        control = self._create_widget_control(
            window, "Group", factory, left, top, width, height, style, exStyle
        )
        control.text = text
        # "Only one Radio button within a Group can be selected at once" and "If you want to
        # have multiple groups without the visible line then you must use GUIStartGroup()":
        # a group is also a radio-group boundary.
        window.radio_variable = None
        return control.control_id

    def GUICtrlCreateTab(
        self,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a Tab control; add TabItems to it and close with GUICtrlCreateTabItem("")."""

        window = self._resolve_window(self._current_window)

        def factory(parent: Any) -> Any:
            return ttk.Notebook(parent)

        control = self._create_widget_control(
            window, "Tab", factory, left, top, width, height, style, exStyle
        )
        return control.control_id

    def GUICtrlCreateTabItem(self, text: str) -> int:
        """Create a TabItem; an empty text closes the tab structure."""

        window = self._resolve_window(self._current_window)
        tabs = [item for item in self._controls.values() if item.kind == "Tab"]
        if not tabs:
            return 0
        tab_control = tabs[-1]
        if text == "":
            window.tab_frame = None
            window.tab_item = None
            return 0
        frame = ttk.Frame(tab_control.widget)
        tab_control.widget.add(frame, text=text)
        control = self._register_control("TabItem", window, frame, -1, -1)
        control.text = text
        control.parent = tab_control.control_id
        control.value = tab_control
        window.tab_frame = frame
        window.tab_item = control.control_id
        return control.control_id

    def GUICtrlCreateMenu(self, submenutext: str, menuID: int = -1, menuentry: int = -1) -> int:
        """Create a menu (top level when ``menuID`` is -1) or a submenu inside one."""

        window = self._resolve_window(self._current_window)
        menu = tkinter.Menu(window.widget, tearoff=0)
        control = self._register_control("Menu", window, menu, -1, -1)
        control.text = submenutext
        control.value = menu
        if menuID == -1:
            if window.menu is None:
                window.menu = tkinter.Menu(window.widget)
                window.widget.configure(menu=window.menu)
            position = len(window.menu_entries) if menuentry < 0 else menuentry
            window.menu.insert_cascade(position, label=submenutext, menu=menu)
            window.menu_entries.insert(position, control.control_id)
            return control.control_id
        parent_menu = self._resolve_control(menuID)
        if parent_menu.kind != "Menu":
            return 0
        control.parent = parent_menu.control_id
        position = len(parent_menu.entries) if menuentry < 0 else menuentry
        parent_menu.value.insert_cascade(position, label=submenutext, menu=menu)
        parent_menu.entries.insert(position, control.control_id)
        return control.control_id

    def GUICtrlCreateMenuItem(
        self, text: str, menuID: int, menuentry: int = -1, menuradioitem: int = 0
    ) -> int:
        """Create a menu item (an empty text makes a separator)."""

        window = self._resolve_window(self._current_window)
        parent_menu = self._resolve_control(menuID)
        if parent_menu.kind not in ("Menu", "ContextMenu"):
            return 0
        menu = parent_menu.value
        control = self._register_control("MenuItem", window, None, -1, -1)
        control.parent = parent_menu.control_id
        control.text = text
        position = len(parent_menu.entries) if menuentry < 0 else menuentry
        if text == "":
            menu.insert_separator(position)
        elif menuradioitem:
            variable = tkinter.IntVar(master=window.widget, value=0)
            menu.insert_radiobutton(
                position,
                label=text,
                variable=variable,
                value=control.control_id,
                command=lambda cid=control.control_id: self._control_event(cid),
            )
            control.value = variable
        else:
            # AutoIt's ordinary menu item can still be checked with GUICtrlSetState(), which
            # a tkinter checkbutton entry is the entry type that can show.
            variable = tkinter.IntVar(master=window.widget, value=0)
            menu.insert_checkbutton(
                position,
                label=text,
                variable=variable,
                command=lambda cid=control.control_id: self._control_event(cid),
            )
            control.value = variable
        parent_menu.entries.insert(position, control.control_id)
        return control.control_id

    def GUICtrlCreateContextMenu(self, controlID: int | None = None) -> int:
        """Create a context menu for a control, or (-1/omitted) for the whole window."""

        window = self._resolve_window(self._current_window)
        menu = tkinter.Menu(window.widget, tearoff=0)
        control = self._register_control("ContextMenu", window, None, -1, -1)
        control.value = menu
        if controlID is None or controlID == -1:
            target = window.widget
            window.context_menus[-1] = menu
        else:
            target_control = self._resolve_control(controlID)
            if target_control.widget is None:
                return 0
            if target_control.kind in ("Edit", "Input"):
                # "You can't create context menus for controls that already have system
                # context menus, i.e. edit or input controls" (GUICtrlCreateContextMenu.htm).
                return 0
            target = target_control.widget
            window.context_menus[target_control.control_id] = menu
        target.bind("<Button-3>", lambda event, m=menu: self._show_context_menu(m, event))
        return control.control_id

    def _show_context_menu(self, menu: tkinter.Menu, event: Any) -> None:
        """Pop up a context menu at the pointer."""

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _create_native_control(
        self,
        window: _window,
        kind: str,
        class_name: str,
        text: str,
        style: int,
        ex_style: int,
        left: int,
        top: int,
        width: int | None,
        height: int | None,
    ) -> _control:
        """Create one of the Win32 control classes tkinter has no widget for.

        These are the classes AutoIt itself creates — ``SysDateTimePick32``, ``SysMonthCal32``,
        ``SysAnimate32`` and ``Static`` — as children of the tkinter frame the control would
        have been placed in, so Windows keeps them positioned inside that frame.

        A native control's size when the caller omits it is the same rule as any other control's:
        the previously used size, or the kind's own default (``_DEFAULT_CONTROL_SIZE``). The kinds
        here had constants of their own, taken from readings that turn out to be *inherited* sizes —
        probe_autoit_parity2 created them after other controls, and probe_autoit_default_size shows
        that is exactly what "previously used" means.
        """

        resolved_left, resolved_top, resolved_width, resolved_height = self._allocate_position(
            window, left, top, width, height, kind
        )
        parent = self._parent_widget(window)
        handle = native.create_control(
            class_name,
            text,
            style,
            ex_style,
            int(parent.winfo_id()),
            resolved_left,
            resolved_top,
            resolved_width,
            resolved_height,
        )
        control = self._register_control(kind, window, None, style, ex_style)
        control.native = handle
        control.text = text
        self._place(window, control, resolved_left, resolved_top, resolved_width, resolved_height)
        native.apply_default_font(handle)
        # A native control reports itself through WM_NOTIFY, so the window and the frame it was
        # placed in are hooked to turn those notifications into the control events AutoIt's
        # scripts see.
        self._hook_window(window)
        return control

    def GUICtrlCreateDate(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a date control, which is the Win32 ``SysDateTimePick32`` class.

        The text is "the preselected date (always as "yyyy/mm/dd")", and the default style is
        ``$DTS_LONGDATEFORMAT`` with ``$WS_TABSTOP`` forced.
        """

        window = self._resolve_window(self._current_window)
        resolved_style = DTS_LONGDATEFORMAT if style == -1 else style
        control = self._create_native_control(
            window,
            "Date",
            "SysDateTimePick32",
            "",
            WS_CHILD | WS_VISIBLE | resolved_style | WS_TABSTOP,
            0 if exStyle == -1 else exStyle,
            left,
            top,
            width,
            height,
        )
        if text:
            self.GUICtrlSetData(control.control_id, text)
        return control.control_id

    def GUICtrlCreateMonthCal(
        self,
        text: str,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create a month calendar control, the Win32 ``SysMonthCal32`` class."""

        window = self._resolve_window(self._current_window)
        control = self._create_native_control(
            window,
            "MonthCal",
            "SysMonthCal32",
            "",
            WS_CHILD | WS_VISIBLE | (0 if style == -1 else style) | WS_TABSTOP,
            0 if exStyle == -1 else exStyle,
            left,
            top,
            width,
            height,
        )
        if text:
            self.GUICtrlSetData(control.control_id, text)
        return control.control_id

    def GUICtrlCreateAvi(
        self,
        filename: str,
        subfileid: int,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create an AVI control, the Win32 ``SysAnimate32`` class.

        "$ACS_TRANSPARENT is always used unless $ACS_NONTRANSPARENT is specified", and the
        default style is ``$ACS_TRANSPARENT``.
        """

        window = self._resolve_window(self._current_window)
        resolved_style = ACS_TRANSPARENT if style == -1 else style
        if not resolved_style & ACS_NONTRANSPARENT:
            resolved_style |= ACS_TRANSPARENT
        control = self._create_native_control(
            window,
            "Avi",
            "SysAnimate32",
            "",
            WS_CHILD | WS_VISIBLE | resolved_style,
            0 if exStyle == -1 else exStyle,
            left,
            top,
            width,
            height,
        )
        control.value = filename
        if filename:
            native.avi_open(control.native, filename)
        return control.control_id

    def GUICtrlCreateIcon(
        self,
        filename: str,
        iconName: int,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
        style: int = -1,
        exStyle: int = -1,
    ) -> int:
        """Create an icon control, which is a Win32 ``Static`` with ``$SS_ICON``.

        "width [optional]: The width of the control (default is 32)" and the same for the
        height; ``$WS_TABSTOP`` and ``$SS_ICON`` are forced.
        """

        window = self._resolve_window(self._current_window)
        control = self._create_native_control(
            window,
            "Icon",
            "Static",
            "",
            WS_CHILD | WS_VISIBLE | SS_ICON | WS_TABSTOP | (0 if style == -1 else style),
            0 if exStyle == -1 else exStyle,
            left,
            top,
            width,
            height,
        )
        control.value = filename
        if filename:
            icon = native.load_icon(filename, iconName)
            if icon:
                control.image = icon
                native.icon_set(control.native, icon)
        return control.control_id

    def GUICtrlCreateObj(
        self,
        ObjectVar: Any,
        left: int,
        top: int,
        width: int | None = None,
        height: int | None = None,
    ) -> int:
        """Create an ActiveX control in the GUI, embedding an object variable.

        "A variable pointing to a previously opened object" is the parameter, and the page's own
        remarks fix the rest: "Not every control can be embedded. They must at least support an
        'IDispatch' interface"; "Failure: 0"; "The GUI functions GUICtrlRead() and GUICtrlSet have
        no effect on this control. The object can only be controlled using 'methods' or
        'properties' on the $ObjectVar" (GUICtrlCreateObj.htm).

        Measured from the interpreter, because the page leaves these unsaid
        (tests/autoit_reference/probe_autoit_obj*_out.txt):

        * the object is hosted in a child window of the GUI whose class is the control's own
          in-place window -- "Shell Embedding" for ``Shell.Explorer.2``, style
          ``$WS_CHILD|$WS_VISIBLE|$WS_TABSTOP``, exStyle ``$WS_EX_CONTROLPARENT`` -- created with
          the control and hidden until the window is shown;
        * ``GUICtrlGetHandle`` returns 0 for it, as that page's own list says;
        * an omitted width and height are **8x8**, and that 8x8 then stands as the previously used
          size for the next control, exactly like any other control's default;
        * an object that is not an embeddable control (``Scripting.Dictionary``) makes the function
          return 0 and leaves no control behind, while ``ObjCreate`` itself succeeded;
        * ``GUICtrlSetData`` and ``GUICtrlSetStyle`` both return 1 and change nothing;
        * its default resizing keeps its size and scales its position, which is ``$GUI_DOCKSIZE``
          (``_DEFAULT_DOCKING``), and ``GUICtrlDelete`` takes the host window with it.
        """

        window = self._resolve_window(self._current_window)
        if not isinstance(ObjectVar, objects.ComObject):
            # "Failure: 0" -- AutoIt takes an object variable, and anything else is not one.
            return 0
        if not native.object_supports_ole(ObjectVar.dispatch):
            # An object the interpreter refuses to embed, and refuses the same way: an object
            # variable works (ObjCreate succeeded), the function returns 0, and no control is
            # left behind.
            return 0
        resolved_left, resolved_top, resolved_width, resolved_height = self._allocate_position(
            window, left, top, width, height, "Obj"
        )
        frame = tkinter.Frame(self._parent_widget(window), highlightthickness=0)
        frame.place(x=resolved_left, y=resolved_top, width=resolved_width, height=resolved_height)
        frame.update_idletasks()
        hresult, owner = native.attach_object_host(int(frame.winfo_id()), ObjectVar.dispatch)
        if hresult != 0:
            # The object cannot be hosted. The interpreter returns 0 for exactly this case
            # (Scripting.Dictionary), and no control of it is left behind, so nothing is
            # registered here either.
            frame.destroy()
            return 0
        control = self._register_control("Obj", window, frame, -1, -1)
        control.value = owner
        self._place(window, control, resolved_left, resolved_top, resolved_width, resolved_height)
        self._bind_control_events(control)
        return control.control_id


    def GUICtrlCreateDummy(self) -> int:
        """Create a Dummy control, which receives messages from GUICtrlSendToDummy()."""

        window = self._resolve_window(self._current_window)
        widget = tkinter.Frame(window.widget, width=1, height=1)
        control = self._register_control("Dummy", window, widget, -1, -1)
        control.value = 0
        return control.control_id

    def GUICtrlCreateUpdown(self, inputcontrolID: int, style: int = -1) -> int:
        """Create an UpDown control on an Input control.

        The control is the Win32 ``msctls_updown32`` class, which is what AutoIt creates, drawn
        at its buddy input's right edge and attached with ``UDM_SETBUDDY`` so that
        ``$UDS_SETBUDDYINT`` writes the position into that input. The reference's page gives the
        default style as ``$GUI_SS_DEFAULT_UPDOWN`` with ``$UDS_SETBUDDYINT`` and
        ``$UDS_ALIGNRIGHT`` forced when no alignment is given; measured from the interpreter, the
        default places the arrows at the input's right edge, 18 pixels wide and as tall as the
        input, overlapping it by two pixels.
        """

        window = self._resolve_window(self._current_window)
        input_control = self._resolve_control(inputcontrolID)
        if input_control.kind != "Input" or input_control.widget is None:
            return 0
        resolved_style = UDS_ALIGNRIGHT | UDS_SETBUDDYINT if style == -1 else style
        if not resolved_style & (UDS_ALIGNRIGHT | UDS_ALIGNLEFT):
            resolved_style |= UDS_ALIGNRIGHT | UDS_SETBUDDYINT
        buddy = int(input_control.widget.winfo_id())
        left, top, width, height = input_control.pos or (0, 0, 0, _UPDOWN_DEFAULT_HEIGHT)
        parent = self._parent_widget(window)
        handle = native.create_control(
            native.UPDOWN_CLASS,
            "",
            WS_CHILD | WS_VISIBLE | resolved_style,
            0,
            int(parent.winfo_id()),
            left + width - _UPDOWN_OVERLAP,
            top,
            _UPDOWN_ARROW_WIDTH,
            height,
        )
        control = self._register_control("Updown", window, None, style, -1)
        control.native = handle
        control.parent = input_control.control_id
        native.updown_set_buddy(handle, buddy)
        native.apply_default_font(handle)
        # Placed last, and deliberately: an UpDown carries $UDS_ALIGNRIGHT, so it aligns itself to
        # its buddy's rectangle both when it is created and when UDM_SETBUDDY is sent — and the
        # buddy is a tkinter Entry, whose window is still 1x1 while the GUI is hidden, so the
        # arrows would end up a speck at the parent's origin (measured: the port's record said
        # 18x22 at the input's edge while the window was 1x1 and the pointer could not reach it).
        # Placing it here also gives the control its docking base, as every other native control
        # gets when it is created.
        self._place(
            window,
            control,
            left + width - _UPDOWN_OVERLAP,
            top,
            _UPDOWN_ARROW_WIDTH,
            height,
        )
        # An UpDown reports itself through WM_NOTIFY, so the window's messages are hooked to turn
        # that notification into the control event AutoIt's scripts see.
        self._hook_window(window)
        return control.control_id

    # ---------------------------------------------------------------------------------
    # Control update functions
    # ---------------------------------------------------------------------------------

    def GUICtrlRead(self, controlID: int, advanced: int = GUI_READ_DEFAULT) -> Any:
        """Read a control's state or data, as the reference's table specifies."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        kind = control.kind
        extended = advanced == GUI_READ_EXTENDED
        if kind in ("Checkbox", "Radio"):
            state = _variable_state(control)
            if extended:
                return control.text
            return state
        if kind in ("Combo", "List"):
            return _selected_value(control)
        if kind == "Input":
            return self._input_text(control)
        if kind == "Edit":
            return control.value.get("1.0", "end-1c")
        if kind in ("Button", "Label", "Group", "Pic", "Graphic"):
            return control.widget.cget("text") if _supports(control.widget, "text") else ""
        if kind == "Obj":
            # "GUICtrlRead() ... have no effect on this control" (GUICtrlCreateObj.htm); the
            # interpreter read an object control as "".
            return ""
        if kind == "Progress":
            return int(float(control.widget.cget("value")))
        if kind == "Slider":
            return int(float(control.widget.get()))
        if kind == "Dummy":
            return control.value
        if kind == "Tab":
            tabs = control.widget.tabs()
            if not tabs:
                return 0
            index = list(tabs).index(control.widget.select())
            if extended:
                for item in self._controls.values():
                    if item.parent == control.control_id and item.widget == control.widget.nametowidget(
                        tabs[index]
                    ):
                        return item.control_id
            return index
        if kind == "TabItem":
            return ""
        if kind == "TreeView":
            selection = control.widget.selection()
            if not selection:
                return 0
            item_control = self._item_control(control, selection[0])
            if extended:
                return control.widget.item(selection[0], "text")
            return item_control.control_id if item_control else 0
        if kind == "TreeViewItem":
            state = 0
            if control.item in control.value.selection():
                state |= GUI_FOCUS
            if control.value.item(control.item, "open"):
                state |= GUI_EXPAND
            if extended:
                return control.value.item(control.item, "text")
            return state
        if kind == "ListView":
            # "Control identifier (controlID) of the selected ListViewItem. 0 means no item
            # is selected" — the reference's advanced table lists no extra value for the
            # ListView itself.
            item_id = self._listview_selected_item(control)
            return item_id if item_id else 0
        if kind == "ListViewItem":
            values = control.value.item(control.item, "values")
            text = self._options["GUIDataSeparatorChar"].join(str(value) for value in values)
            text += self._options["GUIDataSeparatorChar"]
            if extended:
                # Measured from the interpreter: the advanced read returns the item's check
                # state ($GUI_CHECKED when checked, $GUI_UNCHECKED when not), while the default
                # read stays the item's text.
                return control.states & (GUI_CHECKED | GUI_UNCHECKED) or GUI_UNCHECKED
            return text
        if kind == "Updown":
            # Measured from the interpreter: GUICtrlRead() on an UpDown control returns an
            # empty string; the value lives in the buddy Input control it is attached to.
            return ""
        if kind == "Date":
            parts = native.date_get_parts(control.native)
            if parts is None:
                return ""
            # "The selected date in the format defined by the regional settings" — and the
            # control's own format style decides which regional format that is.
            return native.format_date(parts, _date_reads_long(control.style))
        if kind == "MonthCal":
            # A month calendar reads its date as "yyyy/mm/dd", the same shape GUICtrlSetData()
            # takes for it — measured from the interpreter, which read back exactly the date it
            # was given. The control's own selection answers when the user has clicked a day;
            # otherwise the port's record of the date does, because Windows has no message that
            # sets or returns a month calendar's selected date (see docs/AUTOIT_GUI.md).
            selected = native.monthcal_selected_parts(control.native)
            parts = selected if selected is not None else control.value
            if not isinstance(parts, tuple):
                return ""
            return f"{parts[0]:04d}/{parts[1]:02d}/{parts[2]:02d}"
        if kind in ("Avi", "Icon"):
            # Measured from the interpreter: both read as an empty string.
            return ""
        if kind in ("Menu", "MenuItem", "ContextMenu"):
            state = control.states
            if not state & (GUI_ENABLE | GUI_DISABLE):
                state |= GUI_ENABLE
            if not state & (GUI_CHECKED | GUI_UNCHECKED | GUI_INDETERMINATE):
                state |= GUI_UNCHECKED
            if extended:
                # "Menu, MenuItem | The text of the control." (GUICtrlRead.htm, advanced mode)
                return control.text
            return state
        return 0

    def _item_control(self, parent: _control, item: str) -> _control | None:
        """Return the control record of a tree/list item."""

        for control in self._controls.values():
            if control.parent == parent.control_id and control.item == item:
                return control
        return None

    def _listview_columns(self, item_control: _control) -> list[str]:
        """Return the column headings of the ListView an item belongs to."""

        parent = self._controls.get(item_control.parent or 0)
        return parent.columns if parent is not None else []

    def _input_text(self, control: _control) -> str:
        """Return an Input control's text.

        tkinter keeps an Entry's string in Tk, not in the window: measured, ``GetWindowTextW`` on a
        mapped ``TkChild`` entry answers with nothing while Tk holds "5". An UpDown attached to the
        input writes its position into that window through ``$UDS_SETBUDDYINT``, so the window is the
        newer text *only after the control has moved* — and the port records the position it last
        read, so it looks at the window exactly then and pushes what it finds into Tk (which is what
        the user then sees). Reading the window whenever the input had a buddy wiped the input's own
        text instead: the read synced Tk from an empty window.
        """

        widget = control.widget
        if widget is None:
            return ""
        updown = next(
            (
                item
                for item in self._controls.values()
                if item.parent == control.control_id and item.kind == "Updown" and item.native
            ),
            None,
        )
        if updown is None:
            return widget.get()
        position = native.updown_get_position(updown.native)
        if updown.synced_position == position:
            return widget.get()
        window_text = native.get_window_text(int(widget.winfo_id()))
        updown.synced_position = position
        if window_text and window_text != widget.get():
            widget.delete(0, "end")
            widget.insert(0, window_text)
            return window_text
        return widget.get()

    def GUICtrlSetData(self, controlID: int, data: Any = "", default: Any = "") -> int:
        """Modify a control's data, per the reference's per-control rules."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        kind = control.kind
        separator = self._options["GUIDataSeparatorChar"]
        text = str(data)
        if kind == "Obj":
            # "The GUI functions GUICtrlRead() and GUICtrlSet have no effect on this control. The
            # object can only be controlled using 'methods' or 'properties' on the $ObjectVar"
            # (GUICtrlCreateObj.htm). Measured: the interpreter returned 1 and changed nothing.
            return 1
        if kind in ("Combo", "List"):
            if text == "" or text.startswith(separator):
                _clear_items(control)
                text = text.lstrip(separator)
            if text:
                _add_items(control, _split_items(text, separator))
            if default != "":
                _select_value(control, str(default))
            return 1
        if kind == "ListViewItem":
            subitems = _update_subitems(control.subitems, text, separator)
            control.subitems = subitems
            control.text = text
            control.value.item(
                control.item, values=_pad_columns(subitems, len(self._listview_columns(control)))
            )
            return 1
        if kind == "ListView":
            # Measured from the interpreter: GUICtrlSetData() on a ListView replaces the column
            # headings with the separator-separated list and leaves the items alone. Fewer
            # headings than columns leaves the remaining headings as they were.
            headings = _split_items(text, separator)
            headings = headings[: len(control.columns)]
            for index, heading in enumerate(headings):
                control.widget.heading(f"c{index}", text=heading)
                control.columns[index] = heading
            return 1
        if kind == "TreeViewItem":
            control.text = text
            control.value.item(control.item, text=text)
            return 1
        if kind == "MenuItem":
            parent_menu = self._controls.get(control.parent or 0)
            if parent_menu is not None and parent_menu.value is not None:
                parent_menu.value.entryconfigure(
                    parent_menu.entries.index(control.control_id), label=text
                )
            control.text = text
            return 1
        if kind == "Menu":
            control.text = text
            window = self._windows[control.window]
            if control.parent is None:
                window.menu.entryconfigure(
                    window.menu_entries.index(control.control_id), label=text
                )
            else:
                parent_menu = self._controls.get(control.parent)
                if parent_menu is not None and parent_menu.value is not None:
                    parent_menu.value.entryconfigure(
                        parent_menu.entries.index(control.control_id), label=text
                    )
            return 1
        if kind == "TabItem":
            control.text = text
            if control.value is not None:
                control.value.widget.tab(control.widget, text=text)
            return 1
        if kind == "Progress":
            control.value = int(float(text))
            control.widget.configure(value=max(0, min(100, control.value)))
            return 1
        if kind == "Slider":
            control.value = int(float(text))
            control.widget.set(control.value)
            return 1
        if kind == "Date":
            # "Date : The date or time depending the style of the control and the regional
            # settings", and the control takes it as "yyyy/mm/dd".
            parts = _parse_autoit_date(text)
            if parts is None:
                return 0
            return 1 if native.date_set_parts(control.native, *parts) else 0
        if kind == "MonthCal":
            # "The "data" date format is "yyyy/mm/dd"." (GUICtrlSetData.htm, Monthcal remark)
            parts = _parse_autoit_date(text)
            if parts is None:
                return 0
            # The control is brought to that month so the date is in view; the date itself is
            # the port's record of it, which the control's own selection overrides once the user
            # clicks a day.
            native.monthcal_show_month(control.native, parts[0], parts[1])
            control.value = parts
            return 1
        if kind in ("Avi", "Icon"):
            # The reference's per-control list states nothing about these two.
            return 0
        if kind == "Dummy":
            control.value = data
            return 1
        if kind in ("Input", "Edit"):
            if default != "":
                _insert_at_caret(control, str(default))
                return 1
            _set_text(control, text)
            return 1
        if kind in ("Button", "Label", "Group", "Checkbox", "Radio"):
            control.text = text
            control.widget.configure(text=text)
            return 1
        if kind == "Updown":
            # Measured from the interpreter: GUICtrlSetData() on an UpDown returns -1 ("-1 in
            # case of invalid data") and changes nothing; its position is set by the control's
            # own UDM_SETPOS32, and the buddy Input is written by $UDS_SETBUDDYINT.
            return -1
        raise NotImplementedError(
            f"GUICtrlSetData on a {kind} control: the reference's per-control list "
            "(GUICtrlSetData.htm) does not state what 'data' changes for this type"
        )

    def GUICtrlSetState(self, controlID: int, state: int) -> int:
        """Change a control's state; state values can be summed, as the reference says."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        kind = control.kind
        widget = control.widget
        if kind == "ContextMenu":
            # "State of a 'contextmenu' control cannot be changed" (GUICtrlSetState.htm).
            return 0
        if kind in ("Menu", "MenuItem") and state & GUI_HIDE:
            # "State of a 'menu' or a 'menuitem' control cannot be hidden."
            return 0
        if kind == "Avi":
            # The reference's State table names three Avi states, and its include file gives
            # them the values a script actually passes: $GUI_AVISTOP (0), $GUI_AVISTART (1) and
            # $GUI_AVICLOSE (2). The table's own parentheses number them the other way round,
            # which is a discrepancy in the reference; the constants win, because they are what
            # a script sends. Measured: GUICtrlSetState($avi, $GUI_AVISTOP) returned 1.
            if state == GUI_AVICLOSE:
                native.avi_open(control.native, "")
                return 1
            if state == GUI_AVISTART:
                native.avi_play(control.native)
                return 1
            if state == GUI_AVISTOP:
                native.avi_stop(control.native)
                return 1
        changed = 0
        if state & GUI_CHECKED or state & GUI_UNCHECKED or state & GUI_INDETERMINATE:
            new_state = (
                GUI_INDETERMINATE if state & GUI_INDETERMINATE
                else GUI_CHECKED if state & GUI_CHECKED
                else GUI_UNCHECKED
            )
            if kind == "MenuItem":
                control.value.set(1 if new_state == GUI_CHECKED else 0)
            elif kind == "ListViewItem":
                # "State of a 'listviewitem' control can be changed if the associated
                # 'listview' control has been created with an extended style
                # $LVS_EX_CHECKBOXES": the state is always recorded, and the check column the
                # style asked for shows it.
                control.states = new_state
                parent = self._controls.get(control.parent or 0)
                if parent is not None and parent.checkboxes:
                    control.value.item(control.item, text=_check_mark(new_state))
            else:
                _set_control_state(control, new_state)
            control.states = (control.states & ~(GUI_CHECKED | GUI_UNCHECKED)) | new_state
            changed = 1
        if state & GUI_SHOW:
            if kind == "TabItem" and control.value is not None:
                control.value.widget.select(control.widget)
            elif widget is not None and kind != "Dummy":
                _set_visible(control, True)
            control.states = (control.states & ~GUI_HIDE) | GUI_SHOW
            changed = 1
        if state & GUI_HIDE:
            if widget is not None and kind != "Dummy":
                _set_visible(control, False)
            control.states = (control.states & ~GUI_SHOW) | GUI_HIDE
            changed = 1
        if state & GUI_ENABLE or state & GUI_DISABLE:
            enabled = bool(state & GUI_ENABLE)
            if kind == "MenuItem":
                parent_menu = self._controls.get(control.parent or 0)
                if parent_menu is not None and parent_menu.value is not None:
                    parent_menu.value.entryconfigure(
                        parent_menu.entries.index(control.control_id),
                        state="normal" if enabled else "disabled",
                    )
            elif widget is not None:
                _set_enabled(control, enabled)
            control.states = (control.states & ~(GUI_ENABLE | GUI_DISABLE)) | (
                GUI_ENABLE if enabled else GUI_DISABLE
            )
            changed = 1
        if state & GUI_FOCUS:
            if kind == "TreeViewItem":
                tree: Any = control.value
                tree.selection_set(control.item)
            elif widget is not None and kind not in ("Dummy", "Graphic"):
                focus_widget = _content_widget(control)
                if focus_widget is not None:
                    try:
                        focus_widget.focus_set()
                    except tkinter.TclError:
                        pass
            changed = 1
        if state & GUI_EXPAND and kind == "TreeViewItem":
            # "this state is only used for TreeViewItems. If you want to use this 'action'
            # then at least 1 Sub-TreeViewItem has to exist/created under this item!"
            tree_widget: Any = control.value
            tree_widget.item(control.item, open=True)
            changed = 1
        if state & GUI_DEFBUTTON and kind == "TreeViewItem":
            _paint_tree_item_bold(control)
            changed = 1
        if state & GUI_ONTOP and widget is not None:
            widget.lift()
            changed = 1
        if state & GUI_DROPACCEPTED or state & GUI_NODROPACCEPTED:
            # "Control will accept drop action : from file or from a drag of another control."
            # Acceptance is asked of the GUI's own window — the handle GUICreate returns, which is
            # the one the port hooks — and a drop is then routed to the accepting control under the
            # point it carries. The tkinter windows are left alone: making one a drop target puts
            # the shell's own processing on a window whose procedure is tkinter's.
            window = self._windows[control.window]
            accepting = bool(state & GUI_DROPACCEPTED)
            any_accepting = accepting or any(
                other.states & GUI_DROPACCEPTED
                for other in self._controls.values()
                if other.window == control.window
            )
            native.drag_accept(window.handle, any_accepting)
            if any_accepting:
                self._hook_window(window)
            control.states = (
                control.states & ~(GUI_DROPACCEPTED | GUI_NODROPACCEPTED)
            ) | (state & (GUI_DROPACCEPTED | GUI_NODROPACCEPTED))
            changed = 1
        if state & GUI_NOFOCUS:
            # "Listview control will loose focus": the selection it holds is given up.
            if kind == "ListView":
                for item in control.widget.selection():
                    control.widget.selection_remove(item)
            control.states |= GUI_NOFOCUS
            changed = 1
        return 1 if changed else 0

    def GUICtrlGetState(self, controlID: int) -> int:
        """Return a control's state bits (enabled/disabled, shown/hidden, drop accepted).

        "As opposed to GUICtrlRead() this function returns ONLY the state of a control
        enabled/disabled/hidden/show/dropaccepted"; the interpreter reports 80 for a normal
        control (``$GUI_SHOW`` + ``$GUI_ENABLE``), 96 when hidden and 144 when disabled.
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return -1
        if control.kind == "ListView":
            # "For ListView controls it returns the number of the clicked column."
            return control.clicked_column
        state = control.states & (GUI_DROPACCEPTED | GUI_NODROPACCEPTED | GUI_NOFOCUS)
        state |= GUI_HIDE if control.states & GUI_HIDE else GUI_SHOW
        state |= GUI_DISABLE if control.states & GUI_DISABLE else GUI_ENABLE
        return state

    def GUICtrlSetPos(
        self,
        controlID: int,
        left: int,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> int:
        """Change a control's position; ``None`` stands for AutoIt's ``Default`` keyword."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.widget is None and not control.native:
            return 0
        window = self._windows[control.window]
        if control.native:
            # A native control's position and size live in its window, not in a tkinter layout.
            left_now, top_now, width_now, height_now = control.pos or (0, 0, 0, 0)
            current_left, current_top = left_now, top_now
            current_width, current_height = width_now, height_now
        else:
            widget = control.widget
            info = widget.place_info() if widget is not None else {}
            current_left = int(info.get("x", 0))
            current_top = int(info.get("y", 0))
            current_width = int(info.get("width", 0))
            current_height = int(info.get("height", 0))
        mode = self._options["GUICoordMode"]
        if mode == 0 and left != -1:
            left = window.last_left + left
        elif mode == 2 and left != -1:
            left = window.cell_left + left
        resolved_left = left if left != -1 and left is not None else current_left
        resolved_top = current_top if top is None else top
        resolved_width = current_width if width is None else width
        resolved_height = current_height if height is None else height
        self._place(window, control, resolved_left, resolved_top, resolved_width, resolved_height)
        return 1

    def GUICtrlSetStyle(self, controlID: int, style: int, exStyle: int = -1) -> int:
        """Change a control's style."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        control.style = style
        if exStyle != -1:
            control.ex_style = exStyle
        if control.kind == "Obj":
            # As GUICtrlSetData on this kind: "GUICtrlSet has no effect on this control"
            # (GUICtrlCreateObj.htm). Measured: the interpreter returned 1.
            return 1
        if control.native:
            # A native control's style is its window style, which Windows re-creates for it. The
            # reference replaces the style wholesale ("No checking is done on style value"), so
            # only the bits a child window cannot do without are kept.
            native.set_style(control.native, style | WS_CHILD | WS_VISIBLE)
            return 1
        if control.widget is None:
            return 1
        if control.kind in ("Button", "Checkbox", "Radio"):
            options = styles.button_options(style)
            if control.kind == "Checkbox":
                options = styles.checkbox_options(style)
                options.pop("_auto_toggle", None)
            elif control.kind == "Radio":
                options = styles.radio_options(style)
        elif control.kind in ("Label", "Pic"):
            options = styles.label_options(style)
        elif control.kind == "Input":
            options = styles.entry_options(style)
        elif control.kind == "Edit":
            options = styles.text_options(style)
        elif control.kind == "Combo":
            options = styles.combo_options(style)
        elif control.kind == "List":
            options = styles.list_options(style)
        elif control.kind == "Progress":
            options = styles.progress_options(style)
        elif control.kind == "Slider":
            options = styles.slider_options(style)
        else:
            options = {}
        if options:
            try:
                control.widget.configure(**options)
            except tkinter.TclError:
                return 0
        return 1

    def GUICtrlSetResizing(self, controlID: int, resizing: int) -> int:
        """Defines the resizing method used by a control.

        ``0`` and values of ``1024`` and above mean the control type's own default resizing, which
        is what the interpreter did with each (``probe_autoit_resizing6_out.txt``: a Label, an Edit
        and a ListView moved as ``$GUI_DOCKAUTO``, an Input and a Date as ``$GUI_DOCKHEIGHT``, a
        Button and a Pic as ``$GUI_DOCKSIZE``). The window's resize then applies it; the reference
        needs the window to carry ``$WS_SIZEBOX`` and ``$WS_SYSMENU`` for the user to resize it at
        all, which ``GUICreate`` maps onto tkinter's resizable window.
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        control.resizing = resizing
        return 1

    def GUICtrlSetFont(
        self,
        controlID: int,
        size: float,
        weight: int = 0,
        attribute: int = GUI_FONTNORMAL,
        fontname: str = "",
        quality: int = 2,
    ) -> int:
        """Set the font of a single control.

        A native control is given a real GDI font through ``WM_SETFONT``, which is where AutoIt's
        ``quality`` parameter means something: its Font Quality table is the GDI one value for
        value (0 default, 1 draft, 2 proof, 3 nonantialiased, 4 antialiased, 5 cleartype), and the
        control's own ``LOGFONT`` reports it back. A tkinter-drawn control gets a Tk font, and Tk
        draws its text itself — ``quality`` has no equivalent there (``styles.font_tuple``).
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.native:
            window = self._windows[control.window]
            font = native.create_font(size, weight, attribute, fontname, quality)
            if not font:
                return 0
            # Kept alive for the control's life, like the images: Windows draws with the handle, not
            # with a copy of it.
            self._fonts.append(font)
            control.font = font
            native.set_window_font(control.native, font)
            return 1
        widget = _content_widget(control)
        if widget is None or not _supports(widget, "font"):
            return 0
        widget.configure(
            font=styles.font_tuple(size, weight, attribute, fontname, quality)
        )
        return 1

    def GUICtrlSetColor(self, controlID: int, textcolor: int) -> int:
        """Set a control's text colour."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        window = self._windows[control.window]
        self._set_widget_text_color(window, control, textcolor)
        return 1

    def GUICtrlSetBkColor(self, controlID: int, backgroundcolor: int) -> int:
        """Set a control's background colour (or $GUI_BKCOLOR_TRANSPARENT)."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        window = self._windows[control.window]
        self._set_widget_bk_color(window, control, backgroundcolor)
        return 1

    def GUICtrlSetDefColor(self, deftextcolor: int, winhandle: int | None = None) -> int:
        """Set the default text colour of the window's controls."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.default_text_color = deftextcolor
        for control in self._controls.values():
            if control.window == window.handle:
                self._set_widget_text_color(window, control, deftextcolor)
        return 1

    def GUICtrlSetDefBkColor(self, defbkcolor: int, winhandle: int | None = None) -> int:
        """Set the default background colour of the window's controls."""

        try:
            window = self._resolve_window(winhandle)
        except _WindowNotFound:
            return 0
        window.default_bk_color = defbkcolor
        for control in self._controls.values():
            if control.window == window.handle:
                self._set_widget_bk_color(window, control, defbkcolor)
        return 1

    def GUICtrlSetImage(
        self, controlID: int, filename: str, iconname: int = -1, icontype: int = 1
    ) -> int:
        """Set the picture or icon a control displays."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        image = self._load_image(filename)
        control.image = image
        kind = control.kind
        if kind in ("TreeView", "ListView"):
            # "If you use GUICtrlSetImage() on a TreeView or ListView then all items of it
            # will change to this icon/image."
            for item in control.widget.get_children(""):
                _set_tree_item_image(control, item, image)
            control.value = image
            return 1
        if kind in ("TreeViewItem", "ListViewItem"):
            _set_tree_item_image(control.value, control.item, image)
            return 1
        if control.widget is None or not _supports(control.widget, "image"):
            return 0
        # The PhotoImage reference itself is kept in the GUI's image list; a widget option
        # is the only place tkinter needs it.
        control.widget.configure(image=image, compound="left")
        return 1

    def GUICtrlSetCursor(self, controlID: int, cursorID: int) -> int:
        """Set the cursor shown while the mouse is over a control."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.widget is None:
            return 0
        name = "none" if cursorID == _CURSOR_HIDDEN_ID else _CURSOR_BY_ID.get(cursorID, "arrow")
        cursor_widget = _content_widget(control)
        if cursor_widget is None:
            return 0
        try:
            cursor_widget.configure(cursor=name)
        except tkinter.TclError:
            cursor_widget.configure(cursor="arrow")
        return 1

    def GUICtrlSetTip(
        self,
        controlID: int,
        tiptext: str,
        title: str = "",
        icon: int = TIP_INFOICON,
        options: int = 0,
    ) -> int:
        """Set the tooltip text shown when the mouse hovers over a control.

        The reference's parameters are the Windows tooltip control's own: "title: The title for
        the tooltip", "icon: Pre-defined icon to show next to the title: requires a title", and
        "options: $TIP_BALLOON / $TIP_CENTER". The port attaches that same control to the
        control's window, so the title row and its icon are the ones Windows draws.
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        target = _control_window(control)
        if not target:
            return 0
        window = self._windows[control.window]
        # AutoIt gives each control its own tooltip window, and a second GUICtrlSetTip for the same
        # control replaces that window: the probe's handle changed on every call. So the old one
        # goes first, and the new one carries this call's options — which is how two controls in one
        # window can hold different titles, and one a balloon tip while another does not.
        if control.tooltip:
            native.destroy_window(control.tooltip)
        control.tooltip = native.create_tooltip(
            window.handle, balloon=bool(options & TIP_BALLOON)
        )
        if control.tooltip == 0:
            return 0
        native.tooltip_add_tool(
            control.tooltip, target, tiptext, window.handle, center=bool(options & TIP_CENTER)
        )
        if title:
            native.tooltip_set_title(control.tooltip, title, _tooltip_icon(icon))
        return 1

    def GUICtrlSetLimit(self, controlID: int, max: int, min: int = 0) -> int:
        """Limit characters (Input/Edit), scroll extent (List) or range (Slider/Updown)."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        kind = control.kind
        if kind == "Input":
            control.widget.configure(validate="key")
            control.widget.configure(
                validatecommand=(control.widget.register(lambda proposed: len(proposed) <= max),
                                 "%P")
            )
            return 1
        if kind == "Edit":
            text_widget = control.value
            original = text_widget.get("1.0", "end-1c")

            def enforce() -> None:
                current = text_widget.get("1.0", "end-1c")
                if len(current) > max:
                    text_widget.delete(f"1.0 + {max} chars", "end")

            _ = original
            text_widget.bind("<KeyRelease>", lambda _event: enforce(), add="+")
            return 1
        if kind == "List":
            # AutoIt's parameter is named "max" (GUICtrlSetLimit.htm), which shadows the
            # built-in inside this method; the extent is never below one pixel.
            extent = 1 if max < 1 else max
            control.value.configure(xscrollincrement=extent)
            return 1
        if kind == "Slider":
            control.widget.configure(from_=min, to=max)
            return 1
        if kind == "Updown":
            # "For Slider and UpDown controls you can specify a min value. Default = 0"
            return 1 if native.updown_set_range(control.native, min, max) else 0
        return 0

    def GUICtrlSetGraphic(self, controlID: int, type: int, *par: Any) -> int:
        """Draw into a Graphic control, using the reference's $GUI_GR_* command set."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.kind != "Graphic":
            return -1
        window = self._windows[control.window]
        state = window.graphic_state.setdefault(
            control.control_id,
            {"x": 0, "y": 0, "color": "#000000", "bk_color": None, "pen_size": 1, "points": []},
        )
        canvas = control.widget
        close = bool(type & GUI_GR_CLOSE)
        command = type & ~GUI_GR_CLOSE
        if command == GUI_GR_COLOR:
            color = styles.colorref_to_tk(int(par[0]))
            state["color"] = color or "#000000"
            state["bk_color"] = None
            if len(par) > 1 and int(par[1]) != GUI_GR_NOBKCOLOR:
                state["bk_color"] = styles.colorref_to_tk(int(par[1]))
            return 1
        if command == GUI_GR_PENSIZE:
            state["pen_size"] = int(par[0])
            return 1
        if command == GUI_GR_MOVE:
            state["x"], state["y"] = int(par[0]), int(par[1])
            state["points"] = [(state["x"], state["y"])]
            return 1
        if command == GUI_GR_DOT:
            x, y = int(par[0]), int(par[1])
            canvas.create_rectangle(x, y, x + 1, y + 1, fill=state["color"], outline=state["color"])
            state["points"] = [(state["x"], state["y"])]
            return 1
        if command == GUI_GR_PIXEL:
            x, y = int(par[0]), int(par[1])
            canvas.create_line(x, y, x, y, fill=state["color"])
            state["points"] = [(state["x"], state["y"])]
            return 1
        if command == GUI_GR_LINE:
            points = list(state["points"]) + [(int(par[0]), int(par[1]))]
            if close:
                points.append(points[0])
            canvas.create_line(
                *_flatten(points), fill=state["color"], width=state["pen_size"]
            )
            state["x"], state["y"] = int(par[0]), int(par[1])
            return 1
        if command == GUI_GR_BEZIER:
            # "x,y,x1,y1,x2,y2 — Draw a bezier curve with 2 control points"
            # (GUICtrlSetGraphic.htm): x,y is where the curve *ends* and the two x1,y1 / x2,y2
            # pairs are its control points, with the current position as its start. AutoIt draws
            # it with Win32's PolyBezier, which flattens the same cubic; Tk has no curve primitive,
            # so the cubic is flattened here and drawn as a polyline. Tk's own smooth spline treats
            # the points as control points of a different curve and does not pass through them.
            end = (int(par[0]), int(par[1]))
            start = state["points"][0] if state["points"] else (state["x"], state["y"])
            curve = _bezier_points(
                start,
                (int(par[2]), int(par[3])),
                (int(par[4]), int(par[5])),
                end,
            )
            if close:
                curve.append(curve[0])
            canvas.create_line(
                *_flatten(curve), fill=state["color"], width=state["pen_size"]
            )
            state["x"], state["y"] = end
            state["points"] = [end]
            return 1
        if command == GUI_GR_RECT:
            x, y, width, height = (int(par[0]), int(par[1]), int(par[2]), int(par[3]))
            canvas.create_rectangle(x, y, x + width, y + height, outline=state["color"],
                                    fill=state["bk_color"] or "", width=state["pen_size"])
            return 1
        if command == GUI_GR_ELLIPSE:
            x, y, width, height = (int(par[0]), int(par[1]), int(par[2]), int(par[3]))
            canvas.create_oval(x, y, x + width, y + height, outline=state["color"],
                               fill=state["bk_color"] or "", width=state["pen_size"])
            return 1
        if command == GUI_GR_PIE:
            x, y, radius, start, sweep = (
                int(par[0]), int(par[1]), int(par[2]), int(par[3]), int(par[4]))
            canvas.create_arc(x - radius, y - radius, x + radius, y + radius,
                              start=start, extent=sweep, style="pieslice",
                              outline=state["color"], fill=state["bk_color"] or "",
                              width=state["pen_size"])
            return 1
        if command == GUI_GR_REFRESH:
            canvas.update_idletasks()
            return 1
        if command == GUI_GR_HINT:
            points = state["points"]
            if points:
                for x, y in points:
                    canvas.create_rectangle(x - 1, y - 1, x + 1, y + 1, outline=state["color"])
            return 1
        return -1

    def GUICtrlSendMsg(self, controlID: int, msg: int, wParam: Any, lParam: Any) -> int:
        """Send a Windows message to a control and return what ``SendMessage`` returned.

        "This function allows the sending of special Windows messages directly to the control
        using the SendMessage API", and "The parameters (wParam and lParam) can be an integer
        or a string". The port's widgets are windows, so the message goes to the control's own
        window procedure, exactly as AutoIt sends it.
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.widget is None:
            return 0
        handle = int(control.widget.winfo_id())
        if isinstance(lParam, str):
            return native.send_message_text(handle, msg, int(wParam), lParam)
        if isinstance(wParam, str):
            return native.send_message_text(handle, msg, 0, wParam)
        return native.send_message(handle, msg, int(wParam or 0), int(lParam or 0))

    def GUICtrlRecvMsg(
        self, controlID: int, msg: int, wParam: int = 0, lParamType: int = 0
    ) -> Any:
        """Send a Windows message to a control and read the result back.

        ``lParamType`` is the reference's: 0 (the default) returns the two-element array
        ``[wParam, lParam]``, 1 returns lParam as a string, and 2 returns it as the four
        elements of a RECT.
        """

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.widget is None:
            return 0
        handle = int(control.widget.winfo_id())
        if lParamType == 1:
            result, text = native.send_message_buffer(handle, msg, int(wParam), _RECV_TEXT_SIZE)
            return text
        if lParamType == 2:
            result, rect = native.send_message_rect(handle, msg, int(wParam))
            return rect
        buffer = ctypes.create_string_buffer(4)
        result = native.send_message(
            handle, msg, int(wParam), ctypes.cast(buffer, ctypes.c_void_p).value or 0
        )
        lparam = int.from_bytes(buffer.raw[:4], "little", signed=False)
        return [result, lparam]

    def GUICtrlSendToDummy(self, controlID: int, state: Any = 0) -> int:
        """Send a value to a Dummy control, which notifies as if it had been clicked."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.kind != "Dummy":
            return 0
        control.value = state
        window = self._windows.get(control.window)
        # "Note that the function will not action the dummy control if the GUI in which it
        # was created is hidden, as by design none of the controls on such a GUI can be
        # actioned" (GUICtrlSendToDummy.htm).
        if window is not None and window.visible:
            self._control_event(control.control_id)
        return 1

    def GUICtrlGetHandle(self, controlID: int) -> int:
        """Return the control's window handle, or 0 where AutoIt returns none."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.native:
            return control.native
        if control.kind in ("Dummy", "TabItem", "ListViewItem", "MenuItem", "Obj"):
            # "The following controls will not return a handle: GUICtrlCreateDummy(),
            # GUICtrlCreateGraphic(), GUICtrlCreateObj(), GUICtrlCreateListViewItem() and
            # GUICtrlCreateTabItem()" (GUICtrlGetHandle.htm). NOTE: the interpreter probe
            # returned a handle for a Graphic control and for a TreeViewItem, so the page's
            # list and the interpreter disagree; the port follows what the page lists.
            return 0
        if control.widget is None:
            return 0
        if control.kind == "TreeViewItem":
            return 0
        try:
            return int(control.widget.winfo_id())
        except tkinter.TclError:
            return 0

    def GUICtrlRegisterListViewSort(self, controlID: int, function: Any) -> int:
        """Register the function that sorts a ListView when a column heading is clicked."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        if control.kind != "ListView":
            return 0
        if not callable(function):
            raise TypeError(
                "GUICtrlRegisterListViewSort takes a Python callable: AutoIt passes the "
                "*name* of an AutoIt function as a string (GUICtrlRegisterListViewSort.htm)"
            )
        control.sort_function = function
        for index in range(len(control.columns)):
            control.widget.heading(
                f"c{index}",
                command=lambda column=index, c=control: self._sort_listview(c, column),
            )
        return 1

    def _sort_listview(self, control: _control, column: int) -> None:
        """Sort a ListView with the registered callback, as AutoIt's callback does."""

        control.clicked_column = column
        function = control.sort_function
        if function is None:
            return
        items = list(control.widget.get_children(""))

        def item_id(item: str) -> int:
            record = self._item_control(control, item)
            return record.control_id if record else 0

        def compare(first: str, second: str) -> int:
            return int(function(control.control_id, item_id(first), item_id(second), column))

        from functools import cmp_to_key

        items.sort(key=cmp_to_key(compare))
        for position, item in enumerate(items):
            control.widget.move(item, "", position)

    def GUICtrlDelete(self, controlID: int) -> int:
        """Delete a control, or delete one item of a ListView or TreeView."""

        try:
            control = self._resolve_control(controlID)
        except _ControlNotFound:
            return 0
        for child in [
            item.control_id for item in self._controls.values() if item.parent == control.control_id
        ]:
            self.GUICtrlDelete(child)
        if control.kind in ("TreeViewItem", "ListViewItem"):
            # Measured (probe_autoit_delete_item_out.txt): GUICtrlDelete on an item returns 1 and
            # takes its row out of the control -- three rows became two, the neighbours kept their
            # text and the deleted item then read 0. Deleting it again returns 0.
            tree = control.value
            item = control.item
            if tree is not None and item is not None:
                try:
                    tree.delete(item)
                except tkinter.TclError:
                    pass
        elif control.native:
            native.destroy_window(control.native)
        elif control.widget is not None:
            try:
                control.widget.destroy()
            except tkinter.TclError:
                pass
        # AutoIt removes a control's tooltip with the control (probe: the tip window was gone after
        # GUICtrlDelete).
        if control.tooltip:
            native.destroy_window(control.tooltip)
        del self._controls[control.control_id]
        if self._last_control == control.control_id:
            self._last_control = next(reversed(self._controls), None)
        return 1


class _WindowNotFound(Exception):
    """Raised internally when a function names a window that does not exist."""


class _ControlNotFound(Exception):
    """Raised internally when a function names a control that does not exist."""


# --- helpers -------------------------------------------------------------------------

_TTK_CLASS_BY_KIND = {
    "Combo": "TCombobox",
    "ListView": "Treeview",
    "TreeView": "Treeview",
    "Progress": "TProgressbar",
    "Tab": "TNotebook",
}


def _content_widget(control: _control) -> Any:
    """Return the widget that carries a control's text, items and input.

    AutoIt's List and Edit are single windows with their own scrollbars, and tkinter has no such
    widget: the port draws them as a frame holding the widget itself plus a scrollbar, so the
    *frame* is what gets placed on the window (``control.widget``) while the list box or text box
    inside it is what the user selects and types in and what reads and writes its contents
    (``control.value``). Every function that reaches a control's content -- its events, its font,
    its colours, its enabled state, its cursor -- therefore has to reach that inner widget, and
    this is the one place that decides which widget that is. For every other kind the two are the
    same widget, and the kind's own widget is returned.
    """

    if control.kind in ("List", "Edit"):
        # The widget inside the frame, which the creator hands over as the control's value; until
        # it is there the control has no content widget, and its event is bound when it arrives.
        value = control.value
        return value if isinstance(value, tkinter.Misc) else None
    return control.widget


def _supports(widget: Any, option: str) -> bool:
    """Return whether a tkinter widget accepts a configuration option."""

    try:
        return option in widget.configure()
    except (tkinter.TclError, AttributeError):
        return False


def _signed_32(value: int) -> int:
    """Return a style word the way AutoIt reports it: a signed 32-bit integer."""

    value &= 0xFFFFFFFF
    if value >= 0x80000000:
        return value - 0x100000000
    return value


def _tooltip_icon(icon: int) -> int:
    """Map ``GUICtrlSetTip``'s icon value onto the tooltip control's title icon.

    The reference lists ``$TIP_NOICON (0)``, ``$TIP_INFOICON (1)``, ``$TIP_WARNINGICON (2)`` and
    ``$TIP_ERRORICON (3)``, which are the tooltip control's own values.
    """

    return icon if icon in (0, 1, 2, 3) else 0


def _docked_box(
    base: tuple[int, int, int, int],
    before: tuple[int, int],
    after: tuple[int, int],
    dock: int,
) -> tuple[int, int, int, int]:
    """Return the box a control docks to when a window's client goes from ``before`` to ``after``.

    Every reading below is the interpreter's, from ``tests/autoit_reference/``:

    * the position scales by the client ratio and is truncated — with a 398x275 client going to
      684x461 (``probe_autoit_resizing3_out.txt``) a box of ``60,45,100,30`` with
      ``$GUI_DOCKAUTO`` came back as ``103,75,171,50`` (60 * 684/398 = 103.1, 45 * 461/275 = 75.4);
    * without ``$GUI_DOCKWIDTH``/``$GUI_DOCKHEIGHT`` the size scales the same way (171 = 100 *
      1.7186 truncated, not 172);
    * with a pinned edge the *margin* is kept: ``$GUI_DOCKRIGHT`` gave 275 = 684 - (398 - 60 - 100)
      - 171, and ``$GUI_DOCKBOTTOM`` gave 211 = 461 - (275 - 45 - 30) - 50;
    * with both edges pinned the size is the gap between them: ``$GUI_DOCKBORDERS`` gave 386x216;
    * a pinned centre keeps its offset from the client centre: ``$GUI_DOCKWIDTH|$GUI_DOCKHCENTER``
      gave 203 = (684 - 100)/2 + (60 - (398 - 100)/2), truncated (a 683-wide client gave 203 from
      203.5). Alone, ``$GUI_DOCKHCENTER`` left the position scaled, which is why the centre is
      applied only together with ``$GUI_DOCKWIDTH`` here;
    * a position may go negative when the window shrinks past a pinned edge (``$GUI_DOCKRIGHT``
      measured -25), but a size does not: ``$GUI_DOCKBORDERS`` in a client smaller than its margins
      measured ``60,45,0,0`` (probe_autoit_resizing10, from 398x275 to 284x161, where the raw gap
      between the pinned edges is -14x-84), so the sizes stop at 0.
    """

    left0, top0, width0, height0 = base
    width_before, height_before = before
    width_after, height_after = after
    if width_before <= 0 or height_before <= 0:
        return base

    right_margin = width_before - left0 - width0
    if dock & GUI_DOCKLEFT and dock & GUI_DOCKRIGHT:
        left = left0
        width = max(0, width_after - left - right_margin)
    else:
        width = width0 if dock & GUI_DOCKWIDTH else int(width0 * width_after / width_before)
        if dock & GUI_DOCKRIGHT:
            left = width_after - right_margin - width
        elif dock & GUI_DOCKLEFT:
            left = left0
        elif dock & GUI_DOCKHCENTER and dock & GUI_DOCKWIDTH:
            left = int((width_after - width) / 2 + (left0 - (width_before - width0) / 2))
        else:
            left = int(left0 * width_after / width_before)

    bottom_margin = height_before - top0 - height0
    if dock & GUI_DOCKTOP and dock & GUI_DOCKBOTTOM:
        top = top0
        height = max(0, height_after - top - bottom_margin)
    else:
        height = height0 if dock & GUI_DOCKHEIGHT else int(height0 * height_after / height_before)
        if dock & GUI_DOCKBOTTOM:
            top = height_after - bottom_margin - height
        elif dock & GUI_DOCKTOP:
            top = top0
        elif dock & GUI_DOCKVCENTER and dock & GUI_DOCKHEIGHT:
            top = int((height_after - height) / 2 + (top0 - (height_before - height0) / 2))
        else:
            top = int(top0 * height_after / height_before)

    return (left, top, width, height)


def _control_window(control: _control) -> int:
    """Return the window handle a control's own messages arrive at, or 0 for none.

    A native control is a window of its own; a tkinter widget is a window too. A menu item or an
    item of a list view has none.
    """

    if control.native:
        return control.native
    if control.widget is None:
        return 0
    try:
        return int(control.widget.winfo_id())
    except tkinter.TclError:
        return 0


def _parse_autoit_date(text: str) -> tuple[int, int, int] | None:
    """Parse AutoIt's "yyyy/mm/dd" date text into (year, month, day)."""

    parts = text.strip().replace("-", "/").split("/")
    if len(parts) != 3:
        return None
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        return None
    return (year, month, day)


def _date_reads_long(style: int) -> bool:
    """Return whether a Date control's format style reads as the long regional date.

    The control's style decides the format ``GUICtrlRead`` reports: the interpreter returned
    "Friday, January 2, 2026" for the default ``$DTS_LONGDATEFORMAT`` control and "3/4/2027"
    after ``GUICtrlSetStyle($date, $DTS_SHORTDATEFORMAT)``. Win32's four format styles are told
    apart by their low bits, because ``$DTS_SHORTDATECENTURYFORMAT`` (0x0C) shares a bit with
    ``$DTS_LONGDATEFORMAT`` (0x04).
    """

    if style == -1:
        return True
    return (style & 0x000F) == DTS_LONGDATEFORMAT


def _check_mark(state: int) -> str:
    """The mark a ListView item's check column shows for a check state.

    AutoIt's ``$LVS_EX_CHECKBOXES`` draws a checkbox in the list view's first column; the port
    keeps that column and writes the state into it, so ``GUICtrlRead`` of the item's values is
    untouched.
    """

    return "\u2611" if state == GUI_CHECKED else "\u2610"


def _positional_parameter_count(function: Any) -> int:
    """Return how many positional parameters a registered function declares.

    ``GUIRegisterMsg``'s page states that its user function may be declared with four
    parameters (``$hWndGUI, $MsgID, $WParam, $LParam``) or with two, and AutoIt calls it with
    that many; a Python callable is asked the same way instead of guessing.
    """

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return 4
    count = 0
    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            count += 1
        elif parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            return 4
    return count


def _valid_input(proposed: str, style: int) -> bool:
    """Validation callback for the styles tkinter has no option for ($ES_NUMBER, case)."""

    if style & ES_NUMBER and proposed and not proposed.isdigit():
        return False
    if style & ES_UPPERCASE and proposed != proposed.upper():
        return False
    if style & ES_LOWERCASE and proposed != proposed.lower():
        return False
    return True


def _split_items(text: str, separator: str) -> list[str]:
    """Split an AutoIt "Opt('GUIDataSeparatorChar')" separated list."""

    return text.split(separator)


def _flatten(points: Sequence[tuple[int, int]]) -> list[int]:
    """Flatten (x, y) pairs into the coordinate list Tk canvas calls take."""

    flat: list[int] = []
    for x, y in points:
        flat.extend((x, y))
    return flat


#: How finely a cubic is flattened. AutoIt's ``PolyBezier`` flattens the same curve to the device's
#: tolerance; 64 segments put every point within a third of a pixel of the true curve, which is
#: finer than a pen can draw at the sizes a Graphic control is used at.
_BEZIER_STEPS = 64


def _bezier_points(
    start: tuple[int, int],
    control1: tuple[int, int],
    control2: tuple[int, int],
    end: tuple[int, int],
) -> list[tuple[int, int]]:
    """Flatten the cubic Bezier ``$GUI_GR_BEZIER`` draws: B(t) with two control points.

    B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3, sampled ``_BEZIER_STEPS`` times
    from the current position to ``end`` — the same curve Win32's ``PolyBezier`` draws, so the
    endpoints and the shape match rather than approximating it with a different spline.
    """

    points: list[tuple[int, int]] = []
    for step in range(_BEZIER_STEPS + 1):
        t = step / _BEZIER_STEPS
        inverse = 1.0 - t
        x = (
            inverse**3 * start[0]
            + 3 * inverse**2 * t * control1[0]
            + 3 * inverse * t**2 * control2[0]
            + t**3 * end[0]
        )
        y = (
            inverse**3 * start[1]
            + 3 * inverse**2 * t * control1[1]
            + 3 * inverse * t**2 * control2[1]
            + t**3 * end[1]
        )
        points.append((round(x), round(y)))
    return points


def _variable_state(control: _control) -> int:
    """Return the checked state of a Checkbox or Radio control.

    The reference returns "only the $GUI_CHECKED (1), $GUI_UNCHECKED (4) or
    $GUI_INDETERMINATE (2) states" for these controls, so a Checkbox's variable holds the
    state value itself and a Radio compares its shared variable with its own control ID.
    """

    variable = control.value
    try:
        value = int(variable.get())
    except (ValueError, tkinter.TclError):
        return GUI_UNCHECKED
    if control.kind == "Radio":
        return GUI_CHECKED if value == control.control_id else GUI_UNCHECKED
    if value in (GUI_CHECKED, GUI_UNCHECKED, GUI_INDETERMINATE):
        return value
    return GUI_CHECKED if value else GUI_UNCHECKED


def _set_control_state(control: _control, state: int) -> None:
    """Write a Checkbox or Radio control's checked state."""

    variable = control.value
    if control.kind == "Radio":
        if state == GUI_CHECKED:
            variable.set(control.control_id)
        elif int(variable.get()) == control.control_id:
            variable.set(0)
        return
    variable.set(state)


def _selected_value(control: _control) -> str:
    """Return the selected value of a Combo or List control."""

    if control.kind == "Combo":
        return str(control.widget.get())
    listbox = control.value
    selection = listbox.curselection()
    if not selection:
        return ""
    return str(listbox.get(selection[0]))


def _clear_items(control: _control) -> None:
    """Empty a Combo or List control's item list."""

    if control.kind == "Combo":
        control.widget.configure(values=[])
        control.widget.set("")
        return
    control.value.delete(0, "end")


def _add_items(control: _control, items: Sequence[str]) -> None:
    """Add items to a Combo or List control."""

    if control.kind == "Combo":
        values = list(control.widget.cget("values")) + list(items)
        control.widget.configure(values=values)
        return
    sorted_items = bool(control.style != -1 and control.style & LBS_SORT)
    for item in items:
        control.value.insert("end", item)
    if sorted_items:
        values = sorted(str(control.value.get(0, "end")))
        control.value.delete(0, "end")
        for item in values:
            control.value.insert("end", item)


def _select_value(control: _control, value: str) -> None:
    """Select an item by value in a Combo or List control."""

    if control.kind == "Combo":
        control.widget.set(value)
        return
    listbox = control.value
    listbox.selection_clear(0, "end")
    for index in range(listbox.size()):
        if str(listbox.get(index)) == value:
            listbox.selection_set(index)
            listbox.see(index)
            return


def _insert_at_caret(control: _control, text: str) -> None:
    """Insert text at the caret of an Input or Edit control."""

    if control.kind == "Input":
        control.widget.insert("insert", text)
        return
    control.value.insert("insert", text)


def _set_text(control: _control, text: str) -> None:
    """Replace the whole text of an Input or Edit control."""

    if control.kind == "Input":
        control.widget.delete(0, "end")
        control.widget.insert(0, text)
        return
    text_widget = control.value
    text_widget.delete("1.0", "end")
    text_widget.insert("1.0", text)


def _set_visible(control: _control, visible: bool) -> None:
    """Show or hide a control, keeping the position and size it was created with.

    ``$GUI_HIDE`` and ``$GUI_SHOW`` change a control's visibility only: AutoIt's control keeps
    its coordinates while hidden, so showing it again puts it back where it was. tkinter's
    ``place_forget()`` discards the geometry, which is why the control record remembers it.
    """

    if control.native:
        native.show_window(control.native, visible)
        return
    widget = control.widget
    if visible:
        if control.pos is not None:
            left, top, width, height = control.pos
        else:
            info = widget.place_info()
            left = int(info.get("x", 0))
            top = int(info.get("y", 0))
            width = int(info.get("width", 0))
            height = int(info.get("height", 0))
        widget.place(x=left, y=top, width=width, height=height)
    else:
        widget.place_forget()


def _set_enabled(control: _control, enabled: bool) -> None:
    """Enable or disable a control where its widget supports a state."""

    widget = _content_widget(control)
    if widget is None:
        return
    try:
        widget.configure(state="normal" if enabled else "disabled")
    except tkinter.TclError:
        return


def _paint_tree_item_bold(control: _control) -> None:
    """Draw a TreeViewItem in bold, which is AutoIt's $GUI_DEFBUTTON for tree items."""

    tree = control.value
    tag = f"defbutton{control.control_id}"
    tree.tag_configure(tag, font=("TkDefaultFont", 9, "bold"))
    tree.item(control.item, tags=(tag,))


def _set_tree_item_image(tree_widget: Any, item: str, image: Any) -> None:
    """Give a tree or list item an image."""

    tree_widget.item(item, image=image)


def _pad_columns(values: Sequence[str], count: int) -> tuple[str, ...]:
    """Pad subitem values to a ListView's column count.

    A ListView item never carries more subitems than its control has columns: GUICtrlSetData
    on an item updates the columns that exist (GUICtrlSetData.htm).
    """

    padded = list(values[:count])
    while len(padded) < count:
        padded.append("")
    return tuple(padded)


def _update_subitems(
    current: Sequence[str], text: str, separator: str
) -> list[str]:
    """Update ListViewItem subitems the way GUICtrlSetData documents it.

    "To update a specific column just forget about the others ie '||update' to update 3rd
    column. If 'update' is empty the column/subitem will be erased."
    """

    updates = text.split(separator)
    subitems = list(current)
    while len(subitems) < len(updates):
        subitems.append("")
    for index, value in enumerate(updates):
        subitems[index] = value
    return subitems


def _accelerator_sequence(key: str) -> tuple[str, bool] | None:
    """Translate an AutoIt HotKeySet() key into a tkinter event sequence and a Windows-key flag.

    ``^`` ``!`` ``+`` are tkinter's Control, Alt and Shift. ``#`` is AutoIt's Windows key, which
    tkinter cannot spell at all, so it is reported separately: the caller binds the rest of the key
    and asks Windows whether the Windows key is held (measured: ``GetAsyncKeyState($VK_LWIN)``
    reports it while the key is down, and a Tk binding does not see it).
    """

    modifiers: list[str] = []
    rest = key
    needs_win = False
    while rest and rest[0] in "^!+#":
        if rest[0] == "#":
            needs_win = True
        else:
            modifiers.append({"^": "Control", "!": "Alt", "+": "Shift"}[rest[0]])
        rest = rest[1:]
    if not rest:
        return None
    if rest.startswith("{"):
        if not rest.endswith("}"):
            return None
        name = rest[1:-1].upper()
        if name in _ACCELERATOR_KEYS:
            rest = _ACCELERATOR_KEYS[name]
        elif name.startswith("F") and name[1:].isdigit():
            rest = name
        else:
            return None
    elif len(rest) != 1:
        return None
    parts = [*modifiers, rest if rest in ("Return", "Escape", "Tab", "space") else f"Key-{rest}"]
    return ("<" + "-".join(parts) + ">", needs_win)