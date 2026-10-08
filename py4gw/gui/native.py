"""The Windows boundary the AutoIt-compatible GUI layer needs.

AutoIt's GUI *is* Win32: its controls are native classes, its styles are window style bits, and
several of its functions are direct Win32 calls (``GUICtrlSendMsg`` is ``SendMessage``,
``GUISetState(@SW_LOCK)`` is ``LockWindowUpdate``, ``GUIRegisterMsg`` is a window-procedure
hook, ``GUISetIcon``/``GUICtrlCreateIcon`` load icon resources). tkinter's widgets on Windows
are real windows with real handles, so those same calls work on them — which is how this port
reaches parity instead of approximating.

This module is the only place in `py4gw/gui` that declares `ctypes` APIs, in the same way
`py4gw/win32/win32.py` is the process boundary for the rest of the library. Nothing here
touches the game client: these are window, message and icon APIs for the port's own windows.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Any, Callable

from py4gw.gui.constants import (
    ACM_OPENW,
    ACM_PLAY,
    ACM_STOP,
    DTM_GETSYSTEMTIME,
    DTM_SETSYSTEMTIME,
    GDT_ERROR,
    GDT_VALID,
    MCM_GETCURSEL,
    MCM_GETMONTHRANGE,
    MCM_SETCURSEL,
    STM_SETIMAGE,
)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_shell32 = ctypes.WinDLL("shell32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# --- window messages the port sends or watches ------------------------------------------

WM_SETICON = 0x0080
WM_SETFONT = 0x0030
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_DEFAULTSIZE = 0x0040
LR_LOADFROMFILE = 0x0010

GWL_WNDPROC = -4
GWL_EXSTYLE = -20

#: ``$GUI_RUNDEFMSG``: the value an AutoIt message function returns to say "let the default
#: handler run". The port chains to the window's original procedure for this value.
GUI_RUNDEFMSG = "GUI_RUNDEFMSG"

# --- function signatures ------------------------------------------------------------------

_user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.SendMessageW.restype = ctypes.c_ssize_t
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.LockWindowUpdate.argtypes = [wintypes.HWND]
_user32.LockWindowUpdate.restype = wintypes.BOOL
_user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
_user32.LoadImageW.restype = wintypes.HANDLE
_shell32.ExtractIconExW.argtypes = [
    wintypes.LPCWSTR,
    ctypes.c_int,
    ctypes.POINTER(wintypes.HICON),
    ctypes.POINTER(wintypes.HICON),
    wintypes.UINT,
]
_shell32.ExtractIconExW.restype = wintypes.UINT
_user32.DestroyIcon.argtypes = [wintypes.HICON]
_user32.DestroyIcon.restype = wintypes.BOOL
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int


def get_window_text(handle: int) -> str:
    """Read a window's own text, which is what AutoIt's ``GUICtrlRead`` reports.

    tkinter keeps an Entry's string in Tk as well as in the window, so a change made to the
    window from outside — an UpDown writing its buddy through ``$UDS_SETBUDDYINT`` — is invisible
    to ``Entry.get()`` until the port asks the window itself.
    """

    buffer = ctypes.create_unicode_buffer(4096)
    _user32.GetWindowTextW(wintypes.HWND(handle), buffer, 4096)
    return buffer.value

_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)

if sys.maxsize > 2**32:
    _set_window_long = _user32.SetWindowLongPtrW
    _set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    _set_window_long.restype = ctypes.c_void_p
    _get_window_long = _user32.GetWindowLongPtrW
    _call_window_proc = _user32.CallWindowProcW
else:
    _set_window_long = _user32.SetWindowLongW
    _set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    _set_window_long.restype = ctypes.c_void_p
    _get_window_long = _user32.GetWindowLongW
    _call_window_proc = _user32.CallWindowProcW
_call_window_proc.argtypes = [
    ctypes.c_void_p,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_call_window_proc.restype = ctypes.c_ssize_t
_get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
_get_window_long.restype = ctypes.c_void_p


def last_error() -> int:
    """Return the last Windows error the window APIs produced."""

    return ctypes.get_last_error()


# --- messages -----------------------------------------------------------------------------


def send_message(handle: int, message: int, wparam: int, lparam: int) -> int:
    """Send a window message and return the value ``SendMessage`` returned.

    This is what ``GUICtrlSendMsg`` is in AutoIt, and tkinter's widgets are windows, so the
    message reaches the control's own window procedure.

    A synchronous send to a *hooked* window would otherwise call this module's Python window
    procedure back from inside Python, on the same thread — a re-entry whose stack handling is
    not reliable. While the port sends, the hook therefore answers the message itself and leaves
    it to the window's own procedure, which is what a nested message should do.
    """

    global _in_hook
    guard = handle in _hooked and not _in_hook
    if guard:
        _in_hook = True
    try:
        return int(_user32.SendMessageW(wintypes.HWND(handle), message, wparam, lparam))
    finally:
        if guard:
            _in_hook = False


def send_message_text(handle: int, message: int, wparam: int, text: str) -> int:
    """Send a window message whose lParam is a pointer to a string."""

    buffer = ctypes.create_unicode_buffer(text)
    return send_message(handle, message, wparam, ctypes.cast(buffer, ctypes.c_void_p).value or 0)


def send_message_buffer(handle: int, message: int, wparam: int, size: int) -> tuple[int, str]:
    """Send a message whose lParam is a writable buffer, and return (result, text)."""

    buffer = ctypes.create_unicode_buffer(size)
    result = send_message(
        handle, message, wparam, ctypes.cast(buffer, ctypes.c_void_p).value or 0
    )
    return result, buffer.value


def post_message(handle: int, message: int, wparam: int, lparam: int) -> bool:
    """Post a window message without waiting for it to be handled."""

    return bool(_user32.PostMessageW(wintypes.HWND(handle), message, wparam, lparam))


def send_message_rect(handle: int, message: int, wparam: int) -> tuple[int, list[int]]:
    """Send a message whose lParam is a RECT the control fills in."""

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    rect = _RECT()
    result = send_message(handle, message, wparam, ctypes.cast(ctypes.byref(rect),
                                                               ctypes.c_void_p).value or 0)
    return result, [rect.left, rect.top, rect.right, rect.bottom]


# --- painting lock -------------------------------------------------------------------------


def lock_window_update(handle: int) -> bool:
    """Lock a window's painting, which is what ``GUISetState(@SW_LOCK)`` does in AutoIt."""

    return bool(_user32.LockWindowUpdate(wintypes.HWND(handle)))


def unlock_window_update() -> bool:
    """Unlock any locked window: ``LockWindowUpdate(None)`` unlocks, as AutoIt documents."""

    return bool(_user32.LockWindowUpdate(None))


# --- icons ---------------------------------------------------------------------------------


def load_icon(iconfile: str, iconindex: int = -1) -> int:
    """Load an icon out of a file or DLL, the way AutoIt's icon functions do.

    A negative ``iconindex`` selects the 1-based resource index AutoIt documents; a
    non-negative one selects the same icon by name.
    """

    if not iconfile:
        return 0
    small = wintypes.HICON()
    large = wintypes.HICON()
    if iconindex < 0:
        count = _shell32.ExtractIconExW(
            iconfile, abs(iconindex) - 1, ctypes.byref(large), ctypes.byref(small), 2
        )
    else:
        count = _shell32.ExtractIconExW(
            iconfile, iconindex, ctypes.byref(large), ctypes.byref(small), 2
        )
    if not count:
        handle = _user32.LoadImageW(
            None, iconfile, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        return int(handle) if handle else 0
    if small:
        return int(small.value or 0)
    return int(large.value or 0)


def set_window_icon(handle: int, icon: int) -> bool:
    """Set a window's icon, which is what ``GUISetIcon`` and ``GUICtrlSetImage`` end in.

    ``WM_SETICON`` returns the *previous* icon, which is 0 for a window that had none, so its
    return value says nothing about success — the failure that matters is having no icon
    handle to set, which is checked here.
    """

    if not icon:
        return False
    _user32.SendMessageW(wintypes.HWND(handle), WM_SETICON, ICON_SMALL, icon)
    _user32.SendMessageW(wintypes.HWND(handle), WM_SETICON, ICON_BIG, icon)
    return True


# --- window-procedure hooking (GUIRegisterMsg) --------------------------------------------

#: One entry per window whose procedure the port has hooked: the hook object (kept alive, or
#: Windows would call freed memory) and the original procedure to chain to.
_hooked: dict[int, tuple[Any, int]] = {}


#: Set while a hooked window's messages are being handed to Python. A ``SendMessage`` from Python
#: to a hooked window calls the hook back *synchronously*, on the thread that is already inside
#: Python; calling back into Python from there is what corrupts the interpreter's thread state,
#: so a nested message is left to the window's own procedure instead.
_in_hook = False


def hook_messages(
    handle: int,
    handler: Callable[[int, int, int, int], Any],
) -> bool:
    """Hook a window's message procedure and report every message to ``handler``.

    ``handler`` returns ``$GUI_RUNDEFMSG`` (or nothing) to let the window's own procedure run,
    and any other value to answer the message itself — which is the reference's rule for a
    registered message function.
    """

    if handle in _hooked:
        return True
    current = _set_window_long(wintypes.HWND(handle), GWL_WNDPROC, None)
    original = int(current or 0)
    if not original:
        return False

    def procedure(
        hwnd: int, message: int, wparam: int, lparam: int
    ) -> int:  # pragma: no cover - called by Windows
        global _in_hook
        if _in_hook:
            return int(_call_window_proc(original, hwnd, message, wparam, lparam))
        _in_hook = True
        try:
            result = handler(hwnd, message, wparam, lparam)
            if result is not None and result != GUI_RUNDEFMSG:
                return int(result)
            return int(_call_window_proc(original, hwnd, message, wparam, lparam))
        except Exception:  # noqa: BLE001 - an exception must not cross into Windows
            import traceback

            traceback.print_exc()
            return int(_call_window_proc(original, hwnd, message, wparam, lparam))
        finally:
            _in_hook = False

    hook = _WNDPROC(procedure)
    if not _set_window_long(wintypes.HWND(handle), GWL_WNDPROC, ctypes.cast(hook, ctypes.c_void_p)):
        # Setting the procedure returns the previous value; a zero return means failure.
        error = last_error()
        if error:
            return False
    _hooked[handle] = (hook, original)
    return True


def unhook_messages(handle: int) -> bool:
    """Restore a window's own message procedure."""

    entry = _hooked.pop(handle, None)
    if entry is None:
        return False
    hook, original = entry
    _set_window_long(wintypes.HWND(handle), GWL_WNDPROC, ctypes.c_void_p(original))
    _ = hook
    return True


# --- native controls ------------------------------------------------------------------------
#
# AutoIt's Date, MonthCal, Avi and Icon controls are Win32 classes (SysDateTimePick32,
# SysMonthCal32, SysAnimate32 and Static), and tkinter has no widget for any of them. Because
# the port's windows and frames are real windows, the port creates the same classes as children
# of the tkinter frame a control would have been placed in: same class, same styles, same
# messages, and Windows keeps the child positioned inside that frame.

GWL_STYLE = -16
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SW_HIDE = 0
SW_SHOW = 5
DEFAULT_GUI_FONT = 17
DATE_SHORTDATE = 0x00000001
DATE_LONGDATE = 0x00000002
LOCALE_USER_DEFAULT = 0x0400

#: MonthCal's ``MCM_GETMONTHRANGE`` flags. The Windows SDK defines them; AutoIt's include files
#: do not, so they are declared here with the values the SDK gives them. ``GMR_VISIBLE`` gives
#: the first and last day of the month the control is displaying, which is the base the day
#: index below is counted from; ``GMR_DAYSTATE`` gives the day-state range, which spills into
#: the neighbouring months and is therefore not a month.
GMR_VISIBLE = 0
GMR_DAYSTATE = 1

#: ``MCM_GETCURFOCUS``/``MCM_SETCURFOCUS``. AutoIt's includes define neither, and the SDK gives
#: them these values. A script-set day is the control's *focus* day: MCM_SETCURSEL sets it and
#: MCM_GETCURSEL does not report it, while a day the user clicks sets both.
MCM_GETCURFOCUS = 0x1003
MCM_SETCURFOCUS = 0x1004

#: ``MCM_GETCALENDARGRIDINFO`` and its ``MCGRIDINFO`` parts and flags. AutoIt's includes define
#: none of these; the values are the Windows SDK's, and this is the documented way to learn
#: which day a month calendar has selected.
MCM_GETCALENDARGRIDINFO = 0x1018
MCGIP_CALENDAR = 0x4
MCGIP_CALENDARCELL = 0x6
MCGIF_DATE = 0x1

VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_LEFT = 0x25
VK_RIGHT = 0x27
WM_KEYDOWN = 0x0100

_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
_user32.CreateWindowExW.restype = wintypes.HWND
_user32.DestroyWindow.argtypes = [wintypes.HWND]
_user32.DestroyWindow.restype = wintypes.BOOL
_user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
_user32.SetWindowPos.restype = wintypes.BOOL
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_gdi32.GetStockObject.argtypes = [ctypes.c_int]
_gdi32.GetStockObject.restype = wintypes.HANDLE
_gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.LPCWSTR,
]
_gdi32.CreateFontW.restype = wintypes.HANDLE
_gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
_gdi32.GetObjectW.restype = ctypes.c_int
_gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
_gdi32.DeleteObject.restype = wintypes.BOOL
_kernel32.GetDateFormatW.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_int,
]
_kernel32.GetDateFormatW.restype = ctypes.c_int


class SYSTEMTIME(ctypes.Structure):
    """The Win32 ``SYSTEMTIME`` the date and calendar controls exchange."""

    _fields_ = [
        ("wYear", wintypes.WORD),
        ("wMonth", wintypes.WORD),
        ("wDayOfWeek", wintypes.WORD),
        ("wDay", wintypes.WORD),
        ("wHour", wintypes.WORD),
        ("wMinute", wintypes.WORD),
        ("wSecond", wintypes.WORD),
        ("wMilliseconds", wintypes.WORD),
    ]


class MCGRIDINFO(ctypes.Structure):
    """The Win32 ``MCGRIDINFO`` a month calendar fills in for one part of its grid."""

    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwPart", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("iCalendar", ctypes.c_int),
        ("iRow", ctypes.c_int),
        ("iCol", ctypes.c_int),
        ("bSelected", wintypes.BOOL),
        ("stStart", SYSTEMTIME),
        ("stEnd", SYSTEMTIME),
        ("rc", wintypes.RECT),
        ("pszName", wintypes.LPWSTR),
        ("cchName", ctypes.c_size_t),
    ]


def create_control(
    class_name: str,
    text: str,
    style: int,
    ex_style: int,
    parent: int,
    left: int,
    top: int,
    width: int,
    height: int,
) -> int:
    """Create one of the Win32 control classes AutoIt uses, as a child of a tkinter frame."""

    handle = _user32.CreateWindowExW(
        ex_style,
        class_name,
        text,
        style,
        left,
        top,
        width,
        height,
        wintypes.HWND(parent),
        None,
        None,
        None,
    )
    return int(handle or 0)


def destroy_window(handle: int) -> bool:
    """Destroy a native control."""

    return bool(_user32.DestroyWindow(wintypes.HWND(handle)))


def window_exists(handle: int) -> bool:
    """Return whether a window handle still names a live window."""

    return bool(_user32.IsWindow(wintypes.HWND(handle)))


def move_window(handle: int, left: int, top: int, width: int, height: int) -> bool:
    """Move and resize a native control inside its parent."""

    return bool(
        _user32.SetWindowPos(
            wintypes.HWND(handle),
            None,
            left,
            top,
            width,
            height,
            SWP_NOZORDER | SWP_NOACTIVATE,
        )
    )


def show_window(handle: int, visible: bool) -> bool:
    """Show or hide a native control (``$GUI_SHOW``/``$GUI_HIDE``)."""

    return bool(_user32.ShowWindow(wintypes.HWND(handle), SW_SHOW if visible else SW_HIDE))


def get_style(handle: int) -> int:
    """Read a native control's window style."""

    return int(_get_window_long(wintypes.HWND(handle), GWL_STYLE) or 0) & 0xFFFFFFFF


def get_exstyle(handle: int) -> int:
    """Read a native control's extended window style, the second half of ``GUIGetStyle``."""

    return int(_get_window_long(wintypes.HWND(handle), GWL_EXSTYLE) or 0) & 0xFFFFFFFF


def get_parent(handle: int) -> int:
    """Read a window's parent, which is the window a child control or tooltip belongs to."""

    return int(_user32.GetParent(wintypes.HWND(handle)) or 0)


#: The Windows keys, which AutoIt's accelerator syntax spells ``#`` and tkinter cannot spell at all.
VK_LWIN = 0x5B
VK_RWIN = 0x5C


def win_key_down() -> bool:
    """Return whether a Windows key is held, which is what AutoIt's ``#`` accelerator means.

    Read through ``GetAsyncKeyState``, whose high bit says the key is down. The state is the
    system's, not tkinter's: a Tk binding for the base key fires whether or not the Windows key is
    held (measured), so the check is what distinguishes the chord (``probe_autoit_updown``'s
    sibling readings in ``docs/AUTOIT_GUI.md``).
    """

    return bool(
        _user32.GetAsyncKeyState(VK_LWIN) & 0x8000
        or _user32.GetAsyncKeyState(VK_RWIN) & 0x8000
    )


def window_rect(handle: int) -> tuple[int, int, int, int]:
    """Read a window's screen rectangle, which is where a native control really is.

    A control's recorded box is where the port placed it; this is the control's own window, and the
    two can differ — an UpDown aligns itself to its buddy and was measured 1x1 while the port's
    record said 18x22 at the input's right edge.
    """

    rect = wintypes.RECT()
    _user32.GetWindowRect(wintypes.HWND(handle), ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def set_style(handle: int, style: int) -> bool:
    """Replace a native control's window style and let it re-create its frame."""

    _set_window_long(wintypes.HWND(handle), GWL_STYLE, ctypes.c_void_p(style))
    return bool(
        _user32.SetWindowPos(wintypes.HWND(handle), None, 0, 0, 0, 0,
                             SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    )


def apply_default_font(handle: int) -> None:
    """Give a native control the system's GUI font, which is what AutoIt's controls use."""

    font = _gdi32.GetStockObject(DEFAULT_GUI_FONT)
    if font:
        _user32.SendMessageW(wintypes.HWND(handle), WM_SETFONT, int(font), 1)


#: AutoIt's Font Quality table (``GUICtrlSetFont.htm``) is the GDI one, value for value: 0 default,
#: 1 draft, 2 proof, 3 nonantialiased, 4 antialiased, 5 cleartype. So a requested quality goes
#: straight into ``CreateFontW``, and what the control's own ``LOGFONT`` holds is the check.
WM_SETFONT = 0x0030
WM_GETFONT = 0x0031
PROOF_QUALITY = 2

#: The heights ``CreateFontW`` takes are in logical units, and AutoIt's ``size`` is in points:
#: a point is 1/72 inch and a logical unit is 1/72 inch of the *font's* height at 72 dpi, so the
#: height is the point size *negated* — which is how Windows names a character height rather than a
#: cell height ("the font mapper ... a negative value means character height"). AutoIt sizes a
#: control's font from the same rule; the interpreter's own default is 8.5 points.
_POINTS_TO_HEIGHT = -1


def create_font(
    size: float,
    weight: int = 400,
    attribute: int = 0,
    fontname: str = "",
    quality: int = PROOF_QUALITY,
) -> int:
    """Create a GDI font from AutoIt's font parameters, and return its handle (0 on failure).

    ``weight`` is the Win32 weight (400 normal, 700 bold); ``attribute`` is the sum of
    ``$GUI_FONTITALIC`` (2), ``$GUI_FONTUNDER`` (4) and ``$GUI_FONTSTRIKE`` (8); ``quality`` is the
    Font Quality table's value, which this passes on unchanged.
    """

    height = int(round(size * _POINTS_TO_HEIGHT))
    font = _gdi32.CreateFontW(
        height,
        0,                                              # width: let the mapper choose
        0,                                              # escapement
        0,                                              # orientation
        int(weight) if weight else 400,                 # lfWeight
        int(bool(attribute & 2)),                       # $GUI_FONTITALIC
        int(bool(attribute & 4)),                       # $GUI_FONTUNDER
        int(bool(attribute & 8)),                       # $GUI_FONTSTRIKE
        0,                                              # lfCharSet (ANSI)
        0,                                              # lfOutPrecision
        0,                                              # lfClipPrecision
        int(quality),                                   # lfQuality: AutoIt's table, value for value
        0,                                              # lfPitchAndFamily
        str(fontname) if fontname else None,
    )
    return int(font or 0)


def set_window_font(handle: int, font: int) -> bool:
    """Give a window a font, the way every control's font is set in Win32."""

    return bool(_user32.SendMessageW(wintypes.HWND(handle), WM_SETFONT, font, 1))


def window_font_quality(handle: int) -> int:
    """Return the ``lfQuality`` of the font a window carries, as a check that it was set.

    ``WM_GETFONT`` names the font a control is drawing with, and ``GetObjectW`` fills a
    ``LOGFONTW`` from it, whose last field is the quality.
    """

    font = _user32.SendMessageW(wintypes.HWND(handle), WM_GETFONT, 0, 0)
    if not font:
        return -1
    logfont = LOGFONTW()
    written = _gdi32.GetObjectW(wintypes.HANDLE(int(font)), ctypes.sizeof(logfont),
                                ctypes.byref(logfont))
    if written != ctypes.sizeof(logfont):
        return -1
    return int(logfont.lfQuality)


def delete_font(font: int) -> bool:
    """Delete a font this module created."""

    return bool(font) and bool(_gdi32.DeleteObject(wintypes.HANDLE(font)))


class LOGFONTW(ctypes.Structure):
    """The ``LOGFONTW`` a font reports itself through."""

    _fields_ = [
        ("lfHeight", wintypes.LONG),
        ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG),
        ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG),
        ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE),
        ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE),
        ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE),
        ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE),
        ("lfFaceName", wintypes.WCHAR * 32),
    ]


# --- pictures (GUICtrlCreatePic / GUICtrlSetImage) ------------------------------------------
#
# tkinter's PhotoImage reads PNG and GIF; AutoIt's Pic control reads BMP and JPG (and its Icon
# control reads icons). Windows has a decoder for all of them in GDI+, which is what this uses:
# the file is read into an HBITMAP through GdipCreateBitmapFromFile, and its pixels are handed
# over as plain RGB rows. What tkinter can read is left to tkinter (it keeps an image's alpha),
# and this is the path for the formats it cannot.

_gdiplus = ctypes.WinDLL("gdiplus", use_last_error=True)


class _GDIPLUSSTARTUPINPUT(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", wintypes.UINT),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


class _GDIPLUSBITMAPDATA(ctypes.Structure):
    _fields_ = [
        ("width", wintypes.UINT),
        ("height", wintypes.UINT),
        ("stride", ctypes.c_int),
        ("pixel_format", ctypes.c_int),
        ("scan0", ctypes.c_void_p),
        ("reserved", ctypes.c_void_p),
    ]


_gdiplus.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                    ctypes.POINTER(_GDIPLUSSTARTUPINPUT), ctypes.c_void_p]
_gdiplus.GdiplusStartup.restype = ctypes.c_int
_gdiplus.GdipCreateBitmapFromFile.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
_gdiplus.GdipCreateBitmapFromFile.restype = ctypes.c_int
_gdiplus.GdipGetImageWidth.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
_gdiplus.GdipGetImageWidth.restype = ctypes.c_int
_gdiplus.GdipGetImageHeight.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
_gdiplus.GdipGetImageHeight.restype = ctypes.c_int
_gdiplus.GdipBitmapLockBits.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, ctypes.c_int,
    ctypes.POINTER(_GDIPLUSBITMAPDATA),
]
_gdiplus.GdipBitmapLockBits.restype = ctypes.c_int
_gdiplus.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(_GDIPLUSBITMAPDATA)]
_gdiplus.GdipBitmapUnlockBits.restype = ctypes.c_int
_gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]
_gdiplus.GdipDisposeImage.restype = ctypes.c_int

#: The pixel format GDI+ hands back for 32 bits per pixel, and the one ImageLockModeRead asks for.
_PIXEL_FORMAT_32BPP_ARGB = 0x0026200A
_IMAGE_LOCK_MODE_READ = 1
_gdiplus_token = ctypes.c_void_p()


def _start_gdiplus() -> bool:
    """Start GDI+ once, which every GDI+ call needs first."""

    global _gdiplus_token
    if _gdiplus_token:
        return True
    startup = _GDIPLUSSTARTUPINPUT()
    startup.GdiplusVersion = 1
    if _gdiplus.GdiplusStartup(ctypes.byref(_gdiplus_token), ctypes.byref(startup), None) != 0:
        _gdiplus_token = ctypes.c_void_p()
        return False
    return True


def load_image_pixels(filename: str, size: int = 512) -> tuple[int, int, bytes] | None:
    """Read an image file with Windows' own decoder, as ``(width, height, RGB rows)``.

    Returns ``None`` when the file cannot be read. ``size`` bounds the *area* the caller accepts:
    an image wider or taller than it is refused rather than allocated, because the rows are copied
    into Python bytes.
    """

    if not _start_gdiplus():
        return None
    bitmap = ctypes.c_void_p()
    if _gdiplus.GdipCreateBitmapFromFile(str(filename), ctypes.byref(bitmap)) != 0 or not bitmap:
        return None
    try:
        width = wintypes.UINT()
        height = wintypes.UINT()
        if _gdiplus.GdipGetImageWidth(bitmap, ctypes.byref(width)) != 0:
            return None
        if _gdiplus.GdipGetImageHeight(bitmap, ctypes.byref(height)) != 0:
            return None
        if not width.value or not height.value:
            return None
        if width.value > size or height.value > size:
            return None
        data = _GDIPLUSBITMAPDATA()
        # The rectangle GDI+ locks names the pixels it gives back — the whole image — and it is
        # four ints, which is what GpRect is (a float rect comes back as InvalidParameter).
        rectangle = (ctypes.c_int * 4)(0, 0, int(width.value), int(height.value))
        if _gdiplus.GdipBitmapLockBits(
            bitmap, ctypes.byref(rectangle), _IMAGE_LOCK_MODE_READ, _PIXEL_FORMAT_32BPP_ARGB,
            ctypes.byref(data),
        ) != 0:
            return None
        try:
            rows = bytearray()
            scan0 = int(data.scan0 or 0)
            for row in range(data.height):
                # GDI+ hands back BGRA; a Tk photo wants RGB.
                source = ctypes.string_at(scan0 + row * data.stride, data.width * 4)
                for index in range(0, len(source), 4):
                    rows += bytes((source[index + 2], source[index + 1], source[index]))
            return (int(data.width), int(data.height), bytes(rows))
        finally:
            _gdiplus.GdipBitmapUnlockBits(bitmap, ctypes.byref(data))
    finally:
        _gdiplus.GdipDisposeImage(bitmap)


# --- the Date control (SysDateTimePick32) ----------------------------------------------------


def date_get_parts(handle: int) -> tuple[int, int, int] | None:
    """Read a Date control's selected date as (year, month, day), or None when it has none."""

    value = SYSTEMTIME()
    result = send_message(
        handle, DTM_GETSYSTEMTIME, GDT_VALID, ctypes.cast(ctypes.byref(value),
                                                          ctypes.c_void_p).value or 0
    )
    if result != GDT_VALID:
        return None
    return (value.wYear, value.wMonth, value.wDay)


def date_set_parts(handle: int, year: int, month: int, day: int) -> bool:
    """Set a Date control's date from its parts."""

    value = SYSTEMTIME()
    value.wYear = year
    value.wMonth = month
    value.wDay = day
    result = send_message(
        handle, DTM_SETSYSTEMTIME, GDT_VALID, ctypes.cast(ctypes.byref(value),
                                                          ctypes.c_void_p).value or 0
    )
    return result != GDT_ERROR


def format_date(parts: tuple[int, int, int], long_format: bool) -> str:
    """Format a date the way the regional settings do, as ``GUICtrlRead`` reports a Date.

    ``GetDateFormatEx`` with the user's locale is what the control itself draws with, so a long
    format reads like "Friday, January 2, 2026" and a short one like "3/4/2027".
    """

    value = SYSTEMTIME()
    value.wYear, value.wMonth, value.wDay = parts
    buffer = ctypes.create_unicode_buffer(128)
    flags = DATE_LONGDATE if long_format else DATE_SHORTDATE
    written = _kernel32.GetDateFormatW(
        LOCALE_USER_DEFAULT, flags, ctypes.byref(value), None, buffer, 128
    )
    if not written:
        return f"{parts[0]:04d}/{parts[1]:02d}/{parts[2]:02d}"
    return buffer.value


# --- the MonthCal control (SysMonthCal32) ----------------------------------------------------


def monthcal_get_parts(handle: int) -> tuple[int, int, int] | None:
    """Read a MonthCal's selected date as (year, month, day), or None when it has none.

    The day index a month calendar keeps is counted from the first day of the month it is
    displaying, which ``MCM_GETMONTHRANGE`` with ``GMR_VISIBLE`` reports; the index itself is
    the control's focus day, because a script-set day (``MCM_SETCURSEL``) is not what
    ``MCM_GETCURSEL`` reports while a day the user clicks sets both. Measured on the control:
    ``GMR_VISIBLE`` returned (2026-10-01 .. 2026-10-31) for the October 2026 view, and
    ``MCM_SETCURSEL(1)`` then ``MCM_GETCURFOCUS`` returned 1.
    """

    index = send_message(handle, MCM_GETCURFOCUS, 0, 0)
    if index < 0:
        return None
    first, _last = _monthcal_range(handle, GMR_VISIBLE)
    if first is None:
        return None
    return (first.wYear, first.wMonth, index + 1)


def monthcal_set_parts(handle: int, year: int, month: int, day: int) -> bool:
    """Select a date in a MonthCal, moving its view to that month and then to that day.

    A month calendar has no message that sets either the displayed month or the selected day
    directly: ``MCM_SETCURSEL`` does not move the day this control reports, and Page Up/Page
    Down keep the day of the month while they change the month. The port therefore walks the
    view with Page Up/Page Down and then steps the day with the left/right keys, which is what
    a user pressing those keys does. Measured on the control: 35 right-key messages moved the
    view from October 2026 to November 2026.
    """

    if not _monthcal_show_month(handle, year, month):
        return False
    for _ in range(64):
        current = monthcal_get_parts(handle)
        if current is None:
            return False
        if current == (year, month, day):
            return True
        if current[0] != year or current[1] != month:
            # A step crossed a month boundary; put the view back and stop.
            if not _monthcal_show_month(handle, year, month):
                return False
            return False
        key = VK_RIGHT if current[2] < day else VK_LEFT
        send_message(handle, WM_KEYDOWN, key, 0)
    return monthcal_get_parts(handle) == (year, month, day)


def monthcal_selected_parts(handle: int) -> tuple[int, int, int] | None:
    """Return the day the user selected in a MonthCal, or None when it has no selection.

    Windows offers no message that returns a month calendar's selected date, so this walks the
    displayed calendar's cells with ``MCM_GETCALENDARGRIDINFO`` and returns the cell the control
    flags as selected. A calendar no one has clicked reports no selection at all, which is what
    makes a script-set date a matter of the port's own record (see ``GUI.GUICtrlSetData``).
    """

    for row in range(7):
        for column in range(7):
            info = _monthcal_grid_info(handle, MCGIP_CALENDARCELL, row, column)
            if info is None:
                continue
            if info.bSelected:
                return (info.stStart.wYear, info.stStart.wMonth, info.stStart.wDay)
    return None


def monthcal_show_month(handle: int, year: int, month: int) -> bool:
    """Bring a MonthCal's displayed month to a month, which also puts its date in view."""

    return _monthcal_show_month(handle, year, month)


def monthcal_month_range(handle: int) -> tuple[int, int] | None:
    """Return the (year, month) a MonthCal is displaying."""

    first, _last = _monthcal_range(handle, GMR_VISIBLE)
    if first is None:
        return None
    return (first.wYear, first.wMonth)


def _monthcal_grid_info(
    handle: int, part: int, row: int = 0, column: int = 0
) -> MCGRIDINFO | None:
    """Ask a MonthCal for one piece of its calendar grid (``MCM_GETCALENDARGRIDINFO``)."""

    info = MCGRIDINFO()
    info.cbSize = ctypes.sizeof(MCGRIDINFO)
    info.dwPart = part
    info.dwFlags = MCGIF_DATE
    info.iRow = row
    info.iCol = column
    result = send_message(
        handle,
        MCM_GETCALENDARGRIDINFO,
        0,
        ctypes.cast(ctypes.byref(info), ctypes.c_void_p).value or 0,
    )
    return info if result else None


def _monthcal_range(handle: int, flag: int) -> tuple[SYSTEMTIME | None, SYSTEMTIME | None]:
    """Read a MonthCal's month range for ``GMR_VISIBLE`` or ``GMR_DAYSTATE``."""

    values = (SYSTEMTIME * 2)()
    count = send_message(
        handle, MCM_GETMONTHRANGE, flag, ctypes.cast(values, ctypes.c_void_p).value or 0
    )
    if count <= 0:
        return (None, None)
    return (values[0], values[1])


def _monthcal_show_month(handle: int, year: int, month: int) -> bool:
    """Move a MonthCal's view to a month, one month at a time, and report success."""

    for _ in range(240):  # two decades of months either way, then give up
        first, _last = _monthcal_range(handle, GMR_VISIBLE)
        if first is None:
            return False
        current = (first.wYear, first.wMonth)
        if current == (year, month):
            return True
        months = (year - current[0]) * 12 + (month - current[1])
        key = VK_NEXT if months > 0 else VK_PRIOR
        send_message(handle, WM_KEYDOWN, key, 0)
    return False


# --- the Avi control (SysAnimate32) and the Icon control (Static + $SS_ICON) -----------------


def avi_open(handle: int, filename: str) -> bool:
    """Open an AVI file in an Avi control, or release it when the name is empty."""

    if not filename:
        send_message(handle, ACM_OPENW, 0, 0)
        return True
    buffer = ctypes.create_unicode_buffer(filename)
    result = send_message(
        handle, ACM_OPENW, 0, ctypes.cast(buffer, ctypes.c_void_p).value or 0
    )
    return bool(result)


def avi_play(handle: int, repeat: int = -1) -> None:
    """Play the opened clip: ``ACM_PLAY`` with from 0 to -1 plays every frame."""

    send_message(handle, ACM_PLAY, repeat & 0xFFFFFFFF, 0xFFFFFFFF00000000 | 0xFFFF)


def avi_stop(handle: int) -> None:
    """Stop the clip."""

    send_message(handle, ACM_STOP, 0, 0)


def icon_set(handle: int, icon: int) -> bool:
    """Give a Static control an icon (``STM_SETIMAGE``), which is AutoIt's Icon control."""

    return bool(send_message(handle, STM_SETIMAGE, IMAGE_ICON, icon))


# --- the UpDown control (msctls_updown32) ---------------------------------------------------

#: The up-down control's messages and its one notification. ``UpDownConstants.au3`` defines the
#: ``$UDS_*`` styles and none of these, so they carry the Windows SDK's values.
UPDOWN_CLASS = "msctls_updown32"
UDM_SETBUDDY = 0x0469
UDM_SETRANGE32 = 0x046F
UDM_GETPOS32 = 0x0472
UDM_SETPOS32 = 0x0471
UDN_DELTAPOS = -722


def updown_set_buddy(handle: int, buddy: int) -> bool:
    """Attach an UpDown to its buddy Input, which is what ``$UDS_SETBUDDYINT`` writes into."""

    return bool(send_message(handle, UDM_SETBUDDY, buddy, 0))


def updown_set_range(handle: int, minimum: int, maximum: int) -> bool:
    """Set an UpDown's range, which is what ``GUICtrlSetLimit`` does for it.

    ``UDM_SETRANGE32`` returns the range the control had before, not a success flag, so a zero
    return says nothing about whether the range was set.
    """

    send_message(handle, UDM_SETRANGE32, minimum & 0xFFFFFFFF, maximum)
    return True


def updown_get_position(handle: int) -> int:
    """Read an UpDown's position."""

    return send_message(handle, UDM_GETPOS32, 0, 0)


def updown_set_position(handle: int, position: int) -> int:
    """Set an UpDown's position, which is what clicking its arrows does."""

    return send_message(handle, UDM_SETPOS32, 0, position)


# --- dropped files ($GUI_DROPACCEPTED, $GUI_EVENT_DROPPED) -----------------------------------

#: ``WM_DROPFILES`` and the flags a dropped-file payload carries. AutoIt accepts drops by
#: letting Windows hand its controls this message, which is what the port does too.
WM_DROPFILES = 0x0233
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

_shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
_shell32.DragAcceptFiles.restype = None
_shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
_shell32.DragQueryFileW.restype = wintypes.UINT
_shell32.DragFinish.argtypes = [wintypes.HANDLE]
_shell32.DragFinish.restype = None
_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
_kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalLock.restype = wintypes.LPVOID
_kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalUnlock.restype = wintypes.BOOL


def drag_accept(handle: int, accept: bool) -> None:
    """Let a window accept dropped files, which is what ``$GUI_DROPACCEPTED`` turns on."""

    _shell32.DragAcceptFiles(wintypes.HWND(handle), accept)


def dropped_files(drop: int) -> list[str]:
    """Return the file names a ``WM_DROPFILES`` message carries, and release the payload."""

    count = _shell32.DragQueryFileW(wintypes.HANDLE(drop), 0xFFFFFFFF, None, 0)
    names: list[str] = []
    for index in range(count):
        size = _shell32.DragQueryFileW(wintypes.HANDLE(drop), index, None, 0) + 1
        buffer = ctypes.create_unicode_buffer(size)
        _shell32.DragQueryFileW(wintypes.HANDLE(drop), index, buffer, size)
        names.append(buffer.value)
    _shell32.DragFinish(wintypes.HANDLE(drop))
    return names


def make_drop_payload(paths: list[str], point: tuple[int, int] = (0, 0)) -> int:
    """Build the ``HDROP`` a ``WM_DROPFILES`` message carries, for a test to post.

    A drag cannot be synthesized, so a test builds the same payload Windows would: a
    ``DROPFILES`` header (with the drop point in screen coordinates) followed by the
    double-null-terminated wide file list, in global memory whose handle *is* the ``HDROP``.
    """

    text = "".join(f"{path}\0" for path in paths) + "\0"
    data = text.encode("utf-16-le")
    header_size = 20
    size = header_size + len(data)
    handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, size)
    if not handle:
        return 0
    pointer = _kernel32.GlobalLock(handle)
    if not pointer:
        return 0
    buffer = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_byte * size)).contents
    ctypes.memmove(buffer, ctypes.byref(ctypes.c_uint32(header_size)), 4)
    # The header is pFiles, pt (two longs), fNC and fWide, so the point sits at offset 4 and
    # fWide is the last word.
    ctypes.memmove(ctypes.byref(buffer, 4), ctypes.byref(ctypes.c_int(point[0])), 4)
    ctypes.memmove(ctypes.byref(buffer, 8), ctypes.byref(ctypes.c_int(point[1])), 4)
    ctypes.memmove(ctypes.byref(buffer, 16), ctypes.byref(ctypes.c_int(1)), 4)
    ctypes.memmove(ctypes.byref(buffer, header_size), data, len(data))
    _kernel32.GlobalUnlock(handle)
    return int(handle)


def dropped_point(drop: int) -> tuple[int, int]:
    """Return the screen point a dropped-file payload was dropped at.

    The payload is a global-memory handle whose contents must be locked before they are read,
    exactly as ``DragQueryFile`` does internally.
    """

    pointer = _kernel32.GlobalLock(wintypes.HGLOBAL(drop))
    if not pointer:
        return (0, 0)
    try:
        header = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_int * 5)).contents
        return (header[1], header[2])
    finally:
        _kernel32.GlobalUnlock(wintypes.HGLOBAL(drop))


# --- tooltips (GUICtrlSetTip) ---------------------------------------------------------------

#: The Windows tooltip control AutoIt's ``GUICtrlSetTip`` uses, and the constants its own script
#: sets on it. ``ToolTipConstants.au3`` in the AutoIt installation carries the ``$TTF_*`` and
#: ``$TTM_*`` values below; the styles come from the Windows SDK. What AutoIt builds was measured
#: rather than assumed — see ``tests/autoit_reference/probe_autoit_gui_tip.au3`` and
#: ``probe_autoit_gui_tip2.au3``, and the readings in ``docs/AUTOIT_GUI.md``:
#:
#: * one ``tooltips_class32`` window **per control**, created on the first ``GUICtrlSetTip`` for
#:   that control and holding exactly one tool, its ``uId`` the control's own window;
#: * a call to ``GUICtrlSetTip`` for a control that already has a tip **replaces** the control
#:   (the old tooltip window is gone and a new handle is there afterwards — handler numbers rose
#:   on every call in the probe);
#: * style ``0x84000013`` (``$WS_POPUP|$WS_CLIPSIBLINGS|$TTS_ALWAYSTIP|$TTS_NOPREFIX|$TTS_NOANIMATE``)
#:   with ``$TTS_BALLOON`` (``0x84000053``) for ``$TIP_BALLOON``;
#: * exStyle ``0x00080088`` (``$WS_EX_LAYERED|$WS_EX_TOOLWINDOW|$WS_EX_TOPMOST``);
#: * the GUI window is the tooltip's parent;
#: * tool flags ``0x51``, and ``0x53`` after ``$TIP_CENTER`` — that is ``$TTF_IDISHWND``,
#:   ``$TTF_SUBCLASS``, ``$TTF_CENTERTIP`` and the control's own ``0x40`` bit;
#: * deleting the control removes its tooltip, and deleting the window removes the rest.
TOOLTIPS_CLASS = "tooltips_class32"
TTS_ALWAYSTIP = 0x0001
TTS_NOPREFIX = 0x0002
TTS_NOANIMATE = 0x0010
TTS_BALLOON = 0x0040
TTF_IDISHWND = 0x0001
TTF_CENTERTIP = 0x0002
TTF_SUBCLASS = 0x0010
TTM_SETTITLEW = 0x0421
#: ``WM_USER + 35``. ``0x0435`` is ``TTM_GETTOOLINFOW``, not this message, and asking it for the
#: title answers 0 while ``0x0423`` answers with the title and its icon (measured on a live tooltip).
TTM_GETTITLE = 0x0423
TTM_ADDTOOLW = 0x0432
TTM_DELTOOLW = 0x0433
TTM_ENUMTOOLSW = 0x043A
#: ``WM_USER + 56``. ``0x040D`` is ``TTM_GETTOOLCOUNT`` — it answered 1 for the one tool a
#: tooltip held, which is how the tool's presence and this id were both confirmed.
TTM_GETTEXTW = 0x0438
TTM_GETTOOLCOUNT = 0x040D
TTI_NONE = 0
TTI_INFO = 1
TTI_WARNING = 2
TTI_ERROR = 3
WS_POPUP = 0x80000000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
#: The style and exStyle AutoIt's tip windows carry, as the probe read them back.
TOOLTIP_STYLE = WS_POPUP | WS_CLIPSIBLINGS | TTS_ALWAYSTIP | TTS_NOPREFIX | TTS_NOANIMATE
TOOLTIP_EXSTYLE = WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST


class TOOLINFOW(ctypes.Structure):
    """The ``TOOLINFOW`` a tooltip is given for one tool."""

    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("uId", ctypes.c_size_t),
        ("rect", wintypes.RECT),
        ("hinst", wintypes.HINSTANCE),
        ("lpszText", wintypes.LPWSTR),
        ("lParam", wintypes.LPARAM),
        ("lpReserved", ctypes.c_void_p),
    ]


class TTGETTITLE(ctypes.Structure):
    """The ``TTGETTITLE`` a tooltip reports its title and icon through."""

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("uTitleBitmap", wintypes.UINT),
        ("cch", wintypes.UINT),
        ("pszTitle", wintypes.LPWSTR),
    ]


def create_tooltip(parent: int, balloon: bool = False) -> int:
    """Create one control's tooltip control, with the style and exStyle AutoIt's own carries."""

    style = TOOLTIP_STYLE | (TTS_BALLOON if balloon else 0)
    handle = _user32.CreateWindowExW(
        TOOLTIP_EXSTYLE,
        TOOLTIPS_CLASS,
        None,
        style,
        0,
        0,
        0,
        0,
        wintypes.HWND(parent),
        None,
        None,
        None,
    )
    return int(handle or 0)


def tooltip_add_tool(
    tooltip: int, target: int, text: str, parent: int = 0, center: bool = False
) -> bool:
    """Attach a tooltip to a control, with ``TTF_SUBCLASS`` so the control tracks the mouse.

    ``TTF_IDISHWND`` means the tool is named by its window handle, and that the ``hwnd`` member is
    the window the tool belongs to. ``center`` is ``$TIP_CENTER``, which the probe read as
    ``$TTF_CENTERTIP`` on the tool — not as a width setting on the control.
    """

    info = TOOLINFOW()
    info.cbSize = ctypes.sizeof(TOOLINFOW)
    info.uFlags = TTF_IDISHWND | TTF_SUBCLASS | (TTF_CENTERTIP if center else 0)
    info.hwnd = parent or target
    info.uId = target
    # The buffer is held by name for the length of the call: a string assigned straight to an
    # ``LPWSTR`` member is a temporary, and the tooltip reads it inside the message, not at
    # assignment. The measurement that confirmed the text arrives is in ``docs/AUTOIT_GUI.md``.
    text_buffer = ctypes.create_unicode_buffer(text)
    info.lpszText = ctypes.cast(text_buffer, wintypes.LPWSTR)
    return bool(
        send_message(
            tooltip, TTM_ADDTOOLW, 0, ctypes.cast(ctypes.byref(info), ctypes.c_void_p).value or 0
        )
    )


def tooltip_set_title(tooltip: int, title: str, icon: int = TTI_NONE) -> bool:
    """Give a tooltip the title and icon row ``GUICtrlSetTip``'s title and icon parameters mean."""

    return bool(send_message_text(tooltip, TTM_SETTITLEW, icon, title))


def tooltip_tool_count(tooltip: int) -> int:
    """Return how many tools a tooltip holds, which AutoIt's own tip windows hold one of."""

    return int(send_message(tooltip, TTM_GETTOOLCOUNT, 0, 0))


def tooltip_tool_info(tooltip: int) -> tuple[int, int]:
    """Return the first tool's ``uId`` (the control's window) and its ``uFlags``.

    ``TTM_ENUMTOOLSW`` fills a ``TOOLINFO`` in: index 0 for the one tool a control's tooltip holds.
    Its ``lpszText`` is not a readable pointer — the control keeps the text in its own storage, and
    that is why the text is read with ``TTM_GETTEXTW`` and a buffer of the caller's instead.
    """

    info = TOOLINFOW()
    info.cbSize = ctypes.sizeof(TOOLINFOW)
    send_message(
        tooltip, TTM_ENUMTOOLSW, 0, ctypes.cast(ctypes.byref(info), ctypes.c_void_p).value or 0
    )
    return (int(info.uId), int(info.uFlags))


def tooltip_title(tooltip: int, size: int = 128) -> tuple[int, str]:
    """Read a tooltip's title and icon back, as a check that they were set.

    The icon is the ``uTitleBitmap`` the message fills in, not the value it returns: ``TTM_GETTITLE``
    returns TRUE for success, which reads as icon 1 (``$TIP_INFOICON``) whatever was set.
    """

    buffer = ctypes.create_unicode_buffer(size)
    request = TTGETTITLE()
    request.dwSize = ctypes.sizeof(TTGETTITLE)
    request.cch = size
    request.pszTitle = ctypes.cast(buffer, wintypes.LPWSTR)
    send_message(
        tooltip, TTM_GETTITLE, 0, ctypes.cast(ctypes.byref(request), ctypes.c_void_p).value or 0
    )
    return (int(request.uTitleBitmap), buffer.value)


def tooltip_text(tooltip: int, target: int, parent: int = 0, size: int = 512) -> str:
    """Read back the text a tooltip holds for a control, by the same tool identity it was added."""

    buffer = ctypes.create_unicode_buffer(size)
    info = TOOLINFOW()
    info.cbSize = ctypes.sizeof(TOOLINFOW)
    info.uFlags = TTF_IDISHWND
    info.hwnd = parent or target
    info.uId = target
    info.lpszText = ctypes.cast(buffer, wintypes.LPWSTR)
    send_message(
        tooltip, TTM_GETTEXTW, 0, ctypes.cast(ctypes.byref(info), ctypes.c_void_p).value or 0
    )
    return buffer.value


# --- control notifications (WM_NOTIFY) -----------------------------------------------------


class NMHDR(ctypes.Structure):
    """The ``NMHDR`` every control notification begins with."""

    _fields_ = [
        ("hwndFrom", wintypes.HWND),
        ("idFrom", ctypes.c_size_t),
        ("code", wintypes.UINT),
    ]


class NMSELCHANGE(ctypes.Structure):
    """The ``NMSELCHANGE`` a month calendar sends when a day is chosen."""

    _fields_ = [
        ("nmhdr", NMHDR),
        ("stSelStart", SYSTEMTIME),
        ("stSelEnd", SYSTEMTIME),
    ]


def notify_header(lparam: int) -> tuple[int, int] | None:
    """Read a ``WM_NOTIFY`` message's source window and notification code.

    The code is reported as a *signed* 32-bit value, which is how AutoIt's notification constants
    are defined: every one of them is negative (``$UDN_DELTAPOS`` -722, ``$DTN_DATETIMECHANGE``
    -759, ``$MCN_SELECT`` -753). Read as an unsigned ``UINT`` the same code comes back as
    4294966574, which matches none of them (measured: a posted ``$UDN_DELTAPOS`` reached the hook
    and fired nothing).
    """

    if not lparam:
        return None
    header = NMHDR.from_address(lparam)
    code = int(header.code)
    if code >= 0x80000000:
        code -= 0x100000000
    return (int(header.hwndFrom or 0), code)


def notify_selected_date(lparam: int) -> tuple[int, int, int] | None:
    """Read the selected date out of a month calendar's ``NMSELCHANGE`` notification."""

    if not lparam:
        return None
    change = NMSELCHANGE.from_address(lparam)
    return (change.stSelStart.wYear, change.stSelStart.wMonth, change.stSelStart.wDay)


# --- COM: the object an AutoIt script embeds with GUICtrlCreateObj -------------------------
#
# GUICtrlCreateObj takes "a variable pointing to a previously opened object" (GUICtrlCreateObj.htm)
# and embeds it in the GUI; the object is then driven through its own methods and properties. Both
# halves are COM: AutoIt's ObjCreate is CoCreateInstance, and its names are resolved with
# IDispatch. Two mechanisms were measured before this was written (see tests/autoit_reference):
#
#   * the interpreter's object control is a child window of the GUI whose class is the *control's
#     own* in-place window ("Shell Embedding" for Shell.Explorer.2, style `WS_CHILD|WS_VISIBLE|
#     WS_TABSTOP`, exStyle `WS_EX_CONTROLPARENT`), created with the GUI and hidden until
#     `GUISetState` shows the window (probe_autoit_obj2_out.txt);
#   * `GUICtrlGetHandle` on it returns 0 -- which its own page states: "The following controls will
#     not return a handle: GUICtrlCreateDummy(), GUICtrlCreateGraphic(), GUICtrlCreateObj(), ..."
#
# The port hosts the object with the platform's ATL ActiveX host, which is the documented Windows
# API for putting an already-created control into an existing window: `AtlAxWinInit` registers the
# host, and `AtlAxAttachControl` attaches the caller's own `IUnknown` to a window handle the caller
# already owns (here, the tkinter frame's real HWND). `AtlAxGetControl` reads the control back out,
# which is how the tests prove the embedded control *is* the caller's object.

_ole32 = ctypes.WinDLL("ole32", use_last_error=True)
_oleaut32 = ctypes.WinDLL("oleaut32", use_last_error=True)

DISPATCH_METHOD = 0x1
DISPATCH_PROPERTYGET = 0x2
DISPATCH_PROPERTYPUT = 0x4
DISPID_PROPERTYPUT = -3
#: ``MEMBERID_NIL``: the member id that means "the type itself" rather than one of its members.
MEMBERID_NIL = -1

CLSCTX_INPROC_SERVER = 0x1
CLSCTX_LOCAL_SERVER = 0x4
CLSCTX_REMOTE_SERVER = 0x10

#: ``IDispatch::Invoke`` results that mean "this name needs arguments", which is how a name that
#: was read as a bare attribute is told apart from one being called.
DISP_E_BADPARAMCOUNT = 0x8002000E
DISP_E_PARAMNOTOPTIONAL = 0x8002000F
DISP_E_TYPEMISMATCH = 0x80020005
DISP_E_OVERFLOW = 0x8002000A
DISP_E_BADINDEX = 0x8002000B

# VARIANT types this boundary converts. Anything else is reported rather than guessed at.
VT_EMPTY = 0
VT_NULL = 1
VT_I2 = 2
VT_I4 = 3
VT_R4 = 4
VT_R8 = 5
VT_CY = 6
VT_DATE = 7
VT_BSTR = 8
VT_DISPATCH = 9
VT_ERROR = 10
VT_BOOL = 11
VT_VARIANT = 12
VT_UNKNOWN = 13
VT_UI1 = 17
VT_UI2 = 18
VT_UI4 = 19
VT_I8 = 20
VT_UI8 = 21
VT_INT = 22
VT_UINT = 23

_VT_BYREF = 0x4000
_VT_ARRAY = 0x2000
_VT_TYPEMASK = 0x0FFF

#: A RPC/COM identity, as ``COAUTHIDENTITY`` carries it.
RPC_C_AUTHN_WINNT = 10
RPC_C_AUTHZ_NONE = 0
RPC_C_AUTHN_LEVEL_DEFAULT = 0
RPC_C_IMP_LEVEL_IMPERSONATE = 3


class GUID(ctypes.Structure):
    """A COM globally unique identifier, the shape ``ole32`` uses."""

    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(text: str) -> GUID:
    value = GUID()
    if _ole32.IIDFromString(ctypes.c_wchar_p(text), ctypes.byref(value)) != 0:
        raise ValueError(text)
    return value


#: The reserved interface identifier ``IDispatch::GetIDsOfNames`` and ``Invoke`` require in their
#: riid parameter. Passing ``IID_IDispatch`` there instead makes every name lookup fail with
#: ``DISP_E_UNKNOWNNAME`` (0x80020001) -- measured while this boundary was being written, on both
#: Scripting.Dictionary and Shell.Explorer.2.
GUID_NULL = _guid("{00000000-0000-0000-0000-000000000000}")
IID_IDISPATCH = _guid("{00020400-0000-0000-C000-000000000046}")

#: What an object must offer to be embeddable at all: "Not every control can be embedded. They must
#: at least support an 'IDispatch' interface" (GUICtrlCreateObj.htm) is the page's wording, but the
#: interpreter refused an object that has one -- ``ObjCreate("Scripting.Dictionary")`` succeeds and
#: ``GUICtrlCreateObj`` still returned 0 with @error 1 (probe_autoit_obj_out.txt). What that object
#: lacks is an OLE object interface, which is what hosting an in-place control needs, so an object
#: with no ``IOleObject`` is the case the interpreter refuses and the port refuses with it.
IID_IOLEOBJECT = _guid("{00000112-0000-0000-C000-000000000046}")

#: ``IPersist``, whose ``GetClassID`` reports the object's own class identifier -- the key the
#: object's name is looked up by, since the name the interpreter reports is its coclass.
IID_IPERSIST = _guid("{0000010C-0000-0000-C000-000000000046}")


class TYPEATTR(ctypes.Structure):
    """The head of a type library type's description, which its GUID and kind live in."""

    _fields_ = [
        ("guid", GUID),
        ("lcid", ctypes.c_ulong),
        ("dwReserved", ctypes.c_ulong),
        ("memidConstructor", ctypes.c_long),
        ("memidDestructor", ctypes.c_long),
        ("lpstrSchema", ctypes.c_void_p),
        ("cbSizeInstance", ctypes.c_ulong),
        ("typekind", ctypes.c_uint),
        ("cFuncs", ctypes.c_ushort),
        ("cVars", ctypes.c_ushort),
        ("cImplTypes", ctypes.c_ushort),
        ("cbSizeVft", ctypes.c_ushort),
        ("cbAlignment", ctypes.c_ushort),
        ("wTypeFlags", ctypes.c_ushort),
        ("wMajorVerNum", ctypes.c_ushort),
        ("wMinorVerNum", ctypes.c_ushort),
        # TYPEDESC tdescAlias and ELEMDESC idldescType follow; nothing here reads them.
        ("tail", ctypes.c_byte * 40),
    ]


#: The type kinds a type library declares; only a coclass can carry an object's name. (Measured
#: while this was written: scrrun's type library lists "Dictionary" as kind 5 and "IDictionary" as
#: kind 4 -- TKIND_DISPATCH, an interface that is reached through IDispatch.)
TKIND_COCLASS = 5

#: How a type library declares a member is reached.
INVOKE_FUNC = 1
INVOKE_PROPERTYGET = 2
INVOKE_PROPERTYPUT = 4
INVOKE_PROPERTYPUTREF = 8


class FUNCDESC(ctypes.Structure):
    """The head of a type library function's description: its id and how it is invoked."""

    _fields_ = [
        ("memid", ctypes.c_long),
        ("lprgscode", ctypes.c_void_p),
        ("lprgelemdescParam", ctypes.c_void_p),
        ("funckind", ctypes.c_uint),
        ("invkind", ctypes.c_uint),
        ("callconv", ctypes.c_uint),
        ("cParams", ctypes.c_short),
        ("cParamsOpt", ctypes.c_short),
        ("oVft", ctypes.c_short),
        ("cScodes", ctypes.c_short),
        # ELEMDESC elemdescFunc and the short tail follow; nothing here reads them.
        ("tail", ctypes.c_byte * 32),
    ]

#: A ``VARIANT``: eight bytes of header, then a union whose pointer-sized members make it 16 bytes
#: on x86 and 24 on x64.
_VARIANT_UNION = 16 if sys.maxsize > 2**32 else 8


class VARIANT(ctypes.Structure):
    """The ``VARIANT`` this boundary passes to and reads from ``IDispatch::Invoke``."""

    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("reserved1", ctypes.c_ushort),
        ("reserved2", ctypes.c_ushort),
        ("reserved3", ctypes.c_ushort),
        ("value", ctypes.c_byte * _VARIANT_UNION),
    ]


class DISPPARAMS(ctypes.Structure):
    """The argument block of ``IDispatch::Invoke``."""

    _fields_ = [
        ("rgvarg", ctypes.POINTER(VARIANT)),
        ("rgdispidNamedArgs", ctypes.POINTER(ctypes.c_long)),
        ("cArgs", ctypes.c_uint),
        ("cNamedArgs", ctypes.c_uint),
    ]


class COAUTHIDENTITY(ctypes.Structure):
    """The user identity a remote ``CoCreateInstance`` authenticates with."""

    _fields_ = [
        ("User", ctypes.c_void_p),
        ("UserLength", ctypes.c_ulong),
        ("Domain", ctypes.c_void_p),
        ("DomainLength", ctypes.c_ulong),
        ("Password", ctypes.c_void_p),
        ("PasswordLength", ctypes.c_ulong),
        ("Flags", ctypes.c_ulong),
    ]


class COAUTHINFO(ctypes.Structure):
    """How a remote activation authenticates."""

    _fields_ = [
        ("dwAuthnSvc", ctypes.c_ulong),
        ("dwAuthzSvc", ctypes.c_ulong),
        ("pwszServerPrincName", ctypes.c_wchar_p),
        ("dwAuthnLevel", ctypes.c_ulong),
        ("dwImpersonationLevel", ctypes.c_ulong),
        ("pAuthIdentityData", ctypes.POINTER(COAUTHIDENTITY)),
        ("dwCapabilities", ctypes.c_ulong),
    ]


class COSERVERINFO(ctypes.Structure):
    """The remote computer a ``CoCreateInstance`` activates on."""

    _fields_ = [
        ("dwReserved1", ctypes.c_ulong),
        ("pwszName", ctypes.c_wchar_p),
        ("pAuthInfo", ctypes.POINTER(COAUTHINFO)),
        ("dwReserved2", ctypes.c_ulong),
    ]


class DispatchArgument:
    """A COM interface pointer being passed *to* or returned *from* an object call.

    The GUI layer's object type is a Python object wrapping one of these; keeping the pointer in a
    named type is what lets the argument converter tell an object apart from an integer.
    """

    __slots__ = ("pointer",)

    def __init__(self, pointer: int) -> None:
        self.pointer = int(pointer)


_GET_IDS_OF_NAMES = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_wchar_p),
    ctypes.c_uint,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_long),
)
_INVOKE = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_long,
    ctypes.POINTER(GUID),
    ctypes.c_ulong,
    ctypes.c_ushort,
    ctypes.POINTER(DISPPARAMS),
    ctypes.POINTER(VARIANT),
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint),
)
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
_QUERY_INTERFACE = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
)
_GET_TYPE_INFO = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)
)
_GET_DOCUMENTATION = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_long,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_void_p),
)
_GET_CLASS_ID = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID))
_GET_CONTAINING_TYPE_LIB = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)
)
_GET_TYPELIB_TYPE_INFO = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
)
_GET_TYPE_ATTR = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(TYPEATTR))
)
_RELEASE_TYPE_ATTR = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(TYPEATTR))
_GET_REF_TYPE_OF_IMPL_TYPE = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_ulong)
)
_GET_REF_TYPE_INFO = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)
)
_GET_TYPE_INFO_COUNT = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_void_p)
_GET_TYPE_INFO_AT = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)
)
_GET_FUNC_DESC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.POINTER(FUNCDESC))
)
_RELEASE_FUNC_DESC = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(FUNCDESC))

_ole32.CLSIDFromProgID.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
_ole32.CLSIDFromProgID.restype = ctypes.c_long
_ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
_ole32.CLSIDFromString.restype = ctypes.c_long
_ole32.CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID),
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]
_ole32.CoCreateInstance.restype = ctypes.c_long
_ole32.OleInitialize.argtypes = [ctypes.c_void_p]
_ole32.OleInitialize.restype = ctypes.c_long
_oleaut32.SysAllocString.argtypes = [ctypes.c_wchar_p]
_oleaut32.SysAllocString.restype = ctypes.c_void_p
_oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
_oleaut32.SysFreeString.restype = None
_oleaut32.VariantClear.argtypes = [ctypes.POINTER(VARIANT)]
_oleaut32.VariantClear.restype = ctypes.c_long

#: Whether OLE has been initialized on this thread, and with what result. AutoIt's ObjCreate works
#: on the thread that calls it, so the port initializes on the calling thread the first time an
#: object is created or hosted -- not at import, and not on a thread of its own.
_ole_result: int | None = None


def ole_initialize() -> int:
    """Initialize OLE on the calling thread and return the first call's result."""

    global _ole_result
    if _ole_result is None:
        _ole_result = int(_ole32.OleInitialize(None))
    return _ole_result


def _vtable(pointer: int, index: int) -> int:
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return int(table[index] or 0)


def _class_identifier(classname: str, clsid: GUID) -> bool:
    """Resolve a class name the way ``ObjCreate``'s page describes it: a ProgID or a CLSID string."""

    if classname.startswith("{"):
        return _ole32.CLSIDFromString(ctypes.c_wchar_p(classname), ctypes.byref(clsid)) == 0
    return _ole32.CLSIDFromProgID(ctypes.c_wchar_p(classname), ctypes.byref(clsid)) == 0


def create_object(
    classname: str,
    servername: str = "",
    username: str = "",
    password: str = "",
) -> DispatchArgument | None:
    """Create a COM object, which is what AutoIt's ``ObjCreate`` does.

    ``classname`` is "appname.objectype" or a string form of the CLSID; a ``servername`` activates
    the object on that computer, with ``username`` ("computer\\usercode" or "domain\\usercode") and
    ``password`` as the identity to authenticate with (ObjCreate.htm). Returns ``None`` where the
    interpreter returns 0.
    """

    ole_initialize()
    clsid = GUID()
    if not _class_identifier(classname, clsid):
        return None
    if servername:
        return _create_remote(clsid, servername, username, password)
    pointer = ctypes.c_void_p()
    result = _ole32.CoCreateInstance(
        ctypes.byref(clsid),
        None,
        CLSCTX_INPROC_SERVER | CLSCTX_LOCAL_SERVER,
        ctypes.byref(IID_IDISPATCH),
        ctypes.byref(pointer),
    )
    if result != 0 or not pointer.value:
        return None
    return DispatchArgument(pointer.value)


def _split_identity(username: str) -> tuple[str, str]:
    """Split "computer\\usercode" into its two halves, as ``ObjCreate``'s page writes them."""

    if "\\" in username:
        domain, user = username.split("\\", 1)
        return domain, user
    return "", username


def _create_remote(
    clsid: GUID, servername: str, username: str, password: str
) -> DispatchArgument | None:
    """Activate an object on a remote computer (``ObjCreate``'s optional parameters).

    The mechanism is DCOM's: ``CoCreateInstance`` with a ``COSERVERINFO`` naming the computer, and
    a ``COAUTHINFO``/``COAUTHIDENTITY`` carrying the identity when one is given. It has not been
    exercised here -- this machine has no DCOM peer to activate against -- so the port reports it as
    the documented mechanism rather than as a measured one.
    """

    buffers: list[Any] = []
    auth_identity = COAUTHIDENTITY()
    auth_info = COAUTHINFO()
    server_info = COSERVERINFO()
    if username:
        domain, user = _split_identity(username)
        user_buffer = ctypes.create_unicode_buffer(user)
        domain_buffer = ctypes.create_unicode_buffer(domain)
        password_buffer = ctypes.create_unicode_buffer(password)
        buffers.extend((user_buffer, domain_buffer, password_buffer))
        auth_identity.User = ctypes.cast(user_buffer, ctypes.c_void_p)
        auth_identity.UserLength = len(user)
        auth_identity.Domain = ctypes.cast(domain_buffer, ctypes.c_void_p)
        auth_identity.DomainLength = len(domain)
        auth_identity.Password = ctypes.cast(password_buffer, ctypes.c_void_p)
        auth_identity.PasswordLength = len(password)
        auth_info.dwAuthnSvc = RPC_C_AUTHN_WINNT
        auth_info.dwAuthzSvc = RPC_C_AUTHZ_NONE
        auth_info.dwAuthnLevel = RPC_C_AUTHN_LEVEL_DEFAULT
        auth_info.dwImpersonationLevel = RPC_C_IMP_LEVEL_IMPERSONATE
        auth_info.pAuthIdentityData = ctypes.pointer(auth_identity)
        server_info.pAuthInfo = ctypes.pointer(auth_info)
    server_info.pwszName = servername
    pointer = ctypes.c_void_p()
    result = _ole32.CoCreateInstance(
        ctypes.byref(clsid),
        ctypes.cast(ctypes.byref(server_info), ctypes.c_void_p),
        CLSCTX_REMOTE_SERVER,
        ctypes.byref(IID_IDISPATCH),
        ctypes.byref(pointer),
    )
    # The identity strings are held by `buffers` for as long as the call above may read them.
    del buffers
    if result != 0 or not pointer.value:
        return None
    return DispatchArgument(pointer.value)


def release_object(dispatch: DispatchArgument) -> None:
    """Release one reference to an object, which is what dropping an AutoIt object variable does."""

    if not dispatch.pointer:
        return
    release = _RELEASE(_vtable(dispatch.pointer, 2))
    release(ctypes.c_void_p(dispatch.pointer))


def object_supports_ole(dispatch: DispatchArgument) -> bool:
    """Whether an object offers ``IOleObject``, which is what being embedded requires."""

    if not dispatch.pointer:
        return False
    queried = ctypes.c_void_p()
    query_interface = _QUERY_INTERFACE(_vtable(dispatch.pointer, 0))
    result = query_interface(
        ctypes.c_void_p(dispatch.pointer),
        ctypes.byref(IID_IOLEOBJECT),
        ctypes.byref(queried),
    )
    if result != 0 or not queried.value:
        return False
    release = _RELEASE(_vtable(queried.value, 2))
    release(ctypes.c_void_p(queried.value))
    return True


def object_name(dispatch: DispatchArgument) -> str:
    """Read an object's name -- AutoIt's ``ObjName``.

    The interpreter reports "WebBrowser" for ``ObjCreate("Shell.Explorer.2")`` and "Dictionary" for
    ``ObjCreate("Scripting.Dictionary")`` (probe_autoit_obj_out.txt). Neither is the object's
    ProgID ("Shell.Explorer.2", "Scripting.Dictionary") nor the registry's class name ("Microsoft
    Web Browser Version 1"): both are the *coclass* names, so that is what this reads -- the
    object's class identifier (``IPersist::GetClassID``), looked up in the type library the
    object's own interface belongs to (``ITypeInfo::GetContainingTypeLib`` then
    ``ITypeLib::GetTypeInfoOfGuid``), whose ``GetDocumentation`` is the coclass's name.

    An object that offers neither of those interfaces has no name to report, and none is invented
    for it.
    """

    if not dispatch.pointer:
        return ""
    class_identifier = GUID()
    persist = ctypes.c_void_p()
    query_interface = _QUERY_INTERFACE(_vtable(dispatch.pointer, 0))
    result = query_interface(
        ctypes.c_void_p(dispatch.pointer),
        ctypes.byref(IID_IPERSIST),
        ctypes.byref(persist),
    )
    if result == 0 and persist.value:
        try:
            get_class_id = _GET_CLASS_ID(_vtable(persist.value, 3))
            if get_class_id(ctypes.c_void_p(persist.value), ctypes.byref(class_identifier)) != 0:
                return ""
        finally:
            release = _RELEASE(_vtable(persist.value, 2))
            release(ctypes.c_void_p(persist.value))
    else:
        # No class identifier to ask with: find the coclass in the interface's own type library
        # instead, which is what Scripting.Dictionary needs -- it offers no IPersist at all
        # (measured: QueryInterface for it returns E_NOINTERFACE).
        return _coclass_name(dispatch.pointer)

    interface_info = ctypes.c_void_p()
    get_type_info = _GET_TYPE_INFO(_vtable(dispatch.pointer, 4))
    if get_type_info(ctypes.c_void_p(dispatch.pointer), 0, 0, ctypes.byref(interface_info)) != 0:
        return ""
    if not interface_info.value:
        return ""
    library = ctypes.c_void_p()
    try:
        index = ctypes.c_uint()
        get_containing = _GET_CONTAINING_TYPE_LIB(_vtable(interface_info.value, 18))
        if (
            get_containing(
                ctypes.c_void_p(interface_info.value), ctypes.byref(library), ctypes.byref(index)
            )
            != 0
        ):
            return ""
        if not library.value:
            return ""
        coclass_info = ctypes.c_void_p()
        get_type_info_of_guid = _GET_TYPELIB_TYPE_INFO(_vtable(library.value, 6))
        if (
            get_type_info_of_guid(
                ctypes.c_void_p(library.value),
                ctypes.byref(class_identifier),
                ctypes.byref(coclass_info),
            )
            != 0
        ):
            return ""
        if not coclass_info.value:
            return ""
        try:
            return _type_name(coclass_info.value)
        finally:
            release = _RELEASE(_vtable(coclass_info.value, 2))
            release(ctypes.c_void_p(coclass_info.value))
    finally:
        if library.value:
            release = _RELEASE(_vtable(library.value, 2))
            release(ctypes.c_void_p(library.value))
        release = _RELEASE(_vtable(interface_info.value, 2))
        release(ctypes.c_void_p(interface_info.value))


def _type_name(type_info: int) -> str:
    """Read a type's own name out of an ``ITypeInfo``, which its ``GetDocumentation`` returns."""

    name = ctypes.c_void_p()
    documentation = ctypes.c_void_p()
    context = ctypes.c_ulong()
    help_file = ctypes.c_void_p()
    get_documentation = _GET_DOCUMENTATION(_vtable(type_info, 12))
    # Every out parameter of GetDocumentation is a BSTR the caller owns.
    result = get_documentation(
        ctypes.c_void_p(type_info),
        MEMBERID_NIL,
        ctypes.byref(name),
        ctypes.byref(documentation),
        ctypes.byref(context),
        ctypes.byref(help_file),
    )
    if result != 0:
        return ""
    for pointer in (documentation.value, help_file.value):
        if pointer:
            _oleaut32.SysFreeString(ctypes.c_void_p(pointer))
    if not name.value:
        return ""
    try:
        return ctypes.c_wchar_p(name.value).value or ""
    finally:
        _oleaut32.SysFreeString(name)


def _typelib_of(type_info: int) -> int:
    """Return the type library an ``ITypeInfo`` belongs to, or 0."""

    library = ctypes.c_void_p()
    index = ctypes.c_uint()
    get_containing = _GET_CONTAINING_TYPE_LIB(_vtable(type_info, 18))
    if get_containing(ctypes.c_void_p(type_info), ctypes.byref(library), ctypes.byref(index)) != 0:
        return 0
    return int(library.value or 0)


def _type_attr(type_info: int) -> TYPEATTR | None:
    """Read a type's description; the caller must pass it to ``_release_type_attr`` afterwards."""

    attributes = ctypes.POINTER(TYPEATTR)()
    get_type_attr = _GET_TYPE_ATTR(_vtable(type_info, 3))
    if get_type_attr(ctypes.c_void_p(type_info), ctypes.byref(attributes)) != 0:
        return None
    if not attributes:
        return None
    return attributes.contents


def _release_type_attr(type_info: int, attributes: TYPEATTR) -> None:
    """Give a type description back, which ``GetTypeAttr``'s documentation requires."""

    release = _RELEASE_TYPE_ATTR(_vtable(type_info, 19))
    release(ctypes.c_void_p(type_info), ctypes.byref(attributes))


def _coclass_name(pointer: int) -> str:
    """Find the coclass that implements an object's default interface and read its name.

    This is the object's *name* in the sense the interpreter means it: the type library declares a
    coclass for the class the object is an instance of, and that coclass lists the interfaces it
    implements, so the coclass whose list holds the object's own interface is the one to name.
    """

    interface_info = ctypes.c_void_p()
    get_type_info = _GET_TYPE_INFO(_vtable(pointer, 4))
    if get_type_info(ctypes.c_void_p(pointer), 0, 0, ctypes.byref(interface_info)) != 0:
        return ""
    if not interface_info.value:
        return ""
    interface = int(interface_info.value)
    try:
        attributes = _type_attr(interface)
        if attributes is None:
            return ""
        wanted = GUID()
        ctypes.memmove(ctypes.byref(wanted), ctypes.byref(attributes.guid), ctypes.sizeof(GUID))
        _release_type_attr(interface, attributes)
        library = _typelib_of(interface)
        if not library:
            return ""
        try:
            return _search_coclasses(library, wanted)
        finally:
            release = _RELEASE(_vtable(library, 2))
            release(ctypes.c_void_p(library))
    finally:
        release = _RELEASE(_vtable(interface, 2))
        release(ctypes.c_void_p(interface))


def _search_coclasses(library: int, wanted: GUID) -> str:
    """Walk a type library's types for the coclass implementing one interface."""

    count = _GET_TYPE_INFO_COUNT(_vtable(library, 3))
    get_type_info = _GET_TYPE_INFO_AT(_vtable(library, 4))
    total = int(count(ctypes.c_void_p(library)))
    for index in range(total):
        candidate = ctypes.c_void_p()
        if get_type_info(ctypes.c_void_p(library), index, ctypes.byref(candidate)) != 0:
            continue
        if not candidate.value:
            continue
        try:
            attributes = _type_attr(candidate.value)
            if attributes is None:
                continue
            kind = int(attributes.typekind)
            implementations = int(attributes.cImplTypes)
            _release_type_attr(candidate.value, attributes)
            if kind != TKIND_COCLASS:
                continue
            if _implements(candidate.value, implementations, wanted):
                return _type_name(candidate.value)
        finally:
            release = _RELEASE(_vtable(candidate.value, 2))
            release(ctypes.c_void_p(candidate.value))
    return ""


def _implements(coclass: int, implementations: int, wanted: GUID) -> bool:
    """Whether a coclass lists one interface among the ones it implements."""

    get_reference = _GET_REF_TYPE_OF_IMPL_TYPE(_vtable(coclass, 8))
    get_type_info = _GET_REF_TYPE_INFO(_vtable(coclass, 14))
    for index in range(implementations):
        reference = ctypes.c_ulong()
        if get_reference(ctypes.c_void_p(coclass), index, ctypes.byref(reference)) != 0:
            continue
        interface = ctypes.c_void_p()
        if get_type_info(ctypes.c_void_p(coclass), reference, ctypes.byref(interface)) != 0:
            continue
        if not interface.value:
            continue
        try:
            attributes = _type_attr(interface.value)
            if attributes is None:
                continue
            same = (
                ctypes.string_at(ctypes.byref(attributes.guid), ctypes.sizeof(GUID))
                == ctypes.string_at(ctypes.byref(wanted), ctypes.sizeof(GUID))
            )
            _release_type_attr(interface.value, attributes)
            if same:
                return True
        finally:
            release = _RELEASE(_vtable(interface.value, 2))
            release(ctypes.c_void_p(interface.value))
    return False


def member_signature(dispatch: DispatchArgument, identifier: int) -> tuple[str, int]:
    """Say how an object declares a member: ``("method" | "property" | "", parameter count)``.

    AutoIt resolves ``$obj.Name`` and ``$obj.Name(args)`` against the object's own type information,
    which is what decides whether a name is a method or a property there. Python needs the same
    answer at the moment it sees the name, because a property is read by writing its name and a
    method is called by writing its parentheses: an empty tuple here means the object declares
    nothing about the member, and the caller falls back to asking the object itself.
    """

    if not dispatch.pointer:
        return ("", 0)
    type_info = ctypes.c_void_p()
    get_type_info = _GET_TYPE_INFO(_vtable(dispatch.pointer, 4))
    if get_type_info(ctypes.c_void_p(dispatch.pointer), 0, 0, ctypes.byref(type_info)) != 0:
        return ("", 0)
    if not type_info.value:
        return ("", 0)
    try:
        attributes = _type_attr(type_info.value)
        if attributes is None:
            return ("", 0)
        functions = int(attributes.cFuncs)
        _release_type_attr(type_info.value, attributes)
        get_func_desc = _GET_FUNC_DESC(_vtable(type_info.value, 5))
        release_func_desc = _RELEASE_FUNC_DESC(_vtable(type_info.value, 20))
        # A property is declared twice under the same member id -- once to read and once to write --
        # so every description carrying the id is read and the two are told apart afterwards.
        method: tuple[str, int] | None = None
        readable = False
        reader_parameters = 0
        for index in range(functions):
            description = ctypes.POINTER(FUNCDESC)()
            if get_func_desc(
                ctypes.c_void_p(type_info.value), index, ctypes.byref(description)
            ) != 0:
                continue
            if not description:
                continue
            try:
                if int(description.contents.memid) != identifier:
                    continue
                kind = int(description.contents.invkind)
                parameters = int(description.contents.cParams)
            finally:
                release_func_desc(ctypes.c_void_p(type_info.value), description)
            if kind & INVOKE_FUNC:
                method = ("method", parameters)
            elif kind & INVOKE_PROPERTYGET:
                readable = True
                reader_parameters = parameters
        if method is not None:
            return method
        if readable:
            return ("property", reader_parameters)
        return ("", 0)
    finally:
        release = _RELEASE(_vtable(type_info.value, 2))
        release(ctypes.c_void_p(type_info.value))


def dispatch_id(dispatch: DispatchArgument, name: str) -> int | None:
    """Resolve a member name to its dispatch identifier, or ``None`` if the object has no such name."""

    if not dispatch.pointer:
        return None
    names = (ctypes.c_wchar_p * 1)(name)
    identifier = ctypes.c_long()
    get_ids = _GET_IDS_OF_NAMES(_vtable(dispatch.pointer, 5))
    result = get_ids(
        ctypes.c_void_p(dispatch.pointer),
        ctypes.byref(GUID_NULL),
        names,
        1,
        0,
        ctypes.byref(identifier),
    )
    if result != 0:
        return None
    return int(identifier.value)


def _variant_pointer(variant: VARIANT) -> int:
    size = ctypes.sizeof(ctypes.c_void_p)
    raw = ctypes.string_at(ctypes.byref(variant.value), size)
    return int(ctypes.c_void_p.from_buffer_copy(raw).value or 0)


def _variant_set_pointer(variant: VARIANT, pointer: int) -> None:
    holder = ctypes.c_void_p(pointer)
    ctypes.memmove(
        ctypes.byref(variant.value), ctypes.byref(holder), ctypes.sizeof(ctypes.c_void_p)
    )


def _variant_number(variant: VARIANT) -> int | float:
    if variant.vt in (VT_I2, VT_UI2):
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 2), "little", signed=variant.vt == VT_I2)
    if variant.vt in (VT_I4, VT_INT):
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 4), "little", signed=True)
    if variant.vt in (VT_UI4, VT_UINT):
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 4), "little")
    if variant.vt == VT_UI1:
        return ctypes.string_at(ctypes.byref(variant.value), 1)[0]
    if variant.vt == VT_I8:
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 8), "little", signed=True)
    if variant.vt == VT_UI8:
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 8), "little")
    if variant.vt == VT_R4:
        return float(ctypes.c_float.from_buffer_copy(ctypes.string_at(ctypes.byref(variant.value), 4)).value)
    if variant.vt == VT_R8:
        return float(ctypes.c_double.from_buffer_copy(ctypes.string_at(ctypes.byref(variant.value), 8)).value)
    if variant.vt == VT_ERROR:
        return int.from_bytes(ctypes.string_at(ctypes.byref(variant.value), 4), "little", signed=True)
    raise NotImplementedError(f"VARIANT type {variant.vt}")


def _variant_value(variant: VARIANT, allocated: list[int]) -> Any:
    """Convert an outgoing VARIANT back into a Python value.

    ``allocated`` collects the BSTRs the callee returned, which the caller owns and frees once the
    value has been read.
    """

    if variant.vt & _VT_ARRAY:
        raise NotImplementedError(f"VARIANT type 0x{variant.vt:04x}: arrays are not converted")
    if variant.vt & _VT_BYREF:
        raise NotImplementedError(f"VARIANT type 0x{variant.vt:04x}: by-reference results are not converted")
    if variant.vt in (VT_EMPTY, VT_NULL):
        return None
    if variant.vt == VT_BSTR:
        pointer = _variant_pointer(variant)
        if not pointer:
            return ""
        allocated.append(pointer)
        return ctypes.c_wchar_p(pointer).value or ""
    if variant.vt == VT_BOOL:
        raw = ctypes.string_at(ctypes.byref(variant.value), 2)
        return int.from_bytes(raw, "little") != 0
    if variant.vt in (VT_DISPATCH, VT_UNKNOWN):
        pointer = _variant_pointer(variant)
        return DispatchArgument(pointer) if pointer else None
    return _variant_number(variant)


def _argument_variant(value: Any, allocations: list[int]) -> VARIANT:
    """Build the VARIANT for one argument of an object call.

    Strings are handed to the object as its own ``BSTR``, numbers as the narrowest of ``VT_I4`` and
    ``VT_R8``, booleans as ``VT_BOOL``, objects as ``VT_DISPATCH`` and nothing as ``VT_EMPTY`` --
    the types AutoIt's own object calls use.
    """

    variant = VARIANT()
    if value is None:
        variant.vt = VT_EMPTY
        return variant
    if isinstance(value, DispatchArgument):
        variant.vt = VT_DISPATCH
        _variant_set_pointer(variant, value.pointer)
        return variant
    if isinstance(value, bool):
        variant.vt = VT_BOOL
        ctypes.memmove(ctypes.byref(variant.value), ctypes.byref(ctypes.c_short(-1 if value else 0)), 2)
        return variant
    if isinstance(value, int):
        variant.vt = VT_I4
        ctypes.memmove(ctypes.byref(variant.value), ctypes.byref(ctypes.c_long(value)), 4)
        return variant
    if isinstance(value, float):
        variant.vt = VT_R8
        ctypes.memmove(ctypes.byref(variant.value), ctypes.byref(ctypes.c_double(value)), 8)
        return variant
    if isinstance(value, str):
        pointer = _oleaut32.SysAllocString(ctypes.c_wchar_p(value))
        if not pointer:
            raise MemoryError(value)
        allocations.append(pointer)
        variant.vt = VT_BSTR
        _variant_set_pointer(variant, pointer)
        return variant
    raise TypeError(f"an object call cannot take {type(value).__name__}")


def object_invoke(
    dispatch: DispatchArgument,
    name: str,
    identifier: int,
    args: tuple[Any, ...],
    flags: int,
) -> tuple[int, Any]:
    """Invoke one member of an object and return ``(hresult, value)``.

    The result is returned rather than raised because a name that was read as an attribute may turn
    out to need arguments: the caller sees ``DISP_E_BADPARAMCOUNT`` and hands back something
    callable. Arguments are passed in the reverse order Windows' ``DISPPARAMS`` carries them, and a
    property write also names its value ``DISPID_PROPERTYPUT``.
    """

    if not dispatch.pointer:
        return (-2147467261, None)  # E_POINTER
    parameter_allocations: list[int] = []
    variants = [_argument_variant(value, parameter_allocations) for value in reversed(args)]
    array = (VARIANT * max(1, len(variants)))(*variants)
    params = DISPPARAMS()
    params.rgvarg = ctypes.cast(array, ctypes.POINTER(VARIANT))
    params.cArgs = len(variants)
    named = ctypes.c_long(DISPID_PROPERTYPUT)
    if flags & DISPATCH_PROPERTYPUT:
        params.rgdispidNamedArgs = ctypes.pointer(named)
        params.cNamedArgs = 1
    result = VARIANT()
    argument_error = ctypes.c_uint()
    invoke = _INVOKE(_vtable(dispatch.pointer, 6))
    try:
        hresult = int(
            invoke(
                ctypes.c_void_p(dispatch.pointer),
                identifier,
                ctypes.byref(GUID_NULL),
                0,
                flags,
                ctypes.byref(params),
                ctypes.byref(result),
                None,
                ctypes.byref(argument_error),
            )
        )
        if hresult != 0:
            return (hresult, None)
        allocated: list[int] = []
        try:
            value = _variant_value(result, allocated)
        finally:
            _oleaut32.VariantClear(ctypes.byref(result))
        for pointer in allocated:
            _oleaut32.SysFreeString(ctypes.c_void_p(pointer))
        return (0, value)
    finally:
        for pointer in parameter_allocations:
            _oleaut32.SysFreeString(ctypes.c_void_p(pointer))


def is_argument_error(hresult: int) -> bool:
    """Whether an invocation failed because the name takes arguments it was not given.

    An HRESULT arrives as a signed 32-bit value, so a failure is compared in its unsigned form:
    ``DISP_E_BADPARAMCOUNT`` is -2147352562 signed and 0x8002000E unsigned, and only the second
    matches the constants.
    """

    return (hresult & 0xFFFFFFFF) in (
        DISP_E_BADPARAMCOUNT,
        DISP_E_PARAMNOTOPTIONAL,
        DISP_E_TYPEMISMATCH,
        DISP_E_OVERFLOW,
        DISP_E_BADINDEX,
    )


# --- the ActiveX host the object is embedded in --------------------------------------------

_atl: Any = None
_host_error: str | None = None


def object_host_error() -> str | None:
    """Report why the ActiveX host is unavailable, or ``None`` when it is ready."""

    return _host_error


def _load_host() -> Any:
    """Load ``atl.dll`` and register its host window class."""

    global _atl, _host_error
    if _atl is not None:
        return _atl
    try:
        library = ctypes.WinDLL("atl", use_last_error=True)
    except OSError as error:  # pragma: no cover - depends on the machine's ATL
        _host_error = (
            "the platform's ActiveX host (atl.dll,AtlAxWinInit/AtlAxAttachControl) is not "
            f"installed: {error}"
        )
        return None
    library.AtlAxWinInit.argtypes = []
    library.AtlAxWinInit.restype = wintypes.BOOL
    library.AtlAxAttachControl.argtypes = [
        ctypes.c_void_p,
        wintypes.HWND,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    library.AtlAxAttachControl.restype = ctypes.c_long
    library.AtlAxGetControl.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.c_void_p)]
    library.AtlAxGetControl.restype = ctypes.c_long
    if not library.AtlAxWinInit():
        _host_error = "atl.dll's AtlAxWinInit refused to register its host window class"
        return None
    _atl = library
    return library


def attach_object_host(container: int, dispatch: DispatchArgument) -> tuple[int, int]:
    """Embed an object in a window, returning ``(hresult, host owner)``.

    ``container`` is the handle of a window the port owns -- the tkinter frame of the object
    control -- and the object's own in-place window becomes its child, which is the tree the
    interpreter produces too (probe_autoit_obj2_out.txt: the GUI's child is "Shell Embedding").
    """

    library = _load_host()
    if library is None:
        return (-2147467261, 0)  # E_POINTER
    owner = ctypes.c_void_p()
    hresult = int(
        library.AtlAxAttachControl(
            ctypes.c_void_p(dispatch.pointer), wintypes.HWND(container), ctypes.byref(owner)
        )
    )
    return (hresult, int(owner.value or 0))


def host_control(container: int) -> DispatchArgument | None:
    """Read back the control a host window holds -- the caller's own object, by identity."""

    library = _load_host()
    if library is None:
        return None
    pointer = ctypes.c_void_p()
    if library.AtlAxGetControl(wintypes.HWND(container), ctypes.byref(pointer)) != 0:
        return None
    if not pointer.value:
        return None
    return DispatchArgument(pointer.value)
