; A single direct resize, with no grow-then-shrink in between, for the same docking values.
;
; probe_autoit_resizing9's shrink stage produced boxes larger than its grow stage (a 171-wide
; control became 173 wide while the client shrank), which no base-relative model explains: Windows
; can send more than one WM_SIZE for a single WinMove, and AutoIt docks on each. This probe resizes
; once, straight to the target, so there is only one step to measure.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing10.au3
; Writes probe_autoit_resizing10_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing10_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

Local $aFlags = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 768, 802, 102, 544, 576, 34, 514, _
        257, 264, 640, 68, 260, 9, 129, 1024, 1040, 2048, 803, 818, 900, 1023, 1826, 819, 358, _
        870, 12, 300, 44, 6, 20, 96, 160, 192, 18, 24, 48, 272, 5120, 4096]

; Two windows: one grown, one shrunk, each from the creation size in a single WinMove.
For $step = 0 To 1
    Local $hGUI = GUICreate("single", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
    Local $aIds[UBound($aFlags)]
    For $i = 0 To UBound($aFlags) - 1
        $aIds[$i] = GUICtrlCreateButton("c" & $i, 60, 45, 100, 30)
        GUICtrlSetResizing($aIds[$i], $aFlags[$i])
    Next
    GUISetState(@SW_SHOW, $hGUI)
    Sleep(300)
    Local $aBefore = WinGetClientSize($hGUI)
    If $step = 0 Then
        WinMove($hGUI, "", Default, Default, 700, 500)
    Else
        WinMove($hGUI, "", Default, Default, 300, 200)
    EndIf
    Sleep(500)
    Local $aAfter = WinGetClientSize($hGUI)
    _Say("from client " & $aBefore[0] & "x" & $aBefore[1] & " to client " & _
            $aAfter[0] & "x" & $aAfter[1])
    For $i = 0 To UBound($aFlags) - 1
        _Say($aFlags[$i] & "=" & _Box($hGUI, $aIds[$i]))
    Next
    _Say("")
    GUIDelete($hGUI)
    Sleep(300)
Next
