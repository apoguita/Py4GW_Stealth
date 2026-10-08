# The AutoIt reference readings

These AutoIt scripts were run against the AutoIt v3 interpreter installed on this machine
(`C:\Program Files (x86)\AutoIt3\AutoIt3.exe`) to answer what the AutoIt help file does not
state about its GUI functions. Each script wrote the report beside itself; both the script and
its report are kept here, because they are the evidence behind the "verified" readings in
[`docs/AUTOIT_GUI.md`](../../docs/AUTOIT_GUI.md) and the `(AutoIt: ...)` expectations in
`tests/test_gui_offline.py`.

| Script | Report | What it read |
| --- | --- | --- |
| `probe_autoit_constants.au3` | `probe_constants_out.txt` | the `@SW_*` macro values and the default values of the `GUI*` options |
| `probe_autoit_sw.au3` | `probe_sw_out.txt` | `@SW_MAXIMIZE` against `@SW_SHOWMAXIMIZED` |
| `probe_autoit_behavior.au3` | `probe_behavior_out.txt` | default window and control sizes, control IDs against window handles, `GUICtrlRead` and `GUICtrlGetState` values, menu item state, `GUISetState`/`GUISetStyle`/`GUIGetMsg` return values |
| `probe_autoit_eventmode.au3` | `probe_eventmode_out.txt` | where an OnEvent function runs (inside `GUICtrlSendToDummy`), the `@GUI_*` macros it sees, and the same event returned once by `GUIGetMsg()` in message-loop mode |
| `probe_autoit_parity.au3` | `probe_parity_out.txt` | the semantics the port needed to stop refusing functions: `GUICtrlSetData()` on a ListView (it replaces the column headings), a ListViewItem's check state in an advanced read, `GUICtrlRead()` on an UpDown (an empty string), whether a hidden control keeps its geometry (it does), how long an idle `GUIGetMsg()` takes (14.7 ms), and what `GUICtrlSendMsg($button, $BM_CLICK, 0, 0)` returns (0) |
| `probe_autoit_parity2.au3` | `probe_parity2_out.txt` | the control types the port hosts as Win32 classes: what a Date control reads and how `GUICtrlSetData`/`GUICtrlSetStyle` change it, what a MonthCal reads ("yyyy/mm/dd"), that Icon and Avi read "", that all four report handles, the Avi states' return values, and the sizes those controls take when width/height are omitted |
| `probe_autoit_parity3.au3` | `probe_parity3_out.txt` | the UpDown control: that it reads "" and returns -1 from `GUICtrlSetData`, that `GUICtrlSetLimit` returns 1, where the arrows sit against their buddy Input (18 pixels wide, two pixels inside its right edge), that `UDM_SETPOS32` writes the buddy input through `$UDS_SETBUDDYINT`, and its state/position/delete behaviour |
| `probe_autoit_gui_tip.au3` | `probe_autoit_gui_tip_out.txt` | what `GUICtrlSetTip` builds: that no `tooltips_class32` window exists before the first call, that two tipped controls are two such windows each holding one tool, and the tip windows' parent, style and exStyle |
| `probe_autoit_gui_tip2.au3` | `probe_autoit_gui_tip2_out.txt` | the same for eleven steps: that each control's title is its own, that a second `GUICtrlSetTip` replaces that control's tip window, that `$TIP_BALLOON` is `$TTS_BALLOON` on the control's own tip, that `$TIP_CENTER` is `$TTF_CENTERTIP` on the tool (flags `0x51` → `0x53`) while `$TIP_FORCEVISIBLE` leaves them at `0x51`, and that deleting the control or the window takes the tips with it |
| `probe_autoit_resizing.au3` | `probe_autoit_resizing_out.txt` | what a window resize does to controls: one control per docking value at the same box, the window grown 400x300 → 700x500, and each control's client-relative box afterwards; the per-type default resizing with no `GUICtrlSetResizing`; `Opt("GUIResizeMode", $GUI_DOCKALL)` as a default; and `Opt("GUIEventOptions", 1)`, which did **not** stop the docking |
| `probe_autoit_resizing2.au3` | `probe_autoit_resizing2_out.txt` | the client size at each step (398x275 at creation, 684x461, 484x361), so the ratios are known; repeated resizes; `GUIEventOptions` set before `GUICreate`; and the List/ListView/TreeView/MonthCal defaults |
| `probe_autoit_resizing3.au3` | `probe_autoit_resizing3_out.txt` | the docking rule flag by flag: 28 values, each on a control at `60,45,100,30` and one at `149,100` (centred), read after one resize — the reading that showed `$GUI_DOCKHCENTER` alone does nothing and that `$GUI_DOCKBORDERS` stretches |
| `probe_autoit_resizing4.au3` | `probe_autoit_resizing4_out.txt` | which bits the interpreter reacts to (16 behaved as `$GUI_DOCKAUTO`, 1024/2048/4096 inert) and how the pinned-edge arithmetic rounds (truncation, from a 683x460 client) |
| `probe_autoit_resizing5.au3` | `probe_autoit_resizing5_out.txt` | the boundary: 802, 803, 818 and 819 behaved as `$GUI_DOCKALL`, 900 and 1023 as their own bits, and 1024, 1040, 1826 and above as 0 — so it is not a bit mask but "0 or 1024 and above means the control's default" |
| `probe_autoit_resizing6.au3` | `probe_autoit_resizing6_out.txt` | `GUICtrlSetResizing(control, 0)` and `(control, 1024)`: each control type docked as its own default (Label/Edit/ListView `$GUI_DOCKAUTO`, Input/Date `$GUI_DOCKHEIGHT`, Button/Pic `$GUI_DOCKSIZE`) |
| `probe_autoit_resizing7.au3` | `probe_autoit_resizing7_out.txt` | that `GUICtrlSetPos` moves the docking base (a control moved to 200,100 docked from there), that `GUIResizeMode` is read at control creation, and that a control created after a resize docks from the client of that moment |
| `probe_autoit_resizing8.au3` | `probe_autoit_resizing8_out.txt` | the "created after a resize" case step by step, with a control that existed from creation as the reference: the interpreter's boxes there fit no single-ratio model, which is why [`docs/AUTOIT_GUI.md`](../../docs/AUTOIT_GUI.md) states that one case rather than claiming parity for it |
| `probe_autoit_resizing9.au3` | `probe_autoit_resizing9_out.txt` | the matrix the port's arithmetic was compared against: 50 docking values grown and shrunk, each control type's default, and an odd box (`61,46,101,31`) in an odd client (683x460) |
| `probe_autoit_resizing10.au3` | `probe_autoit_resizing10_out.txt` | a **single** resize in each direction from the creation size (398x275 → 684x461 and → 284x161), which is what the port's own resize path was compared against box by box: 100 boxes, 0 mismatches, and the reading that shows a stretched size stops at 0 while a position goes negative |
| `probe_autoit_events.au3` | `probe_autoit_events_out.txt` | what real input does to a native control: the pointer is moved to each control's screen position and a click is injected, with the window on top. Readings: an UpDown's **down arrow** fires its `GUICtrlSetOnEvent` function (and `GUICtrlRead($input)` goes 5 → 4), the *up* arrow click that activates the window fires nothing, a Date's dropdown click fires nothing by itself, and a Button's click fires its function — the readings the port's own real-input runs were compared against |
| `probe_autoit_updown.au3` | `probe_autoit_updown_out.txt` | an UpDown's style word and which arrow does what: the interpreter's control is `0x50000106` (`$UDS_HOTTRACK|$UDS_ALIGNRIGHT|$UDS_SETBUDDYINT`), an **upper-half** click on an already-activated window takes the input 5 → 6 and a lower-half click 6 → 5, and the input reads "5" before anything is clicked. This is the oracle the port's own arrows are compared against, and it is where the port's inverted arrows were found |
| `probe_autoit_updown3.au3` | `probe_autoit_updown3_out.txt` | the same control, but the probe ticks its **own** position (`UDM_GETPOS32`, sent in-process, so nothing blocks) and the input text every 200 ms while an outside controller clicks the arrows. Reading `5 -> 6` on an upper-half click shows the *control itself* steps up in the interpreter's process — so the interpreter is not overriding the control, and the port's inverted arrows are a difference between the two processes rather than of the port's arithmetic. (An earlier probe read the position across processes with `SendMessage`, which hung the interpreter until it was killed; it was removed.) |

| `probe_autoit_gui_event_options.au3` | `probe_autoit_gui_event_options_out.txt` | what `Opt("GUIEventOptions", 1)` does with a minimize request, sent as the system command a minimize button sends (`$WM_SYSCOMMAND` with `$SC_MINIMIZE` — an earlier version that clicked the title bar hung the interpreter and was replaced). With the option unset the window goes to state 23 (minimised) and calls `$GUI_EVENT_MINIMIZE`; with it set the window stays at state 15 and the function is called anyway, which is the "suppress windows behavior … just sends the notification" the option's page describes |

A probe that reads another process's control with `SendMessage` blocks until that process services
the message, and a script sitting in `Sleep` may never do it — the cross-process probe used to read
AutoIt's UpDown position hung the interpreter and had to be killed. A probe that needs its own
control's state should read it in-process (`_SendMessage`), as `probe_autoit_updown3.au3` does.

| `probe_autoit_graphic.au3` | `probe_autoit_graphic_out.txt` | where `$GUI_GR_BEZIER` actually draws: a Graphic control is given `MOVE 20,120` and `BEZIER 200,120,20,20,200,20`, and the darkest pixel of nine columns is read from the control's own device context. The rows show a cubic arch (column 100 → row 46, where the analytic cubic gives y=45), which is what the port's flattened cubic matches to under a pixel; the shape also settles the parameter order — `x,y` is the end point and the two pairs are the control points |

| `probe_autoit_obj.au3` | `probe_autoit_obj_out.txt` | `GUICtrlCreateObj` against an object `ObjCreate` made: that `ObjName(ObjCreate("Shell.Explorer.2"))` is "WebBrowser" and of `Scripting.Dictionary` is "Dictionary", that a class name that does not exist comes back as 0 (with @error 0, though its page says the flag is set), that `GUICtrlGetHandle` on the object control is **0** while the GUI does hold a child window ("Shell Embedding"), that it reads `""` and its state is 80, that `GUICtrlSetData`/`GUICtrlSetStyle` return 1, and that `GUICtrlCreateObj(ObjCreate("Scripting.Dictionary"))` returns **0** with @error 1 — an object that has an IDispatch and still cannot be embedded |
| `probe_autoit_obj2.au3` | `probe_autoit_obj2_out.txt` | the same control's window followed through a GUI's life: created with the control and hidden until `GUISetState` (style `0x50010000`, exStyle `0x00010000`, parent "AutoIt v3 GUI"), moved by `GUICtrlSetPos`, hidden and shown by `GUICtrlSetState` (the style loses `$WS_VISIBLE`, state 96 then 80), docked by `$GUI_DOCKAUTO` and `$GUI_DOCKSIZE` as the window resizes, and gone — with the GUI holding no child window — after `GUICtrlDelete`. (Its second window created three controls from *one* object variable and found one host window, which is why `probe_autoit_obj3` gives each control its own object.) |
| `probe_autoit_obj3.au3` | `probe_autoit_obj3_out.txt` | the size rule for an object control, with one `ObjCreate` per control: no width or height is **8x8** whatever the last control's size was, an explicit 60x40 is used, and one with no size after a Label or after a 40x30 object is still 8x8. Also that the *same* object variable embedded twice leaves one host window — the first creation here, the last in probe 2, which is why no rule is claimed for it |
| `probe_autoit_obj4.au3` | `probe_autoit_obj4_out.txt` | the two remaining size questions: an object with no size leaves **8x8** as the "previously used" size for the next control (an Input after it came out 8x8, not 200x20), and an object created with an explicit `0, 0` is **0x0** and leaves 0x0 behind |
| `probe_autoit_zero_size.au3` | `probe_autoit_zero_size_out.txt` | that an explicit `0, 0` is 0x0 for ordinary controls too (Input, Edit, List 0x6, Label, Button, Group) and that the next control with no size then inherits 0x0 — the general rule the object probe turned up |
| `probe_autoit_delete_item.au3` | `probe_autoit_delete_item_out.txt` | what `GUICtrlDelete` does to an item: a ListView with three rows lost the middle one (3 -> 2), the neighbours kept their text, the deleted item then read 0 and deleting it again returned 0; a TreeViewItem behaved the same; and deleting a whole List works. This is the reading behind the port's `GUICtrlDelete`, which deleted only its own control record and left the row in the control |
| `probe_autoit_listview_event.au3` | `probe_autoit_listview_event_out.txt` | which control a click reports: clicking a row of a **List** called the function registered on the List with `@GUI_CtrlId` = the List's ID, and clicking a row of a **ListView** called the function registered on the ListView with `@GUI_CtrlId` = the ListView's ID -- the functions registered on the two items never ran. `GUICtrlRead(List)` then read the clicked row's text. This is why the port binds a List's selection on the list box rather than the frame around it, and why a ListView selection reports the ListView |
| `probe_autoit_default_size.au3` | `probe_autoit_default_size_out.txt` | the reference's sentence "width/height default is the previously used width/height", measured twice over: an Input with no size in a fresh window is **200x20**; an Input with no size after an Input made 50x10 is **50x10**; and an Input with no size after a **Button** is **23x25** — the Button's own text-computed size — so a size a control was given by computation still counts as the size last used. Also that an explicit 120x60 Edit is followed by a 120x60 Edit and a **120x58** List (a list box snapping to whole items), and that showing the window does not change any of it |
| `probe_autoit_defaults.au3` | `probe_autoit_defaults_out.txt` | each kind of control created first in a window of its own, with short text and long text: Input 200x20, Edit 200x150, Combo 200x21, List 200x149, Progress and Slider **0x0**, Tab/TreeView/ListView/Pic/Graphic 150x150, Date 200x20, MonthCal 229x164, Group 200x150 — the per-kind seeds [`docs/AUTOIT_GUI.md`](../../docs/AUTOIT_GUI.md) records — and the four kinds whose size *is* their text: Button 23x25/147x25, Label 18x21/163x21, Checkbox 25x21/176x21, Radio 21x21/148x21. (This is the probe that corrected an inherited 120x120/116x116 reading: those were the sizes of a control made *before* the Date and the MonthCal, not their own defaults.) |

| `probe_autoit_pic.au3` | `probe_autoit_pic_out.txt` | the sizes a Pic control takes: with a 6x4 BMP and a 255x40 JPG, no width or height gave the size the control before it used (and 150x150 for the first control in a fresh window, not the window's 400), `width=0 height=0` gave the **file's own** size, and an explicit 40x30 gave that. `GUICtrlRead` on a Pic is `""`. The BMP is written by the caller and its path and size are passed in: an earlier version wrote one with `DllStruct` and got a broken file, which shows up as a Pic reporting the *window's* box |

A probe that clicks the title bar of its own window can hang the interpreter too (measured, on a
probe that clicked the minimize button); sending the message that button sends
(`$WM_SYSCOMMAND` with `$SC_MINIMIZE`) is the same measurement without the risk, which is what
`probe_autoit_gui_event_options.au3` does.

Run one again with:

```text
& 'C:\Program Files (x86)\AutoIt3\AutoIt3.exe' /ErrorStdOut tests\autoit_reference\probe_autoit_behavior.au3
```

The behaviour probe never shows a window; the event-mode probe shows a 200x100 window for
about two seconds, because `GUICtrlSendToDummy` only notifies on a visible window
(`GUICtrlSendToDummy.htm`). Both write their report line by line, so a failure still leaves
the readings gathered before it. `/ErrorStdOut` makes a compile error visible in the console
instead of only in the editor.

One caveat the reports themselves show: a probe that calls an AutoIt function with the wrong
number of arguments stops on a modal error dialog. The invalid-argument probes were removed
from `probe_autoit_behavior.au3` for that reason, and a rerun should be watched rather than
left unattended.

A second caveat, learned from the tip probes: an include that this installation does not ship
(`TipConstants.au3`) fails the script before it runs at all, and the `$TIP_*` values live in
`AutoItConstants.au3` while the `$TTF_*`/`$TTM_*` values live in `ToolTipConstants.au3`.

A third, from the resizing probes: AutoIt has no array literals as a function argument, so an
array of values has to be assigned to a variable first (`Local $a = [1, 2]` then `_Func($a)`), and
a probe that resizes windows shows them, so it runs while the desktop is free.

A fourth, and the reason the resizing probes are numbered: the *client* size is what the docking
ratios are taken from, and a window made 400x300 has a **398x275** client on this machine, while
tkinter's geometry is the client itself. The port's comparison scripts therefore create their
window at 398x275 and set the client directly, so both sides use the same client sizes.
