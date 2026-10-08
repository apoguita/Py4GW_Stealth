; What curve does GUICtrlSetGraphic's $GUI_GR_BEZIER draw? Read from the control's own pixels.
;
; The port used Tk's smooth spline, which treats the points as control points and does not pass
; through them; this records where the interpreter's own curve actually runs, column by column, so
; the port's flattened cubic can be compared with it.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_graphic.au3
; Writes probe_autoit_graphic_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <StaticConstants.au3>
#include <WindowsConstants.au3>
#include <WinAPIGdi.au3>
#include <WinAPIGdiDC.au3>

Const $sReport = @ScriptDir & "\probe_autoit_graphic_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Local $hGUI = GUICreate("graphic", 320, 220, 150, 150)
Local $idGraphic = GUICtrlCreateGraphic(10, 10, 240, 160)
GUICtrlSetBkColor($idGraphic, 0xFFFFFF)
GUICtrlSetGraphic($idGraphic, $GUI_GR_COLOR, 0x000000)
GUICtrlSetGraphic($idGraphic, $GUI_GR_MOVE, 20, 120)
; Start (20,120), control points (20,20) and (200,20), end (200,120): a symmetric arch.
GUICtrlSetGraphic($idGraphic, $GUI_GR_BEZIER, 200, 120, 20, 20, 200, 20)
GUICtrlSetGraphic($idGraphic, $GUI_GR_REFRESH)
GUISetState(@SW_SHOW, $hGUI)
Sleep(800)

Local $hGraphic = GUICtrlGetHandle($idGraphic)
Local $aPos = ControlGetPos($hGUI, "", $hGraphic)
Local $hDC = _WinAPI_GetDC($hGraphic)
_Say("graphic control box = " & $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3])
_Say("command: MOVE 20,120 then BEZIER x=200 y=120 x1=20 y1=20 x2=200 y2=20")

; For several columns, the darkest pixel's row is where the curve is.
Local $aColumns[9] = [20, 40, 60, 80, 100, 120, 140, 160, 180]
For $i = 0 To UBound($aColumns) - 1
    Local $iX = $aColumns[$i]
    Local $iDarkest = -1
    Local $iDarkestValue = 256
    For $iY = 0 To 159
        Local $iColour = _WinAPI_GetPixel($hDC, $iX, $iY)
        Local $iValue = BitAND($iColour, 0xFF) + BitAND(BitShift($iColour, 8), 0xFF) + _
                BitAND(BitShift($iColour, 16), 0xFF)
        If $iValue < $iDarkestValue Then
            $iDarkestValue = $iValue
            $iDarkest = $iY
        EndIf
    Next
    _Say("column " & $iX & ": darkest row " & $iDarkest & " (value " & $iDarkestValue & ")")
Next

; And a second shape, to separate a cubic from a spline clearly: an asymmetric one.
GUICtrlSetGraphic($idGraphic, $GUI_GR_COLOR, 0xFF0000)
GUICtrlSetGraphic($idGraphic, $GUI_GR_MOVE, 20, 20)
GUICtrlSetGraphic($idGraphic, $GUI_GR_BEZIER, 220, 20, 20, 150, 220, 150)
GUICtrlSetGraphic($idGraphic, $GUI_GR_REFRESH)
Sleep(500)
_Say("command: MOVE 20,20 then BEZIER x=220 y=20 x1=20 y1=150 x2=220 y2=150")
For $i = 0 To UBound($aColumns) - 1
    Local $iX = $aColumns[$i]
    Local $iDarkest = -1
    Local $iDarkestValue = 256
    For $iY = 0 To 159
        ; the red curve: darkest in the red channel
        Local $iColour = _WinAPI_GetPixel($hDC, $iX, $iY)
        Local $iValue = BitAND(BitShift($iColour, 16), 0xFF)
        If $iValue < $iDarkestValue Then
            $iDarkestValue = $iValue
            $iDarkest = $iY
        EndIf
    Next
    _Say("red column " & $iX & ": darkest row " & $iDarkest & " (red " & $iDarkestValue & ")")
Next

_WinAPI_ReleaseDC($hGraphic, $hDC)
GUIDelete($hGUI)
Exit
