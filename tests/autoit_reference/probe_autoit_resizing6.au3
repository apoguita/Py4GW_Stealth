; Does GUICtrlSetResizing(0) or (1024) mean "keep the control's own default"?
;
; A Button cannot tell them apart: its default is $GUI_DOCKSIZE and a flag-0 box is the same shape.
; A Label/Edit (default $GUI_DOCKAUTO) and an Input/Date (default $GUI_DOCKHEIGHT) can.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_resizing6.au3
; Writes probe_autoit_resizing6_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <DateTimeConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_resizing6_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

; Three columns: no GUICtrlSetResizing, 0, and 1024, on controls of the same kind.
Func _RunKind($sKind, $vSet)
    Local $hGUI = GUICreate($sKind, 400, 300, 100, 100, $WS_SIZEBOX + $WS_SYSMENU)
    Local $aIds[3]
    For $i = 0 To 2
        Switch $sKind
            Case "Label"
                $aIds[$i] = GUICtrlCreateLabel("label", 60, 45, 100, 30)
            Case "Edit"
                $aIds[$i] = GUICtrlCreateEdit("edit", 60, 45, 100, 30)
            Case "Input"
                $aIds[$i] = GUICtrlCreateInput("input", 60, 45, 100, 30)
            Case "Date"
                $aIds[$i] = GUICtrlCreateDate("2026/01/02", 60, 45, 100, 30)
            Case "Button"
                $aIds[$i] = GUICtrlCreateButton("button", 60, 45, 100, 30)
            Case "Pic"
                $aIds[$i] = GUICtrlCreatePic("", 60, 45, 100, 30)
            Case "ListView"
                $aIds[$i] = GUICtrlCreateListView("col", 60, 45, 100, 30)
        EndSwitch
    Next
    GUICtrlSetResizing($aIds[1], $vSet)
    GUICtrlSetResizing($aIds[2], 1024)
    GUISetState(@SW_SHOW, $hGUI)
    Sleep(300)
    Local $sBefore = _Box($hGUI, $aIds[0])
    WinMove($hGUI, "", Default, Default, 700, 500)
    Sleep(400)
    _Say(StringFormat("%-9s", $sKind) & " default=" & $sBefore & _
            "  [0]=" & _Box($hGUI, $aIds[1]) & "  [1024]=" & _Box($hGUI, $aIds[2]))
    GUIDelete($hGUI)
    Sleep(200)
EndFunc

_Say("creation box 60,45,100,30 in a 398x275 client; after a resize to a 684x461 client")
_Say("AUTO would be 103,75,171,50; DOCKSIZE/flag-0 would be 103,75,100,30; HEIGHT would be 103,75,171,30")
_Say("")
_Say("GUICtrlSetResizing(control, 0):")
For $i = 0 To 6
    Local $aKinds = ["Label", "Edit", "Input", "Date", "Button", "Pic", "ListView"]
    _RunKind($aKinds[$i], 0)
Next
