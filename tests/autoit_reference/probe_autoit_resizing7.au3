; Two questions the port's implementation depends on:
;   1. When a control is moved with GUICtrlSetPos and the window is then resized, is the docking
;      computed from the control's creation box or from where it was moved to?
;   2. Is Opt("GUIResizeMode", ...) read when a control is created, or when the window is resized?
;      (A third: a control created after a resize, whose window has already changed size.)
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing7.au3
; Writes probe_autoit_resizing7_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing7_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

_Say("=== Part 1: GUICtrlSetPos before a resize (dock = $GUI_DOCKAUTO) ===")
Local $hGUI = GUICreate("move", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
; Both created at the same place; one is moved to 200,100 before the resize.
Local $idKept = GUICtrlCreateButton("kept", 60, 45, 100, 30)
GUICtrlSetResizing($idKept, $GUI_DOCKAUTO)
Local $idMoved = GUICtrlCreateButton("moved", 60, 45, 100, 30)
GUICtrlSetResizing($idMoved, $GUI_DOCKAUTO)
GUICtrlSetPos($idMoved, 200, 100)
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
Local $aClient = WinGetClientSize($hGUI)
_Say("client at creation=" & $aClient[0] & "x" & $aClient[1])
_Say("  kept  before resize -> " & _Box($hGUI, $idKept))
_Say("  moved before resize -> " & _Box($hGUI, $idMoved))
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
Local $aClient2 = WinGetClientSize($hGUI)
_Say("client after =" & $aClient2[0] & "x" & $aClient2[1])
_Say("  kept  after resize -> " & _Box($hGUI, $idKept) & "  (creation box would give 103,75,171,50)")
_Say("  moved after resize -> " & _Box($hGUI, $idMoved) & _
        "  (from 200,100 it would be 343,167,171,50; from 60,45 it would be 103,75,171,50)")
GUIDelete($hGUI)
Sleep(300)

_Say("")
_Say("=== Part 2: GUIResizeMode set after the control was created ===")
Opt("GUIResizeMode", 0)
Local $hGUI2 = GUICreate("late", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $idLate = GUICtrlCreateButton("late", 60, 45, 100, 30)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(250)
Opt("GUIResizeMode", $GUI_DOCKAUTO)
WinMove($hGUI2, "", Default, Default, 700, 500)
Sleep(400)
_Say("  button created with GUIResizeMode=0, option set to AUTO before the resize:")
_Say("    -> " & _Box($hGUI2, $idLate) & _
        "  (AUTO would be 103,75,171,50; the Button default is 103,75,100,30)")
GUIDelete($hGUI2)
Sleep(250)

_Say("")
_Say("=== Part 3: a control created after the window was resized ===")
Opt("GUIResizeMode", 0)
Local $hGUI3 = GUICreate("late-control", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
GUISetState(@SW_SHOW, $hGUI3)
Sleep(250)
WinMove($hGUI3, "", Default, Default, 700, 500)
Sleep(400)
Local $aC3 = WinGetClientSize($hGUI3)
Local $idLateControl = GUICtrlCreateButton("late", 60, 45, 100, 30)
GUICtrlSetResizing($idLateControl, $GUI_DOCKAUTO)
Sleep(250)
_Say("  window client now " & $aC3[0] & "x" & $aC3[1] & "; control created then at 60,45 100x30")
WinMove($hGUI3, "", Default, Default, 500, 400)
Sleep(400)
Local $aC4 = WinGetClientSize($hGUI3)
_Say("  after resizing back to a " & $aC4[0] & "x" & $aC4[1] & " client -> " & _Box($hGUI3, $idLateControl))
_Say("  (from the 398x275 creation client the ratio would be " & _
        StringFormat("%.3f", $aC4[0] / 398) & " x, giving 60*ratio=" & Int(60 * $aC4[0] / 398) & ")")
_Say("  (from the 684x461 client the ratio would be " & _
        StringFormat("%.3f", $aC4[0] / $aC3[0]) & " x, giving 60*ratio=" & Int(60 * $aC4[0] / $aC3[0]) & ")")
GUIDelete($hGUI3)
