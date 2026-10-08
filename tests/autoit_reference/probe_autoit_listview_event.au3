; Which control event does a click deliver for a List and for a ListView?
;
; The port bound a List's selection event on the frame around the list box, so a List answered
; nothing at all; and its ListView path delivers the *item's* control ID rather than the
; ListView's. Both are questions about AutoIt's own behaviour, measured here with AutoIt's own
; MouseClick so nothing outside the script is needed.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_listview_event.au3
; Writes probe_autoit_listview_event_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_listview_event_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Global $gEvents = ""

Func _Note($sWho)
    $gEvents &= $sWho & "(@GUI_CtrlId=" & @GUI_CtrlId & ") "
EndFunc

Func _ListViewClicked()
    _Note("listview")
EndFunc

Func _ListItemOneClicked()
    _Note("item-one")
EndFunc

Func _ListItemTwoClicked()
    _Note("item-two")
EndFunc

Func _ListClicked()
    _Note("list")
EndFunc

Opt("GUIOnEventMode", 1)

Local $hGUI = GUICreate("listview events", 620, 320, 120, 120)
Local $idList = GUICtrlCreateList("", 20, 20, 240, 180)
GUICtrlSetData($idList, "alpha")
GUICtrlSetData($idList, "beta")
GUICtrlSetData($idList, "gamma")
Local $idView = GUICtrlCreateListView("col a|col b", 300, 20, 300, 180)
Local $idOne = GUICtrlCreateListViewItem("first|1", $idView)
Local $idTwo = GUICtrlCreateListViewItem("second|2", $idView)

GUICtrlSetOnEvent($idList, "_ListClicked")
GUICtrlSetOnEvent($idView, "_ListViewClicked")
GUICtrlSetOnEvent($idOne, "_ListItemOneClicked")
GUICtrlSetOnEvent($idTwo, "_ListItemTwoClicked")
GUISetOnEvent($GUI_EVENT_CLOSE, "_Close")

GUISetState(@SW_SHOW, $hGUI)
Sleep(600)

Func _Close()
    GUIDelete($hGUI)
EndFunc

Func _ClickIn($hControl, $iRow)
    ; Click inside a control's own screen rectangle, on the given row of it.
    Local $aPos = ControlGetPos($hGUI, "", $hControl)
    Local $aWin = WinGetPos($hGUI)
    If Not IsArray($aPos) Or Not IsArray($aWin) Then Return "no position"
    Local $iX = $aWin[0] + $aPos[0] + 30
    Local $iY = $aWin[1] + $aPos[1] + 12 + ($iRow * 16)
    WinActivate($hGUI)
    Sleep(200)
    MouseMove($iX, $iY, 0)
    Sleep(150)
    MouseClick("left", $iX, $iY, 1, 0)
    Sleep(300)
    Return $iX & "," & $iY
EndFunc

_Say("list box window class : " & _ClassName(GUICtrlGetHandle($idList)))
_Say("listview class        : " & _ClassName(GUICtrlGetHandle($idView)))
_Say("listview item ids     : item one=" & $idOne & " item two=" & $idTwo & " listview=" & $idView)

$gEvents = ""
_Say("click the List row 1  : at " & _ClickIn($idList, 1) & " -> " & $gEvents)
$gEvents = ""
_Say("click the List row 2  : at " & _ClickIn($idList, 2) & " -> " & $gEvents)
$gEvents = ""
_Say("click the ListView r1 : at " & _ClickIn($idView, 1) & " -> " & $gEvents)
$gEvents = ""
_Say("click the ListView r2 : at " & _ClickIn($idView, 2) & " -> " & $gEvents)

_Say("GUICtrlRead(list)     : " & GUICtrlRead($idList))
_Say("GUICtrlRead(listview) : " & GUICtrlRead($idView))

Func _ClassName($hWnd)
    Local $tBuffer = DllStructCreate("wchar[256]")
    DllCall("user32.dll", "int", "GetClassNameW", "hwnd", $hWnd, "ptr", DllStructGetPtr($tBuffer), "int", 256)
    Return DllStructGetData($tBuffer, 1)
EndFunc

GUIDelete($hGUI)
Exit
