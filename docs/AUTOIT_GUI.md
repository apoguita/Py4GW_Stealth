# The AutoIt-compatible GUI layer (`py4gw.gui`)

**Status: implemented and verified against AutoIt itself. Not a port.**

This document is the specification record for `py4gw/gui`: an AutoIt v3-compatible GUI
layer backed by tkinter. It exists because AutoIt GUI scripts -- the GwAu3 lineage this
project's owner already writes -- have a small, familiar, well-documented statement set for
building windows and controls, and Python's own toolkits do not.

## Why this is not a port, and what that changes

The project's porting rule says the two source projects are the only content: *"Nothing that
is in neither source may be added here."* This layer is not an exception to that rule
quietly taken -- it is a **Stealth-owned component**, the same category as
`py4gw/game_thread/`:

| | ported classes (`Map`, `Player`, `Party`, `Dialog`, ... ) | Stealth-owned components |
| --- | --- | --- |
| Spec source | Reforged Python and Reforged Native, line for line | a written, external specification |
| Examples | `Map`, `Player`, `Party`, `Dialog` | `py4gw/game_thread/` (its spec: `docs/NATIVE_EXECUTION_PLAN.md`), `py4gw/gui` (its spec: this document) |
| Parity test | member-for-member against the source file | against the specification and its reference implementation |

Neither Reforged nor Reforged Native has a host-window toolkit (Reforged's UI is an
in-client ImGui overlay: `Py4GWCoreLib/ImGui.py`, `ImGui_src`), so there is no source to
port here and none is claimed. The specification is the **AutoIt v3 GUI reference**, and the
reference implementation is the **AutoIt interpreter installed on this machine**, which was
run to answer what its help file leaves open.

Nothing in this layer touches the game client. It is a controller-side window toolkit, and it
is now the project's only window layer: `main.py` was ported onto it on 2026-10-11 and NiceGUI
-- with its `native` extra, pywebview, and the interpreter dependency it brought -- was removed
from the project in the same change. The package installs with no runtime dependencies.

**What moved.** The previous `main.py` had a "Guild Wars clients" tab and a "Client data" tab
carrying one sub-tab per context. The port keeps the two tabs and the same readers, formatters
and status lines, but a GUI holds a single AutoIt Tab control (and the reference's own note
says a second belongs in a child GUI), so the data tab holds a context **list** and one hidden
control set per context instead of twenty-one sub-tabs: the chosen context's controls are
shown with `GUICtrlSetState($GUI_SHOW)` and the rest with `($GUI_HIDE)`. The window runs in
OnEvent mode, so its callbacks are the AutoIt style -- one function per control -- rather than a
`GUIGetMsg()` loop. Everything else about the window is unchanged: the client list is still
read-only, `Connect selected` still installs the game-thread layer, and the context tables
still show the maintained properties first and the raw layout fields after them.

## The specification, and where it comes from

| Source | Path on this machine | Use |
| --- | --- | --- |
| AutoIt v3 GUI reference (`GUIRef.htm`, `GUIRef_MessageLoopMode.htm`, `GUIRef_OnEventMode.htm`, the 71 `functions/GUI*.htm` pages, `appendix/GUIStyles.htm`) | `C:\Program Files (x86)\AutoIt3\AutoIt.chm`, decompiled with `hh.exe -decompile <dir> AutoIt.chm` | function set, signatures, parameter defaults, return values, styles, the two event modes |
| AutoIt include files (`GUIConstantsEx.au3`, `AutoItConstants.au3`, `WindowsConstants.au3`, the per-control `*Constants.au3` files) | `C:\Program Files (x86)\AutoIt3\Include\` | every constant the reference names, value for value |
| The AutoIt interpreter | `C:\Program Files (x86)\AutoIt3\AutoIt3.exe` | the numbers the help file does not state |

The decompiled help file is not copied into this repository; it is a local AutoIt
installation artifact. The three probe scripts that read the interpreter, and the reports
they wrote, are kept in `tests/autoit_reference/`.

### Regenerating the constants

`py4gw/gui/constants.py` is generated, not hand-written:

```text
python tools/generate_autoit_gui_constants.py
```

It reads `Global Const $NAME = <expression>` lines from the include files listed in
`INCLUDE_FILES`, resolves each expression (`BitOR` and friends are evaluated, `$` references
are resolved), and writes one section per source file with that file's own AutoIt version in
the header comment. 3111 constants are produced. AutoIt's names are kept with the leading
`$` removed, so an AutoIt line `GUISetState(@SW_SHOW)` reads `GUISetState(SW_SHOW)` here, and
`@SW_SHOW` is `SW_SHOW`.

The `@SW_*` show-state macros are not in any include file -- the interpreter defines them.
Their values were read from the interpreter (see the readings table below) and are written
into the top of the generated module.

## Using it

The 71 function names, the constants, and the two event modes are AutoIt's:

```python
from py4gw.gui import *

WINDOW = GUICreate("Hello World", 200, 100)
GUICtrlCreateLabel("Hello world! How are you?", 30, 10)
ID_OK = GUICtrlCreateButton("OK", 70, 50, 60)
GUISetState(SW_SHOW)

while True:
    MESSAGE = GUIGetMsg()
    if MESSAGE == ID_OK:
        GUICtrlSetData(ID_OK, "pressed")
    elif MESSAGE == GUI_EVENT_CLOSE:
        break

GUIDelete()
```

OnEvent mode is the same switch AutoIt uses, and the same idle loop:

```python
Opt("GUIOnEventMode", 1)
WINDOW = GUICreate("Hello World", 200, 100)
GUISetOnEvent(GUI_EVENT_CLOSE, on_close)
ID_OK = GUICtrlCreateButton("OK", 70, 50, 60)
GUICtrlSetOnEvent(ID_OK, on_ok)
GUISetState(SW_SHOW)
while not closed:
    Sleep(50)
```

`examples/autoit_gui.py` is a working window in that shape (a group, a character combo, an
On Top checkbox, Start/Refresh buttons, a progress bar and a log list) and is the shape a
GwAu3 script already has (`Scripts\Exemples\Exemple_AutoitGUI_Tester.au3`).

Internally one `GUI` instance owns everything -- windows, controls, the control-ID counter,
the current window, the pending messages, the options and the macros -- and the module-level
functions are AutoIt's global functions over that one instance. `@GUI_CtrlId`, `@GUI_WinHandle`,
`@GUI_CtrlHandle`, `@GUI_DragId`, `@GUI_DragFile`, `@GUI_DropId` and `@error` are module
attributes and instance attributes (Python has no macro syntax, so the `@` is dropped).

## What the interpreter verified

Everything below was read from `AutoIt3.exe` with the probe scripts in
`tests/autoit_reference/`, because the help file does not state it. The ports' tests assert
these same numbers (`tests/test_gui_offline.py`, marked `(AutoIt: ...)`).

| Reading | AutoIt's answer | Probe |
| --- | --- | --- |
| `GUICreate()` with no width/height | client area 400x400 | `probe_autoit_behavior.au3` |
| Control IDs | AutoIt's own counter starting at 3; **not** window handles (`Button id=3 handle=0x00D20B34`) | same |
| `GUICtrlGetHandle` | a real handle for widgets; `0` for Dummy, TabItem and ListViewItem | same |
| Default window style / exStyle | `0x84CA0000` (`$WS_POPUP|$WS_CAPTION|$WS_SYSMENU|$WS_MINIMIZEBOX|$WS_CLIPSIBLINGS`) / `0x100`; `GUIGetStyle` reports them signed: `-2067136512, 256` | same |
| `GUICtrlRead` | checkbox unchecked 4 / checked 1; advanced adds the text; Button/Label/Input/Edit their text; Progress the percentage; Slider the value; List and Combo the selected value; Tab the 0-based index and (advanced) the tab item's ID; TabItem `""`; TreeView the selected item's ID; TreeViewItem its state and (advanced) its text; ListView the selected item's ID; ListViewItem its subitems plus a trailing separator (`'a|b|'`); Dummy the value sent; Date the regional long date | same |
| `GUICtrlGetState` | 80 normal (`$GUI_SHOW|$GUI_ENABLE`), 96 hidden, 144 disabled; the checked state is **not** included; `-1` for an undefined control | same |
| Menu / MenuItem read | state `68` (`$GUI_ENABLE|$GUI_UNCHECKED`); advanced returns the text | same |
| Option defaults | `GUIOnEventMode=0`, `GUIEventOptions=0`, `GUICoordMode=1`, `GUIResizeMode=0`, `GUICloseOnESC=1`, `GUIDataSeparatorChar="|"` | `probe_autoit_constants.au3` |
| `@SW_*` macros | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 for the Win32 states; `@SW_ENABLE=64`, `@SW_DISABLE=65`, `@SW_LOCK=66`, `@SW_UNLOCK=67`; `@SW_MAXIMIZE=@SW_SHOWMAXIMIZED=3` | `probe_autoit_constants.au3`, `probe_autoit_sw.au3` |
| OnEvent delivery | `GUICtrlSendToDummy` calls the registered function *inside the call*, with `@GUI_CtrlId` = the dummy's ID, `@GUI_WinHandle` = the window, `@GUI_CtrlHandle` = 0 | `probe_autoit_eventmode.au3` |
| Message-loop delivery | the same send is then returned once by `GUIGetMsg()`, then `0` | same |

## Style and state mapping

AutoIt styles are Win32 style bits; tkinter has none. Each style with an equivalent is
translated in `py4gw/gui/styles.py`, and the translation is written out per entry:

| AutoIt | tkinter |
| --- | --- |
| `$WS_DISABLED` | widget `state="disabled"` |
| `$ES_PASSWORD`, `$ES_READONLY` | `show="*"`, `state="readonly"` |
| `$ES_CENTER`/`$ES_RIGHT`/`$ES_LEFT` | `justify` |
| `$ES_NUMBER`, `$ES_UPPERCASE`, `$ES_LOWERCASE` | a validation callback on the Entry |
| `$CBS_DROPDOWNLIST` | `ttk.Combobox` `state="readonly"` |
| `$LBS_SORT` | items sorted as they are added |
| `$LBS_MULTIPLESEL`/`$LBS_EXTENDEDSEL` | `selectmode="multiple"`/`"extended"` |
| `$BS_FLAT`, `$BS_MULTILINE`, `$BS_CENTER`/`$BS_LEFT`/`$BS_RIGHT` | `relief="flat"`, `wraplength`, `justify`/`anchor` |
| `$BS_PUSHLIKE` | `indicatoron=False` |
| `$BS_AUTO3STATE` | `tristatevalue=2` (`$GUI_INDETERMINATE`) |
| `$BS_ICON`/`$BS_BITMAP`, `$SS_ICON`/`$SS_BITMAP` | `compound="left"`/`"center"` with the image from `GUICtrlSetImage` |
| `$SS_SUNKEN`, `$SS_ETCHEDFRAME`, `$SS_BLACKFRAME`/`$SS_GRAYFRAME`, `$SS_WHITEFRAME` | `relief` and `borderwidth` |
| `$SS_CENTERIMAGE`, `$SS_LEFTNOWORDWRAP` | `compound`, `wraplength=0` |
| `$TVS_CHECKBOXES` | recorded (`ttk.Treeview` has no checkbox column) |
| `$PBS_VERTICAL`, `$PBS_MARQUEE` | `orient="vertical"`, `mode="indeterminate"` |
| `$TBS_VERT` | `orient="vertical"` |
| `$UDS_WRAP` | the native up-down control's own style (`GUICtrlCreateUpdown`) |
| `$WS_EX_TOPMOST` | `attributes("-topmost", True)` |
| `$GUI_DOCK*` resizing values | the docking rule, applied when the window changes size (see the resizing section) |
| `$GUI_BKCOLOR_TRANSPARENT` | the parent widget's colour, which is how tkinter looks transparent |

States are implemented as the reference documents them: `$GUI_CHECKED`,
`$GUI_INDETERMINATE`, `$GUI_UNCHECKED`, `$GUI_SHOW`, `$GUI_HIDE`, `$GUI_ENABLE`,
`$GUI_DISABLE`, `$GUI_FOCUS`, `$GUI_EXPAND` (tree items), `$GUI_DEFBUTTON` (a tree item's
bold face), `$GUI_ONTOP` (`lift`). Values can be summed, as the State table says.

## Accepted but not applied, and why

These are kept, recorded on the control or window, and reported back by `GUICtrlGetStyle`
style bits and `GUIGetState`, but have no visual effect because tkinter has no equivalent.
They are listed here rather than silently dropped:

* Window bits: `$WS_POPUP`, `$WS_CAPTION`, `$WS_SYSMENU`, `$WS_MINIMIZEBOX`,
  `$WS_MAXIMIZEBOX`, `$WS_SIZEBOX`, `$WS_CHILD`, `$WS_CLIPSIBLINGS`, `$WS_CLIPCHILDREN`,
  `$WS_TABSTOP`, `$WS_GROUP`, `$WS_HSCROLL`, `$WS_VSCROLL` and the `$WS_EX_*` family. The
  `$WS_SIZEBOX`/`$WS_MAXIMIZEBOX` pair still decides whether the Tk window is resizable, and
  `$WS_EX_TOPMOST` still sets the topmost attribute.
* Control styles: `$SS_NOTIFY`, `$SS_SIMPLE`, `$SS_NOPREFIX`, `$ES_AUTOVSCROLL`,
  `$ES_WANTRETURN`, `$CBS_AUTOHSCROLL`, `$CBS_SIMPLE`, `$LBS_NOINTEGRALHEIGHT`,
  `$LVS_ICON`, `$LVS_SMALLICON`, `$LVS_LIST`, `$TVS_HASBUTTONS`, `$TVS_HASLINES`,
  `$TVS_LINESATROOT`, `$TVS_SHOWSELALWAYS`, `$TVS_DISABLEDRAGDROP`, `$TBS_AUTOTICKS`,
  `$TBS_NOTICKS`, `$TBS_BOTH`, `$TCS_TOOLTIPS`, `$UDS_ALIGNRIGHT`/`$UDS_ALIGNLEFT`.
* States: `$GUI_DROPACCEPTED` and `$GUI_NODROPACCEPTED` (tkinter has no drop target) and
  `$GUI_NOFOCUS`.
* Options: `GUIEventOptions=1` **is applied**: measured from the interpreter
  (`probe_autoit_gui_event_options_out.txt`), a `$SC_MINIMIZE` system command left a window at
  state 15 and still called its `$GUI_EVENT_MINIMIZE` function, where the same command with the
  option unset took the window to state 23 (minimised) and called the function too. The port hooks
  the window while the option is set -- suppressing the window's own behaviour means seeing the
  system command first, which is a window procedure's job -- swallows
  `$SC_MINIMIZE`/`$SC_MAXIMIZE`/`$SC_RESTORE` and delivers the notification from the pump. The
  page's mention of a *window resize* is not covered: the port does not suppress the sizing path.
* Font `quality` **reaches a native control**: `GUICtrlSetFont`'s quality table (0 default, 1 draft,
  2 proof, 3 nonantialiased, 4 antialiased, 5 cleartype) is GDI's own `lfQuality` list value for
  value, so the port creates a real font with it and applies it with `WM_SETFONT`; measured, the
  control's own `LOGFONT` (through `WM_GETFONT` and `GetObjectW`) reports 5 or 4 back as asked. The
  same call on a tkinter-drawn control sets a Tk font, and Tk draws its text itself, so the quality
  has no effect there -- that half is a stated divergence rather than a silent one. (An attempt to
  read the *interpreter's* own `LOGFONT` with a probe came back all zeros, so the mapping is the
  reference's table plus the port's read-back, not a measurement of AutoIt.)

## Win32 parity: the functions that call what AutoIt calls

AutoIt's GUI *is* Win32, and tkinter's widgets on Windows are real windows with real handles.
That is the whole reason this layer can reach parity rather than approximate: for anything
tkinter has no widget-level equivalent for, the port uses **the same Win32 call AutoIt uses**
on the same handle. `py4gw/gui/native.py` is the one module that declares `ctypes`, in the same
way `py4gw/win32/win32.py` is the process boundary for the rest of the library.

| AutoIt function | What it is in Win32 | What the port does |
| --- | --- | --- |
| `GUICtrlSendMsg` | `SendMessage(hwndCtrl, msg, wParam, lParam)` | the widget's `winfo_id()` handle, `SendMessageW`; an integer or string wParam/lParam is accepted, as the reference says. Measured: `GUICtrlSendMsg($button, $BM_CLICK, 0, 0)` returns 0 in AutoIt, and 0 here |
| `GUICtrlRecvMsg` | `SendMessage` plus reading lParam back | lParamType 0 -> `[result, lParam]` from a 4-byte buffer, 1 -> a string buffer (the port's 1024 characters, stated because AutoIt does not state its own), 2 -> a `RECT`'s four elements |
| `GUISetState($SW_LOCK)` / `($SW_UNLOCK)` | `LockWindowUpdate(hwnd)` / `LockWindowUpdate(NULL)` | exactly that, including "@SW_UNLOCK just ignored the winhandle to unlock any locked window" |
| `GUIRegisterMsg` | a window-procedure hook (AutoIt's own internal WndProc) | `SetWindowLongPtrW`/`SetWindowLongW(GWL_WNDPROC)` with a Python `WNDPROC`, chaining through `CallWindowProcW` to tkinter's own procedure. A registered function declared with two parameters is called with two and one declared with four with four, as the page says; returning `$GUI_RUNDEFMSG` (or nothing) lets the window's own procedure run |
| `GUISetIcon` | `ExtractIconEx`/`LoadImage` plus `WM_SETICON` | the same, with AutoIt's "negative number causes 1-based index behaviour" |
| `GUICtrlSetData` on a ListView | `LVM_SETCOLUMN` per column | replaces the column headings and leaves the items alone -- measured from the interpreter |
| `$LVS_EX_CHECKBOXES` item state | the list view's own check state | the control gains the check column the style asks for (`' `/`''` in a narrow first column) while the item's values stay exactly what `GUICtrlRead` returns; `GUICtrlRead($item, 1)` returns `$GUI_CHECKED`/`$GUI_UNCHECKED` as AutoIt does |
| `GUICtrlRead` on an UpDown | the control's position; the buddy input holds the value | `""`, and `GUICtrlSetData` returns -1, as the interpreter does |
| `GUICtrlCreateUpdown` | the Win32 `msctls_updown32` class | the same class, attached to its buddy Input with `UDM_SETBUDDY`, so `$UDS_SETBUDDYINT` writes the position into that input: measured, after `UDM_SETPOS32(20)` the interpreter's input read "20" and so does the port's. `GUICtrlSetLimit` is `UDM_SETRANGE32`; the arrows are 18 pixels wide at the input's right edge, as the interpreter places them, and a real click on an arrow fires the control's function. The control is *placed after* `UDM_SETBUDDY` on purpose: it carries `$UDS_ALIGNRIGHT` and aligns itself to the buddy's rectangle, which for a tkinter Entry is still 1x1 while the GUI is hidden -- measured, the port's record said 18x22 while the window was 1x1 at the parent's origin and the pointer could not reach the arrows. **The arrows are inverted** (the lower half increases where the interpreter's upper half does) -- an open finding with its evidence below |
| control notifications | `WM_NOTIFY` to the control's parent | the window and the widget a control was placed in are hooked, so an UpDown's `UDN_DELTAPOS`, a Date's `DTN_DATETIMECHANGE`, a month calendar's `MCN_SELECT`/`MCN_SELCHANGE` and an Avi's `ACN_START`/`ACN_STOP` become control events, and a chosen day is recorded from the notification's `NMSELCHANGE`. The code is read signed (the header's `UINT` holds a negative constant), and the event is delivered by the pump rather than inside the procedure; a real click on an UpDown's arrow is verified to fire it |
| `GUICtrlCreateDate` | the Win32 `SysDateTimePick32` class | the same class, created as a child of the tkinter frame in its place, with `DTM_GETSYSTEMTIME`/`DTM_SETSYSTEMTIME` and `GetDateFormatW` for the regional date. Measured against the interpreter: read "Friday, January 2, 2026", `SetData` "2027/03/04" -> "Thursday, March 4, 2027", `$DTS_SHORTDATEFORMAT` -> "3/4/2027" |
| `GUICtrlCreateMonthCal` | the Win32 `SysMonthCal32` class | the same class; reads and sets "yyyy/mm/dd" as the interpreter does |
| `GUICtrlCreateAvi` | the Win32 `SysAnimate32` class | the same class, with `ACM_OPENW`/`ACM_PLAY`/`ACM_STOP` for `$GUI_AVISTART`/`$GUI_AVISTOP`/`$GUI_AVICLOSE`; reads `""` as the interpreter does |
| `GUICtrlCreateIcon` | a Win32 `Static` with `$SS_ICON` | the same class, with the icon loaded by `ExtractIconEx`/`LoadImage` and set with `STM_SETIMAGE`; 32x32 by default, and reads `""`, as the interpreter does |
| `GUICtrlSetTip` | the `tooltips_class32` control, **one per control**, holding one tool | the same class, built the way the interpreter's own tip windows are: `$WS_POPUP|$WS_CLIPSIBLINGS|$TTS_ALWAYSTIP|$TTS_NOPREFIX|$TTS_NOANIMATE` (`$TTS_BALLOON` added for `$TIP_BALLOON`) with `$WS_EX_LAYERED|$WS_EX_TOOLWINDOW|$WS_EX_TOPMOST`, parented to the GUI window, the control added with `TTM_ADDTOOLW` (`$TTF_IDISHWND|$TTF_SUBCLASS`, plus `$TTF_CENTERTIP` for `$TIP_CENTER`), and the title row with `TTM_SETTITLEW`, whose `wParam` is the icon -- the reference's `title`/`icon`/`options` parameters *are* this control's. A second call for the same control replaces its tip window, and the tip goes when the control or the window does, as the interpreter's does |

The interpreter's own tips were measured rather than assumed, by
`tests/autoit_reference/probe_autoit_gui_tip.au3` and `probe_autoit_gui_tip2.au3`. Their readings,
and the port's answer to each:

| Reading (AutoIt) | The port |
| --- | --- |
| no `tooltips_class32` in the process before the first `GUICtrlSetTip` | created on the first `GUICtrlSetTip` for each control |
| two tipped controls -> **two** tip windows, each with **one** tool whose `uId` is that control's window | the same: one tooltip per control, `uId` = `GUICtrlGetHandle(control)` |
| style `0x84000013`, and `0x84000053` with `$TIP_BALLOON` | the same values, read back from the port's windows |
| exStyle `0x00080088` | the same |
| the GUI window is the tip's parent | the same (`GetParent`) |
| tool flags `0x51`, and `0x53` after `$TIP_CENTER` | the same values |
| `$TIP_CENTER` is `$TTF_CENTERTIP` **on the tool** -- the style stays plain | the same (the port sets no width instead, as it first did) |
| `$TIP_FORCEVISIBLE` left the flags at `0x51` and the style unchanged | accepted, and nothing else changes -- the measurement is what the port reproduces |
| titling one control's tip left the other control's title alone | titles are per control, because the tips are |
| a repeated `GUICtrlSetTip` produced a **new** window handle (the old one gone) | the old window is destroyed and a new one created |
| `GUICtrlDelete` removed that control's tip; `GUIDelete` removed the rest | the same |

Three more readings were needed to ask a tooltip anything, and each corrects a mistake the port made
first:

* `TTM_GETTITLE` is `WM_USER + 35` (**`0x0423`**). `0x0435` is `TTM_GETTOOLINFOW` and answers 0
  when asked for the title, which is how the wrong constant was found.
* `TTM_GETTEXTW` is `WM_USER + 56` (**`0x0438`**). `0x040D` is `TTM_GETTOOLCOUNT`, and it answered
  1 for the one tool a tooltip held -- the reading that identified it.
* `TTM_GETTITLE` returns **TRUE**, not the icon; the icon is the `uTitleBitmap` the message fills
  into its `TTGETTITLE`. Reading the return value instead reports icon 1 (`$TIP_INFOICON`) for
  every title, whatever icon was set -- which is exactly what the port's own check did until the
  control was asked both ways in one process and the two answers disagreed.

**What is verified about the drawing, exactly.** The tip was seen to appear with a real pointer over
a control -- `WindowFromPoint` was the control, and `IsWindowVisible` on the tip window turned true
while the pointer sat there -- with the tip attached through this same control and the same
`TTM_ADDTOOLW`/`TTM_SETTITLEW` messages, before the tips were made per-control. Re-running that
check after the change was not possible: this desktop now has a topmost full-screen window
(`D3 Main Window Class`, the foreground window, at every point of the 3440x1440 screen) that
`SetWindowPos(HWND_TOPMOST)` cannot lift our window above, so the pointer never reaches the control.
Windows' own `TTM_POPUP` and `TTM_RELAYEVENT` both answered 0 and left the tip hidden, and a posted
`WM_MOUSEMOVE` did not activate it either. Those are the reasons the drawing re-check is outstanding
rather than a claim about the port; what the port's windows *are* is verified against the interpreter
in the table above.

## Parity, function by function

Every function of the AutoIt GUI reference, and what it is in this port. **Parity** means the
behaviour was checked against the interpreter or is the behaviour the reference documents;
**native** means the port creates the Win32 class AutoIt creates. No function is left as a named
gap any more (see "Named gaps" below); where the reference states nothing about a behaviour, the
port says so at that call site rather than returning a plausible wrong value.

### Window functions

| Function | Port | Status |
| --- | --- | --- |
| `GUICreate` | tkinter toplevel; the real window handle from `wm frame`; 400x400 with no size, and the default style `0x84CA0000` / `$WS_EX_WINDOWEDGE` | parity |
| `GUISetState` | show/hide/minimize/maximize/restore/enable/disable; `$SW_LOCK`/`$SW_UNLOCK` are `LockWindowUpdate` | parity (measured) |
| `GUISetStyle` | stores the style; resizability and topmost follow it; native controls get their window style replaced | parity |
| `GUIGetStyle` | `[style, exStyle]`, reported as the signed 32-bit values the interpreter returns | parity (measured) |
| `GUISetCoord` | sets the cell `GUICoordMode` 2 uses | parity |
| `GUISetBkColor` | the window's background, from AutoIt's `0x00BBGGRR` | parity |
| `GUISetFont` | the window's default font, applied to its controls | parity |
| `GUISetIcon` | `ExtractIconEx`/`LoadImage` + `WM_SETICON`, with AutoIt's 1-based negative index | parity (measured) |
| `GUISetCursor` | Win32 cursor IDs mapped to Tk cursor names; `16` hides the cursor | parity |
| `GUISetHelp` | records the file and runs it on F1 | parity |
| `GUISetAccelerators` | `^`, `!`, `+`, `#` and the named keys translated to bindings, with `#` checked against the Windows key's own state; an unset table unbinds what it set | parity (measured live) |
| `GUIRegisterMsg` | a real window-procedure hook, chaining to tkinter's own; two- and four-parameter functions, and the function is called from the pump (see below) | parity for what the reference documents, except that the function cannot answer the message |
| `GUIGetCursorInfo` | five-element array from Tk's pointer position and the port's button state | parity |
| `GUIGetMsg` | drains the queue; advanced array; 0 and `error = 1` in OnEvent mode; idles like AutoIt (14.7 ms measured there, 10 ms here) | parity |
| `GUIDelete` | destroys the window, its controls (native ones included) and any hooked procedure | parity |
| `GUISwitch` | the current window, and the tab item new controls belong to | parity |
| `GUIStartGroup` | a radio-group boundary | parity |
| `GUISetOnEvent` | system events by `specialID`, `""` unregisters | parity |
| `$GUI_EVENT_RESIZED` | delivered when the window's own size changes. A toplevel is in the bindtags of the widgets inside it, so the handler also receives their Configure events (traced: a 500x300 window's handler was called with the frame's, a scrollbar's and a text's sizes, down to 1x1); only the window's own event is a resize, and only it docks the controls | parity (measured) |
| `GUICtrlSetOnEvent` | a control's function, `""` unregisters | parity |

### Control creation

| Function | Port | Status |
| --- | --- | --- |
| `GUICtrlCreateLabel` | `tk.Label`, text autofit, `$SS_*` styles | parity |
| `GUICtrlCreateButton` | `tk.Button`, autofit, `$BS_*` styles | parity |
| `GUICtrlCreateInput` | `tk.Entry`, `$ES_PASSWORD`/`$ES_READONLY`/`$ES_NUMBER` and the case folds | parity |
| `GUICtrlCreateEdit` | `tk.Text` in a frame with a scrollbar | parity |
| `GUICtrlCreateCheckbox` | `tk.Checkbutton`; the variable holds `$GUI_CHECKED`/`$GUI_UNCHECKED`/`$GUI_INDETERMINATE` | parity (measured) |
| `GUICtrlCreateRadio` | `tk.Radiobutton` sharing a group variable | parity (measured) |
| `GUICtrlCreateCombo` | `ttk.Combobox`; `$CBS_DROPDOWNLIST` is read-only | parity |
| `GUICtrlCreateList` | `tk.Listbox` in a frame with a scrollbar | parity (measured) |
| `GUICtrlCreateListView` | `ttk.Treeview` in report mode; `LVM_SETCOLUMN` headings; `$LVS_EX_CHECKBOXES` gains the check column | parity (measured) |
| `GUICtrlCreateListViewItem` | a row, with its values and its check state | parity (measured) |
| `GUICtrlCreateTreeView` | `ttk.Treeview` with a tree column | parity (measured) |
| `GUICtrlCreateTreeViewItem` | a node, under the tree or under another node | parity (measured) |
| `GUICtrlCreatePic` | `tk.Label` with a `PhotoImage`: PNG and GIF read by Tk, and BMP, JPG, TIF and the rest read by GDI+ -- Windows' own decoder, handed to Tk as a PPM. Its size is the reference's: what the caller gives, **0 meaning the file's own size**, and otherwise the previously used size (the interpreter's first Pic in a fresh window is 150x150) | parity (measured) |
| `GUICtrlCreateIcon` | **native** `Static` + `$SS_ICON`, icon from `ExtractIconEx`/`LoadImage` | parity (measured) |
| `GUICtrlCreateGraphic` | a `Canvas` drawn with the `$GUI_GR_*` commands | parity (bezier uses Tk's spline, see below) |
| `GUICtrlCreateProgress` | `ttk.Progressbar`, `$PBS_VERTICAL`/`$PBS_MARQUEE` | parity (measured) |
| `GUICtrlCreateSlider` | `tk.Scale` with `GUICtrlSetLimit` as its range | parity (measured) |
| `GUICtrlCreateGroup` | `tk.LabelFrame`, and a radio-group boundary | parity |
| `GUICtrlCreateTab` / `GUICtrlCreateTabItem` | `ttk.Notebook` and a frame per item, closed by `GUICtrlCreateTabItem("")` | parity (measured) |
| `GUICtrlCreateMenu` / `GUICtrlCreateMenuItem` | tkinter menus with cascade, submenu, entry positions and separators | parity (measured) |
| `GUICtrlCreateContextMenu` | a `tk.Menu` popped on right click, refused for Edit/Input as the page says | parity |
| `GUICtrlCreateDate` | **native** `SysDateTimePick32`, `DTM_*` and the regional date | parity (measured) |
| `GUICtrlCreateMonthCal` | **native** `SysMonthCal32`; see the date caveat above | parity (measured, with one caveat) |
| `GUICtrlCreateAvi` | **native** `SysAnimate32`, `ACM_OPENW`/`ACM_PLAY`/`ACM_STOP` | parity (measured) |
| `GUICtrlCreateDummy` | a hidden frame holding the value `GUICtrlSendToDummy` gives it | parity (measured) |
| `GUICtrlCreateUpdown` | **native** `msctls_updown32` on its buddy Input | parity (measured; its event awaits a live click) |
| `GUICtrlCreateObj` | the caller's object hosted in a frame with the platform's ActiveX host (`AtlAxAttachControl`), driven through `py4gw/gui/objects.py` | parity (measured; see the object-control section) |

### Control update and read

| Function | Port | Status |
| --- | --- | --- |
| `GUICtrlRead` | every documented per-control value, including the advanced table | parity (measured) |
| `GUICtrlSetData` | every documented per-control effect; ListView headings; UpDown returns -1 | parity (measured) |
| `GUICtrlSetState` | the state table, summed values, tree-item states, Avi's own states | parity (measured) |
| `GUICtrlGetState` | `$GUI_SHOW`/`$GUI_HIDE` + `$GUI_ENABLE`/`$GUI_DISABLE`; -1 for an unknown control; a ListView's clicked column | parity (measured) |
| `GUICtrlSetPos` | moves a control, `None` for AutoIt's `Default`, `GUICoordMode` honoured | parity |
| `GUICtrlSetStyle` | styles re-applied per control kind; native controls get their window style | parity |
| `GUICtrlSetResizing` | the docking value, applied when the window is resized (see the resizing section) | parity (measured, 223 boxes) |
| `GUICtrlSetFont` | a font per control from size/weight/attribute/name/quality: a Tk font for a tkinter control, a real GDI font applied with `WM_SETFONT` for a native one, where the quality is the control's own | parity (quality reaches native controls; tkinter-drawn text has no GDI quality) |
| `GUICtrlSetColor` / `GUICtrlSetBkColor` | text and background colours, `$GUI_BKCOLOR_TRANSPARENT` as the parent's colour | parity for the controls the page lists |
| `GUICtrlSetDefColor` / `GUICtrlSetDefBkColor` | the window's defaults, applied to its controls | parity |
| `GUICtrlSetImage` | pictures on Label/Pic/Button, icons on an Icon control, images on tree and list items | parity for what Tk reads, plus native icons |
| `GUICtrlSetCursor` | a Win32 cursor ID mapped to a Tk cursor | parity |
| `GUICtrlSetTip` | one `tooltips_class32` per control, with `$TIP_BALLOON`/`$TIP_CENTER` as its style and tool flags and its own title and icon row | parity (measured, eleven readings from the interpreter) |
| `GUICtrlSetLimit` | Input/Edit length, List extent, Slider and UpDown ranges | parity |
| `GUICtrlSetGraphic` | the whole `$GUI_GR_*` command set on a canvas | parity (the bezier is the cubic itself, flattened the way `PolyBezier` does) |
| `GUICtrlSendMsg` | `SendMessage` on the control's window, integer or string parameters | parity (measured) |
| `GUICtrlRecvMsg` | `SendMessage` and the documented return shapes | parity |
| `GUICtrlSendToDummy` | sets the value and notifies, only while the window is shown | parity (measured) |
| `GUICtrlGetHandle` | the control's window handle, 0 where the page says none | parity (measured) |
| `GUICtrlRegisterListViewSort` | heading clicks call the registered comparator | parity |
| `GUICtrlDelete` | destroys the control, native ones included, and takes a ListViewItem's or TreeViewItem's row out of its control | parity (measured) |

**Behavioural items still recorded as accepted but not applied**: `$TCS_MULTILINE` (tkinter's
Notebook cannot wrap tabs). Font `quality`, the bezier command and the `Pic` control's formats were
on this list and are not any more -- see the notes below this table.

### The widget a control's content and events live in

AutoIt's List and Edit are single windows carrying their own scrollbars; tkinter has no such widget,
so the port draws each as a frame holding the widget itself plus a scrollbar. The *frame* is what
gets placed on the window, and the list box or text box inside it is what the user selects and types
in. That difference has one rule attached to it, and it was measured the hard way: **every function
that reaches a control's content -- its events, its font, its colours, its enabled state, its cursor
-- must reach the inner widget** (`_content_widget` in `py4gw/gui/gui.py`). Binding the events on
the frame instead left a List answering nothing at all, and the interpreter's own reading is that a
List answers a click with **its own** control ID:

| Reading (probe_autoit_listview_event_out.txt) | Value |
| --- | --- |
| clicking a row of a List | calls the function registered on the **List**, `@GUI_CtrlId` = the List's ID |
| clicking a row of a ListView | calls the function registered on the **ListView**, `@GUI_CtrlId` = the ListView's ID -- the functions registered on the two items were never called |
| `GUICtrlRead(List)` after the click | the selected item's text |
| `GUICtrlRead(ListView)` after the click | the selected item's identifier, which is what its own page documents |

`GUICtrlDelete` reaches an item too: measured (probe_autoit_delete_item_out.txt), deleting a
ListViewItem returned 1 and took its row out of the control -- three rows became two, the neighbours
kept their text, the deleted item then read 0 and deleting it again returned 0 -- and a TreeViewItem
behaved the same way. The port deleted only its own control record, so a table that clears itself by
deleting its items and then refilling them grew a duplicate row on every redraw.


### Accelerators, including the Windows key

`GUISetAccelerators` takes AutoIt's `HotKeySet()` keys. `^`, `!` and `+` are tkinter's Control, Alt
and Shift and become a binding; **`#` is the Windows key, which tkinter cannot spell at all**, so
that key's base key is bound and the chord is decided by asking Windows:

* `native.win_key_down()` reads `GetAsyncKeyState($VK_LWIN)`/`($VK_RWIN)` -- the system's own state,
  which is what the modifier means;
* measured, with the real key held down and the base key delivered to the window: the base key
  *alone* actions nothing, and the same press **with the Windows key held** actions the control --
  `GUIGetMsg()` returns its control ID and, in OnEvent mode, its function runs. The Windows key was
  injected with `keybd_event` for that check (`SendInput` with the extended flag did not set its
  state), and the base key was delivered by Tk itself (`event_generate`), because no window can hold
  the foreground on this desktop while the harness's overlay is on top -- so the *interpreter's* own
  `#` accelerator was not exercised, and the port's behaviour is what the reference states the key
  means rather than a copy of a measurement;
* unsetting the table now unbinds what it bound: "passing this function a non-array parameter will
  unset all accelerators", and before this the binding stayed live, so an unset accelerator kept
  firing. The port's own `$GUICloseOnESC` binding is left alone, because an accelerator can name the
  same key.

### Resizing a window: `GUICtrlSetResizing` and `GUIResizeMode`
The reference's page gives the docking table and says a control's default resizing is control
dependent; the interpreter answered the rest, through `probe_autoit_resizing.au3` to
`probe_autoit_resizing10.au3` (their reports are in `tests/autoit_reference/`). What the port does,
and what each piece was read from:

| Question | The interpreter's answer | The port |
| --- | --- | --- |
| what a resizing value means | `0` and values of `1024` and above mean **the control's own default**; `1`..`1023` is the docking value and is taken whole -- `1040` (= 16 + 1024) behaved as `0` did, not as 16 did, so it is not a plain bit mask | the same: `control.resizing if 0 < resizing < 1024 else control.dock_default` |
| when `GUIResizeMode` is read | at **control creation**: a Button created while the option was 0 kept its own `$GUI_DOCKSIZE` even though the option was set to `$GUI_DOCKAUTO` before the resize | the control records its default when it is created |
| each kind's default | Button, Pic, Tab, Icon, Avi and MonthCal `$GUI_DOCKSIZE`; Input, Checkbox, Radio, Combo and Date `$GUI_DOCKHEIGHT`; Label, Edit, List, Progress, Slider and Group `$GUI_DOCKAUTO` (their pages say so); ListView and TreeView measured as `$GUI_DOCKAUTO` | the same table |
| the position | scales by the client ratio and is **truncated**: 60 -> 103 and 45 -> 75 for a 398x275 client becoming 684x461 | `int()` |
| the size | scales the same way unless `$GUI_DOCKWIDTH`/`$GUI_DOCKHEIGHT` keep it: 100 -> 171, 30 -> 50 | the same |
| a pinned edge | keeps its **margin**: `$GUI_DOCKRIGHT` gave 275 = 684 - (398 - 60 - 100) - 171, `$GUI_DOCKBOTTOM` 211 = 461 - (275 - 45 - 30) - 50 | the same |
| both edges pinned | the size is the gap between them: `$GUI_DOCKBORDERS` gave 386x216 | the same, and it stops at 0 when the window is smaller than the margins (`$GUI_DOCKBORDERS` gave `60,45,0,0` in a 284x161 client, where the gap is -14x-84) |
| a pinned centre | keeps its offset from the client centre, and truncates: `$GUI_DOCKWIDTH|$GUI_DOCKHCENTER` gave 203 from 203.5 (683-wide client) | the same |
| `$GUI_DOCKHCENTER`/`$GUI_DOCKVCENTER` alone | **nothing** -- the position stayed scaled (measured for 8, 9, 128 and 129); each took effect together with `$GUI_DOCKWIDTH`/`$GUI_DOCKHEIGHT` | the centre is applied only with those bits |
| the base a resize computes from | the box the control was created or last **`GUICtrlSetPos`**-ed at, and the client size of that moment: repeated resizes do not drift (two resizes and back gave `50,43,100,32` from a creation box of `50,40,100,30` in a client that returned to 400x300), while a control moved to `200,100` docked from there (giving `343,167,171,50`) | the control records `dock_base` and `dock_client` at creation and in `GUICtrlSetPos` |
| where a control may land | a position may go negative (`$GUI_DOCKRIGHT` gave -25, `$GUI_DOCKBOTTOM` -56) but a size does not | the same |
| `GUIEventOptions=1` | did **not** stop the docking, though the page's remark says it can | the port docks too |

**Verification.** `tests/autoit_reference/probe_autoit_resizing10.au3` resizes one window once in
each direction from its creation size, and the port's own resize path was compared against it box
by box: **100 boxes, 0 mismatches**, for a grow (398x275 -> 684x461) and a shrink (398x275 ->
284x161) over all 50 docking values. The docking arithmetic was compared the same way against
every reading the probes took -- probe 9's grow and shrink stages, its odd-box part, probe 6's
per-kind defaults and probe 10 -- **223 boxes, 0 mismatches**.

**One case the port states rather than claims.** A control created *after* the window was already
resized docks from the box it was created at and the client size of that moment; the interpreter's
own numbers for that case fit no single-ratio model (probe_autoit_resizing8: a control created at
`60,45,100,30` in a 684x461 client came back `41,34,70,22` when the client went to 484x361, where
`60 * 484/684` is 42.46 and `100 * 484/684` is 70.76, so its x is one less and its y and height are
one less than that ratio gives). The port computes that case with the same rule it uses everywhere;
the divergence is this paragraph.

### Applied states beyond the recorded ones

* **`$GUI_DROPACCEPTED` / `$GUI_NODROPACCEPTED`** are real drop acceptance: the GUI's own window
  is told to accept dropped files, and the `WM_DROPFILES` message Windows sends on a drop is
  routed to the accepting control the drop's point falls in -- the point is in the payload, which
  is why routing needs no hit-test against the desktop. An Edit or Input control is then "set with
  the filename" (several files as separate lines), `@GUI_DragId` is -1, `@GUI_DragFile` is the
  file, `@GUI_DropId` is the control, and the drop arrives as that control's event.
* **`$GUI_NOFOCUS`** gives up the selection a ListView holds, which is what "Listview control
  will loose focus" asks for.
* **`$GUI_ONTOP`** lifts the control.

Four notes on how the message hook behaves, all measured here rather than assumed:

1. **A hooked procedure must not call tkinter, and the port's does not.** A hooked procedure runs on
   Windows' terms, in the middle of another window's message. A tkinter call from inside it releases
   the interpreter's thread state (`_tkinter` releases the GIL around every Tcl call), and a message
   arriving during that window re-enters the ctypes procedure with no thread state to restore. The
   result is fatal and uncatchable:

   ```text
   Fatal Python error: PyEval_RestoreThread: the function must be called with the GIL held, ... (the current Python thread state is NULL)
   ```

   Measured, by driving the port with real input: a real click on the arrow of an UpDown -- or on the
   dropdown of a Date, or in an Avi -- killed the process outright, and so did a real click on a
   *tkinter* Button once any window was hooked (`GUIRegisterMsg` alone was enough). The trigger was
   one Tcl call in the handler: `_window_for_handle` called `window.widget.winfo_id()` for every
   message. With the handler reduced to returning `$GUI_RUNDEFMSG` the same clicks survived, and so
   did a hand-written equivalent with no port code at all. The port now caches each window's widget
   handle (`_window.widget_id`), reads only what the message carries while inside the procedure, and
   **queues the work for the next pump**, which runs outside it. A control's event, a dropped file
   and a registered function are all delivered there.
2. **A native control only notifies on real input.** Even a plain Win32 host window receives no
   `DTN_DATETIMECHANGE` when a Date control's date is set programmatically, and no `MCN_*` when a
   calendar's view is moved by a posted key message.
3. **The notification code is a signed value, and the port reads it signed.** AutoIt's constants are
   all negative (`$UDN_DELTAPOS` -722, `$MCN_SELECT` -753, `$DTN_DATETIMECHANGE` -759). Read as the
   `UINT` the header declares, the same code is 4294966574, which matched none of the port's
   constants -- so a notification that arrived fired nothing, and no native control event could ever
   fire (measured: a posted `$UDN_DELTAPOS` reached the hook and produced no event until the code was
   signed).
4. **A message the port sends does not re-enter its own handlers.** A synchronous `SendMessage`
   from Python into a hooked window calls the hook back on the same thread from inside Python,
   which is not a reliable re-entry; while the port sends, the hook leaves the message to the
   window's own procedure.

**A registered function cannot answer the message, and that is a divergence.** AutoIt calls the
function while the message is being handled and uses its return value (`$GUI_RUNDEFMSG` or an
answer). The port calls it from the pump, for the reason in (1), so the value is not used and the
call happens one pump later. Everything else the reference states -- the GUI's own handle as the
first parameter, two parameters for a two-parameter function and four for a four-parameter one --
is as documented.

**The native-control events, driven by real input.** With the two defects above fixed, a real click
on an UpDown's arrow fires the control's function and writes the position into its buddy Input
(`GUICtrlRead($input)` reads `0` then `1` where the interpreter's own probe read the same kind of
change, `5` then `4` on the down arrow), and a real click on a tkinter Button fires its function
through the hook as well. A click on a Date's dropdown, which only opens its calendar, fires nothing
-- the interpreter's probe fired the Date's function only when a date changed, so that agrees.

## Named gaps: none left

Every function of the GUI reference now exists under its AutoIt name and is backed by a mechanism.
`GUICtrlCreateObj` was the last one and is closed: it needed the two halves an AutoIt script already
has -- an object variable (`ObjCreate`) and something to host it in -- and both are here now (see
the object-control section below). Where the reference states nothing about a behaviour, the port
still raises `NotImplementedError` naming that -- a `GUICtrlSetData` on a kind whose "data" the
reference's own per-control list does not define, for instance -- rather than returning a plausible
wrong value.

`GUICtrlSetTip`'s icon row was on this list and is not any more: the port attaches the Windows
tooltip control, so the title and its icon are Windows' own (see the Win32 table above).
`GUISetAccelerators` with the Windows key (`#`) is not on it any more either: the key is bound by
its base key and Windows is asked whether the Windows key is held, which is what the modifier means
(see the accelerator row above).

## Where the native controls differ, and why

Three things about the native controls are worth stating plainly, because each is a place the
port had to choose a mechanism rather than copy a call:

1. **A MonthCal's date is the port's record, with the control's own selection preferred.**
   Windows exposes no message that sets *or* returns a month calendar's selected date:
   `MCM_SETCURSEL`/`MCM_SETCURFOCUS` leave it unchanged, `MCM_GETCURSEL` reports 0 throughout, and
   `MCM_GETCALENDARGRIDINFO` flags no cell as selected on a calendar no one has clicked -- all
   measured on this machine. So `GUICtrlCreateMonthCal` and `GUICtrlSetData` move the control's
   *view* to the date's month (`GMR_VISIBLE` reports the displayed month, and Page Up/Page Down
   move it) and keep the date itself; `GUICtrlRead` prefers the control's own selection when
   there is one, which is how a day the user clicked is reported -- the `MCN_SELECT` notification
   carries that date, and the port records it there. The visible consequence is that a
   script-set day is not highlighted in the calendar until the user clicks.
2. **`$GUI_AVI*` follows AutoIt's include file, not its state table's parentheses.**
   `GUIConstantsEx.au3` defines `$GUI_AVISTOP = 0`, `$GUI_AVISTART = 1` and `$GUI_AVICLOSE = 2`,
   while the State table numbers them 0 = start, 1 = stop, 2 = close. The constants are what a
   script passes, so the port follows them; the interpreter agrees (it returned 1 for
   `$GUI_AVISTOP`).
3. **A control created with no size takes the size last used, and its kind's own default the first
   time -- both measured, per kind.** Let the reference speak first: "width/height default is the
   previously used width/height". The interpreter fills that in two ways.
   `probe_autoit_default_size_out.txt` measures the first: an Input with no size in a fresh window
   came out 200x20; an Input with no size after an Input made 50x10 came out 50x10; and an Input with
   no size after a *Button* came out **23x25**, the size the Button had computed for itself from its
   text. So a size a control was given by computation still counts as the size last used, and that is
   how the port treats the boxes of Button, Label, Checkbox and Radio. `probe_autoit_defaults_out.txt`
   measures the second -- each kind created first in a window of its own, short text and long text --
   and its readings are the port's per-kind seeds: Input 200x20, Edit 200x150, Combo 200x21, List
   200x149 (a list box snaps its height to whole items, so the port asks for the 150 behind it), a
   Progress and a Slider 0x0, no size at all, a Tab, TreeView, ListView, Pic and Graphic 150x150, a
   Date 200x20, a MonthCal 229x164 and a Group 200x150. Those four text-fitting kinds are absent from
   the table because their size *is* their text (short/long: Button 23x25/147x25, Label 18x21/163x21,
   Checkbox 25x21/176x21, Radio 21x21/148x21), and an Icon uses 32x32, which the reference states
   outright (`GUICtrlCreateIcon.htm`) rather than the probe. An UpDown takes the height of the Input
   it is attached to. A kind the probe did not seed falls back to 200x20 -- the value the reference's
   own sentence produces for the very first control in a window.


**An UpDown's event is verified live, and its arrows are inverted -- an open finding.** A real click
on either arrow fires the control's function (`$UDN_DELTAPOS` becomes the control event) and writes
the position into the buddy Input . But **the port's control increases on the *lower* half and
decreases on the upper one**, where the interpreter's does the opposite -- `probe_autoit_updown3_out.txt`
ticks its own control's position while an outside click is delivered: an upper-half click takes the
position and the input 5 -> 6, and AutoIt's page says "Windows increases the value when clicking the
upper arrow button". What has been ruled out, each measured on this machine:

* the style word: the interpreter's control is `0x50000106`
  (`$UDS_HOTTRACK|$UDS_ALIGNRIGHT|$UDS_SETBUDDYINT`) and the port's is `0x50000006`; a control
  created in the port's process with *the interpreter's exact style word* behaved the same way as
  the port's (lower half increases), so the style is not the cause;
* the class and geometry: both are `msctls_updown32`, and the port's window measures 18x22 with a
  normal 18x22 client rect and no extended style;
* the notification's own sign: the control reports `iDelta = -1` for the upper half and `+1` for
  the lower half, so it is the control's own hit-testing, not the port's arithmetic.

Everything below was tried in the port's own process, and each kept the same result -- the lower
half increasing:

* **the buddy**: a native `Edit` control as the buddy instead of the tkinter Entry;
* **the parent**: a plain native `Static` child of the toplevel instead of the toplevel itself;
* **no tkinter at all**: the same control in a plain Win32 host window in a Python process, which
  was the reading quoted in the previous revision of this page: that run's position reads were
  garbage (a control with a default range of 0..100 reported 536), and the corrected run using the
  port's own `native.updown_get_position` shows the same inversion;
* **the process's comctl32 version**: `CreateActCtx`/`ActivateActCtx` for
  `Microsoft.Windows.Common-Controls` 6.0.0.0 before the control is created;
* **the documented common-controls initialisation**: `InitCommonControlsEx` with
  `$ICC_WIN95_CLASSES`, `$ICC_DATE_CLASSES` and `$ICC_STANDARD_CLASSES`;
* **DPI awareness**: unaware, system-aware and per-monitor-v2 (the screen is at 96 DPI here);
* **the style word**: the port's `0x50000006` and the interpreter's exact `0x50000106`.

The interpreter's process is not the same environment: **`RTSSHooks.dll` (RivaTuner Statistics
Server) is loaded in `AutoIt3.exe` and in no Python process here** (measured by enumerating both
processes' modules -- the port even recorded RTSS on this machine before, for the access rights it
refuses). Loading that DLL into a Python process by hand does not change the behaviour (the hooks are
installed by the server's own initialisation, which is not an export), so this is a *candidate*, not
a conclusion: what is established is that the port's own code has been excluded, variable by
variable, and that the control is self-consistent -- its `iDelta` matches its own hit-testing, so a
script that reads `$iDelta` and applies it would step the same way Windows does here.

The controllable consequence for the port is written down rather than worked around: an UpDown in a
Python process on this machine steps down on the upper half, its events fire correctly, and the port
does not invert the control's own answer to hide it.

**Reading an Input that has an UpDown on it was wiping the input, and that is fixed.** tkinter keeps
an Entry's string in Tk, not in the window (measured: `GetWindowTextW` on the mapped window answers
with nothing while Tk holds "5"), and the port used to trust the window whenever the input had a
buddy -- so `GUICtrlRead` returned `""` and wrote that back into Tk. It now reads the window only
after the control has moved (the port records the position it last saw), which is exactly when the
window is the newer text, and pushes what it finds into Tk so the user sees the number the arrows
moved. An Input created with "5" now reads "5" before anything is clicked, as the interpreter's does
(`probe_autoit_events_out.txt`).

## The object control (`GUICtrlCreateObj`), measured

The reference's page for it is short, and four probes were written to fill in what it leaves unsaid
(`probe_autoit_obj.au3`, `probe_autoit_obj2.au3`, `probe_autoit_obj3.au3`, `probe_autoit_obj4.au3`,
and `probe_autoit_zero_size.au3` for the last question below). What the interpreter does:

| Reading | Value |
| --- | --- |
| the window the object lives in | a child of the GUI whose class is the **object's own** in-place window -- `Shell Embedding` for `Shell.Explorer.2`, style `0x50010000` (`$WS_CHILD|$WS_VISIBLE|$WS_TABSTOP`), exStyle `0x00010000` (`$WS_EX_CONTROLPARENT`), parent class `AutoIt v3 GUI` |
| when it is created | with the control, hidden until `GUISetState` shows the window |
| `GUICtrlGetHandle` on it | **0**, which is what its own page's list says ("The following controls will not return a handle: ... GUICtrlCreateObj() ...") |
| `GUICtrlRead` | `""` |
| `GUICtrlGetState` | 80 shown, 96 hidden -- the ordinary state word |
| `GUICtrlSetData` / `GUICtrlSetStyle` | both return 1 and change nothing ("GUICtrlRead() and GUICtrlSet have no effect on this control") |
| `GUICtrlSetPos` | moves the host window (50, 60, 120x80 read back from the object's own window) |
| omitted width/height | **8x8** -- and that 8x8 then stands as the size later controls inherit: an Input created after it with no size came out 8x8, not 200x20 |
| explicit `0, 0` | 0x0, and the next control with no size inherited the 0x0 |
| default resizing | the size stays and the position scales, which is `$GUI_DOCKSIZE` |
| `GUICtrlDelete` | the host window goes with the control; `GUICtrlGetState` for that id is then -1 |
| an object that cannot be embedded | `GUICtrlCreateObj(ObjCreate("Scripting.Dictionary"))` returned **0** with @error 1, while `ObjCreate` itself had succeeded |
| `ObjCreate` of a class that does not exist | returned 0 (with @error 0, though its page says the flag is set) |
| `ObjName` | "WebBrowser" for `Shell.Explorer.2` and "Dictionary" for `Scripting.Dictionary` -- the **coclass** names, neither the ProgIDs nor the registry's display names |
| the same object variable embedded twice | two controls were created and one host window existed -- measured both ways round (the last creation in one probe, the first in another), so the port does not claim a rule for it |

The port reproduces each of these. Two things are worth stating as choices:

1. **Hosting goes through the platform's ActiveX host.** The object is attached to the tkinter
   frame's real HWND with `AtlAxWinInit` + `AtlAxAttachControl` (the documented API for putting an
   already-created control into a window the caller owns), and `AtlAxGetControl` reads it back --
   which is how the test proves the embedded control *is* the caller's object, pointer for pointer.
   Where AutoIt hosts its own `IDispatch` with its own OLE site implementation, the port asks
   `atl.dll`, a Windows component. The window tree therefore has one extra level: the interpreter's
   GUI holds `Shell Embedding` directly, while the port's GUI holds the control's frame, which holds
   `Shell Embedding`. If `atl.dll` (or its host class) is missing on a machine,
   `native.object_host_error()` names exactly that instead of reporting a control that is not there.
2. **An object variable is `py4gw/gui/objects.py`.** `ObjCreate`, `IsObj` and `ObjName` are AutoIt's
   own functions and are provided under those names, because `GUICtrlCreateObj`'s parameter is
   "a variable pointing to a previously opened object" and there is no way to write that call
   without one. `ObjCreate` is `CoCreateInstance` over the class name (a ProgID or a CLSID string);
   its `servername`/`username`/`password` parameters are the documented DCOM mechanism
   (`COSERVERINFO` + `COAUTHINFO`/`COAUTHIDENTITY`, with the user split on the backslash the page
   writes), and are **inferred rather than measured** -- this machine has no DCOM peer to activate
   against. `ObjEvent` and `ObjGet` are not ported: neither is a GUI function and neither is needed
   to create or embed an object.
   Member access is resolved against the object's own type information, as AutoIt resolves it: a
   property with no arguments is read as its value, a method (or a property with arguments) is
   called. Python writes the two forms apart -- a name AutoIt writes bare because it takes no
   arguments (`$oIE.GoBack`) is written `browser.GoBack()` here -- and that is the whole of the
   difference in spelling.

## Divergences a caller will notice

1. **A function name is a callable.** AutoIt passes the *name* of an AutoIt function as a
   string (`GUICtrlSetOnEvent($id, "OnOK")`); Python needs the object. `""` still unregisters,
   as documented. `GUICtrlRegisterListViewSort` takes a callable the same way.
2. **`None` is AutoIt's `Default` keyword.** Where the reference says "If the Default keyword
   is used as a parameter, the current value is not modified" (`GUICtrlSetPos`), the port takes
   `None`.
3. **`GUIGetMsg()` idles when the queue is empty**, instead of calling
   `MsgWaitForMultipleObjects`: the reference's own words are "This function automatically
   idles the CPU when required so that it can be safely used in tight loops without hogging
   all the CPU". The interpreter was measured doing the same: 2000 idle calls took 14.7 ms
   each, against the port's 10 ms.
4. **`Sleep()` runs the event loop while it waits.** The OnEvent page's idle loop is
   `While 1 / Sleep(100) / WEnd` with "no action on the GUI inside the loop"; if `Sleep` did
   not pump, no event could ever arrive.
5. **Control IDs for items that are not widgets** (menu items, tab items, list items, tree
   items) come from the same counter as every other control. AutoIt's numbering for those is
   internal and undocumented; only "positive, unique" is promised, and that holds.
6. **`$GUI_EVENT_DROPPED` cannot be produced**: tkinter has no drag-and-drop, so the event the
   reference lists for a finished drop never arrives.
7. **`GUIGetCursorInfo()` reports no hovered control for a hidden window** -- there is nothing
   under the pointer to hit-test.
8. **`GUICtrlSetGraphic($GUI_GR_BEZIER)` draws the cubic itself.** Its parameters are
   "x,y,x1,y1,x2,y2 -- Draw a bezier curve with 2 control points", so `x,y` is where the curve ends
   and the two pairs are its control points, with the current position as its start. Tk has no
   `PolyBezier`, so the cubic is flattened (64 segments, finer than a pen can draw) and drawn as a
   polyline -- the same curve, not a different one: the interpreter's own rendering of
   `MOVE 20,120` and `BEZIER 200,120,20,20,200,20` was read pixel by pixel
   (`probe_autoit_graphic_out.txt`), and the port's curve crosses those columns within a pixel,
   where Tk's smooth spline -- which treats the points as control points of another curve and does
   not pass through them -- was up to 57 pixels away. Rectangles, ellipses, pies, lines, dots,
   pixels, colours and pen sizes are the control's own canvas operations.
9. **`GUISetFont`/`GUICtrlSetDefColor`/`GUICtrlSetDefBkColor` apply to the window's existing
   controls too.** The reference describes them as the window's defaults ("Sets the default
   text color of all the controls of the GUI window"); the port reads that sentence literally.
10. **`GUICoordMode`** is implemented as the `Opt()` page describes it: 1 (the interpreter's
    default) is absolute coordinates relative to the dialog box, 0 is relative to the start of
    the last control, 2 is cell positioning where `-1` does not increment and `GUISetCoord`
    sets the cell. Where the help file does not state what `-1` means in modes 0 and 1, the
    port uses the last control's coordinate.
11. **Text autofit sizes differ.** AutoIt computes an omitted width/height from its own
    metrics (the probe read `23x25` for an "OK" button); the port asks Tk for the widget's
    requested size (`winfo_reqwidth/reqheight`), which is the same idea with Tk's font
    metrics. Controls whose page says "default is the previously used width/height" inherit
    the previous control's size, as documented; `GUICtrlCreateGraphic()` uses the observed
    150x150 default.

## Tests

```text
python -m unittest tests.test_gui_offline -v
```

132 tests: the constant surface and its values, the control-ID rule, every documented
`GUICtrlRead` value (including an Input with an UpDown on it reading its own text), the
`GUICtrlGetState` word, a picture decoded from a BMP written by the test and the sizes a Pic takes
from the interpreter's readings, the size an omitted width/height takes (the previously used size,
including one a control computed for itself, and each kind's own default as the probe read it),
the two event modes, `GUIEventOptions=1` suppressing a minimize request
while still notifying and not stopping the docking, a native control's font quality read back from
its own LOGFONT, the bezier
curve compared against the interpreter's own pixels, OnEvent macro values, accelerators (`^` and the
Windows key's base key, and that an unset table stops firing),
the sorting callback, the Win32 functions above (messages, the painting lock,
icons and the `WM_` hook), the tooltip controls (`GUICtrlSetTip`'s text, title, icon, per-control
independence, `$TIP_BALLOON`/`$TIP_CENTER`/`$TIP_FORCEVISIBLE` as measured, replacement and
deletion), the docking table with the interpreter's own boxes (including a shrink, a negative
position and a size stopped at 0), each control type's default resizing, `GUIResizeMode`, a
notification whose code is one of AutoIt's negative constants firing its control's event, the
UpDown's window being where the port says it is, a List's and a ListView's selection events as the
interpreter reports them (the control's own ID; the item's identifier is what the ListView's *read*
answers), `GUICtrlDelete` on a ListView or TreeView item taking its row out of the control, and a
List's and an Edit's font and enabled state reaching the widget that shows them, the
native Date/MonthCal/Avi/Icon controls and the
UpDown against the interpreter's own readings, a dropped file reaching its control, the ListView
behaviour measured from the interpreter,
and the object control: that `ObjCreate` names its object as the interpreter does, that a class name
that does not exist is 0, that an object is driven through its own methods and properties (with the
argument order checked, since that is what `DISPPARAMS` decides), and that
`GUICtrlCreateObj` hosts *the caller's own* object (asserted pointer for pointer through
`AtlAxGetControl`), reads `""` and returns 0 for its handle, is 8x8 when given no size and passes
that 8x8 on to the next control, docks as `$GUI_DOCKSIZE`, and takes its hosted object with it when
deleted. The suite opens Tk
windows and shows one only in the event tests. It never touches the game client, and it needs no
client and no elevation.

`tests/autoit_reference/` holds the AutoIt probe scripts and the reports they wrote (34 scripts,
listed one by one in that directory's `README.md`); they are the evidence for the "verified" rows
above, and they are what a future version of AutoIt should be re-probed with.

The root window itself is driven offline by `tests/test_main_window_offline.py` (4 cases, over a
stand-in Windows layer, so it needs no client and no elevation): that a refresh **replaces** the
client list rather than adding a second copy of every row, that choosing a context shows that
context's controls and runs its reader, that a read which *failed* is reported as the failure
instead of as "in selection menus", and that **an unelevated shell connects nothing at all** -- the
client list is built with "(elevation required)" in it, and neither a refresh nor the Connect button
constructs a connection, because `ConnectedClient.__init__` asserts elevation before it resolves or
writes anything.


