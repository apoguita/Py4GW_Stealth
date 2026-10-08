; The docking matrix, for comparison against the port's own output.
;
; Prints one line per docking value: "flag=l,t,w,h" after a resize from a 398x275 client to a
; 684x461 client, then after a resize back to a 484x361 client. A second part does the same for a
; control of each type with no GUICtrlSetResizing at all (its default resizing), and a third for a
; box that is not a round number.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing9.au3
; Writes probe_autoit_resizing9_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <ListviewConstants.au3>
#include <DateTimeConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing9_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

; --- Part 1: the docking values --------------------------------------------------------------
Local $aFlags = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 768, 802, 102, 544, 576, 34, 514, _
        257, 264, 640, 68, 260, 9, 129, 1024, 1040, 2048, 803, 818, 900, 1023, 1826, 819, 358, _
        870, 12, 300, 44, 6, 20, 96, 160, 192, 18, 24, 48, 272, 5120, 4096]

Local $hGUI = GUICreate("matrix", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aIds[UBound($aFlags)]
For $i = 0 To UBound($aFlags) - 1
    $aIds[$i] = GUICtrlCreateButton("c" & $i, 60, 45, 100, 30)
    GUICtrlSetResizing($aIds[$i], $aFlags[$i])
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(300)
Local $aClient = WinGetClientSize($hGUI)
_Say("client " & $aClient[0] & "x" & $aClient[1] & " (creation)")
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
Local $aA = WinGetClientSize($hGUI)
_Say("grow to client " & $aA[0] & "x" & $aA[1])
For $i = 0 To UBound($aFlags) - 1
    _Say($aFlags[$i] & "=" & _Box($hGUI, $aIds[$i]))
Next
WinMove($hGUI, "", Default, Default, 500, 400)
Sleep(400)
Local $aB = WinGetClientSize($hGUI)
_Say("shrink to client " & $aB[0] & "x" & $aB[1])
For $i = 0 To UBound($aFlags) - 1
    _Say($aFlags[$i] & "=" & _Box($hGUI, $aIds[$i]))
Next
GUIDelete($hGUI)
Sleep(300)

; --- Part 2: each control type's own default resizing ----------------------------------------
_Say("")
_Say("part2")
Local $aKinds = ["Label", "Button", "Input", "Edit", "Checkbox", "Radio", "Combo", "List", _
        "Progress", "Slider", "Group", "Pic", "Tab", "ListView", "TreeView", "Date", "MonthCal", _
        "Avi", "Icon", "Graphic", "Updown"]
Local $hGUI2 = GUICreate("defaults", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aKindsIds[UBound($aKinds)]
For $i = 0 To UBound($aKinds) - 1
    Switch $aKinds[$i]
        Case "Label"
            $aKindsIds[$i] = GUICtrlCreateLabel("label", 60, 45, 100, 30)
        Case "Button"
            $aKindsIds[$i] = GUICtrlCreateButton("button", 60, 45, 100, 30)
        Case "Input"
            $aKindsIds[$i] = GUICtrlCreateInput("input", 60, 45, 100, 30)
        Case "Edit"
            $aKindsIds[$i] = GUICtrlCreateEdit("edit", 60, 45, 100, 30)
        Case "Checkbox"
            $aKindsIds[$i] = GUICtrlCreateCheckbox("check", 60, 45, 100, 30)
        Case "Radio"
            $aKindsIds[$i] = GUICtrlCreateRadio("radio", 60, 45, 100, 30)
        Case "Combo"
            $aKindsIds[$i] = GUICtrlCreateCombo("combo", 60, 45, 100, 30)
        Case "List"
            $aKindsIds[$i] = GUICtrlCreateList("list", 60, 45, 100, 30)
        Case "Progress"
            $aKindsIds[$i] = GUICtrlCreateProgress(60, 45, 100, 30)
        Case "Slider"
            $aKindsIds[$i] = GUICtrlCreateSlider(60, 45, 100, 30)
        Case "Group"
            $aKindsIds[$i] = GUICtrlCreateGroup("group", 60, 45, 100, 30)
        Case "Pic"
            $aKindsIds[$i] = GUICtrlCreatePic("", 60, 45, 100, 30)
        Case "Tab"
            $aKindsIds[$i] = GUICtrlCreateTab(60, 45, 100, 30)
        Case "ListView"
            $aKindsIds[$i] = GUICtrlCreateListView("col", 60, 45, 100, 30)
        Case "TreeView"
            $aKindsIds[$i] = GUICtrlCreateTreeView(60, 45, 100, 30)
        Case "Date"
            $aKindsIds[$i] = GUICtrlCreateDate("2026/01/02", 60, 45, 100, 30)
        Case "MonthCal"
            $aKindsIds[$i] = GUICtrlCreateMonthCal("2026/01/02", 60, 45, 100, 30)
        Case "Avi"
            $aKindsIds[$i] = GUICtrlCreateAvi(@ScriptDir & "\..\..\..\does-not-exist.avi", 0, 60, 45, 100, 30)
        Case "Icon"
            $aKindsIds[$i] = GUICtrlCreateIcon("shell32.dll", -1, 60, 45, 100, 30)
        Case "Graphic"
            $aKindsIds[$i] = GUICtrlCreateGraphic(60, 45, 100, 30)
        Case "Updown"
            Local $hBuddy = GUICtrlCreateInput("0", 60, 45, 100, 30)
            $aKindsIds[$i] = GUICtrlCreateUpdown($hBuddy)
    EndSwitch
Next
GUISetState(@SW_SHOW, $hGUI2)
Sleep(300)
WinMove($hGUI2, "", Default, Default, 700, 500)
Sleep(400)
_Say("part2 client " & (WinGetClientSize($hGUI2))[0] & "x" & (WinGetClientSize($hGUI2))[1])
For $i = 0 To UBound($aKinds) - 1
    _Say($aKinds[$i] & "=" & _Box($hGUI2, $aKindsIds[$i]))
Next
GUIDelete($hGUI2)
Sleep(300)

; --- Part 3: a box that is not a round number, and a pinned centre ---------------------------
_Say("")
_Say("part3")
Local $hGUI3 = GUICreate("odd", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aOdd = [0, 1, 2, 4, 8, 32, 64, 128, 256, 512, 802, 102, 264, 640, 257, 514]
Local $aOddIds[UBound($aOdd)]
For $i = 0 To UBound($aOdd) - 1
    $aOddIds[$i] = GUICtrlCreateButton("o" & $i, 61, 46, 101, 31)
    GUICtrlSetResizing($aOddIds[$i], $aOdd[$i])
Next
GUISetState(@SW_SHOW, $hGUI3)
Sleep(300)
WinMove($hGUI3, "", Default, Default, 699, 499)
Sleep(400)
Local $aC = WinGetClientSize($hGUI3)
_Say("part3 client " & $aC[0] & "x" & $aC[1] & " from a 398x275 client, box 61,46,101,31")
For $i = 0 To UBound($aOdd) - 1
    _Say($aOdd[$i] & "=" & _Box($hGUI3, $aOddIds[$i]))
Next
GUIDelete($hGUI3)
