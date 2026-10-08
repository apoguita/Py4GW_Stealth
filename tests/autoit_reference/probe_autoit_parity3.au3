#NoTrayIcon
; Parity probe 3: the UpDown control (msctls_updown32).
; Reads how AutoIt's UpDown relates to its buddy Input: what GUICtrlRead returns, what
; GUICtrlSetData and GUICtrlSetLimit change, the control's size and position against the
; input's, and whether SetPos/SetState act on it.

#include <GUIConstantsEx.au3>
#include <UpDownConstants.au3>
#include <EditConstants.au3>

Global $g_hFile = FileOpen(@ScriptDir & "\probe_parity3_out.txt", 2)

Func Note($text)
    FileWrite($g_hFile, $text & @CRLF)
EndFunc

Func Rect_Of($id)
    Local $h = GUICtrlGetHandle($id)
    If $h = 0 Then Return "no-handle"
    Local $a = WinGetPos($h)
    Return "at " & $a[0] & "," & $a[1] & " size " & $a[2] & "x" & $a[3]
EndFunc

Opt("GUIOnEventMode", 0)
Local $hWin = GUICreate("probe3", 400, 300)

Local $input = GUICtrlCreateInput("5", 10, 10, 120, 22)
Local $updown = GUICtrlCreateUpdown($input)
Note("[ud] default: read=[" & GUICtrlRead($updown) & "] input=[" & GUICtrlRead($input) & "]")
Note("[ud] handle=" & GUICtrlGetHandle($updown) & " " & Rect_Of($updown) & " | input " & Rect_Of($input))
Note("[ud] getstate=" & GUICtrlGetState($updown))

Local $ret = GUICtrlSetData($updown, 12)
Note("[ud] SetData(12) ret=" & $ret & " read=[" & GUICtrlRead($updown) & "] input=[" & GUICtrlRead($input) & "]")

Local $retLimit = GUICtrlSetLimit($updown, 30, 3)
Note("[ud] SetLimit(30,3) ret=" & $retLimit & " input=[" & GUICtrlRead($input) & "]")

; The arrow buttons are clicked with a mouse; UDM_SETPOS32 through the handle is the same thing.
Local $hUd = GUICtrlGetHandle($updown)
DllCall("user32.dll", "lresult", "SendMessageW", "hwnd", $hUd, "uint", 0x0471, "wparam", 0, "lparam", 20)
Note("[ud] after UDM_SETPOS32(20): read=[" & GUICtrlRead($updown) & "] input=[" & GUICtrlRead($input) & "]")
Local $pos = DllCall("user32.dll", "lresult", "SendMessageW", "hwnd", $hUd, "uint", 0x0472, "wparam", 0, "lparam", 0)
Note("[ud] UDM_GETPOS32=" & $pos[0])

Note("[ud] SetPos ret=" & GUICtrlSetPos($updown, 50, 50) & " " & Rect_Of($updown))
Note("[ud] hide ret=" & GUICtrlSetState($updown, $GUI_HIDE) & " state=" & GUICtrlGetState($updown))
Note("[ud] show ret=" & GUICtrlSetState($updown, $GUI_SHOW) & " state=" & GUICtrlGetState($updown))
Note("[ud] disable ret=" & GUICtrlSetState($updown, $GUI_DISABLE) & " state=" & GUICtrlGetState($updown))
Note("[ud] input after all=[" & GUICtrlRead($input) & "]")
Note("[ud] delete ret=" & GUICtrlDelete($updown) & " read=[" & GUICtrlRead($updown) & "]")

; A second updown with $UDS_HORZ, for its size.
Local $input2 = GUICtrlCreateInput("1", 10, 60, 120, 22)
Local $updown2 = GUICtrlCreateUpdown($input2, $UDS_HORZ)
Note("[ud2] horz handle=" & GUICtrlGetHandle($updown2) & " " & Rect_Of($updown2))

FileClose($g_hFile)
