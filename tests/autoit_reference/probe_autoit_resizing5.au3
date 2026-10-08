; Is a resizing value above $GUI_DOCKALL (802) rejected as a whole?
;
; 1040 (= 16 + 1024) behaved like 0, not like 16, which a bit mask cannot explain. If the rule is
; "a value above $GUI_DOCKALL is not a docking value at all", then 802 behaves as ALL and 803 or
; 818 behave as 0.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing5.au3
; Writes probe_autoit_resizing5_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing5_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

Local $aFlags = [0, 802, 803, 818, 900, 1023, 1024, 1040, 1826, 819]
Local $hGUI = GUICreate("threshold", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aIds[UBound($aFlags)]
For $i = 0 To UBound($aFlags) - 1
    $aIds[$i] = GUICtrlCreateButton("t" & $i, 60, 45, 100, 30)
    GUICtrlSetResizing($aIds[$i], $aFlags[$i])
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
_Say("creation box 60,45,100,30; 802 = $GUI_DOCKALL (no displacement)")
_Say("a flag-0 answer is 103,75,100,30 (position scaled, size kept)")
_Say("an ALL answer is 60,45,100,30 (nothing moves)")
_Say("")
For $i = 0 To UBound($aFlags) - 1
    _Say("  flag " & $aFlags[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next
GUIDelete($hGUI)

; The same question for the GUIResizeMode option, whose page says "<1024".
_Say("")
_Say("=== Opt(""GUIResizeMode"", n) with the same boundary ===")
Local $aModes = [802, 803, 1024]
For $m = 0 To UBound($aModes) - 1
    Opt("GUIResizeMode", $aModes[$m])
    Local $hGUI2 = GUICreate("mode" & $aModes[$m], 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
    Local $id = GUICtrlCreateButton("m", 60, 45, 100, 30)
    GUISetState(@SW_SHOW, $hGUI2)
    Sleep(250)
    WinMove($hGUI2, "", Default, Default, 700, 500)
    Sleep(350)
    _Say("  GUIResizeMode=" & $aModes[$m] & " -> " & _Box($hGUI2, $id))
    GUIDelete($hGUI2)
    Sleep(200)
Next
Opt("GUIResizeMode", 0)
