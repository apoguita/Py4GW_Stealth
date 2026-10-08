; The UpDown's style word and which arrow changes the value, read from the interpreter.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_updown.au3
; Writes probe_autoit_updown_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPI.au3>

Opt("GUIOnEventMode", 1)

Const $sReport = @ScriptDir & "\probe_autoit_updown_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _ScreenX($hWnd, $iX)
    Local $tPoint = DllStructCreate("long x; long y")
    DllStructSetData($tPoint, "x", $iX)
    DllStructSetData($tPoint, "y", 0)
    _WinAPI_ClientToScreen($hWnd, $tPoint)
    Return DllStructGetData($tPoint, "x")
EndFunc

Func _ScreenY($hWnd, $iY)
    Local $tPoint = DllStructCreate("long x; long y")
    DllStructSetData($tPoint, "x", 0)
    DllStructSetData($tPoint, "y", $iY)
    _WinAPI_ClientToScreen($hWnd, $tPoint)
    Return DllStructGetData($tPoint, "y")
EndFunc

Func _Click($hGUI, $iClientX, $iClientY)
    Opt("MouseCoordMode", 1)
    MouseMove(_ScreenX($hGUI, $iClientX), _ScreenY($hGUI, $iClientY), 0)
    Sleep(200)
    MouseDown("left")
    Sleep(80)
    MouseUp("left")
    Sleep(500)
EndFunc

Local $hGUI = GUICreate("updown", 500, 300, 120, 120)
Local $idInput = GUICtrlCreateInput("5", 10, 10, 120, 22)
Local $idUpdown = GUICtrlCreateUpdown($idInput)
GUISetState(@SW_SHOW, $hGUI)
WinActivate($hGUI)
WinSetOnTop($hGUI, "", 1)
Sleep(600)

Local $hUpdown = GUICtrlGetHandle($idUpdown)
Local $aUp = ControlGetPos($hGUI, "", $hUpdown)
Local $aInput = ControlGetPos($hGUI, "", GUICtrlGetHandle($idInput))
_Say("input box  = " & $aInput[0] & "," & $aInput[1] & "," & $aInput[2] & "," & $aInput[3])
_Say("updown box = " & $aUp[0] & "," & $aUp[1] & "," & $aUp[2] & "," & $aUp[3])
_Say("updown style = 0x" & Hex(_WinAPI_GetWindowLong($hUpdown, $GWL_STYLE)))
_Say("input reads before = " & GUICtrlRead($idInput))

; A click on the window first, so the first arrow click is not the one that activates it.
_Click($hGUI, 250, 200)
_Say("after an activating click, input = " & GUICtrlRead($idInput))

Local $iX = $aUp[0] + Int($aUp[2] / 2)
Local $iTopY = $aUp[1] + 4
Local $iBottomY = $aUp[1] + $aUp[3] - 4
_Say("upper arrow client y = " & $iTopY & ", lower arrow client y = " & $iBottomY)

For $i = 1 To 4
    If Mod($i, 2) = 1 Then
        _Click($hGUI, $iX, $iTopY)
        _Say("click " & $i & " on the upper half -> " & GUICtrlRead($idInput))
    Else
        _Click($hGUI, $iX, $iBottomY)
        _Say("click " & $i & " on the lower half -> " & GUICtrlRead($idInput))
    EndIf
Next
