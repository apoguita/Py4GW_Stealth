"""AutoIt style, colour and font values translated into tkinter options.

AutoIt's styles are Win32 style bits (``$WS_*``, ``$BS_*``, ``$ES_*``, ``$CBS_*``,
``$LBS_*``, ``$LVS_*``, ``$TVS_*``, ``$TBS_*``, ``$PBS_*``, ``$UDS_*``, ``$SS_*``,
``$TCS_*``). tkinter has no window-class style bits at all, so each entry below is an
explicit, written-down translation of one AutoIt style into the tkinter option that has the
same visible effect, taken from the AutoIt "GUI Control Styles Appendix" (decompiled from
the local ``AutoIt.chm``; see ``docs/AUTOIT_GUI.md``).

Styles with no tkinter equivalent are **kept, not invented around**: they are stored on the
control, reported back by ``GUICtrlGetStyle``, and listed in ``docs/AUTOIT_GUI.md`` as
accepted-but-not-applied. Nothing here silently drops a style without that list naming it.
"""

from __future__ import annotations

from typing import Any

from py4gw.gui.constants import (
    BS_AUTO3STATE,
    BS_AUTOCHECKBOX,
    BS_AUTORADIOBUTTON,
    BS_BITMAP,
    BS_BOTTOM,
    BS_CENTER,
    BS_CHECKBOX,
    BS_DEFPUSHBUTTON,
    BS_FLAT,
    BS_GROUPBOX,
    BS_ICON,
    BS_LEFT,
    BS_MULTILINE,
    BS_PUSHLIKE,
    BS_RADIOBUTTON,
    BS_RIGHT,
    BS_TOP,
    BS_VCENTER,
    CBS_AUTOHSCROLL,
    CBS_DROPDOWNLIST,
    CBS_SORT,
    ES_AUTOHSCROLL,
    ES_AUTOVSCROLL,
    ES_CENTER,
    ES_LEFT,
    ES_MULTILINE,
    ES_PASSWORD,
    ES_READONLY,
    ES_RIGHT,
    ES_WANTRETURN,
    GUI_BKCOLOR_DEFAULT,
    GUI_BKCOLOR_TRANSPARENT,
    LBS_EXTENDEDSEL,
    LBS_MULTIPLESEL,
    LBS_NOINTEGRALHEIGHT,
    LBS_NOTIFY,
    LBS_SORT,
    PBS_MARQUEE,
    PBS_SMOOTH,
    PBS_VERTICAL,
    SS_BITMAP,
    SS_BLACKFRAME,
    SS_CENTER,
    SS_CENTERIMAGE,
    SS_ETCHEDFRAME,
    SS_GRAYFRAME,
    SS_ICON,
    SS_LEFT,
    SS_LEFTNOWORDWRAP,
    SS_NOPREFIX,
    SS_NOTIFY,
    SS_RIGHT,
    SS_SIMPLE,
    SS_SUNKEN,
    SS_WHITEFRAME,
    TBS_AUTOTICKS,
    TBS_BOTH,
    TBS_DOWNISLEFT,
    TBS_HORZ,
    TBS_NOTICKS,
    TBS_VERT,
    TCS_TOOLTIPS,
    TVS_CHECKBOXES,
    TVS_DISABLEDRAGDROP,
    TVS_HASBUTTONS,
    TVS_HASLINES,
    TVS_LINESATROOT,
    TVS_SHOWSELALWAYS,
    UDS_ALIGNLEFT,
    UDS_ALIGNRIGHT,
    UDS_ARROWKEYS,
    UDS_HORZ,
    UDS_SETBUDDYINT,
    UDS_WRAP,
    WS_BORDER,
    WS_DISABLED,
    WS_EX_CLIENTEDGE,
    WS_EX_STATICEDGE,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
    WS_GROUP,
    WS_HSCROLL,
    WS_TABSTOP,
    WS_VSCROLL,
)

# AutoIt's $GUI_BKCOLOR_DEFAULT (-1) and $GUI_BKCOLOR_TRANSPARENT (-2) are not colours: they
# select "the colour the control would use anyway" and "no background". tkinter needs a real
# colour for the second case, so the caller passes the parent's colour.
_COLOR_DEFAULT = GUI_BKCOLOR_DEFAULT
_COLOR_TRANSPARENT = GUI_BKCOLOR_TRANSPARENT


def colorref_to_tk(color: int) -> str | None:
    """Convert an AutoIt colour (``0x00BBGGRR``) to a tkinter ``#rrggbb`` string.

    AutoIt colours are Windows ``COLORREF`` values: blue in the low byte, red in the third.
    ``$GUI_BKCOLOR_DEFAULT`` (-1) and ``$GUI_BKCOLOR_TRANSPARENT`` (-2) return ``None``: they
    are not colours and the caller decides what to do with them.
    """

    if color in (_COLOR_DEFAULT, _COLOR_TRANSPARENT):
        return None
    if color < 0:
        color += 1 << 32
    red = color & 0xFF
    green = (color >> 8) & 0xFF
    blue = (color >> 16) & 0xFF
    return f"#{red:02x}{green:02x}{blue:02x}"


def font_tuple(
    size: float,
    weight: int,
    attribute: int,
    fontname: str,
    quality: int,
) -> tuple[str, int, str]:
    """Build a tkinter font description from AutoIt's font parameters.

    ``weight`` is the Win32 weight (400 normal, 700 bold); ``attribute`` is the sum of
    ``$GUI_FONTITALIC`` (2), ``$GUI_FONTUNDER`` (4) and ``$GUI_FONTSTRIKE`` (8). ``quality`` is a
    GDI setting and Tk draws its own text, so it has no place in a Tk font: a *native* control is
    given a real GDI font with the requested quality instead (see ``GUICtrlSetFont``).
    """

    family = fontname if fontname else "TkDefaultFont"
    styles: list[str] = []
    if weight >= 700:
        styles.append("bold")
    if attribute & 2:
        styles.append("italic")
    if attribute & 4:
        styles.append("underline")
    if attribute & 8:
        styles.append("overstrike")
    return (family, int(round(size)), " ".join(styles))


def _horizontal_alignment(style: int, center: int, left: int, right: int) -> str | None:
    """Map a Win32 horizontal text style onto a tkinter anchor/justify value."""

    if style & center:
        return "center"
    if style & right:
        return "e"
    if style & left:
        return "w"
    return None


def _vertical_alignment(style: int) -> str | None:
    """Map a Win32 vertical text style onto a tkinter anchor value."""

    if style & BS_VCENTER:
        return "center"
    if style & BS_BOTTOM:
        return "s"
    if style & BS_TOP:
        return "n"
    return None


def button_options(style: int) -> dict[str, Any]:
    """tkinter options for a Button, Checkbox or Radio control."""

    options: dict[str, Any] = {}
    if style & BS_FLAT:
        options["relief"] = "flat"
    if style & BS_MULTILINE:
        # tkinter wraps with a pixel wraplength; a small value makes the text wrap rather
        # than stretch the control, which is what $BS_MULTILINE asks for.
        options["wraplength"] = 1
        options["justify"] = "left"
    horizontal = _horizontal_alignment(style, BS_CENTER, BS_LEFT, BS_RIGHT)
    if horizontal == "center":
        options["justify"] = "center"
        options["anchor"] = "center"
    elif horizontal == "e":
        options["justify"] = "right"
        options["anchor"] = "e"
    elif horizontal == "w":
        options["justify"] = "left"
        options["anchor"] = "w"
    vertical = _vertical_alignment(style)
    if vertical is not None:
        options["anchor"] = vertical
    if style & (BS_ICON | BS_BITMAP):
        # The image itself arrives with GUICtrlSetImage(); the style only selects the kind,
        # which tkinter does not distinguish. Compound keeps the text visible next to it.
        options["compound"] = "left"
    return options


def checkbox_options(style: int) -> dict[str, Any]:
    """tkinter options for a Checkbox control, adding the push-like and tristate cases."""

    options = button_options(style)
    if style & BS_PUSHLIKE:
        options["indicatoron"] = False
    if style & BS_AUTO3STATE:
        # tkinter's Checkbutton has a tristate value; AutoIt's $GUI_INDETERMINATE (2) is the
        # third state, and the variable type decides whether it is reachable.
        options["tristatevalue"] = 2
    if style & BS_CHECKBOX and not style & BS_AUTOCHECKBOX:
        # $BS_CHECKBOX (not auto) only notifies; the check state is set by the script.
        # tkinter's Checkbutton always toggles itself, which is AutoIt's auto behaviour.
        options["_auto_toggle"] = False
    # $BS_AUTORADIOBUTTON is the Radio case and needs no option of its own.
    _ = (BS_AUTORADIOBUTTON, BS_RADIOBUTTON, BS_GROUPBOX, BS_DEFPUSHBUTTON)
    return options


def radio_options(style: int) -> dict[str, Any]:
    """tkinter options for a Radio control."""

    options = button_options(style)
    if style & BS_PUSHLIKE:
        options["indicatoron"] = False
    return options


def label_options(style: int) -> dict[str, Any]:
    """tkinter options for a Label, Pic, Icon or Graphic control's frame."""

    options: dict[str, Any] = {}
    horizontal = _horizontal_alignment(style, SS_CENTER, SS_LEFT, SS_RIGHT)
    if horizontal == "center":
        options["anchor"] = "center"
        options["justify"] = "center"
    elif horizontal == "e":
        options["anchor"] = "e"
        options["justify"] = "right"
    elif horizontal == "w":
        options["anchor"] = "w"
        options["justify"] = "left"
    if style & SS_LEFTNOWORDWRAP:
        options["wraplength"] = 0
    if style & SS_CENTERIMAGE:
        options["compound"] = "center"
    if style & SS_SUNKEN:
        options["relief"] = "sunken"
    elif style & SS_ETCHEDFRAME or style & SS_BLACKFRAME or style & SS_GRAYFRAME:
        options["relief"] = "groove"
        options["borderwidth"] = 1
    elif style & SS_WHITEFRAME:
        options["relief"] = "ridge"
        options["borderwidth"] = 1
    if style & (SS_ICON | SS_BITMAP):
        options["compound"] = "center"
    if style & WS_BORDER:
        options["borderwidth"] = 1
        options["relief"] = "solid"
    # $SS_NOTIFY, $SS_SIMPLE and $SS_NOPREFIX change how Windows delivers and draws the
    # static: tkinter labels always notify their bindings, never elide to one line and never
    # interpret "&" as a mnemonic. See docs/AUTOIT_GUI.md.
    _ = (SS_NOTIFY, SS_SIMPLE, SS_NOPREFIX)
    return options


def entry_options(style: int) -> dict[str, Any]:
    """tkinter options for an Input control (single-line Edit)."""

    options: dict[str, Any] = {}
    if style & ES_PASSWORD:
        options["show"] = "*"
    if style & ES_READONLY:
        options["state"] = "readonly"
    horizontal = _horizontal_alignment(style, ES_CENTER, ES_LEFT, ES_RIGHT)
    if horizontal is not None:
        options["justify"] = {"w": "left", "center": "center", "e": "right"}[horizontal]
    # $ES_AUTOHSCROLL, $ES_AUTOVSCROLL and $ES_WANTRETURN have no Entry option: tkinter
    # entries always scroll with the caret and never accept a newline. $ES_NUMBER and the
    # case folds are applied by the GUI class through a validation callback; both are
    # recorded in docs/AUTOIT_GUI.md.
    _ = (ES_AUTOHSCROLL, ES_AUTOVSCROLL, ES_WANTRETURN)
    return options


def text_options(style: int) -> dict[str, Any]:
    """tkinter options for an Edit control (multi-line text)."""

    options: dict[str, Any] = {"wrap": "none"}
    if style & ES_READONLY:
        options["state"] = "disabled"
    horizontal = _horizontal_alignment(style, ES_CENTER, ES_LEFT, ES_RIGHT)
    if horizontal == "center":
        options["justify"] = "center"
    elif horizontal == "e":
        options["justify"] = "right"
    elif horizontal == "w":
        options["justify"] = "left"
    # $ES_WANTRETURN, $ES_MULTILINE and the scroll styles are served by the Text widget the
    # GUI class builds, not by these options.
    _ = (ES_WANTRETURN, ES_MULTILINE)
    return options


def combo_options(style: int) -> dict[str, Any]:
    """tkinter options for a Combo control."""

    options: dict[str, Any] = {}
    if style & CBS_DROPDOWNLIST:
        options["state"] = "readonly"
    if style & WS_DISABLED:
        options["state"] = "disabled"
    # $CBS_DROPDOWNLIST selects the read-only list form; $CBS_DROPDOWN (the AutoIt default)
    # is the editable form, which is tkinter's default state. $CBS_SORT is applied when items
    # are added by GUICtrlSetData(). $CBS_AUTOHSCROLL and $CBS_SIMPLE have no ttk.Combobox
    # equivalent (ttk has no always-open list form).
    _ = (CBS_AUTOHSCROLL, CBS_SORT)
    return options


def list_options(style: int) -> dict[str, Any]:
    """tkinter options for a List control."""

    options: dict[str, Any] = {}
    if style & LBS_EXTENDEDSEL:
        options["selectmode"] = "extended"
    elif style & LBS_MULTIPLESEL:
        options["selectmode"] = "multiple"
    if style & WS_BORDER:
        options["borderwidth"] = 1
        options["relief"] = "solid"
    elif style & WS_EX_CLIENTEDGE:
        options["borderwidth"] = 2
        options["relief"] = "sunken"
    # $LBS_SORT is applied when items are added, $LBS_NOTIFY is inherent in tkinter's
    # <<ListboxSelect>> binding, and $LBS_NOINTEGRALHEIGHT has no equivalent.
    _ = (LBS_SORT, LBS_NOTIFY, LBS_NOINTEGRALHEIGHT)
    return options


def listview_options(style: int) -> dict[str, Any]:
    """tkinter options for a ListView control (a ttk.Treeview in report mode)."""

    options: dict[str, Any] = {"show": "headings"}
    # AutoIt forces $LVS_REPORT and defaults to $LVS_SHOWSELALWAYS + $LVS_SINGLESEL, which is
    # exactly a ttk.Treeview with headings and "browse" selection. $LVS_ICON, $LVS_SMALLICON
    # and $LVS_LIST have no Treeview equivalent: ttk has no icon view, and GUICtrlSetStyle()
    # records them without changing the layout. See docs/AUTOIT_GUI.md.
    _ = (WS_EX_CLIENTEDGE, style)
    return options


def treeview_options(style: int) -> dict[str, Any]:
    """tkinter options for a TreeView control."""

    options: dict[str, Any] = {"show": "tree headings"}
    if style & TVS_CHECKBOXES:
        options["_checkboxes"] = True
    # ttk.Treeview always draws expander buttons and indentation lines and always shows the
    # selection, so $TVS_HASBUTTONS, $TVS_HASLINES, $TVS_LINESATROOT, $TVS_SHOWSELALWAYS and
    # $TVS_DISABLEDRAGDROP need no option of their own.
    _ = (TVS_HASBUTTONS, TVS_HASLINES, TVS_LINESATROOT, TVS_SHOWSELALWAYS, TVS_DISABLEDRAGDROP)
    return options


def progress_options(style: int) -> dict[str, Any]:
    """tkinter options for a Progress control."""

    options: dict[str, Any] = {"mode": "determinate"}
    if style & PBS_VERTICAL:
        options["orient"] = "vertical"
    if style & PBS_MARQUEE:
        options["mode"] = "indeterminate"
    # $PBS_SMOOTH is what ttk.Progressbar always draws.
    _ = (PBS_SMOOTH,)
    return options


def slider_options(style: int) -> dict[str, Any]:
    """tkinter options for a Slider control."""

    options: dict[str, Any] = {"orient": "vertical" if style & TBS_VERT else "horizontal"}
    if style & TBS_DOWNISLEFT:
        options["_down_is_left"] = True
    # tk.Scale draws no tick marks, so $TBS_AUTOTICKS, $TBS_NOTICKS and $TBS_BOTH are
    # recorded but not drawn.
    _ = (TBS_AUTOTICKS, TBS_NOTICKS, TBS_BOTH, TBS_HORZ)
    return options


def tab_options(style: int) -> dict[str, Any]:
    """tkinter options for a Tab control."""

    # ttk.Notebook always shows tabs with tab stops and clipping siblings; $TCS_TOOLTIPS and
    # the $TCS_* drawing styles have no Notebook equivalent.
    _ = (TCS_TOOLTIPS, style)
    return {}


def updown_options(style: int) -> dict[str, Any]:
    """tkinter options for an UpDown control (a tkinter Spinbox around the input)."""

    options: dict[str, Any] = {}
    if style & UDS_WRAP:
        options["wrap"] = True
    if style & UDS_HORZ:
        options["_horizontal"] = True
    # $UDS_ALIGNRIGHT/$UDS_ALIGNLEFT place the arrows; tkinter's Spinbox keeps them on the
    # right. $UDS_SETBUDDYINT (write the value back into the input) and the buddy
    # relationship are what the GUI class does when the arrows are used, so they need no
    # option. AutoIt's UpDownConstants.au3 defines no $UDS_AUTOBUDDY, so the port has none.
    _ = (UDS_ALIGNRIGHT, UDS_ALIGNLEFT, UDS_SETBUDDYINT, UDS_ARROWKEYS)
    return options


def window_options(style: int, ex_style: int) -> dict[str, Any]:
    """tkinter window options derived from a GUICreate() style and exStyle."""

    options: dict[str, Any] = {}
    if style & WS_DISABLED:
        options["_disabled"] = True
    if ex_style & WS_EX_TOPMOST:
        options["topmost"] = True
    if ex_style & WS_EX_TRANSPARENT:
        options["_transparent"] = True
    if ex_style & WS_EX_STATICEDGE:
        options["_static_edge"] = True
    # Window style bits GUICreate() accepts and tkinter cannot express are recorded (the GUI
    # class keeps them and GUIGetStyle reports them back) and listed in docs/AUTOIT_GUI.md:
    # $WS_POPUP, $WS_CAPTION, $WS_SYSMENU, $WS_MINIMIZEBOX, $WS_MAXIMIZEBOX, $WS_SIZEBOX,
    # $WS_CHILD, $WS_CLIPSIBLINGS, $WS_CLIPCHILDREN, $WS_TABSTOP, $WS_GROUP, $WS_HSCROLL,
    # $WS_VSCROLL, $WS_EX_*.
    _ = (WS_TABSTOP, WS_GROUP, WS_HSCROLL, WS_VSCROLL, WS_BORDER)
    return options
