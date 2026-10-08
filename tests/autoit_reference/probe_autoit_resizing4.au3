; Two details left for the docking rule: which bits the interpreter reacts to, and how the
; pinned-edge arithmetic rounds when the result is not a whole number.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing4.au3
; Writes probe_autoit_resizing4_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing4_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

; --- Part A: which bits are recognized ------------------------------------------------------
_Say("=== Part A: bits the interpreter reacts to (creation box 60,45,100,30) ===")
Local $aFlags = [0, 16, 16 + 1024, 1024, 2048, 4096, 8192, 16384, 24, 48, 1040, 16 + 256, 5120]
Local $hGUI = GUICreate("bits", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aIds[UBound($aFlags)]
For $i = 0 To UBound($aFlags) - 1
    $aIds[$i] = GUICtrlCreateButton("b" & $i, 60, 45, 100, 30)
    GUICtrlSetResizing($aIds[$i], $aFlags[$i])
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
Local $aClient = WinGetClientSize($hGUI)
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
Local $aClient2 = WinGetClientSize($hGUI)
_Say("client " & $aClient[0] & "x" & $aClient[1] & " -> " & $aClient2[0] & "x" & $aClient2[1] & _
        "  (ratios " & StringFormat("%.4f", $aClient2[0] / $aClient[0]) & ", " & _
        StringFormat("%.4f", $aClient2[1] / $aClient[1]) & ")")
For $i = 0 To UBound($aFlags) - 1
    _Say("  flag " & $aFlags[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next
GUIDelete($hGUI)
Sleep(300)

; --- Part B: rounding of the pinned-edge and centre arithmetic --------------------------------
_Say("")
_Say("=== Part B: odd client sizes, so the arithmetic has halves to round ===")
Local $hGUI2 = GUICreate("round", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
; A control whose centre is off the client centre, and one whose is on it.
Local $idCentre = GUICtrlCreateButton("c", 61, 46, 100, 30)
GUICtrlSetResizing($idCentre, $GUI_DOCKWIDTH + $GUI_DOCKHCENTER)
Local $idCentreH = GUICtrlCreateButton("ch", 61, 46, 100, 30)
GUICtrlSetResizing($idCentreH, $GUI_DOCKHEIGHT + $GUI_DOCKVCENTER)
Local $idRight = GUICtrlCreateButton("r", 61, 46, 100, 30)
GUICtrlSetResizing($idRight, $GUI_DOCKWIDTH + $GUI_DOCKRIGHT)
Local $idBottom = GUICtrlCreateButton("b", 61, 46, 100, 30)
GUICtrlSetResizing($idBottom, $GUI_DOCKHEIGHT + $GUI_DOCKBOTTOM)
Local $idAll = GUICtrlCreateButton("a", 61, 46, 100, 30)
GUICtrlSetResizing($idAll, $GUI_DOCKBORDERS)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(300)
_Say("at creation: " & _Box($hGUI2, $idCentre) & " / " & _Box($hGUI2, $idRight))
; Sizes chosen so the client delta is odd: 699x499 window.
WinMove($hGUI2, "", Default, Default, 699, 499)
Sleep(400)
Local $aC = WinGetClientSize($hGUI2)
_Say("after 699x499 window: client=" & $aC[0] & "x" & $aC[1])
_Say("  WIDTH|HCENTER      -> " & _Box($hGUI2, $idCentre))
_Say("  HEIGHT|VCENTER     -> " & _Box($hGUI2, $idCentreH))
_Say("  WIDTH|RIGHT        -> " & _Box($hGUI2, $idRight))
_Say("  HEIGHT|BOTTOM      -> " & _Box($hGUI2, $idBottom))
_Say("  BORDERS            -> " & _Box($hGUI2, $idAll))
GUIDelete($hGUI2)
