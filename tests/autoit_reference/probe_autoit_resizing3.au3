; The docking rule, flag by flag: one control off-centre and one centred, per flag value.
;
; Every control is created at a known place in a 400x300 window, the window is resized once, and
; both controls' boxes are read back. The creation client size is printed too, because the ratios
; are taken against it.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing3.au3
; Writes probe_autoit_resizing3_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing3_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

Local $aFlags = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 768, 802, 102, 544, 576, _
        34, 514, 257, 264, 640, 68, 512 + 64, 256 + 4, 8 + 1, 128 + 1, 1024, 2048]

Local $hGUI = GUICreate("matrix", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aOff[UBound($aFlags)]
Local $aMid[UBound($aFlags)]
For $i = 0 To UBound($aFlags) - 1
    $aOff[$i] = GUICtrlCreateButton("off" & $i, 60, 45, 100, 30)
    GUICtrlSetResizing($aOff[$i], $aFlags[$i])
    $aMid[$i] = GUICtrlCreateButton("mid" & $i, 149, 100, 100, 30)
    GUICtrlSetResizing($aMid[$i], $aFlags[$i])
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)

Local $aClient = WinGetClientSize($hGUI)
Local $aWindow = WinGetPos($hGUI)
_Say("creation: window=" & $aWindow[2] & "x" & $aWindow[3] & " client=" & $aClient[0] & "x" & $aClient[1])
_Say("controls: off='60,45,100,30' (right margin " & ($aClient[0] - 160) & _
        ", bottom margin " & ($aClient[1] - 75) & "), mid='149,100,100,30' (centred: " & _
        Int(($aClient[0] - 100) / 2) & ")")
_Say("")

WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
Local $aClient2 = WinGetClientSize($hGUI)
Local $aWindow2 = WinGetPos($hGUI)
_Say("after: window=" & $aWindow2[2] & "x" & $aWindow2[3] & " client=" & $aClient2[0] & "x" & $aClient2[1])
_Say("ratios: " & StringFormat("%.4f", $aClient2[0] / $aClient[0]) & " x, " & _
        StringFormat("%.4f", $aClient2[1] / $aClient[1]) & " y")
_Say("")
_Say("flag | off-centre        | centred")
For $i = 0 To UBound($aFlags) - 1
    _Say($aFlags[$i] & " | " & _Box($hGUI, $aOff[$i]) & " | " & _Box($hGUI, $aMid[$i]))
Next
GUIDelete($hGUI)
