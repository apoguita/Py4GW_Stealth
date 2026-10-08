; A control created after the window was resized, step by step, with a reference control that
; existed from creation. The point is which client size AutoIt uses as that control's base.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing8.au3
; Writes probe_autoit_resizing8_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing8_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

Func _Client($hGUI)
    Local $a = WinGetClientSize($hGUI)
    Local $w = WinGetPos($hGUI)
    Return "client=" & $a[0] & "x" & $a[1] & " window=" & $w[2] & "x" & $w[3]
EndFunc

Local $hGUI = GUICreate("late", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $idEarly = GUICtrlCreateButton("early", 60, 45, 100, 30)
GUICtrlSetResizing($idEarly, $GUI_DOCKAUTO)
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
_Say("0. at creation        : " & _Client($hGUI))
_Say("   early (from start) : " & _Box($hGUI, $idEarly))

WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
_Say("1. after 700x500      : " & _Client($hGUI))
_Say("   early              : " & _Box($hGUI, $idEarly))

; The control of interest is created now, while the window is already bigger.
Local $idLate = GUICtrlCreateButton("late", 60, 45, 100, 30)
GUICtrlSetResizing($idLate, $GUI_DOCKAUTO)
Sleep(300)
_Say("2. late created       : " & _Client($hGUI))
_Say("   late               : " & _Box($hGUI, $idLate))

WinMove($hGUI, "", Default, Default, 500, 400)
Sleep(400)
_Say("3. after 500x400      : " & _Client($hGUI))
_Say("   early              : " & _Box($hGUI, $idEarly))
_Say("   late               : " & _Box($hGUI, $idLate))

WinMove($hGUI, "", Default, Default, 600, 450)
Sleep(400)
_Say("4. after 600x450      : " & _Client($hGUI))
_Say("   early              : " & _Box($hGUI, $idEarly))
_Say("   late               : " & _Box($hGUI, $idLate))

; And a third control created at the smaller size, for one more comparison.
Local $idThird = GUICtrlCreateButton("third", 60, 45, 100, 30)
GUICtrlSetResizing($idThird, $GUI_DOCKAUTO)
Sleep(300)
_Say("5. third created      : " & _Client($hGUI))
_Say("   third              : " & _Box($hGUI, $idThird))
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
_Say("6. after 700x500 again: " & _Client($hGUI))
_Say("   third              : " & _Box($hGUI, $idThird))
GUIDelete($hGUI)
