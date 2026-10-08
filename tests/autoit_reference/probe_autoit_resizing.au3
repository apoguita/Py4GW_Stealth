; What does AutoIt's automatic resizing do? Follow-up for GUICtrlSetResizing/GUIResizeMode.
;
; Part 1: one control per docking value, all created at the same place, then the window is resized
;         and each control's client-relative position and size is read again with ControlGetPos.
; Part 2: the same for a control of each type with no GUICtrlSetResizing call, which is the
;         "control dependent" default the page mentions.
; Part 3: Opt("GUIResizeMode", ...) as the default for controls made afterwards.
; Part 4: Opt("GUIEventOptions", 1), which the page says disables the automatic resizing event.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing.au3
; Writes probe_autoit_resizing_out.txt next to itself, a line at a time as it goes.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <ListviewConstants.au3>
#include <DateTimeConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

; "x,y,w,h" of a control, relative to the window's client area.
Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

; One window, a set of controls, a resize, and each control's box before and after.
Func _Run($sTitle, $aDocks, $iMode = -1, $iEventOptions = -1)
    Local $hGUI = GUICreate($sTitle, 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
    If $iMode >= 0 Then Opt("GUIResizeMode", $iMode)
    If $iEventOptions >= 0 Then Opt("GUIEventOptions", $iEventOptions)
    Local $aIds[UBound($aDocks)]
    For $i = 0 To UBound($aDocks) - 1
        $aIds[$i] = GUICtrlCreateButton("c" & $i, 50, 40, 100, 30)
        If $aDocks[$i] <> -1 Then GUICtrlSetResizing($aIds[$i], $aDocks[$i])
    Next
    GUISetState(@SW_SHOW, $hGUI)
    Sleep(250)
    Local $sBefore = ""
    For $i = 0 To UBound($aDocks) - 1
        $sBefore &= "[" & $aDocks[$i] & ":" & _Box($hGUI, $aIds[$i]) & "] "
    Next
    _Say($sTitle & " 400x300 -> " & $sBefore)
    WinMove($hGUI, "", Default, Default, 700, 500)
    Sleep(400)
    Local $aClient = WinGetClientSize($hGUI)
    Local $sAfter = ""
    For $i = 0 To UBound($aDocks) - 1
        $sAfter &= "[" & $aDocks[$i] & ":" & _Box($hGUI, $aIds[$i]) & "] "
    Next
    _Say("  after " & $aClient[0] & "x" & $aClient[1] & " -> " & $sAfter)
    _Say("")
    GUIDelete($hGUI)
    Sleep(200)
    If $iMode >= 0 Then Opt("GUIResizeMode", 0)
    If $iEventOptions >= 0 Then Opt("GUIEventOptions", 0)
EndFunc

_Say("=== Part 1: one button per docking value, 400x300 -> 700x500 ===")
_Say("window style: $WS_SIZEBOX + $WS_SYSMENU; each control at 50,40 100x30")
_Say("")
Local $aDocks = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 768, 544, 576, 802, 102]
_Run("docks", $aDocks)

_Say("=== Part 2: the default resizing of each control type (no GUICtrlSetResizing) ===")
Local $hGUI = GUICreate("defaults", 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
Local $aKinds[16][2]
$aKinds[0][0] = "Label"
$aKinds[1][0] = "Button"
$aKinds[2][0] = "Input"
$aKinds[3][0] = "Edit"
$aKinds[4][0] = "Checkbox"
$aKinds[5][0] = "Radio"
$aKinds[6][0] = "Combo"
$aKinds[7][0] = "List"
$aKinds[8][0] = "Progress"
$aKinds[9][0] = "Slider"
$aKinds[10][0] = "Group"
$aKinds[11][0] = "Pic"
$aKinds[12][0] = "Tab"
$aKinds[13][0] = "ListView"
$aKinds[14][0] = "TreeView"
$aKinds[15][0] = "Date"
For $i = 0 To UBound($aKinds) - 1
    Switch $aKinds[$i][0]
        Case "Label"
            $aKinds[$i][1] = GUICtrlCreateLabel("label", 50, 40, 100, 30)
        Case "Button"
            $aKinds[$i][1] = GUICtrlCreateButton("button", 50, 40, 100, 30)
        Case "Input"
            $aKinds[$i][1] = GUICtrlCreateInput("input", 50, 40, 100, 30)
        Case "Edit"
            $aKinds[$i][1] = GUICtrlCreateEdit("edit", 50, 40, 100, 30)
        Case "Checkbox"
            $aKinds[$i][1] = GUICtrlCreateCheckbox("check", 50, 40, 100, 30)
        Case "Radio"
            $aKinds[$i][1] = GUICtrlCreateRadio("radio", 50, 40, 100, 30)
        Case "Combo"
            $aKinds[$i][1] = GUICtrlCreateCombo("combo", 50, 40, 100, 30)
        Case "List"
            $aKinds[$i][1] = GUICtrlCreateList("list", 50, 40, 100, 30)
        Case "Progress"
            $aKinds[$i][1] = GUICtrlCreateProgress(50, 40, 100, 30)
        Case "Slider"
            $aKinds[$i][1] = GUICtrlCreateSlider(50, 40, 100, 30)
        Case "Group"
            $aKinds[$i][1] = GUICtrlCreateGroup("group", 50, 40, 100, 30)
        Case "Pic"
            $aKinds[$i][1] = GUICtrlCreatePic("", 50, 40, 100, 30)
        Case "Tab"
            $aKinds[$i][1] = GUICtrlCreateTab(50, 40, 100, 30)
        Case "ListView"
            $aKinds[$i][1] = GUICtrlCreateListView("col", 50, 40, 100, 30)
        Case "TreeView"
            $aKinds[$i][1] = GUICtrlCreateTreeView(50, 40, 100, 30)
        Case "Date"
            $aKinds[$i][1] = GUICtrlCreateDate("2026/01/02", 50, 40, 100, 30)
    EndSwitch
Next
GUISetState(@SW_SHOW, $hGUI)
Sleep(250)
For $i = 0 To UBound($aKinds) - 1
    _Say($aKinds[$i][0] & " before " & _Box($hGUI, $aKinds[$i][1]))
Next
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(400)
Local $aClient = WinGetClientSize($hGUI)
_Say("after " & $aClient[0] & "x" & $aClient[1] & ":")
For $i = 0 To UBound($aKinds) - 1
    _Say("  " & $aKinds[$i][0] & " " & _Box($hGUI, $aKinds[$i][1]))
Next
GUIDelete($hGUI)
Sleep(300)

_Say("")
_Say("=== Part 3: Opt(""GUIResizeMode"", $GUI_DOCKALL) as the default ===")
Local $aNoSet = [-1, -1]
_Run("resizemode", $aNoSet, $GUI_DOCKALL)

_Say("=== Part 4: Opt(""GUIEventOptions"", 1) ===")
Local $aMixed = [2, 1, 802]
_Run("eventoptions", $aMixed, -1, 1)
