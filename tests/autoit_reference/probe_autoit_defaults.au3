; Are a control's default width and height computed from its text, or fixed for the type?
;
; probe_autoit_behavior.au3 read one size per type with one piece of text in each. This creates two
; of every type, with short and long text (or content), so the answer decides whether a control
; created with no width or height is autofit or a fixed size.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_defaults.au3
; Writes probe_autoit_defaults_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <ListviewConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_defaults_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Size($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[2] & "x" & $aPos[3]
EndFunc

; Each control is created in a window of its own, so nothing it inherits comes from another control.
Func _Pair($sKind, $sShort, $sLong)
    Local $hGUI = GUICreate("defaults " & $sKind, 600, 400, 100, 100)
    Local $idShort = _Make($sKind, $sShort, 10, 10)
    Local $idLong = _Make($sKind, $sLong, 10, 200)
    GUISetState(@SW_SHOW, $hGUI)
    Sleep(150)
    Local $sShortSize = _Size($hGUI, $idShort)
    Local $sLongSize = _Size($hGUI, $idLong)
    _Say(StringFormat("%-10s short=%-9s long=%-9s", $sKind, $sShortSize, $sLongSize))
    GUIDelete($hGUI)
    Sleep(80)
EndFunc

Func _Make($sKind, $sText, $iLeft, $iTop)
    Switch $sKind
        Case "Button"
            Return GUICtrlCreateButton($sText, $iLeft, $iTop)
        Case "Label"
            Return GUICtrlCreateLabel($sText, $iLeft, $iTop)
        Case "Input"
            Return GUICtrlCreateInput($sText, $iLeft, $iTop)
        Case "Edit"
            Return GUICtrlCreateEdit($sText, $iLeft, $iTop)
        Case "Checkbox"
            Return GUICtrlCreateCheckbox($sText, $iLeft, $iTop)
        Case "Radio"
            Return GUICtrlCreateRadio($sText, $iLeft, $iTop)
        Case "Combo"
            Return GUICtrlCreateCombo($sText, $iLeft, $iTop)
        Case "List"
            Return GUICtrlCreateList($sText, $iLeft, $iTop)
        Case "Progress"
            Return GUICtrlCreateProgress($iLeft, $iTop)
        Case "Slider"
            Return GUICtrlCreateSlider($iLeft, $iTop)
        Case "Tab"
            Return GUICtrlCreateTab($iLeft, $iTop)
        Case "TreeView"
            Return GUICtrlCreateTreeView($iLeft, $iTop)
        Case "ListView"
            Return GUICtrlCreateListView($sText, $iLeft, $iTop)
        Case "Date"
            Return GUICtrlCreateDate($sText, $iLeft, $iTop)
        Case "MonthCal"
            Return GUICtrlCreateMonthCal($sText, $iLeft, $iTop)
        Case "Group"
            Return GUICtrlCreateGroup($sText, $iLeft, $iTop)
        Case "Pic"
            Return GUICtrlCreatePic("", $iLeft, $iTop)
        Case "Graphic"
            Return GUICtrlCreateGraphic($iLeft, $iTop)
    EndSwitch
    Return 0
EndFunc

_Say("each control created with no width or height, short text vs long text")
_Pair("Button", "OK", "A much longer button caption")
_Pair("Label", "Hi", "A much longer label caption here")
_Pair("Input", "", "123456789012345678901234567890")
_Pair("Edit", "", "line one" & @CRLF & "line two" & @CRLF & "line three")
_Pair("Checkbox", "x", "A much longer checkbox caption")
_Pair("Radio", "x", "A much longer radio caption")
_Pair("Combo", "", "123456789012345678901234567890")
_Pair("List", "", "123456789012345678901234567890")
_Pair("Progress", "", "")
_Pair("Slider", "", "")
_Pair("Tab", "", "")
_Pair("TreeView", "", "")
_Pair("ListView", "A", "Column A|Column B|Column C")
_Pair("Date", "2026/01/02", "2026/01/02")
_Pair("MonthCal", "2026/01/02", "2026/01/02")
_Pair("Group", "g", "A much longer group caption")
_Pair("Pic", "", "")
_Pair("Graphic", "", "")
