; The resizing arithmetic: what are the scales taken from, and are they relative to the previous
; size or the original one? Follow-up to probe_autoit_resizing.au3.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing2.au3
; Writes probe_autoit_resizing2_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <ListviewConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing2_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

Func _Sizes($hGUI)
    Local $aClient = WinGetClientSize($hGUI)
    Local $aWindow = WinGetPos($hGUI)
    Return "window=" & $aWindow[2] & "x" & $aWindow[3] & " client=" & $aClient[0] & "x" & $aClient[1]
EndFunc

; --- Part A: the client sizes at each step, with several dock values -------------------------
_Say("=== Part A: GUICreate(400,300) then WinMove(700,500) then WinMove(500,400) ===")
Local $hGUI = GUICreate("scales", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aDocks = [0, 1, 2, 256, 512, 768, 802]
Local $aIds[UBound($aDocks)]
For $i = 0 To UBound($aDocks) - 1
    $aIds[$i] = GUICtrlCreateButton("c" & $i, 50, 40, 100, 30)
    GUICtrlSetResizing($aIds[$i], $aDocks[$i])
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
_Say("at creation : " & _Sizes($hGUI))
For $i = 0 To UBound($aDocks) - 1
    _Say("  dock " & $aDocks[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next

WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
_Say("after 700x500 window: " & _Sizes($hGUI))
For $i = 0 To UBound($aDocks) - 1
    _Say("  dock " & $aDocks[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next

WinMove($hGUI, "", Default, Default, 500, 400)
Sleep(400)
_Say("after 500x400 window: " & _Sizes($hGUI))
For $i = 0 To UBound($aDocks) - 1
    _Say("  dock " & $aDocks[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next

; Back to the original window size: does everything return to where it started?
WinMove($hGUI, "", Default, Default, 416, 339)
Sleep(400)
_Say("after 416x339 window (the original window size): " & _Sizes($hGUI))
For $i = 0 To UBound($aDocks) - 1
    _Say("  dock " & $aDocks[$i] & " -> " & _Box($hGUI, $aIds[$i]))
Next
GUIDelete($hGUI)
Sleep(300)

; --- Part B: GUIEventOptions set before the window exists -----------------------------------
_Say("")
_Say("=== Part B: Opt(""GUIEventOptions"", 1) before GUICreate ===")
Opt("GUIEventOptions", 1)
Local $hGUI2 = GUICreate("eventoptions", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $idLeft = GUICtrlCreateButton("left", 50, 40, 100, 30)
GUICtrlSetResizing($idLeft, $GUI_DOCKLEFT)
Local $idAuto = GUICtrlCreateButton("auto", 50, 40, 100, 30)
GUICtrlSetResizing($idAuto, $GUI_DOCKAUTO)
Local $idBorders = GUICtrlCreateButton("borders", 50, 40, 100, 30)
GUICtrlSetResizing($idBorders, $GUI_DOCKBORDERS)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(300)
_Say("at creation : " & _Sizes($hGUI2))
WinMove($hGUI2, "", Default, Default, 700, 500)
Sleep(400)
_Say("after resize: " & _Sizes($hGUI2))
_Say("  dock 2 (left)   -> " & _Box($hGUI2, $idLeft))
_Say("  dock 1 (auto)   -> " & _Box($hGUI2, $idAuto))
_Say("  dock 102 (borders) -> " & _Box($hGUI2, $idBorders))
GUIDelete($hGUI2)
Sleep(300)
Opt("GUIEventOptions", 0)

; --- Part C: the controls Part 2 left unclear: List, ListView, TreeView, MonthCal, Updown ----
_Say("")
_Say("=== Part C: List / ListView / TreeView / MonthCal defaults ===")
Local $hGUI3 = GUICreate("others", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $idList = GUICtrlCreateList("list", 50, 40, 100, 60)
Local $idListView = GUICtrlCreateListView("col", 50, 40, 100, 60)
Local $idTree = GUICtrlCreateTreeView(50, 40, 100, 60)
Local $idMonth = GUICtrlCreateMonthCal("2026/01/02", 50, 40, 100, 60)
Local $idSlider = GUICtrlCreateSlider(50, 40, 100, 60)
GUISetState(@SW_SHOW, $hGUI3)
Sleep(300)
_Say("at creation : " & _Sizes($hGUI3))
_Say("  List      -> " & _Box($hGUI3, $idList))
_Say("  ListView  -> " & _Box($hGUI3, $idListView))
_Say("  TreeView  -> " & _Box($hGUI3, $idTree))
_Say("  MonthCal  -> " & _Box($hGUI3, $idMonth))
_Say("  Slider    -> " & _Box($hGUI3, $idSlider))
WinMove($hGUI3, "", Default, Default, 700, 500)
Sleep(400)
_Say("after resize: " & _Sizes($hGUI3))
_Say("  List      -> " & _Box($hGUI3, $idList))
_Say("  ListView  -> " & _Box($hGUI3, $idListView))
_Say("  TreeView  -> " & _Box($hGUI3, $idTree))
_Say("  MonthCal  -> " & _Box($hGUI3, $idMonth))
_Say("  Slider    -> " & _Box($hGUI3, $idSlider))
GUIDelete($hGUI3)
